import asyncio
import hashlib
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import quote
from uuid import uuid4

from fastapi import FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import Field, ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from trazia.copilot import CopilotAnswer, CopilotUnavailable
from trazia.copilot import ask as ask_copilot
from trazia.copilot.cache import answer_cached
from trazia.ifc import build_ifc
from trazia.model import FieldState, Identifier, Model, Revision, Source, fields
from trazia.queue import ProcessQueue
from trazia.queue.redis import RedisQueue
from trazia.review import approve
from trazia.revisions import compare
from trazia.store import (
    AuditRecord,
    DocumentRecord,
    EventRecord,
    IdempotencyConflict,
    JobRecord,
    RevisionRecord,
    Store,
)

from . import corrections, review_sessions
from .cors import origins
from .jobs import TERMINAL, recover_jobs, run_job
from .repository import check_match, get_revision, read_report, save_revision, seed_demo
from .security import UploadLimit

MAX_UPLOAD = 25 * 1024 * 1024


class JobInput(Model):
    documents: list[str] = Field(min_length=1, max_length=30)
    project_id: Identifier = "DEMO-PLANT"
    equipment_id: Identifier = Field(
        default="vessel-001", description="ID estable del equipo; no cambia al renombrar el tag"
    )
    revision: str = Field(default="C", min_length=1, max_length=50)
    strategy: str = Field(default="b_reglas", min_length=1, max_length=80)
    use_learning: bool = True
    providers: list[str] = Field(default_factory=list, max_length=10)
    dataset: Literal["synthetic", "real"] = "synthetic"
    previous_id: str | None = None
    timeout_seconds: float = Field(default=300, gt=0, le=3600)
    max_attempts: int = Field(default=3, ge=1, le=5)
    retry_backoff_seconds: float = Field(default=1, ge=0, le=30)


class StudyInput(Model):
    conjuntos: list[Literal["s-dev", "s-reservado", "s-adversarial", "s-mecanico"]] = Field(
        default_factory=lambda: ["s-dev"], min_length=1, max_length=4
    )
    variantes: list[str] = Field(default_factory=lambda: ["b_reglas"], min_length=1, max_length=20)
    casos: int | None = Field(default=None, ge=1, le=1000)
    degradaciones: list[str] | None = Field(default=None, max_length=20)
    remuestreos: int = Field(default=1000, ge=1, le=10000)
    semilla: int = Field(default=2026, ge=0, le=2**32 - 1)
    timeout_seconds: float = Field(default=3600, gt=0, le=7200)


class FieldInput(Model):
    state: FieldState
    value: float | str | None = None
    unit: str | None = Field(default=None, min_length=1)
    decimal_separator: Literal[".", ","] | None = None
    source: Source | None = None
    explanation: str | None = Field(default=None, max_length=2000)
    actor: str = Field(min_length=2, max_length=100)
    seconds: float | None = Field(default=None, ge=0, le=3600)
    review_session_id: str | None = None
    action: Literal["accept", "correct", "assume", "reject"] | None = None
    expected: dict | None = None


class UndoInput(Model):
    actor: str = Field(min_length=2, max_length=100)
    seconds: float | None = Field(default=None, ge=0, le=3600)
    review_session_id: str | None = None


class ApprovalInput(Model):
    reviewer: str = Field(min_length=2, max_length=100)


class CopilotInput(Model):
    question: str = Field(min_length=1, max_length=2000)
    revision_id: str = Field(default="A", min_length=1, max_length=300)
    path: str | None = Field(default=None, max_length=300)
    previous_id: str | None = Field(default=None, max_length=300)


def require_key(value: str | None) -> str:
    if value is None or not 1 <= len(value) <= 128:
        raise HTTPException(428, "Se requiere Idempotency-Key de 1 a 128 caracteres")
    return value


def reply(result: dict):
    headers = {"ETag": f'"{result["version"]}"'} if "version" in result else {}
    if result.get("audit_id") is not None:
        headers["X-Audit-Id"] = str(result["audit_id"])
    return JSONResponse(result["data"], status_code=result.get("status", 200), headers=headers)


def pending_corrections(result: dict):
    return JSONResponse(
        {
            "detail": "Cambio guardado; la exportación JSONL está pendiente. Reintenta exportar.",
            "persisted": True,
            "revision": result["data"],
        },
        status_code=503,
        headers={"ETag": f'"{result["version"]}"', "X-Audit-Id": str(result["audit_id"])},
    )


