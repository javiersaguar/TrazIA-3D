"""Propuestas de cambio de diseño: preparar, previsualizar, confirmar y deshacer (K.1–K.3).

Una propuesta nunca modifica su revisión base. Confirmarla publica una revisión DRAFT nueva
con el candidato y el IFC exactos que se previsualizaron; deshacerla crea otra revisión
compensatoria. Ninguna salida de un modelo de lenguaje confirma ni publica nada.
"""

import asyncio
import json
import os
import re
import time
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import Field
from sqlalchemy import and_, or_, update
from sqlmodel import Session, select

from trazia.design import ENGINE_VERSION, ProposalInput, catalog
from trazia.design.catalog import FAMILY_MATRIX, geometry_supported
from trazia.design.intent import IntentInput, interpret
from trazia.design.proposal import (
    digest,
    evaluate,
    evaluate_reversion,
    order_document,
)
from trazia.model import SHA256, Model, Revision
from trazia.store import (
    AuditRecord,
    ChangeProposalRecord,
    DocumentRecord,
    EventRecord,
    JobRecord,
    RevisionArtifactRecord,
    RevisionRecord,
    Store,
)

from .repository import check_match, get_revision

router = APIRouter()
OPEN = ("draft", "needs_clarification", "invalid", "ready", "previewed")
PREVIEW_STEPS = 4
SEMANTIC = {
    "shell": "shell",
    "top_head": "head-top",
    "bottom_head": "head-bottom",
    "skirt": "skirt",
}


def ttl() -> float:
    return float(os.getenv("TRAZIA_PROPOSAL_TTL", "7200"))


class PreviewInput(Model):
    express_rules: bool = True
    timeout_seconds: float = Field(default=180, gt=0, le=900)


class ApplyInput(Model):
    actor: str = Field(min_length=2, max_length=100)
    proposal_sha256: SHA256
    preview_ifc_sha256: SHA256


class DiscardInput(Model):
    actor: str = Field(min_length=2, max_length=100)


class RevertInput(Model):
    actor: str = Field(min_length=2, max_length=100)
    reason: str = Field(min_length=3, max_length=1000)


def require_key(value: str | None) -> str:
    if value is None or not 1 <= len(value) <= 128:
        raise HTTPException(428, "Se requiere Idempotency-Key de 1 a 128 caracteres")
    return value


def reply(result: dict):
    headers = {"ETag": f'"{result["version"]}"'} if "version" in result else {}
    return JSONResponse(result["data"], status_code=result.get("status", 200), headers=headers)


def stamp(value: float) -> str:
    moment = datetime.fromtimestamp(value, timezone.utc)
    return moment.isoformat(timespec="microseconds").replace("+00:00", "Z")


def next_label(session: Session, base: Revision) -> str:
    """Etiqueta libre `<raíz>-D<n>`; una revisión derivada de otra continúa la serie."""
    root = re.sub(r"-D\d+$", "", base.revision)
    rows = session.exec(
        select(RevisionRecord.revision).where(
            RevisionRecord.project_id == base.project_id,
            RevisionRecord.equipment_id == base.equipment.id,
        )
    ).all()
    used = [int(m[1]) for row in rows if (m := re.fullmatch(rf"{re.escape(root)}-D(\d+)", row))]
    return f"{root}-D{max(used, default=0) + 1}"


def load(session: Session, identity: str) -> ChangeProposalRecord:
    record = session.get(ChangeProposalRecord, identity)
    if record is None:
        raise HTTPException(404, "No existe esa propuesta de cambio")
    return record


def snapshot(session: Session, applied: ChangeProposalRecord) -> Revision:
    """Base exacta en el momento de aplicar, conservada en la auditoría de la revisión nueva."""
    audit = session.exec(
        select(AuditRecord)
        .where(
            AuditRecord.revision_id == applied.applied_revision_id,
            AuditRecord.path.in_(["$design", "$reversion"]),
        )
        .order_by(AuditRecord.id)
    ).first()
    if audit is None:
        raise HTTPException(409, "Falta la auditoría de la orden aplicada")
    return Revision.model_validate_json(audit.before_json)


