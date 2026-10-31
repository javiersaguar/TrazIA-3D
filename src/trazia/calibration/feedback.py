"""Convierte intervenciones del JSONL en etiquetas de revisiones aprobadas vigentes."""

import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from sqlmodel import Session, select

from trazia.model import Revision, fields
from trazia.store import AuditRecord, CorrectionRecord, RevisionRecord, Store

from . import conformal


def training_rows(store: Store, ledger: Path) -> tuple[list[dict], dict]:
    """Una etiqueta por predicción original, nunca por cada clic repetido.

    El JSONL selecciona intervenciones; SQL acredita su autenticidad, la predicción previa y
    la aprobación vigente. No se usa una corrección histórica como verdad por sí sola.
    """
    counts = Counter()
    snapshot = ledger.read_bytes()
    with Session(store.engine) as session:
        known = {r.payload_json for r in session.exec(select(CorrectionRecord)).all()}
        selected = defaultdict(list)
        for text in snapshot.decode("utf-8").splitlines():
            if not text.strip():
                continue
            counts["ledger_rows"] += 1
            if text not in known:
                counts["unverified"] += 1
                continue
            row = json.loads(text)
            selected[(row["revision_id"], row["path"])].append(row)
        rows = []
        for (identity, path), interventions in selected.items():
            record = session.get(RevisionRecord, identity)
            if record is None:
                counts["missing_revision"] += 1
                continue
            current = Revision.model_validate_json(record.payload)
            if (
                current.dataset != "synthetic"
                or current.approval is None
                or current.approval.input_sha256 != current.fingerprint()
            ):
                counts["unapproved_or_non_synthetic"] += 1
                continue
            last = max(interventions, key=lambda r: r["at"])
            final = fields(current.equipment).get(path)
            if (
                final is None
                or final.state not in ("accepted", "corrected")
                or (final.value, final.unit, final.state)
                != (last["value_after"], last["unit"], last["state_after"])
            ):
                counts["superseded"] += 1
                continue
            audits = session.exec(
                select(AuditRecord)
                .where(AuditRecord.revision_id == identity, AuditRecord.path == path)
                .order_by(AuditRecord.id)
            ).all()
            if not audits:
                counts["missing_prediction"] += 1
                continue
            prediction = fields(Revision.model_validate_json(audits[0].before_json).equipment)[path]
            source = prediction.source
            if (
                prediction.state in ("accepted", "corrected", "assumed")
                or source.channel == "humano"
            ):
                counts["not_model_prediction"] += 1
                continue
            raw = source.confidence_raw
            if raw is None:
                # Sin confianza bruta identificable no se vuelve a calibrar una ya calibrada.
                counts["missing_raw_confidence"] += 1
                continue
            strategy = source.strategy or (current.run.strategy if current.run else None)
            if not strategy or not math.isfinite(raw):
                counts["missing_strategy"] += 1
                continue
            for document in current.documents:
                store.read(document.sha256)
            if prediction.unit != final.unit:
                counts["unit_change_unusable"] += 1
                continue  # No etiquetar como error una conversión que aún no se ha normalizado.
            numeric = isinstance(prediction.value, (float, int)) and isinstance(
                final.value, (float, int)
            )
            same_unit = prediction.unit == final.unit
            kind = conformal.kind_of(prediction.value, prediction.unit) if same_unit else None
            residual = (
                conformal.residual(kind, prediction.value, final.value)
                if numeric and kind
                else None
            )
            correct = (
                (residual == 0)
                if residual is not None
                else (
                    str(prediction.value).strip().upper() == str(final.value).strip().upper()
                    if isinstance(prediction.value, str) and isinstance(final.value, str)
                    else prediction.value == final.value
                )
            )
            rows.append(
                {
                    "tag": current.equipment.tag.value,
                    "revision_id": identity,
                    "path": path,
                    "strategy": strategy,
                    "channel": source.channel or "*",
                    # El ledger no demuestra si el PDF tiene capa de texto: curva por canal.
                    "media": "unknown",
                    "raw": raw,
                    "correct": correct,
                    "kind": kind,
                    "residual": residual,
                    "approval_sha256": current.approval.input_sha256,
                    "document_id": source.document_id,
                    "page": source.page,
                    "bbox": source.bbox,
                    "prediction": prediction.value,
                    "value": final.value,
                    "unit": final.unit,
                }
            )
        counts["usable_fields"] = len(rows)
        counts["equipment"] = len({r["tag"] for r in rows})
        return rows, {
            **dict(counts),
            "ledger_sha256": hashlib.sha256(snapshot).hexdigest(),
        }
