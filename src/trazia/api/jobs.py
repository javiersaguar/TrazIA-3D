import asyncio
import json
import logging
import time

from sqlmodel import Session, select

from trazia.ifc import build_ifc
from trazia.model import Revision
from trazia.store import DocumentRecord, EventRecord, JobRecord, RevisionRecord, Store

from .pipeline_adapter import InputDocument, process
from .repository import revision_id

logger = logging.getLogger("trazia.jobs")
TERMINAL = {"done", "error", "cancelled", "timeout"}


class JobCancelled(RuntimeError):
    pass


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
                InputDocument(document.filename, store.read(document.sha256), document.document_id)
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
    if result.error or result.revision is None:
        return result, None
    revision = Revision.model_validate_json(result.revision.model_dump_json())
    revision.approval = None
    expected = (
        request["project_id"],
        request["equipment_id"],
        request["revision"],
        request["dataset"],
    )
    actual = (revision.project_id, revision.equipment.id, revision.revision, revision.dataset)
    if expected != actual:
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
    digest = store.put(model.to_string().encode())
    emit(store, job_id, "ifc", "ok", "", f"IFC4 DRAFT almacenado: {digest[:12]}")
    emit(store, job_id, "validate", "ok", "", "Contrato 0.3 válido y geometría IFC exportable")
    return result, revision


async def run_job(store: Store, job_id: str):
    started = time.perf_counter()
    with Session(store.engine) as session:
        job = session.get(JobRecord, job_id)
        if job is None or job.status in TERMINAL or job.cancel_requested:
            return
        request = json.loads(job.request_json)
        job.status = "running"
        job.attempts += 1
        job.updated_at = time.time()
        session.add(job)
        session.commit()
    try:
        async with asyncio.timeout(request.get("timeout_seconds", 300)):
            result, revision = await asyncio.to_thread(execute_pipeline, store, job_id, request)
        with Session(store.engine) as session:
            job = session.get(JobRecord, job_id)
            if job.cancel_requested or job.status != "running":
                return
            run = result.run.model_copy(update={"seconds": time.perf_counter() - started})
            job.run_json = run.model_dump_json()
            job.updated_at = time.time()
            if revision:
                identity = revision_id(revision)
                if session.get(RevisionRecord, identity):
                    raise ValueError("La revisión de destino ya existe; no se sobrescribe")
                revision.run = run
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
                job.revision_id = identity
                job.status = "done"
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
        with Session(store.engine) as session:
            job = session.get(JobRecord, job_id)
            job.status = "cancelled" if job.cancel_requested else "queued"
            job.updated_at = time.time()
            session.add(job)
            session.commit()
        raise
    except Exception as error:
        with Session(store.engine) as session:
            job = session.get(JobRecord, job_id)
            if job.cancel_requested:
                job.status = "cancelled"
            else:
                job.status = "timeout" if isinstance(error, TimeoutError) else "error"
            job.error = "Tiempo máximo agotado" if isinstance(error, TimeoutError) else str(error)
            job.updated_at = time.time()
            session.add(job)
            session.add(
                EventRecord(
                    job_id=job_id, stage="job", status="error", file="", detail=job.error[:4000]
                )
            )
            session.commit()


async def recover_jobs(store: Store, queue):
    with Session(store.engine) as session:
        jobs = session.exec(
            select(JobRecord).where(JobRecord.status.in_(["queued", "running"]))
        ).all()
        identities = []
        for job in jobs:
            job.status = "cancelled" if job.cancel_requested else "queued"
            session.add(job)
            if not job.cancel_requested:
                identities.append(job.id)
        session.commit()
    for identity in identities:
        await queue.enqueue(identity)
