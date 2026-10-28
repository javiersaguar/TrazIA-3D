import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path

from .model import Approval, Revision, fields


def export_fields(revision: Revision, destination: Path) -> Path:
    """Tabla de revisión de solo lectura; conserva evidencia y no concede aprobación."""
    if destination.suffix.lower() not in (".csv", ".xlsx"):
        raise ValueError("La tabla de campos debe terminar en .csv o .xlsx")
    # También comprueba aprobaciones obsoletas de objetos modificados en memoria.
    revision = Revision.model_validate_json(revision.model_dump_json())
    documents = {d.id: d for d in revision.documents}
    rows = []
    fingerprint = revision.fingerprint()
    for path, field in sorted(fields(revision.equipment).items()):
        source = field.source
        document = documents[source.document_id]
        rows.append(
            {
                "project_id": revision.project_id,
                "equipment_id": revision.equipment.id,
                "revision": revision.revision,
                "dataset": revision.dataset,
                "revision_status": "APPROVED" if revision.approval else "DRAFT",
                "revision_sha256": fingerprint,
                "field": path,
                "value": field.value,
                "unit": field.unit,
                "state": field.state,
                "confidence": source.confidence,
                "reviewed": source.reviewed,
                "document_id": source.document_id,
                "document": document.filename,
                "document_sha256": document.sha256,
                "page": source.page,
                "sheet": source.sheet,
                "cell": source.cell,
                "locator": source.locator,
                "bbox": json.dumps(source.bbox) if source.bbox is not None else None,
                "text_original": source.text_original,
                "unit_original": source.unit_original,
                "channel": source.channel,
                "strategy": source.strategy,
                "model": source.model,
                "prompt_sha256": source.prompt_sha256,
                "grounded": source.grounded,
                "interval_low": field.interval.low if field.interval else None,
                "interval_high": field.interval.high if field.interval else None,
                "interval_level": field.interval.level if field.interval else None,
                "alternatives": json.dumps(
                    [a.model_dump(mode="json") for a in field.alternatives], ensure_ascii=False
                ),
                "explanation": field.explanation,
                "reviewer": revision.approval.reviewer if revision.approval else None,
            }
        )
    headers = list(rows[0])
    if destination.suffix.lower() == ".csv":
        text = io.StringIO(newline="")
        writer = csv.writer(text)
        writer.writerow(headers)
        for row in rows:
            # Las cadenas procedentes de documentos siguen siendo datos en Excel.
            writer.writerow(
                "'" + value
                if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@"))
                else value
                for value in row.values()
            )
        payload = text.getvalue().encode("utf-8-sig")
    else:
        from openpyxl import Workbook
        from openpyxl.cell import WriteOnlyCell
        from openpyxl.utils.exceptions import IllegalCharacterError

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Campos"
        sheet.append(headers)
        for row in rows:
            cells = []
            for value in row.values():
                if isinstance(value, str) and len(value) > 32767:
                    raise ValueError("Un texto supera el límite de Excel (32767 caracteres)")
                try:
                    cell = WriteOnlyCell(sheet, value=value)
                except IllegalCharacterError as error:
                    raise ValueError(
                        "Un texto contiene caracteres no representables en Excel"
                    ) from error
                if isinstance(value, str):
                    cell.data_type = "s"
                cells.append(cell)
            sheet.append(cells)
        sheet.freeze_panes = "G2"
        sheet.auto_filter.ref = sheet.dimensions
        buffer = io.BytesIO()
        workbook.save(buffer)
        payload = buffer.getvalue()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload)
    return destination


def verify_originals(revision: Revision, originals: dict[str, bytes]) -> list[str]:
    errors = []
    for document in revision.documents:
        data = originals.get(document.id)
        if data is None:
            errors.append(f"{document.id}: falta el original")
        elif hashlib.sha256(data).hexdigest() != document.sha256:
            errors.append(f"{document.id}: el SHA-256 no coincide")
    return errors


def approve(revision: Revision, reviewer: str, originals: dict[str, bytes]) -> Revision:
    if not reviewer.strip() or len(reviewer.strip()) < 2:
        raise ValueError("Indique quién ha revisado los datos")
    errors = verify_originals(revision, originals)
    if errors:
        raise ValueError("; ".join(errors))
    if any(
        f.state in ("conflict", "abstained", "assumed") for f in fields(revision.equipment).values()
    ):
        raise ValueError("Resuelva los conflictos, abstenciones y supuestos antes de aprobar")
    result = revision.model_copy(deep=True)
    result.approval = None
    for field in fields(result.equipment).values():
        if field.state != "corrected":
            field.state = "accepted"
        field.source.reviewed = True
    result.approval = Approval(
        reviewer=reviewer.strip(),
        timestamp=datetime.now(timezone.utc),
        input_sha256=result.fingerprint(),
    )
    return Revision.model_validate_json(result.model_dump_json())