def compute(session: Session, record: ChangeProposalRecord):
    """Evaluación determinista de la propuesta tal como está guardada."""
    base_record = session.get(RevisionRecord, record.revision_id)
    base = Revision.model_validate_json(base_record.payload)
    body = ProposalInput.model_validate_json(record.input_json)
    label = next_label(session, base)
    options = dict(proposal_id=record.id, label=label, created_at=stamp(record.created_at))
    if record.kind == "reversion":
        applied = session.get(ChangeProposalRecord, record.reverts_proposal_id)
        evaluation, content = evaluate_reversion(
            base,
            json.loads(applied.content_json),
            snapshot(session, applied),
            base_id=base_record.id,
            actor=body.actor,
            reason=body.reason,
            **options,
        )
    else:
        evaluation, content = evaluate(base, body, base_id=base_record.id, **options)
    sha = digest({"content": content, "label": label, "engine": ENGINE_VERSION})
    return evaluation, content, label, sha, base_record, base


def evaluate_into(session: Session, record: ChangeProposalRecord):
    evaluation, content, label, sha, _, _ = compute(session, record)
    record.status = evaluation.status
    record.evaluation_json = json.dumps(evaluation.summary(), ensure_ascii=False)
    record.content_json = json.dumps(content, ensure_ascii=False)
    record.target_label, record.proposal_sha256 = label, sha
    record.preview_json = record.preview_ifc_sha256 = record.candidate_json = None
    record.params_sha256 = record.generator_version = None
    record.updated_at = time.time()
    record.expires_at = record.updated_at + ttl()


def refresh(session: Session, record: ChangeProposalRecord) -> bool:
    """Marca obsoleta una propuesta abierta cuya base cambió o que caducó."""
    if record.status not in OPEN:
        return False
    base = session.get(RevisionRecord, record.revision_id)
    reason = None
    if base is None or base.version != record.base_version:
        reason = "La revisión base ha cambiado; prepara la propuesta de nuevo sobre la vigente."
    elif time.time() > record.expires_at:
        reason = "La propuesta ha caducado; vuelve a validarla y previsualizarla."
    if reason is None:
        return False
    record.status, record.stale_reason, record.updated_at = "stale", reason, time.time()
    session.add(record)
    return True


def view(record: ChangeProposalRecord) -> dict:
    evaluation = json.loads(record.evaluation_json or "{}")
    content = json.loads(record.content_json or "{}")
    body = json.loads(record.input_json)
    preview = json.loads(record.preview_json) if record.preview_json else None
    if preview:
        preview["ifc_url"] = f"/change-proposals/{record.id}/preview.ifc"
        preview["ifc_sha256"] = record.preview_ifc_sha256
    return {
        "id": record.id,
        "status": record.status,
        "kind": record.kind,
        "origin": record.origin,
        "actor": record.actor,
        "reason": body.get("reason"),
        "request_text": body.get("request_text"),
        "input": body,
        "base": {
            "revision_id": record.revision_id,
            "revision": content.get("base", {}).get("revision"),
            "version": record.base_version,
            "input_sha256": record.base_sha256,
        },
        "target_revision": record.target_label,
        "operations": evaluation.get("operations", []),
        "issues": evaluation.get("issues", []),
        "effects": evaluation.get("effects", []),
        "derived": evaluation.get("derived", {}),
        "engine_version": evaluation.get("engine_version"),
        "proposal_sha256": record.proposal_sha256,
        "preview": preview,
        "applied_revision_id": record.applied_revision_id,
        "reverts": record.reverts_proposal_id,
        "reverted_by": record.reverted_by,
        "stale_reason": record.stale_reason,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "expires_at": record.expires_at,
        "notice": "Valores de diseño propuestos por una persona; no son lecturas del plano.",
    }


def referenced(session: Session, sha: str, *, excluding: str | None = None) -> bool:
    if session.exec(select(DocumentRecord).where(DocumentRecord.sha256 == sha)).first():
        return True
    if session.exec(
        select(RevisionArtifactRecord).where(RevisionArtifactRecord.sha256 == sha)
    ).first():
        return True
    others = session.exec(
        select(ChangeProposalRecord).where(
            ChangeProposalRecord.preview_ifc_sha256 == sha,
            ChangeProposalRecord.id != (excluding or ""),
            ChangeProposalRecord.status.in_(["previewed", "applied"]),
        )
    ).first()
    return others is not None


