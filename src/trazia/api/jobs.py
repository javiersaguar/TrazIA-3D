import asyncio
import json
import logging
import time

import httpx
from sqlalchemy import and_, or_, update
from sqlmodel import Session, select

from trazia.ifc import build_ifc, validate_ifc
from trazia.model import Revision, RunInfo
from trazia.queue.accounting import Accounting
from trazia.store import DocumentRecord, EventRecord, JobRecord, RevisionRecord, Store

from .pipeline_adapter import InputDocument, process
from .repository import revision_id

logger = logging.getLogger("trazia.jobs")
TERMINAL = {"done", "error", "cancelled", "timeout"}


class JobCancelled(RuntimeError):
    pass


class TransientPipelineFailure(RuntimeError):
    def __init__(self, detail, run):
        super().__init__(detail)
        self.run = run


def emit(store: Store, job_id: str, stage: str, status: str, file: str, detail: str):
    with Session(store.engine) as session:
        job = session.get(JobRecord, job_id)
        if job is None or job.cancel_requested or job.status != "running":
            raise JobCancelled("El trabajo ya no está activo")
        session.add(
            EventRecord(job_id=job_id, stage=stage, status=status, file=file, detail=detail[:4000])
        )
        session.commit()
    logger.info(
        json.dumps({"job_id": job_id, "stage": stage, "status": status}, ensure_ascii=False)
    )


def execute_pipeline(store: Store, job_id: str, request: dict):
    documents = []
    with Session(store.engine) as session:
        for identity in request["documents"]:
            document = session.get(DocumentRecord, identity)
            if document is None:
                raise ValueError("Ha desaparecido un documento del trabajo")
            documents.append(
                InputDocument(
                    document.filename,
                    store.read(document.sha256),
                    document.document_id,
                    document.revision,
                )
            )
        previous = None
        if request.get("previous_id"):
            record = session.get(RevisionRecord, request["previous_id"])
            if record:
                previous = Revision.model_validate_json(record.payload)

    def event(value):
        emit(store, job_id, value.stage, value.status, value.file, value.detail)

    result = process(
        documents,
        project_id=request["project_id"],
        equipment_id=request["equipment_id"],
        revision=request["revision"],
        strategy=request["strategy"],
        previous=previous,
        providers=request["providers"],
        dataset=request["dataset"],
        on_event=event,
    )
    if result.error and getattr(result, "retryable", False):
        raise TransientPipelineFailure(result.error, result.run)
    if result.error or result.revision is None:
        return result, None
    revision = Revision.model_validate_json(result.revision.model_dump_json())
    revision.approval = None
    revision.run = result.run
    expected = (
        request["project_id"],
        request["equipment_id"],
        request["revision"],
        request["dataset"],
    )
    actual = (revision.project_id, revision.equipment.id, revision.revision, revision.dataset)
    if expected != actual or revision.equipment.tag.value != request.get(
        "tag", revision.equipment.tag.value
    ):
        raise ValueError("La salida de Lectura no coincide con los identificadores del trabajo")
    emit(
        store,
        job_id,
        "family",
        "ok",
        "",
        f"{revision.equipment.kind}, nivel {revision.equipment.lod}",
    )
    model = build_ifc(revision, draft=True)
    issues = validate_ifc(model)
    if issues:
        raise ValueError("IFC inválido: " + issues[0]["message"][:1000])
    digest = store.put(model.to_string().encode())
    emit(store, job_id, "ifc", "ok", "", f"IFC4 DRAFT almacenado: {digest[:12]}")
    emit(store, job_id, "validate", "ok", "", "Contrato 0.3 y validación IFC/EXPRESS correctos")
    return result, revision


