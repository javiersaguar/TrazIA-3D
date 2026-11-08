"""Trabajos CPU para planos GA nuevos, vinculados al IFC y a una revisión inmutable."""

import asyncio
import json
import time
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import Response
from pydantic import Field
from sqlalchemy import update
from sqlmodel import Session, select

from trazia.model import Model, Revision
from trazia.store import JobRecord, RevisionArtifactRecord, RevisionRecord

from .repository import check_match, get_revision

router = APIRouter()
KINDS = {
    "pdf": ("ga_pdf", "application/pdf"),
    "svg": ("ga_svg", "image/svg+xml"),
    "manifest": ("ga_manifest", "application/json"),
    "ifc": ("ga_ifc", "application/x-step"),
}


class DrawingInput(Model):
    scale: int | None = Field(default=None, ge=1, le=10000)


@router.post("/revisions/{identity}/ga-drawings", status_code=202)
async def create_drawing(
    request: Request,
    identity: str,
    body: DrawingInput,
    if_match: str | None = Header(None),
    idempotency_key: str | None = Header(None),
):
    from .change_proposals import reply, require_key

    def action(session):
        row = get_revision(session, identity)
        check_match(row, if_match)
        model = Revision.model_validate_json(row.payload)
        job = JobRecord(
            id=str(uuid4()),
            tag=row.tag,
            kind="ga_drawing",
            request_json=json.dumps(
                {
                    "revision_id": row.id,
                    "version": row.version,
                    "input_sha256": model.fingerprint(),
                    "scale": body.scale,
                }
            ),
        )
        session.add(job)
        return {
            "status": 202,
            "data": {"job_id": job.id, "revision_id": row.id, "status": "queued"},
        }

    result = request.app.state.store.perform(
        f"POST ga/{identity}",
        require_key(idempotency_key),
        {**body.model_dump(), "if_match": if_match},
        action,
    )
    await request.app.state.queue.enqueue(result["data"]["job_id"])
    return reply(result)


@router.get("/revisions/{identity}/ga-drawings")
def drawings(request: Request, identity: str):
    with Session(request.app.state.store.engine) as session:
        row = get_revision(session, identity)
        fingerprint = Revision.model_validate_json(row.payload).fingerprint()
        rows = session.exec(
            select(RevisionArtifactRecord)
            .where(
                RevisionArtifactRecord.revision_id == row.id,
                RevisionArtifactRecord.input_sha256 == fingerprint,
            )
            .order_by(RevisionArtifactRecord.id.desc())
        ).all()
        result = {}
        for item in rows:
            for extension, (kind, _) in KINDS.items():
                if item.kind == kind and extension not in result:
                    result[extension] = {
                        "sha256": item.sha256,
                        "url": f"/revisions/{row.id}/ga-drawings/{extension}?sha={item.sha256}",
                    }
        return {"revision_id": row.id, "input_sha256": fingerprint, "files": result, "draft": True}


@router.get("/revisions/{identity}/ga-drawings/{extension}")
def drawing_file(request: Request, identity: str, extension: str, sha: str):
    if extension not in KINDS:
        raise HTTPException(404, "Formato de plano desconocido")
    with Session(request.app.state.store.engine) as session:
        row = get_revision(session, identity)
        kind, media = KINDS[extension]
        artifact = session.exec(
            select(RevisionArtifactRecord).where(
                RevisionArtifactRecord.revision_id == row.id,
                RevisionArtifactRecord.kind == kind,
                RevisionArtifactRecord.sha256 == sha,
            )
        ).first()
        if artifact is None:
            raise HTTPException(404, "No existe ese artefacto de plano")
        data = request.app.state.store.read(artifact.sha256)
    suffix = "json" if extension == "manifest" else extension
    return Response(
        data,
        media_type=media,
        headers={
            "Content-Disposition": f'attachment; filename="GA_NUEVO_DERIVADO_DRAFT.{suffix}"',
            "X-Derived-Document": "true",
            "X-Content-SHA256": sha,
        },
    )