def purge_previews(store: Store) -> int:
    """Limpia IFC temporales de propuestas descartadas, obsoletas o caducadas."""
    removed = 0
    with Session(store.engine) as session:
        rows = session.exec(
            select(ChangeProposalRecord).where(ChangeProposalRecord.preview_ifc_sha256.is_not(None))
        ).all()
        for record in rows:
            refresh(session, record)
            if record.status in ("previewed", "applied"):
                continue
            sha = record.preview_ifc_sha256
            record.preview_ifc_sha256 = record.preview_json = record.candidate_json = None
            session.add(record)
            if not referenced(session, sha, excluding=record.id):
                store.discard(sha)
                removed += 1
        session.commit()
    return removed


@router.get("/revisions/{identity}/design-operations")
def design_operations(request: Request, identity: str):
    with Session(request.app.state.store.engine) as session:
        record = get_revision(session, identity)
        model = Revision.model_validate_json(record.payload)
    return JSONResponse(
        {
            **catalog(model),
            "revision_id": record.id,
            "revision": model.revision,
            "version": record.version,
            "geometry_supported": geometry_supported(model.equipment),
            "families": FAMILY_MATRIX,
            "derived_from": model.derived_from.model_dump(mode="json")
            if model.derived_from
            else None,
        },
        headers={"ETag": f'"{record.version}"'},
    )


@router.post("/revisions/{identity}/change-proposals", status_code=201)
def create_proposal(
    request: Request,
    identity: str,
    body: ProposalInput,
    if_match: str | None = Header(None),
    idempotency_key: str | None = Header(None),
):
    if body.origin == "deshacer":
        raise HTTPException(422, "Para deshacer usa POST /change-proposals/{id}/revert")

    def action(session):
        record = get_revision(session, identity)
        check_match(record, if_match)
        base = Revision.model_validate_json(record.payload)
        now = time.time()
        proposal = ChangeProposalRecord(
            id=uuid4().hex,
            revision_id=record.id,
            base_version=record.version,
            base_sha256=base.fingerprint(),
            status="draft",
            kind="cambio_diseno",
            origin=body.origin,
            actor=body.actor,
            input_json=body.model_dump_json(),
            evaluation_json="{}",
            content_json="{}",
            proposal_sha256="0" * 64,
            target_label="",
            created_at=now,
            updated_at=now,
            expires_at=now + ttl(),
        )
        evaluate_into(session, proposal)
        session.add(proposal)
        return {"data": view(proposal), "status": 201}

    return reply(
        request.app.state.store.perform(
            f"POST change-proposals/{identity}",
            require_key(idempotency_key),
            {**body.model_dump(mode="json"), "if_match": if_match},
            action,
        )
    )


@router.get("/revisions/{identity}/change-proposals")
def list_proposals(request: Request, identity: str):
    with Session(request.app.state.store.engine) as session:
        record = get_revision(session, identity)
        rows = session.exec(
            select(ChangeProposalRecord)
            .where(
                or_(
                    ChangeProposalRecord.revision_id == record.id,
                    ChangeProposalRecord.applied_revision_id == record.id,
                )
            )
            .order_by(ChangeProposalRecord.created_at.desc())
        ).all()
        for row in rows:
            refresh(session, row)
        session.commit()
        return {"revision_id": record.id, "proposals": [view(row) for row in rows]}


@router.get("/change-proposals/{identity}")
def get_proposal(request: Request, identity: str):
    with Session(request.app.state.store.engine) as session:
        record = load(session, identity)
        if refresh(session, record):
            session.commit()
        return view(record)


@router.put("/change-proposals/{identity}")
def replace_proposal(
    request: Request,
    identity: str,
    body: ProposalInput,
    idempotency_key: str | None = Header(None),
):
    def action(session):
        record = load(session, identity)
        refresh(session, record)
        if record.kind != "cambio_diseno" or body.origin == "deshacer":
            raise HTTPException(409, "Una propuesta de deshacer no se edita; descártala")
        if record.status not in OPEN:
            raise HTTPException(409, f"La propuesta está {record.status}; prepara una nueva")
        record.input_json, record.origin, record.actor = (
            body.model_dump_json(),
            body.origin,
            body.actor,
        )
        evaluate_into(session, record)
        session.add(record)
        return {"data": view(record)}

    result = request.app.state.store.perform(
        f"PUT change-proposals/{identity}",
        require_key(idempotency_key),
        body.model_dump(mode="json"),
        action,
    )
    purge_previews(request.app.state.store)
    return reply(result)


