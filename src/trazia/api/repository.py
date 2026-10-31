import json
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import update
from sqlmodel import Session, select

from trazia.model import Revision, load_revision
from trazia.store import AuditRecord, DocumentRecord, RevisionRecord, Store


def revision_id(revision: Revision) -> str:
    return f"{revision.project_id}:{revision.equipment.id}:{revision.revision}"


def get_revision(session: Session, identity: str) -> RevisionRecord:
    record = session.get(RevisionRecord, identity)
    if record is None and identity in ("A", "B"):
        record = session.exec(
            select(RevisionRecord).where(
                RevisionRecord.project_id == "DEMO-PLANT",
                RevisionRecord.tag == "V-101",
                RevisionRecord.revision == identity,
            )
        ).first()
    if record is None:
        raise HTTPException(404, "No existe esa revisión")
    return record


def check_match(record: RevisionRecord, if_match: str | None):
    if if_match is None:
        raise HTTPException(428, "Se requiere If-Match con el ETag de la revisión")
    if if_match != f'"{record.version}"':
        raise HTTPException(412, "La revisión ha cambiado; vuelva a cargarla antes de editar")


def save_revision(
    session: Session,
    record: RevisionRecord,
    revision: Revision,
    *,
    path: str,
    actor: str,
    seconds: float | None = None,
    review_session_id: str | None = None,
    undo_of: int | None = None,
):
    before = record.payload
    version = record.version
    changed = session.exec(
        update(RevisionRecord)
        .where(RevisionRecord.id == record.id, RevisionRecord.version == version)
        .values(
            payload=revision.model_dump_json(),
            version=version + 1,
            tag=revision.equipment.tag.value,
        )
    )
    if changed.rowcount != 1:
        raise HTTPException(412, "Otra persona ha modificado la revisión")
    audit = AuditRecord(
        revision_id=record.id,
        path=path,
        actor=actor,
        before_json=before,
        after_json=revision.model_dump_json(),
        seconds=seconds,
        review_session_id=review_session_id,
        undo_of=undo_of,
    )
    session.add(audit)
    session.flush()
    from .corrections import record_change

    record_change(session, record, Revision.model_validate_json(before), revision, path, actor)
    return {
        "data": revision.model_dump(mode="json"),
        "version": version + 1,
        "status": 200,
        "audit_id": audit.id,
    }


def seed_demo(store: Store, root: Path):
    with Session(store.engine) as session:
        for suffix in ("a", "b"):
            revision = load_revision(root / "examples" / f"vessel_rev_{suffix}.json")
            identity = revision_id(revision)
            if session.get(RevisionRecord, identity):
                continue
            for document in revision.documents:
                content = (root / "examples" / "documents" / document.filename).read_bytes()
                digest = store.put(content)
                if digest != document.sha256:
                    raise ValueError("La demo no coincide con los hashes de sus originales")
                session.add(
                    DocumentRecord(
                        id=f"seed-{suffix}-{document.id}",
                        document_id=document.id,
                        filename=document.filename,
                        revision=document.revision,
                        sha256=digest,
                        size=len(content),
                    )
                )
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
        session.commit()


def read_report(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