def build_drawing(store, job_id, config):
    from trazia.design.drawing import generate_ga
    from trazia.ifc import build_ifc, validate_ifc

    from .change_proposals import published_ifc
    from .jobs import emit

    with Session(store.engine) as session:
        row = get_revision(session, config["revision_id"])
        model = Revision.model_validate_json(row.payload)
        if row.version != config["version"] or model.fingerprint() != config["input_sha256"]:
            raise ValueError("La revisión cambió antes de generar el plano")
        published = published_ifc(session, row, model)
    if published:
        content = store.read(published)
    else:
        ifc = build_ifc(model, draft=True, details=model.dataset == "synthetic")
        errors = validate_ifc(ifc)
        if errors:
            raise ValueError("IFC inválido: " + errors[0]["message"])
        content = ifc.to_string().encode()
    emit(store, job_id, "ifc", "ok", "", "Paso 1/2 · geometría IFC verificada")
    result = generate_ga(content, model, scale=config.get("scale"))
    result["manifest"]["revision_id"] = config["revision_id"]
    result["manifest"]["base_version"] = config["version"]
    emit(store, job_id, "drawing", "ok", "", "Paso 2/2 · tres vistas, cotas y cajetín generados")
    return {
        "pdf": result["pdf"],
        "svg": result["svg"],
        "manifest": json.dumps(result["manifest"], ensure_ascii=False, sort_keys=True).encode(),
        "ifc": content,
    }


async def run_drawing_job(store, job_id):
    started = time.perf_counter()
    with Session(store.engine) as session:
        job = session.get(JobRecord, job_id)
        if (
            not job
            or job.status in {"done", "error", "timeout", "cancelled"}
            or job.cancel_requested
        ):
            return None
        if job.status == "running" and job.lease_until and job.lease_until > time.time():
            return job.lease_until - time.time()
        claimed = session.exec(
            update(JobRecord)
            .where(
                JobRecord.id == job_id,
                JobRecord.status == job.status,
                JobRecord.lease_until == job.lease_until,
                JobRecord.cancel_requested.is_(False),
            )
            .values(
                status="running", lease_until=time.time() + 270, attempts=JobRecord.attempts + 1
            )
        )
        if claimed.rowcount != 1:
            return 0.1
        config = json.loads(job.request_json)
        session.commit()
    status, error = "error", None
    try:
        async with asyncio.timeout(240):
            blobs = await asyncio.to_thread(build_drawing, store, job_id, config)
        hashes = {key: store.put(value) for key, value in blobs.items()}
        with Session(store.engine) as session:
            job = session.get(JobRecord, job_id)
            if job.cancel_requested or job.status != "running":
                raise ValueError("Generación cancelada; no se publica el plano")
            locked = session.exec(
                update(JobRecord)
                .where(
                    JobRecord.id == job_id,
                    JobRecord.status == "running",
                    JobRecord.cancel_requested.is_(False),
                )
                .values(status="done")
            )
            if locked.rowcount != 1:
                raise ValueError("Trabajo cancelado; no se publica el resultado")
            job.status = "done"
            guard = session.exec(
                update(RevisionRecord)
                .where(
                    RevisionRecord.id == config["revision_id"],
                    RevisionRecord.version == config["version"],
                )
                .values(version=RevisionRecord.version)
            )
            if guard.rowcount != 1:
                raise ValueError(
                    "La revisión cambió durante la generación; vuelve a generar el plano"
                )
            for key, sha in hashes.items():
                kind, media = KINDS[key]
                session.add(
                    RevisionArtifactRecord(
                        revision_id=config["revision_id"],
                        kind=kind,
                        sha256=sha,
                        media_type=media,
                        input_sha256=config["input_sha256"],
                        generator_version="ga-ifc-1",
                    )
                )
            job.result_sha256 = hashes["manifest"]
            session.add(job)
            session.commit()
        status = "done"
    except asyncio.CancelledError:
        status = "queued"
        raise
    except TimeoutError:
        status, error = "timeout", "Tiempo de generación agotado"
    except Exception as failure:
        error = str(failure)[-4000:]
    finally:
        with Session(store.engine) as session:
            job = session.get(JobRecord, job_id)
            if job.cancel_requested or job.status == "cancelled":
                status = "cancelled"
            job.status, job.error = status, error
            job.lease_until = None
            job.elapsed_seconds = time.perf_counter() - started
            session.add(job)
            session.commit()
        # El endpoint SSE usa el estado terminal persistido incluso sin evento final.
    return None