@router.post("/change-proposals/{identity}/preview", status_code=202)
async def preview(
    request: Request,
    identity: str,
    body: PreviewInput | None = None,
    idempotency_key: str | None = Header(None),
):
    options = body or PreviewInput()

    def action(session):
        record = load(session, identity)
        refresh(session, record)
        if record.status not in ("ready", "previewed"):
            detail = record.stale_reason or f"La propuesta está {record.status}; corrígela antes"
            raise HTTPException(409, detail)
        job = JobRecord(
            id=str(uuid4()),
            tag=f"propuesta:{record.id[:8]}",
            kind="design_preview",
            request_json=json.dumps(
                {
                    "proposal_id": record.id,
                    "proposal_sha256": record.proposal_sha256,
                    **options.model_dump(),
                }
            ),
        )
        session.add(job)
        return {
            "data": {"job_id": job.id, "status": "queued", "steps": PREVIEW_STEPS},
            "status": 202,
        }

    result = request.app.state.store.perform(
        f"POST preview/{identity}",
        require_key(idempotency_key),
        options.model_dump(),
        action,
    )
    await request.app.state.queue.enqueue(result["data"]["job_id"])
    return reply(result)


@router.get("/change-proposals/{identity}/preview.ifc")
def preview_ifc(request: Request, identity: str):
    with Session(request.app.state.store.engine) as session:
        record = load(session, identity)
        sha = record.preview_ifc_sha256
    if sha is None:
        raise HTTPException(404, "La propuesta no tiene previsualización vigente")
    try:
        content = request.app.state.store.read(sha)
    except (OSError, ValueError) as failure:
        raise HTTPException(409, "No se puede verificar el IFC temporal") from failure
    return Response(
        content,
        media_type="application/x-step",
        headers={
            "Content-Disposition": f'attachment; filename="propuesta_{identity[:8]}_DRAFT.ifc"',
            "Cache-Control": "private, max-age=600",
            "X-Content-SHA256": sha,
        },
    )


