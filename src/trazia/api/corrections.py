"""Registro transaccional y salida JSONL recuperable de correcciones humanas."""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlmodel import Session, select

from trazia.model import fields
from trazia.store import CorrectionCursorRecord, CorrectionRecord


def record_change(session, record, before, after, path, actor):
    old, new = fields(before.equipment).get(path), fields(after.equipment).get(path)
    if old is None or new is None:
        return
    if (old.value, old.unit, old.state) == (new.value, new.unit, new.state):
        return
    source = old.source
    at = datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    payload = {
        "revision_id": record.id,
        "equipment_tag": after.equipment.tag.value,
        "revision": after.revision,
        "path": path,
        "value_before": old.value,
        "value_after": new.value,
        "unit": new.unit,
        "state_before": old.state,
        "state_after": new.state,
        "confidence": source.confidence,
        "confidence_raw": source.confidence_raw,
        "channel": source.channel,
        "strategy": source.strategy,
        "document_id": source.document_id,
        "page": source.page,
        "bbox": list(source.bbox) if source.bbox is not None else None,
        "actor": actor,
        "at": at,
        "data_sha256": after.fingerprint(),
    }
    session.add(CorrectionRecord(at=at, payload_json=json.dumps(payload, ensure_ascii=False)))


def append_records(path: Path, offset: int, records) -> int:
    with path.open("r+b" if path.exists() else "w+b") as stream:
        stream.seek(offset)
        # Elimina únicamente una cola que no llegó a confirmarse en SQL tras un fallo.
        stream.truncate()
        for row in records:
            stream.write(row.payload_json.encode("utf-8") + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
        return stream.tell()


def flush(store, path: Path):
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(str(path).encode()).hexdigest()
    insert = pg_insert if store.engine.dialect.name == "postgresql" else sqlite_insert
    # Confirmar el cursor antes de escribir permite recuperar también el primer lote fallido.
    with Session(store.engine) as session:
        session.exec(
            insert(CorrectionCursorRecord)
            .values(
                key=key,
                byte_offset=path.stat().st_size if path.exists() else 0,
            )
            .on_conflict_do_nothing(index_elements=["key"])
        )
        session.commit()
    with Session(store.engine) as session:
        # UPDATE toma un bloqueo de escritura en SQLite y de fila en Postgres.
        session.exec(
            update(CorrectionCursorRecord)
            .where(CorrectionCursorRecord.key == key)
            .values(
                byte_offset=CorrectionCursorRecord.byte_offset,
            )
        )
        cursor = session.get(CorrectionCursorRecord, key)
        records = session.exec(
            select(CorrectionRecord)
            .where(
                CorrectionRecord.exported.is_(False),
            )
            .order_by(CorrectionRecord.id)
        ).all()
        size = path.stat().st_size if path.exists() else 0
        if size < cursor.byte_offset:
            # Archivo perdido/truncado: la tabla conserva todas las líneas confirmadas.
            records = session.exec(select(CorrectionRecord).order_by(CorrectionRecord.id)).all()
            cursor.byte_offset = 0
        if records or size > cursor.byte_offset:
            cursor.byte_offset = append_records(path, cursor.byte_offset, records)
            for row in records:
                row.exported = True
                session.add(row)
            session.add(cursor)
        session.commit()


def read(store, since: datetime | None):
    with Session(store.engine) as session:
        query = select(CorrectionRecord).order_by(CorrectionRecord.at, CorrectionRecord.id)
        if since:
            stamp = since.astimezone(timezone.utc).isoformat(timespec="microseconds")
            query = query.where(CorrectionRecord.at >= stamp.replace("+00:00", "Z"))
        return [json.loads(row.payload_json) for row in session.exec(query).all()]
