"""Estudios cancelables con reclamación atómica y publicación por SHA-256."""

import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path

from sqlalchemy import and_, or_, update
from sqlmodel import Session

from trazia.store import EventRecord, JobRecord, Store


async def start_study(config_path: Path, output: Path):
    return await asyncio.create_subprocess_exec(
        sys.executable,
        "-u",
        "-m",
        "trazia.api.study_worker",
        str(config_path),
        str(output),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        **({"creationflags": 0x08000000} if sys.platform == "win32" else {}),
    )


async def run_study_job(store: Store, job_id: str):
    from .jobs import JobCancelled, emit

    now = time.time()
    with Session(store.engine) as session:
        job = session.get(JobRecord, job_id)
        if (
            not job
            or job.cancel_requested
            or job.status in {"done", "error", "timeout", "cancelled"}
        ):
            return None
        config = json.loads(job.request_json)
        if job.status == "running" and job.lease_until and job.lease_until > now:
            return job.lease_until - now
        claimed = session.exec(
            update(JobRecord)
            .where(
                JobRecord.id == job_id,
                JobRecord.cancel_requested.is_(False),
                or_(
                    JobRecord.status == "queued",
                    and_(
                        JobRecord.status == "running",
                        or_(JobRecord.lease_until.is_(None), JobRecord.lease_until <= now),
                    ),
                ),
            )
            .values(
                status="running",
                attempts=JobRecord.attempts + 1,
                updated_at=now,
                lease_until=now + config["timeout_seconds"] + 30,
            )
        )
        if claimed.rowcount != 1:
            return 0.1
        session.commit()

    started, process = time.perf_counter(), None
    temporary = tempfile.TemporaryDirectory(prefix="study-", dir=store.root)
    status, error, digest = "error", None, None
    try:
        folder = temporary.name
        config_path, output = Path(folder) / "config.json", Path(folder) / "estudio.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        async with asyncio.timeout(config["timeout_seconds"]):
            emit(store, job_id, "estudio", "ok", "", "Inicia el estudio comparativo")
            process = await start_study(config_path, output)
            # Lecturas acotadas: los logs de un arnés no pueden llenar la memoria del API.
            tail = ""
            while chunk := await process.stdout.read(4096):
                text = chunk.decode("utf-8", errors="replace")
                tail = (tail + text)[-4000:]
                emit(store, job_id, "estudio", "ok", "", text[:4000])
            code = await process.wait()
            if code:
                raise ValueError(tail.strip() or f"El estudio terminó con código {code}")
            result = json.loads(output.read_text(encoding="utf-8"))
            if not result.get("variants"):
                raise ValueError("El estudio no contiene variantes medidas")
            # El blob puede existir sin publicarse si se cancela justo al finalizar.
            digest = store.put(json.dumps(result, ensure_ascii=False).encode())
            status = "done"
    except asyncio.CancelledError:
        status = "queued"
        raise
    except TimeoutError:
        status, error = "timeout", "Tiempo máximo del estudio agotado"
    except JobCancelled:
        status = "cancelled"
    except Exception as failure:
        error = str(failure)[-4000:]
    finally:
        # Terminar antes de borrar sus temporales, también en Windows.
        if process is not None and process.returncode is None:
            process.kill()
            await process.wait()
        temporary.cleanup()
        with Session(store.engine) as session:
            job = session.get(JobRecord, job_id)
            if job.cancel_requested or job.status == "cancelled":
                status, digest = "cancelled", None
            job.status, job.error = status, error
            job.updated_at, job.lease_until = time.time(), None
            job.result_sha256 = digest if status == "done" else None
            # El arnés publica métricas por variante, no un RunInfo agregado completo.
            job.elapsed_seconds = time.perf_counter() - started
            job.run_json = None
            session.add(job)
            session.add(
                EventRecord(
                    job_id=job_id,
                    stage="job",
                    status="ok" if status == "done" else "error",
                    file="",
                    detail="Estudio publicado" if status == "done" else error or status,
                )
            )
            session.commit()
    return None