@router.post("/change-proposals/{identity}/apply", status_code=201)
def apply(
    request: Request,
    identity: str,
    body: ApplyInput,
    if_match: str | None = Header(None),
    idempotency_key: str | None = Header(None),
):
    store = request.app.state.store

    def action(session):
        record = load(session, identity)
        refresh(session, record)
        if record.status == "applied":
            raise HTTPException(
                409, f"La propuesta ya se aplicó en la revisión {record.applied_revision_id}"
            )
        if record.status != "previewed":
            detail = record.stale_reason or "Confirma solo una propuesta previsualizada y vigente"
            raise HTTPException(409, detail)
        base_record = session.get(RevisionRecord, record.revision_id)
        check_match(base_record, if_match)
        if (body.proposal_sha256, body.preview_ifc_sha256) != (
            record.proposal_sha256,
            record.preview_ifc_sha256,
        ):
            raise HTTPException(
                409, "La propuesta o su previsualización han cambiado; revisa la vigente"
            )
        base = Revision.model_validate_json(base_record.payload)
        candidate = Revision.model_validate_json(record.candidate_json)
        if base.fingerprint() != record.base_sha256 or candidate.fingerprint() != (
            record.params_sha256
        ):
            raise HTTPException(409, "Los datos no coinciden con la previsualización")
        target = f"{candidate.project_id}:{candidate.equipment.id}:{candidate.revision}"
        if session.get(RevisionRecord, target):
            raise HTTPException(
                409, f"Ya existe la revisión {candidate.revision}; vuelve a previsualizar"
            )
        content = json.loads(record.content_json)
        document, payload = order_document(content)
        if document not in candidate.documents:
            raise HTTPException(409, "El documento de orden no corresponde al candidato")
        # Blobs por hash antes de la transacción: si falla el commit solo quedan huérfanos
        # inmutables, nunca una revisión a medias.
        store.put(payload)
        store.read(record.preview_ifc_sha256)
        now = time.time()
        claimed = session.exec(
            update(ChangeProposalRecord)
            .where(ChangeProposalRecord.id == record.id, ChangeProposalRecord.status == "previewed")
            .values(status="applied", applied_revision_id=target, updated_at=now)
        )
        if claimed.rowcount != 1:
            raise HTTPException(409, "Otra confirmación ha cambiado la propuesta")
        if record.kind == "reversion":
            reverted = session.exec(
                update(ChangeProposalRecord)
                .where(
                    ChangeProposalRecord.id == record.reverts_proposal_id,
                    ChangeProposalRecord.reverted_by.is_(None),
                )
                .values(reverted_by=record.id, updated_at=now)
            )
            if reverted.rowcount != 1:
                raise HTTPException(409, "Esa orden ya se ha deshecho")
        session.add(
            RevisionRecord(
                id=target,
                project_id=candidate.project_id,
                equipment_id=candidate.equipment.id,
                tag=candidate.equipment.tag.value,
                revision=candidate.revision,
                payload=candidate.model_dump_json(),
            )
        )
        session.add(
            DocumentRecord(
                id=f"design-{record.id}",
                document_id=document.id,
                filename=document.filename,
                revision=document.revision,
                sha256=document.sha256,
                size=len(payload),
            )
        )
        session.flush()
        session.add(
            AuditRecord(
                revision_id=target,
                path="$reversion" if record.kind == "reversion" else "$design",
                actor=body.actor,
                before_json=base_record.payload,
                after_json=candidate.model_dump_json(),
            )
        )
        preview_data = json.loads(record.preview_json)
        for kind, sha, media in (
            ("ifc", record.preview_ifc_sha256, "application/x-step"),
            ("orden_diseno", document.sha256, "application/json"),
        ):
            session.add(
                RevisionArtifactRecord(
                    revision_id=target,
                    kind=kind,
                    sha256=sha,
                    media_type=media,
                    input_sha256=candidate.fingerprint(),
                    generator_version=preview_data["generator_version"],
                    proposal_id=record.id,
                )
            )
        record.status, record.applied_revision_id, record.updated_at = "applied", target, now
        return {
            "data": {
                "proposal": view(record),
                "revision_id": target,
                "revision": candidate.model_dump(mode="json"),
            },
            "status": 201,
            "version": 1,
        }

    return reply(
        store.perform(
            f"POST apply/{identity}",
            require_key(idempotency_key),
            {**body.model_dump(), "if_match": if_match},
            action,
        )
    )


@router.post("/change-proposals/{identity}/discard")
def discard(
    request: Request,
    identity: str,
    body: DiscardInput,
    idempotency_key: str | None = Header(None),
):
    def action(session):
        record = load(session, identity)
        refresh(session, record)
        if record.status == "applied":
            raise HTTPException(409, "Una propuesta aplicada se deshace, no se descarta")
        if record.status != "discarded":
            record.status, record.updated_at = "discarded", time.time()
            session.add(record)
        return {"data": view(record)}

    result = request.app.state.store.perform(
        f"POST discard/{identity}", require_key(idempotency_key), body.model_dump(), action
    )
    purge_previews(request.app.state.store)
    return reply(result)


@router.post("/change-proposals/{identity}/revert", status_code=201)
def revert(
    request: Request,
    identity: str,
    body: RevertInput,
    if_match: str | None = Header(None),
    idempotency_key: str | None = Header(None),
):
    """Prepara la revisión compensatoria; se previsualiza y confirma como cualquier otra."""

    def action(session):
        applied = load(session, identity)
        if applied.status != "applied" or applied.applied_revision_id is None:
            raise HTTPException(409, "Solo se deshace una propuesta aplicada")
        if applied.reverted_by:
            raise HTTPException(409, "Esa orden ya se ha deshecho")
        current = get_revision(session, applied.applied_revision_id)
        check_match(current, if_match)
        model = Revision.model_validate_json(current.payload)
        now = time.time()
        proposal_input = ProposalInput(reason=body.reason, actor=body.actor, origin="deshacer")
        record = ChangeProposalRecord(
            id=uuid4().hex,
            revision_id=current.id,
            base_version=current.version,
            base_sha256=model.fingerprint(),
            status="draft",
            kind="reversion",
            origin="deshacer",
            actor=body.actor,
            input_json=proposal_input.model_dump_json(),
            evaluation_json="{}",
            content_json="{}",
            proposal_sha256="0" * 64,
            target_label="",
            reverts_proposal_id=applied.id,
            created_at=now,
            updated_at=now,
            expires_at=now + ttl(),
        )
        evaluate_into(session, record)
        session.add(record)
        return {"data": view(record), "status": 201}

    return reply(
        request.app.state.store.perform(
            f"POST revert/{identity}",
            require_key(idempotency_key),
            {**body.model_dump(), "if_match": if_match},
            action,
        )
    )


