"""Sesiones declaradas de revisión; el reloj del cliente no demuestra uso humano."""

import time
import uuid

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from trazia.model import Revision
from trazia.store import AuditRecord, ReviewSessionRecord, RevisionRecord


class SessionInput(BaseModel):
    revision_id: str
    actor: str = Field(min_length=2, max_length=100)
    kind: str = Field(default="human", pattern="^(human|test)$")


class FinishInput(BaseModel):
    active_seconds: float = Field(ge=0, allow_inf_nan=False)


def start(session: Session, revision, body: SessionInput):
    record = ReviewSessionRecord(
        id=uuid.uuid4().hex,
        revision_id=revision.id,
        actor=body.actor.strip(),
        kind=body.kind,
        dataset=Revision.model_validate_json(revision.payload).dataset,
    )
    if len(record.actor) < 2:
        raise HTTPException(422, "Indica el nombre del revisor")
    session.add(record)
    session.flush()
    return record.model_dump()


def validate_clock(session: Session, identity: str, revision_id: str, actor: str, seconds):
    record = session.get(ReviewSessionRecord, identity)
    if not record or record.revision_id != revision_id or record.actor != actor:
        raise HTTPException(422, "La sesión no corresponde a esta revisión y revisor")
    if record.finished_at is not None:
        raise HTTPException(409, "La sesión ya está finalizada; inicia otra sesión")
    if seconds is None:
        raise HTTPException(422, "Envía el tiempo activo de esta acción")
    used = sum(
        row.seconds or 0
        for row in session.exec(
            select(AuditRecord).where(AuditRecord.review_session_id == identity)
        ).all()
    )
    if used + seconds > time.time() - record.started_at + 2:
        raise HTTPException(422, "El tiempo activo supera la duración de la sesión")
    return record


def finish(session: Session, identity: str, seconds: float):
    record = session.get(ReviewSessionRecord, identity)
    if not record:
        raise HTTPException(404, "No existe la sesión de revisión")
    if record.finished_at is not None:
        return record.model_dump()
    validate_clock(session, identity, record.revision_id, record.actor, 0)
    used = sum(
        row.seconds or 0
        for row in session.exec(
            select(AuditRecord).where(AuditRecord.review_session_id == identity)
        ).all()
    )
    if seconds + 0.01 < used or seconds > time.time() - record.started_at + 2:
        raise HTTPException(422, "El tiempo final debe incluir las acciones y caber en la sesión")
    record.active_seconds = seconds
    record.finished_at = time.time()
    session.add(record)
    session.commit()
    session.refresh(record)
    return record.model_dump()


def metrics(session: Session, revision_id: str):
    records = session.exec(
        select(ReviewSessionRecord).where(ReviewSessionRecord.revision_id == revision_id)
    ).all()
    human = [r for r in records if r.kind == "human" and r.finished_at is not None]
    reviewed = {
        a.review_session_id
        for a in session.exec(select(AuditRecord).where(AuditRecord.revision_id == revision_id))
        if not a.path.startswith("$")
    }
    measured = [r for r in human if r.id in reviewed]
    return {
        "revision_id": revision_id,
        "measurement": "active_client_reported",
        "human_participation": "self_declared",
        "completed_human_sessions": len(human),
        "measurable_review_sessions": len(measured),
        "active_seconds": sum(r.active_seconds for r in measured) if measured else None,
        "test_sessions": sum(r.kind == "test" for r in records),
        "open_sessions": sum(r.finished_at is None for r in records),
        "sessions": [r.model_dump() for r in records],
    }


def equipment_metrics(session: Session, tag: str, project_id: str | None):
    statement = select(RevisionRecord).where(RevisionRecord.tag == tag)
    if project_id:
        statement = statement.where(RevisionRecord.project_id == project_id)
    groups = {}
    for record in session.exec(statement).all():
        model = Revision.model_validate_json(record.payload)
        key = (record.project_id, record.equipment_id, model.dataset)
        group = groups.setdefault(
            key,
            {
                "project_id": key[0],
                "equipment_id": key[1],
                "dataset": key[2],
                "equipment_tag": tag,
                "revisions": [],
            },
        )
        measure = metrics(session, record.id)
        group["revisions"].append(
            {
                **measure,
                "approved": model.approval is not None,
                "pending_fields": len(model.pending_review()),
            }
        )
    for group in groups.values():
        known = [r["active_seconds"] for r in group["revisions"] if r["active_seconds"] is not None]
        group["active_seconds"] = sum(known) if known else None
        group["all_revisions_approved"] = all(r["approved"] for r in group["revisions"])
    return {
        "equipment": list(groups.values()),
        "measurement": "active_client_reported",
        "usage_sample_verified": False,
    }
