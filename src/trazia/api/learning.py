"""Entrega de correcciones aprobadas; no ajusta modelos ni modifica las revisiones."""

import hashlib

from sqlmodel import Session, select

from trazia.model import Revision, fields
from trazia.store import AuditRecord, RevisionRecord, Store


def approved_examples(store: Store, *, after: int = 0, limit: int = 100):
    examples = {}
    with Session(store.engine) as session:
        rows = session.exec(
            select(AuditRecord, RevisionRecord)
            .join(RevisionRecord, AuditRecord.revision_id == RevisionRecord.id)
            .where(AuditRecord.id > after)
            .order_by(AuditRecord.id)
            .limit(limit)
        ).all()
        for audit, record in rows:
            current = Revision.model_validate_json(record.payload)
            if current.dataset != "synthetic" or current.approval is None:
                continue
            before = Revision.model_validate_json(audit.before_json)
            corrected = Revision.model_validate_json(audit.after_json)
            old = fields(before.equipment).get(audit.path)
            new = fields(corrected.equipment).get(audit.path)
            final = fields(current.equipment).get(audit.path)
            if (
                not old
                or not new
                or not final
                or new.state != "corrected"
                or final.state != "corrected"
                or (old.value, old.unit) == (new.value, new.unit)
                or new.model_dump(mode="json") != final.model_dump(mode="json")
            ):
                continue
            documents = {d.id: d for d in current.documents}
            document = documents[final.source.document_id]
            # Una aprobación no sustituye la comprobación de que su original sigue disponible.
            store.read(document.sha256)
            identity = hashlib.sha256(
                f"{record.id}:{audit.path}:{current.approval.input_sha256}".encode()
            ).hexdigest()
            examples[identity] = {
                "id": identity,
                "audit_id": audit.id,
                "revision_id": record.id,
                "revision_version": record.version,
                "equipment_id": current.equipment.id,
                "path": audit.path,
                "prediction": old.model_dump(mode="json"),
                "correction": final.model_dump(mode="json"),
                "document": document.model_dump(mode="json"),
                "approval": current.approval.model_dump(mode="json"),
                "actor": audit.actor,
                "created_at": audit.created_at,
            }
    return {
        "schema_version": "1",
        "dataset": "synthetic",
        "examples": list(examples.values()),
        "next_cursor": rows[-1][0].id if len(rows) == limit else None,
        "recalibrated": False,
        "detail": "Correcciones aprobadas; sin entrenamiento ni recalibración ejecutados",
    }