@router.post("/copiloto/design-proposals")
def design_intent(request: Request, body: IntentInput):
    """Prepara un borrador desde texto. No crea, valida ni confirma ninguna propuesta."""
    from trazia.design.intent import model_provider

    with Session(request.app.state.store.engine) as session:
        record = get_revision(session, body.revision_id)
        model = Revision.model_validate_json(record.payload)
    provider = getattr(request.app.state, "design_intent_provider", None)
    if provider is None and body.use_model:
        provider = model_provider
    draft = interpret(model, body.text, selected_id=body.selected_id, provider=provider)
    return {**draft, "revision_id": record.id, "version": record.version}


@router.get("/revisions/{identity}/artifacts")
def artifacts(request: Request, identity: str):
    with Session(request.app.state.store.engine) as session:
        record = get_revision(session, identity)
        model = Revision.model_validate_json(record.payload)
        rows = session.exec(
            select(RevisionArtifactRecord)
            .where(RevisionArtifactRecord.revision_id == record.id)
            .order_by(RevisionArtifactRecord.id)
        ).all()
        current = model.fingerprint()
        return {
            "revision_id": record.id,
            "derived_from": model.derived_from.model_dump(mode="json")
            if model.derived_from
            else None,
            "artifacts": [
                {**row.model_dump(), "current": row.input_sha256 == current} for row in rows
            ],
        }


@router.get("/revisions/{identity}/design-report.pdf")
def design_report_pdf(request: Request, identity: str):
    """PDF derivado con la tabla de cambios y anotaciones; el original no se modifica."""
    from trazia.design.report import design_report

    store = request.app.state.store
    with Session(store.engine) as session:
        record = get_revision(session, identity)
        model = Revision.model_validate_json(record.payload)
        if model.derived_from is None:
            raise HTTPException(404, "Esta revisión no procede de una orden de diseño")
        proposal = session.get(ChangeProposalRecord, model.derived_from.proposal_id)
        if proposal is None:
            raise HTTPException(409, "Falta la propuesta que originó la revisión")
        content = json.loads(proposal.content_json)
        artifact = session.exec(
            select(RevisionArtifactRecord).where(
                RevisionArtifactRecord.revision_id == record.id,
                RevisionArtifactRecord.kind == "ifc",
            )
        ).first()
        order = next(d for d in model.documents if d.id == model.derived_from.order_document_id)
        originals = {}
        for document in model.documents:
            if document.role is None and document.filename.lower().endswith(".pdf"):
                try:
                    originals[document.sha256] = store.read(document.sha256)
                except (OSError, ValueError):
                    continue  # se declara pendiente; nunca se anota un original no verificado
        meta = {
            "generated_at": stamp(proposal.updated_at),
            "order_sha256": order.sha256,
            "ifc_sha256": artifact.sha256 if artifact else "—",
        }
        try:
            content_pdf = design_report(model, content, originals, meta=meta)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        sha = store.put(content_pdf)
        exists = session.exec(
            select(RevisionArtifactRecord).where(
                RevisionArtifactRecord.revision_id == record.id,
                RevisionArtifactRecord.kind == "informe_pdf",
                RevisionArtifactRecord.sha256 == sha,
            )
        ).first()
        if exists is None:
            session.add(
                RevisionArtifactRecord(
                    revision_id=record.id,
                    kind="informe_pdf",
                    sha256=sha,
                    media_type="application/pdf",
                    input_sha256=model.fingerprint(),
                    generator_version=f"informe-derivado-1; motor {ENGINE_VERSION}",
                    proposal_id=proposal.id,
                )
            )
            session.commit()
    name = f"{model.equipment.tag.value}_{model.revision}_DERIVADO_DRAFT.pdf"
    return Response(
        content_pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{name}"',
            "X-Content-SHA256": sha,
            "X-Derived-Document": "true",
        },
    )