async def run_job(store: Store, job_id: str):
    started = time.perf_counter()
    now = time.time()
    with Session(store.engine) as session:
        job = session.get(JobRecord, job_id)
        if job is None or job.status in TERMINAL or job.cancel_requested:
            return None
        if job.status == "running" and job.lease_until and job.lease_until > now:
            return job.lease_until - now
        request = json.loads(job.request_json)
        maximum = request.get("max_attempts", 3)
        previous_attempts = job.attempts
        accounting = Accounting(request["strategy"])
        if previous_attempts:
            accounting.add(RunInfo.model_validate_json(job.run_json) if job.run_json else None)
        if previous_attempts >= maximum:
            job.status, job.error, job.lease_until = "error", "Límite de intentos agotado", None
            session.add(job)
            session.commit()
            return None
        claim = session.exec(
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
                attempts=previous_attempts + 1,
                updated_at=now,
                lease_until=now + request.get("timeout_seconds", 300) + 30,
            )
        )
        if claim.rowcount != 1:
            return 0.1
        session.commit()
    in_flight = False
    try:
        async with asyncio.timeout(request.get("timeout_seconds", 300)):
            for attempt in range(maximum - previous_attempts):
                if attempt:
                    with Session(store.engine) as session:
                        job = session.get(JobRecord, job_id)
                        if job.cancel_requested or job.status != "running":
                            raise JobCancelled("Trabajo cancelado")
                        job.attempts += 1
                        session.add(job)
                        session.commit()
                in_flight = True
                try:
                    result, revision = await asyncio.to_thread(
                        execute_pipeline, store, job_id, request
                    )
                except (ConnectionError, httpx.TransportError, TransientPipelineFailure) as error:
                    in_flight = False
                    accounting.add(
                        error.run if isinstance(error, TransientPipelineFailure) else None
                    )
                    if attempt + previous_attempts + 1 >= maximum:
                        raise
                    delay = min(30, request.get("retry_backoff_seconds", 1) * 2**attempt)
                    emit(
                        store,
                        job_id,
                        "job",
                        "omitido",
                        "",
                        f"Fallo transitorio; reintento en {delay:g} s",
                    )
                    await asyncio.sleep(delay)
                else:
                    in_flight = False
                    accounting.add(result.run)
                    break
        with Session(store.engine) as session:
            job = session.get(JobRecord, job_id)
            if job.cancel_requested or job.status != "running":
                return None
            job.run_json = accounting.finish(time.perf_counter() - started).model_dump_json()
            job.warnings_json = json.dumps(result.warnings, ensure_ascii=False)
            job.updated_at, job.lease_until = time.time(), None
            if revision:
                identity = revision_id(revision)
                if session.get(RevisionRecord, identity):
                    raise ValueError("La revisión de destino ya existe; no se sobrescribe")
                session.add(
                    RevisionRecord(
                        id=identity,
                        project_id=revision.project_id,
                        equipment_id=revision.equipment.id,
                        tag=revision.equipment.tag.value,
                        revision=revision.revision,
                        payload=revision.model_dump_json(),
                    )
                )
                job.revision_id, job.status = identity, "done"
            else:
                job.status, job.error = "error", result.error or "Lectura no produjo una revisión"
            session.add(job)
            session.add(
                EventRecord(
                    job_id=job_id,
                    stage="job",
                    status="ok" if revision else "error",
                    file="",
                    detail="Trabajo terminado" if revision else job.error,
                )
            )
            session.commit()
    except asyncio.CancelledError:
        if in_flight:
            accounting.add(None)
        with Session(store.engine) as session:
            job = session.get(JobRecord, job_id)
            job.status = "cancelled" if job.cancel_requested else "queued"
            job.updated_at, job.lease_until = time.time(), None
            job.run_json = accounting.finish(time.perf_counter() - started).model_dump_json()
            session.add(job)
            session.commit()
        raise
    except Exception as error:
        if in_flight:
            accounting.add(None)
        with Session(store.engine) as session:
            job = session.get(JobRecord, job_id)
            job.status = (
                "cancelled"
                if job.cancel_requested
                else ("timeout" if isinstance(error, TimeoutError) else "error")
            )
            job.error = "Tiempo máximo agotado" if isinstance(error, TimeoutError) else str(error)
            job.updated_at, job.lease_until = time.time(), None
            job.run_json = accounting.finish(time.perf_counter() - started).model_dump_json()
            session.add(job)
            session.add(
                EventRecord(
                    job_id=job_id, stage="job", status="error", file="", detail=job.error[:4000]
                )
            )
            session.commit()
    return None


async def recover_jobs(store: Store, queue):
    with Session(store.engine) as session:
        jobs = session.exec(
            select(JobRecord).where(JobRecord.status.in_(["queued", "running"]))
        ).all()
        identities = []
        for job in jobs:
            if job.cancel_requested:
                job.status, job.lease_until = "cancelled", None
                session.add(job)
            else:
                identities.append(job.id)
        session.commit()
    for identity in identities:
        await queue.enqueue(identity)