def create_app(
    *,
    data_root: Path | None = None,
    root: Path | None = None,
    database_url: str | None = None,
    seed: bool = True,
) -> FastAPI:
    from trazia.runtime import configure_offline

    configure_offline()
    repo = (root or Path(os.getenv("TRAZIA_ROOT", "."))).resolve()
    data = data_root or Path(os.getenv("TRAZIA_DATA", "data"))
    corrections_file = Path(
        os.getenv("TRAZIA_CORRECTIONS_FILE")
        or (
            (data_root if data_root is not None else repo)
            / "generated/correcciones/correcciones.jsonl"
        )
    ).resolve()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        store = Store(data, database_url or os.getenv("TRAZIA_DATABASE_URL"))
        app.state.store = store
        app.state.corrections_file = corrections_file
        try:
            corrections.flush(store, corrections_file)
        except (OSError, SQLAlchemyError):
            logging.getLogger("trazia.api").warning("Correcciones pendientes de exportar a JSONL")
        app.state.copilot_limit = asyncio.Semaphore(1)
        if seed:
            seed_demo(store, repo)
        queue_mode = os.getenv("TRAZIA_QUEUE", "process")
        if queue_mode == "redis":
            queue = await RedisQueue.connect(
                os.getenv("TRAZIA_REDIS_URL", "redis://localhost:6379/0")
            )
        elif queue_mode == "process":
            queue = ProcessQueue(lambda identity: run_job(store, identity))
        else:
            raise ValueError("TRAZIA_QUEUE debe ser process o redis")
        app.state.queue = queue
        await recover_jobs(store, queue)
        try:
            yield
        finally:
            await queue.close()
            store.close()

    app = FastAPI(title="TrazIA-3D", version="0.3", lifespan=lifespan)
    from .snapshots import router as snapshots_router

    app.include_router(snapshots_router)
    app.add_middleware(UploadLimit, limit=MAX_UPLOAD + 1024 * 1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins(),
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type", "Idempotency-Key", "If-Match", "Last-Event-ID"],
        expose_headers=["ETag", "X-Audit-Id"],
    )

    @app.exception_handler(IdempotencyConflict)
    async def conflict(_, error):
        return JSONResponse({"detail": str(error)}, status_code=409)

    @app.exception_handler(RequestValidationError)
    @app.exception_handler(ValidationError)
    async def invalid(_, error):
        from .validation import issues_for

        issues = issues_for(error, _.path_params.get("path"))
        return JSONResponse(
            {
                "detail": "No se ha guardado el cambio. "
                + "; ".join(f"{i['path']}: {i['message']} {i['action']}" for i in issues),
                "issues": issues,
            },
            status_code=422,
        )

    @app.get("/reference-system")
    def reference_system():
        from .validation import REFERENCE_SYSTEM

        return REFERENCE_SYSTEM

    @app.post("/review-sessions", status_code=201)
    def start_review_session(
        request: Request,
        body: review_sessions.SessionInput,
        idempotency_key: str | None = Header(None),
    ):
        def action(session):
            record = get_revision(session, body.revision_id)
            return {"data": review_sessions.start(session, record, body), "status": 201}

        return reply(
            request.app.state.store.perform(
                "POST review-sessions", require_key(idempotency_key), body.model_dump(), action
            )
        )

    @app.post("/review-sessions/{session_id}/finish")
    def finish_review_session(request: Request, session_id: str, body: review_sessions.FinishInput):
        with Session(request.app.state.store.engine) as session:
            return review_sessions.finish(session, session_id, body.active_seconds)

    @app.get("/revisions/{identity}/review-metrics")
    def review_metrics(request: Request, identity: str):
        with Session(request.app.state.store.engine) as session:
            record = get_revision(session, identity)
            result = review_sessions.metrics(session, record.id)
            model = Revision.model_validate_json(record.payload)
            return {
                **result,
                "equipment_tag": record.tag,
                "dataset": model.dataset,
                "pending_fields": len(model.pending_review()),
                "approved": model.approval is not None,
            }

    @app.get("/revisions/{identity}/validation")
    def review_validation(request: Request, identity: str):
        from .validation import diagnostics

        with Session(request.app.state.store.engine) as session:
            record = get_revision(session, identity)
            return diagnostics(Revision.model_validate_json(record.payload))

    @app.get("/equipment/{tag}/review-metrics")
    def equipment_review_metrics(request: Request, tag: str, project_id: str | None = None):
        with Session(request.app.state.store.engine) as session:
            return review_sessions.equipment_metrics(session, tag, project_id)

    @app.get("/health")
    def health():
        from trazia.runtime import offline

        return {
            "status": "ok",
            "schema_version": "0.3",
            "queue": os.getenv("TRAZIA_QUEUE", "process"),
            "offline": offline(),
        }

    @app.post("/documents", status_code=201)
    async def upload(
        request: Request,
        file: Annotated[UploadFile, File()],
        document_id: Annotated[str | None, Form()] = None,
        revision: Annotated[str, Form()] = "A",
        idempotency_key: str | None = Header(None),
    ):
        key = require_key(idempotency_key)
        content = await file.read(MAX_UPLOAD + 1)
        if not content or len(content) > MAX_UPLOAD:
            raise HTTPException(413, "El documento debe tener entre 1 byte y 25 MiB")
        filename = (file.filename or "documento.pdf").replace("\\", "/").rsplit("/", 1)[-1]
        if Path(filename).suffix.lower() not in (".pdf", ".xlsx", ".png", ".jpg", ".jpeg"):
            raise HTTPException(415, "Formato no admitido: use PDF, XLSX o imagen PNG/JPEG")
        digest = hashlib.sha256(content).hexdigest()
        logical_id = document_id or f"DOC-{digest[:16]}"
        if not logical_id or any(
            c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
            for c in logical_id
        ):
            raise HTTPException(422, "El identificador documental no es válido")
        if not revision.strip() or len(revision) > 50:
            raise HTTPException(422, "La revisión documental debe tener de 1 a 50 caracteres")
        body = {
            "filename": filename,
            "sha256": digest,
            "document_id": logical_id,
            "revision": revision,
        }

        def action(session):
            request.app.state.store.put(content)
            record = DocumentRecord(
                id=str(uuid4()),
                document_id=logical_id,
                filename=filename,
                revision=revision,
                sha256=digest,
                size=len(content),
            )
            session.add(record)
            return {"data": record.model_dump(), "status": 201}

        return reply(request.app.state.store.perform("POST /documents", key, body, action))

    @app.get("/equipment")
    def equipment(request: Request):
        with Session(request.app.state.store.engine) as session:
            rows = session.exec(select(RevisionRecord)).all()
            grouped = {}
            for row in rows:
                item = grouped.setdefault(
                    (row.project_id, row.equipment_id),
                    {
                        "tag": row.tag,
                        "kind": "Recipiente vertical",
                        "area": "Unidad 100",
                        "revisions": [],
                        "status": "draft",
                        "illustrative": False,
                        "ifcUrl": "",
                        "project_id": row.project_id,
                        "equipment_id": row.equipment_id,
                    },
                )
                revision = Revision.model_validate_json(row.payload)
                item["kind"] = revision.equipment.kind
                item["revisions"].append(row.revision)
                item["ifcUrl"] = (
                    f"/revisions/{quote(row.id, safe='')}/ifc?draft=true&v={row.version}"
                )
                item["status"] = "approved" if revision.approval else "draft"
            return list(grouped.values())

    @app.get("/equipment/{tag}/revisions/{rev}", response_model=Revision)
    def revision(request: Request, tag: str, rev: str, project_id: str = "DEMO-PLANT"):
        with Session(request.app.state.store.engine) as session:
            row = session.exec(
                select(RevisionRecord).where(
                    RevisionRecord.tag == tag,
                    RevisionRecord.revision == rev,
                    RevisionRecord.project_id == project_id,
                )
            ).first()
            if row is None:
                raise HTTPException(404, "No existe esa revisión del equipo")
            return JSONResponse(json.loads(row.payload), headers={"ETag": f'"{row.version}"'})

    @app.get("/revisions/{identity}/fields")
    def review_fields(request: Request, identity: str):
        with Session(request.app.state.store.engine) as session:
            row = get_revision(session, identity)
            model = Revision.model_validate_json(row.payload)
            return JSONResponse(
                {
                    path: value.model_dump(mode="json")
                    for path, value in fields(model.equipment).items()
                },
                headers={"ETag": f'"{row.version}"'},
            )

    @app.patch("/revisions/{identity}/fields/{path}", response_model=Revision)
    def update_field(
        request: Request,
        identity: str,
        path: str,
        body: FieldInput,
        if_match: str | None = Header(None),
        idempotency_key: str | None = Header(None),
    ):
        def action(session):
            record = get_revision(session, identity)
            check_match(record, if_match)
            model = Revision.model_validate_json(record.payload)
            target = fields(model.equipment).get(path)
            if target is None:
                raise HTTPException(404, "No existe ese campo")
            if body.expected is not None and type(target).model_validate(body.expected) != target:
                raise HTTPException(
                    412, "El campo ha cambiado; recarga y revisa su evidencia antes de editar"
                )
            if body.state == "corrected" and body.value is None:
                raise HTTPException(422, "Corregir requiere un valor")
            expected = {
                "accept": "accepted",
                "correct": "corrected",
                "assume": "assumed",
                "reject": "abstained",
            }
            if body.action and expected[body.action] != body.state:
                raise HTTPException(422, "La acción no corresponde al estado solicitado")
            if body.review_session_id:
                review_sessions.validate_clock(
                    session, body.review_session_id, record.id, body.actor, body.seconds
                )
            from .normalization import normalize_patch

            value, unit, source = normalize_patch(target, body)
            if body.value is not None:
                target.value = value
                target.interval = None
                if body.source is None:
                    target.source = target.source.model_copy(
                        update={
                            "channel": "humano",
                            "grounded": None,
                            "strategy": None,
                            "model": None,
                            "prompt_sha256": None,
                        }
                    )
            if unit is not None:
                target.unit = unit
                target.interval = None
            if source is not None:
                target.source = source
            target.state = body.state
            if "explanation" in body.model_fields_set:
                target.explanation = body.explanation
            if body.action == "reject":
                target.explanation = "Rechazado por el revisor. " + (
                    body.explanation or "Hace falta una lectura nueva."
                )
            model.approval = None
            model = Revision.model_validate_json(model.model_dump_json())
            return save_revision(
                session,
                record,
                model,
                path=path,
                actor=body.actor,
                seconds=body.seconds,
                review_session_id=body.review_session_id,
            )

        fingerprint = {**body.model_dump(mode="json"), "if_match": if_match}
        result = request.app.state.store.perform(
            f"PATCH {identity}/{path}", require_key(idempotency_key), fingerprint, action
        )
        try:
            corrections.flush(request.app.state.store, request.app.state.corrections_file)
        except (OSError, SQLAlchemyError):
            return pending_corrections(result)
        return reply(result)

    @app.post("/revisions/{identity}/audit/{audit_id}/undo", response_model=Revision)
    def undo_field(
        request: Request,
        identity: str,
        audit_id: int,
        body: UndoInput,
        if_match: str | None = Header(None),
        idempotency_key: str | None = Header(None),
    ):
        def action(session):
            record = get_revision(session, identity)
            check_match(record, if_match)
            original = session.get(AuditRecord, audit_id)
            if not original or original.revision_id != record.id or original.path.startswith("$"):
                raise HTTPException(404, "No existe esa acción de campo en esta revisión")
            if session.exec(select(AuditRecord).where(AuditRecord.undo_of == audit_id)).first():
                raise HTTPException(409, "Esta acción ya se ha deshecho")
            model = Revision.model_validate_json(record.payload)
            before = Revision.model_validate_json(original.before_json)
            after = Revision.model_validate_json(original.after_json)
            target = fields(model.equipment).get(original.path)
            old = fields(before.equipment).get(original.path)
            changed = fields(after.equipment).get(original.path)
            if target is None or old is None or changed is None or target != changed:
                raise HTTPException(
                    409, "El campo ha cambiado después de esta acción; recárgalo antes de deshacer"
                )
            if body.review_session_id:
                review_sessions.validate_clock(
                    session, body.review_session_id, record.id, body.actor, body.seconds
                )
            for key in type(old).model_fields:
                setattr(target, key, getattr(old, key))
            model.approval = None
            model = Revision.model_validate_json(model.model_dump_json())
            return save_revision(
                session,
                record,
                model,
                path=original.path,
                actor=body.actor,
                seconds=body.seconds,
                review_session_id=body.review_session_id,
                undo_of=audit_id,
            )

        result = request.app.state.store.perform(
            f"POST undo/{identity}/{audit_id}",
            require_key(idempotency_key),
            {**body.model_dump(), "if_match": if_match},
            action,
        )
        try:
            corrections.flush(request.app.state.store, request.app.state.corrections_file)
        except (OSError, SQLAlchemyError):
            return pending_corrections(result)
        return reply(result)

    @app.post("/correcciones/export")
    def export_corrections(request: Request):
        try:
            corrections.flush(request.app.state.store, request.app.state.corrections_file)
        except (OSError, SQLAlchemyError) as failure:
            raise HTTPException(
                503, "El registro SQL sigue guardado; no se pudo exportar el JSONL"
            ) from failure
        return {"status": "ok", "detail": "JSONL actualizado"}

    @app.get("/correcciones")
    def correction_log(request: Request, desde: datetime | None = None):
        if desde is not None and desde.tzinfo is None:
            raise HTTPException(
                422, "desde requiere fecha ISO 8601 con zona horaria, por ejemplo Z"
            )
        rows = corrections.read(request.app.state.store, desde)
        return {"correcciones": rows, "count": len(rows)}

    @app.post("/revisions/{identity}/approve", response_model=Revision)
    def approve_revision(
        request: Request,
        identity: str,
        body: ApprovalInput,
        if_match: str | None = Header(None),
        idempotency_key: str | None = Header(None),
    ):
        def action(session):
            record = get_revision(session, identity)
            check_match(record, if_match)
            model = Revision.model_validate_json(record.payload)
            if model.pending_review():
                raise HTTPException(409, "Quedan campos sin aceptar o corregir")
            originals = {d.id: request.app.state.store.read(d.sha256) for d in model.documents}
            approved = approve(model, body.reviewer, originals)
            return save_revision(session, record, approved, path="$approval", actor=body.reviewer)

        return reply(
            request.app.state.store.perform(
                f"POST approve/{identity}",
                require_key(idempotency_key),
                {**body.model_dump(), "if_match": if_match},
                action,
            )
        )

    @app.get("/revisions/{identity}/audit")
    def audit(request: Request, identity: str):
        with Session(request.app.state.store.engine) as session:
            row = get_revision(session, identity)
            actions = session.exec(
                select(AuditRecord)
                .where(AuditRecord.revision_id == row.id)
                .order_by(AuditRecord.id)
            ).all()
            return {
                "actions": [a.model_dump() for a in actions],
                "review_seconds": (
                    sum(a.seconds or 0 for a in actions)
                    if any(a.seconds is not None for a in actions)
                    else None
                ),
                "timed_actions": sum(a.seconds is not None for a in actions),
                "untimed_actions": sum(a.seconds is None for a in actions),
                "measurement": "sum_reported_action_seconds",
            }

    @app.get("/revisions/{identity}/ifc")
    def ifc(
        request: Request,
        identity: str,
        schema: Literal["IFC4", "IFC4X3", "IFC2X3"] = "IFC4",
        draft: bool = False,
    ):
        with Session(request.app.state.store.engine) as session:
            row = get_revision(session, identity)
            model = Revision.model_validate_json(row.payload)
        try:
            content = (
                build_ifc(model, draft=draft, schema=schema, details=model.dataset == "synthetic")
                .to_string()
                .encode()
            )
        except ValueError as error:
            raise HTTPException(409, str(error)) from error
        filename = quote(f"{model.equipment.tag.value}_{model.revision}", safe="")
        return Response(
            content,
            media_type="application/x-step",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{filename}"
                f"{'_DRAFT' if draft else ''}.ifc"
            },
        )

    @app.get("/revisions/{identity}/documents/{document_id}")
    def original(request: Request, identity: str, document_id: str):
        with Session(request.app.state.store.engine) as session:
            model = Revision.model_validate_json(get_revision(session, identity).payload)
        document = next((d for d in model.documents if d.id == document_id), None)
        if document is None:
            raise HTTPException(404, "El documento no pertenece a la revisión")
        return Response(
            request.app.state.store.read(document.sha256),
            media_type="application/pdf"
            if document.filename.endswith(".pdf")
            else "application/octet-stream",
        )

    @app.post("/equipment/{tag}/jobs", status_code=202)
    async def create_job(
        request: Request, tag: str, body: JobInput, idempotency_key: str | None = Header(None)
    ):
        def action(session):
            logical_ids = set()
            for identity in body.documents:
                document = session.get(DocumentRecord, identity)
                if document is None:
                    raise HTTPException(404, "No existe un documento del trabajo")
                if document.document_id in logical_ids:
                    raise HTTPException(422, "Identificadores documentales duplicados")
                logical_ids.add(document.document_id)
            identity = f"{body.project_id}:{body.equipment_id}:{body.revision}"
            if session.get(RevisionRecord, identity):
                raise HTTPException(409, "La revisión de destino ya existe")
            if body.previous_id:
                previous = get_revision(session, body.previous_id)
                if (previous.project_id, previous.equipment_id) != (
                    body.project_id,
                    body.equipment_id,
                ):
                    raise HTTPException(
                        422, "La memoria debe pertenecer al mismo equipo y proyecto"
                    )
                if not Revision.model_validate_json(previous.payload).approval:
                    raise HTTPException(409, "La revisión usada como memoria debe estar aprobada")
            config = {**body.model_dump(mode="json"), "tag": tag}
            if body.previous_id:
                config["previous_id"] = previous.id
            from trazia.runtime import offline

            if offline():
                from .job_cache import CacheMiss, load

                try:
                    load(request.app.state.store, session, config)
                except CacheMiss as failure:
                    raise HTTPException(409, str(failure)) from failure
            job = JobRecord(
                id=str(uuid4()),
                tag=tag,
                request_json=json.dumps(config),
            )
            session.add(job)
            return {"data": {"job_id": job.id, "status": "queued"}, "status": 202}

        result = request.app.state.store.perform(
            f"POST jobs/{tag}", require_key(idempotency_key), body.model_dump(mode="json"), action
        )
        await request.app.state.queue.enqueue(result["data"]["job_id"])
        return reply(result)

    @app.get("/jobs/{identity}")
    def job(request: Request, identity: str):
        with Session(request.app.state.store.engine) as session:
            record = session.get(JobRecord, identity)
            if record is None:
                raise HTTPException(404, "No existe ese trabajo")
            result = record.model_dump(exclude={"request_json", "run_json", "warnings_json"})
            result["run"] = json.loads(record.run_json) if record.run_json else None
            result["warnings"] = json.loads(record.warnings_json)
            return result

    @app.post("/jobs/{identity}/cancel")
    async def cancel(request: Request, identity: str, idempotency_key: str | None = Header(None)):
        def action(session):
            record = session.get(JobRecord, identity)
            if record is None:
                raise HTTPException(404, "No existe ese trabajo")
            if record.status not in TERMINAL:
                record.cancel_requested, record.status = True, "cancelled"
                session.add(record)
            return {"data": {"job_id": identity, "status": record.status}}

        result = request.app.state.store.perform(
            f"POST cancel/{identity}", require_key(idempotency_key), {}, action
        )
        await request.app.state.queue.cancel(identity)
        return reply(result)

    @app.get("/jobs/{identity}/events")
    async def events(request: Request, identity: str, last_event_id: int = Header(0, ge=0)):
        with Session(request.app.state.store.engine) as session:
            if session.get(JobRecord, identity) is None:
                raise HTTPException(404, "No existe ese trabajo")

        async def stream():
            cursor, heartbeat = last_event_id, time.monotonic()
            while not await request.is_disconnected():
                with Session(request.app.state.store.engine) as session:
                    batch = session.exec(
                        select(EventRecord)
                        .where(EventRecord.job_id == identity, EventRecord.id > cursor)
                        .order_by(EventRecord.id)
                        .limit(100)
                    ).all()
                    record = session.get(JobRecord, identity)
                    finished = record.status in TERMINAL
                for entry in batch:
                    cursor = entry.id
                    yield f"id: {cursor}\nevent: stage\ndata: {entry.model_dump_json()}\n\n"
                if finished and len(batch) < 100:
                    yield f"event: complete\ndata: {json.dumps({'status': record.status})}\n\n"
                    break
                if time.monotonic() - heartbeat > 10:
                    yield ": heartbeat\n\n"
                    heartbeat = time.monotonic()
                await asyncio.sleep(0.15)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/diff")
    def diff(
        request: Request,
        before: str = Query("A", alias="from"),
        after: str = Query("B", alias="to"),
        layers: bool = False,
    ):
        with Session(request.app.state.store.engine) as session:
            a = Revision.model_validate_json(get_revision(session, before).payload)
            b = Revision.model_validate_json(get_revision(session, after).payload)
        try:
            originals = (
                {
                    d.sha256: request.app.state.store.read(d.sha256)
                    for d in a.documents + b.documents
                }
                if layers
                else None
            )
            return compare(a, b, include_geometry=layers, originals=originals)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    @app.get("/diff/bcf")
    def bcf(
        request: Request,
        before: str = Query("A", alias="from"),
        after: str = Query("B", alias="to"),
    ):
        from trazia.bcf import export_bcf

        with Session(request.app.state.store.engine) as session:
            a = Revision.model_validate_json(get_revision(session, before).payload)
            b = Revision.model_validate_json(get_revision(session, after).payload)
        try:
            payload = export_bcf(a, b)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        return Response(
            payload,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=changes_DRAFT.bcfzip"},
        )

    @app.get("/diff/visual")
    def diff_visual(
        request: Request,
        document_id: str,
        page: int = Query(1, ge=1),
        before: str = Query("A", alias="from"),
        after: str = Query("B", alias="to"),
    ):
        from trazia.families.change_detection import render_pdf, visual_diff_images

        with Session(request.app.state.store.engine) as session:
            a = Revision.model_validate_json(get_revision(session, before).payload)
            b = Revision.model_validate_json(get_revision(session, after).payload)
        originals = []
        for revision in (a, b):
            document = next(
                (
                    d
                    for d in revision.documents
                    if d.id == document_id and d.filename.lower().endswith(".pdf")
                ),
                None,
            )
            if document is None:
                raise HTTPException(404, "Falta ese PDF en una revisión")
            try:
                originals.append(render_pdf(request.app.state.store.read(document.sha256), page))
            except ValueError as error:
                raise HTTPException(422, str(error)) from error
        result, image = visual_diff_images(*originals, return_png=True)
        if image is None:
            raise HTTPException(409, result.get("detail", "No se pudo alinear"))
        return Response(image, media_type="image/png", headers={"X-Alignment": result["method"]})

    @app.get("/bench")
    def bench(extractor: Literal["etiquetas", "combinado"] = "etiquetas"):
        result = read_report(repo / "web/public/demo/json" / f"bench-{extractor}.json")
        return result or {"status": "empty", "detail": "No hay resultados medidos"}

    @app.get("/plant")
    def plant(request: Request):
        return {
            "equipment": equipment(request),
            "layout": None,
            "detail": "La posición real en planta todavía no se ha extraído",
        }

    @app.get("/estudio")
    def study(request: Request, job_id: str | None = None):
        store = request.app.state.store
        with Session(store.engine) as session:
            if job_id:
                record = session.get(JobRecord, job_id)
                if not record or record.kind != "study":
                    raise HTTPException(404, "No existe ese estudio")
                if record.status != "done":
                    return JSONResponse(
                        {"job_id": job_id, "status": record.status, "detail": record.error},
                        status_code=202,
                    )
            else:
                record = session.exec(
                    select(JobRecord)
                    .where(JobRecord.kind == "study", JobRecord.status == "done")
                    .order_by(JobRecord.updated_at.desc(), JobRecord.id)
                ).first()
            if record:
                if not record.result_sha256:
                    raise HTTPException(409, "El estudio terminado no tiene resultado persistido")
                try:
                    return json.loads(store.read(record.result_sha256))
                except (OSError, ValueError) as failure:
                    raise HTTPException(
                        409, "No se puede verificar el resultado del estudio"
                    ) from failure
        result = read_report(repo / "generated/estudio/estudio.json")
        return result or {
            "status": "empty",
            "variants": [],
            "detail": "Lectura todavía no ha publicado resultados del estudio",
        }

    @app.get("/learning/corrections")
    def learning_corrections(
        request: Request, after: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000)
    ):
        from .learning import approved_examples

        try:
            return approved_examples(request.app.state.store, after=after, limit=limit)
        except (OSError, ValueError) as failure:
            raise HTTPException(
                409, "No se pueden verificar las correcciones y sus originales"
            ) from failure

    @app.post("/estudio", status_code=202)
    async def launch_study(
        request: Request, body: StudyInput, idempotency_key: str | None = Header(None)
    ):
        key = require_key(idempotency_key)
        data = Path(os.getenv("TRAZIA_STUDY_DATA", str(repo / "generated/synthetic_v2"))).resolve()
        # Solo datos sintéticos administrados localmente; la petición no acepta rutas.
        if any(part.casefold() == "private" for part in data.parts):
            raise HTTPException(422, "El estudio de la API solo admite el conjunto sintético")
        for name in body.conjuntos:
            if not (data / name).resolve().is_relative_to(data):
                raise HTTPException(422, "El conjunto debe permanecer en la carpeta sintética")
            try:
                manifest = json.loads((data / name / "manifest.json").read_text(encoding="utf-8"))
            except (OSError, ValueError) as failure:
                raise HTTPException(422, f"No existe un manifiesto válido para {name}") from failure
            if manifest.get("synthetic") is not True:
                raise HTTPException(422, "El manifiesto debe identificar datos sintéticos")

        config = {**body.model_dump(mode="json"), "datos": str(data)}

        def action(session):
            record = JobRecord(
                id=str(uuid4()), tag="estudio", kind="study", request_json=json.dumps(config)
            )
            session.add(record)
            return {"data": {"job_id": record.id, "status": "queued"}, "status": 202}

        result = request.app.state.store.perform("POST /estudio", key, config, action)
        await request.app.state.queue.enqueue(result["data"]["job_id"])
        return reply(result)

    @app.get("/learning/few-shot")
    def few_shot(
        request: Request,
        path: str | None = None,
        strategy: str | None = None,
        target_revision_id: str | None = None,
        limit: int = Query(3, ge=1, le=5),
    ):
        from .few_shot import select_examples

        target = None
        if target_revision_id:
            with Session(request.app.state.store.engine) as session:
                target = Revision.model_validate_json(
                    get_revision(session, target_revision_id).payload
                )
        return select_examples(
            request.app.state.store, path=path, strategy=strategy, target=target, limit=limit
        )

    @app.get("/learning/few-shot/{example_id}/evidence")
    def few_shot_evidence(request: Request, example_id: str):
        from .learning import approved_examples

        store = request.app.state.store
        cursor = 0
        for _ in range(50):
            page = approved_examples(store, after=cursor, limit=200)
            match = next((e for e in page["examples"] if e["id"] == example_id), None)
            if match:
                if not match["document"]["filename"].lower().endswith(".pdf"):
                    raise HTTPException(422, "Este ejemplo no tiene una evidencia PDF renderizable")
                from .few_shot import render_evidence

                return Response(
                    render_evidence(store, match),
                    media_type="image/png",
                    headers={"Cache-Control": "no-store"},
                )
            cursor = page["next_cursor"]
            if cursor is None:
                break
        raise HTTPException(404, "El ejemplo no existe o su aprobación ya no es vigente")

    @app.post("/copiloto", response_model=CopilotAnswer)
    async def copilot(request: Request, body: CopilotInput):
        if not body.question.strip():
            raise HTTPException(422, "Escribe una pregunta")
        store = request.app.state.store
        from .few_shot import select_examples

        with Session(store.engine) as session:
            record = get_revision(session, body.revision_id)
            revision = Revision.model_validate_json(record.payload)
            identity, version = record.id, record.version
            examples = select_examples(store, path=body.path, target=revision, limit=2)
            previous = None
            previous_version = None
            if body.previous_id:
                previous_record = get_revision(session, body.previous_id)
                previous = Revision.model_validate_json(previous_record.payload)
                if (previous.project_id, previous.equipment.id) != (
                    revision.project_id,
                    revision.equipment.id,
                ):
                    raise HTTPException(422, "La comparación debe ser del mismo proyecto y equipo")
                previous_version = (previous_record.id, previous_record.version)
        try:
            async with asyncio.timeout(95):
                async with request.app.state.copilot_limit:
                    result = await answer_cached(
                        revision,
                        body.question.strip(),
                        cache_root=store.root / "cache/copilot",
                        call=ask_copilot,
                        revision_id=identity,
                        revision_version=version,
                        path=body.path,
                        previous=previous,
                        read_document=store.read,
                        examples=examples,
                    )
        except CopilotUnavailable as error:
            raise HTTPException(503, str(error)) from error
        except TimeoutError as error:
            raise HTTPException(
                503, "El copiloto local ha agotado el tiempo de consulta"
            ) from error
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        with Session(store.engine) as session:
            if get_revision(session, identity).version != version or (
                previous_version
                and get_revision(session, previous_version[0]).version != previous_version[1]
            ):
                raise HTTPException(
                    409, "La revisión cambió durante la consulta; vuelve a preguntar"
                )
        return result

    return app