def is_derived_report(session: Session, sha: str) -> bool:
    return (
        session.exec(
            select(RevisionArtifactRecord).where(
                RevisionArtifactRecord.sha256 == sha,
                RevisionArtifactRecord.kind == "informe_pdf",
            )
        ).first()
        is not None
    )


def published_ifc(session: Session, record: RevisionRecord, model: Revision) -> str | None:
    """SHA del IFC publicado con la revisión, si sigue correspondiendo a sus datos."""
    row = session.exec(
        select(RevisionArtifactRecord)
        .where(
            RevisionArtifactRecord.revision_id == record.id,
            RevisionArtifactRecord.kind == "ifc",
            RevisionArtifactRecord.input_sha256 == model.fingerprint(),
        )
        .order_by(RevisionArtifactRecord.id.desc())
    ).first()
    return row.sha256 if row else None


# --- Trabajo de previsualización ---------------------------------------------------------


def build_preview(store: Store, job_id: str, config: dict) -> dict:
    """Candidato, IFC temporal, validación y delta. No publica nada."""
    import ifcopenshell

    from trazia.ifc import build_ifc, validate_ifc
    from trazia.revisions import compare

    from .jobs import emit

    timings = {}
    started = time.perf_counter()
    with Session(store.engine) as session:
        record = load(session, config["proposal_id"])
        if refresh(session, record):
            session.commit()
            raise ValueError(record.stale_reason)
        if record.proposal_sha256 != config["proposal_sha256"]:
            raise ValueError("La propuesta cambió durante la previsualización; repítela")
        evaluation, _, label, sha, _, base = compute(session, record)
    if sha != record.proposal_sha256:
        raise ValueError(
            "La revisión de destino o los datos cambiaron; vuelve a validar la propuesta"
        )
    if evaluation.status != "ready" or evaluation.candidate is None:
        raise ValueError(
            "La propuesta ya no es válida: "
            + "; ".join(i["message"] for i in evaluation.issues if i["severity"] == "error")[:1000]
        )
    candidate = evaluation.candidate
    timings["candidate_ms"] = round(1000 * (time.perf_counter() - started))
    emit(
        store,
        job_id,
        "candidate",
        "ok",
        "",
        f"Paso 1/{PREVIEW_STEPS} · candidato validado: "
        f"{len(evaluation.operations)} operaciones, revisión de destino {label}",
    )

    moment = time.perf_counter()
    model = build_ifc(candidate, draft=True, details=candidate.dataset == "synthetic")
    content = model.to_string().encode()
    timings["ifc_ms"] = round(1000 * (time.perf_counter() - moment))
    emit(
        store,
        job_id,
        "ifc",
        "ok",
        "",
        f"Paso 2/{PREVIEW_STEPS} · IFC4 DRAFT temporal generado ({len(content) // 1024} KiB)",
    )

    moment = time.perf_counter()
    issues = validate_ifc(model, express_rules=config.get("express_rules", True))
    timings["validation_ms"] = round(1000 * (time.perf_counter() - moment))
    if issues:
        raise ValueError("IFC inválido: " + issues[0]["message"][:1000])
    rules = "esquema y reglas EXPRESS" if config.get("express_rules", True) else "esquema"
    emit(store, job_id, "validate", "ok", "", f"Paso 3/{PREVIEW_STEPS} · IFC válido ({rules})")

    moment = time.perf_counter()
    delta = compare(base, candidate, include_visual=False)
    by_path = {}
    for operation in evaluation.operations:
        by_path.setdefault(operation["path"], []).append(operation["id"])
    changes = [
        {**change, "operation_ids": by_path.get(change["path"], [])} for change in delta["changes"]
    ]
    elements = element_map(base, candidate, evaluation, model)
    timings["delta_ms"] = round(1000 * (time.perf_counter() - moment))
    emit(
        store,
        job_id,
        "delta",
        "ok",
        "",
        f"Paso 4/{PREVIEW_STEPS} · {len(changes)} cambios "
        f"y {sum(e['geometry_changed'] for e in elements)} piezas regeneradas",
    )
    timings["total_ms"] = round(1000 * (time.perf_counter() - started))
    return {
        "ifc": content,
        "candidate_json": candidate.model_dump_json(),
        "params_sha256": candidate.fingerprint(),
        "proposal_sha256": sha,
        "preview": {
            "target_revision": label,
            "schema": "IFC4",
            "ifc_bytes": len(content),
            "params_sha256": candidate.fingerprint(),
            "generator_version": f"ifcopenshell {ifcopenshell.version}; motor {ENGINE_VERSION}",
            "validation": {"express_rules": config.get("express_rules", True), "issues": 0},
            "timings_ms": timings,
            "delta": {"summary": delta.get("summary"), "changes": changes},
            "elements": elements,
            "created_at": stamp(time.time()),
        },
    }


def element_map(base: Revision, candidate: Revision, evaluation, model) -> list[dict]:
    """Cada pieza del IFC temporal con su GUID estable y las operaciones que la afectan."""
    from trazia.families import parts
    from trazia.ifc import stable_guid

    before = {p.id: p for p in parts(base.equipment)}
    after = parts(candidate.equipment)
    effects = {e["part"]: e for e in evaluation.effects}
    conflicts = {i.get("nozzle_id") for i in evaluation.issues if i["code"] == "nozzle_conflict"}
    key = f"{candidate.project_id}/equipment/{candidate.equipment.id}"
    result = []
    for index, part in enumerate(after):
        guid = stable_guid(key if index == 0 else f"{key}/{part.guid_key}")
        try:
            present = model.by_guid(guid) is not None
        except RuntimeError:
            present = False
        effect = effects.get(part.id, {})
        result.append(
            {
                "part": part.id,
                "semantic_id": SEMANTIC.get(part.id)
                or (f"nozzle:{part.id}" if part.ifc_class == "IfcPipeSegment" else part.id),
                "global_id": guid,
                "in_ifc": present,
                "existed_before": part.id in before,
                "geometry_changed": before.get(part.id) != part,
                "conflict": part.id in conflicts,
                "operations": effect.get("operations", []),
            }
        )
    return result


async def run_preview_job(store: Store, job_id: str):
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

    from .jobs import JobCancelled

    started = time.perf_counter()
    status, error, sha = "error", None, None
    try:
        async with asyncio.timeout(config["timeout_seconds"]):
            result = await asyncio.to_thread(build_preview, store, job_id, config)
        sha = store.put(result["ifc"])
        with Session(store.engine) as session:
            job = session.get(JobRecord, job_id)
            record = load(session, config["proposal_id"])
            refresh(session, record)
            # Publicación única y condicionada: cancelar o editar la propuesta lo impide.
            if job.cancel_requested or job.status != "running":
                raise JobCancelled("Previsualización cancelada")
            if record.status not in ("ready", "previewed") or (
                record.proposal_sha256 != result["proposal_sha256"]
            ):
                raise ValueError("La propuesta cambió durante la previsualización; repítela")
            previous = record.preview_ifc_sha256
            record.status = "previewed"
            record.preview_ifc_sha256 = sha
            record.preview_json = json.dumps(result["preview"], ensure_ascii=False)
            record.candidate_json = result["candidate_json"]
            record.params_sha256 = result["params_sha256"]
            record.generator_version = result["preview"]["generator_version"]
            record.updated_at = time.time()
            record.expires_at = record.updated_at + ttl()
            record.stale_reason = None
            session.add(record)
            session.commit()
            if previous and previous != sha and not referenced(session, previous):
                store.discard(previous)
        status = "done"
    except asyncio.CancelledError:
        status = "queued"
        raise
    except TimeoutError:
        status, error = "timeout", "Tiempo máximo de previsualización agotado"
    except JobCancelled:
        status = "cancelled"
    except Exception as failure:
        error = str(failure)[-4000:]
    finally:
        with Session(store.engine) as session:
            job = session.get(JobRecord, job_id)
            if job.cancel_requested or job.status == "cancelled":
                status = "cancelled"
            if status != "done" and sha and not referenced(session, sha):
                store.discard(sha)
            job.status, job.error = status, error
            job.updated_at, job.lease_until = time.time(), None
            job.result_sha256 = sha if status == "done" else None
            job.elapsed_seconds = time.perf_counter() - started
            session.add(job)
            session.add(
                EventRecord(
                    job_id=job_id,
                    stage="job",
                    status="ok" if status == "done" else "error",
                    file="",
                    detail="Previsualización lista" if status == "done" else error or status,
                )
            )
            session.commit()
    return None
