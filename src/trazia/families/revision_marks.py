"""Cruce documental F.5: pistas vectoriales, nunca aprobación ni ausencia de cambios."""

import hashlib
import io
from dataclasses import asdict

import pdfplumber

from ..extractors.revision_marks import MarkReading, check_changes, find_marks
from ..model import fields


def entity(path):
    parts = path.split(".")
    return ".".join(parts[:2]) if len(parts) > 1 and parts[0] == "nozzles" else path


def locations(after, changes):
    """Solo coordenadas de la revisión nueva; no se trasladan cajas antiguas sin alinear."""
    current = fields(after.equipment)
    result = []
    for change in changes:
        related = [
            f
            for path, f in current.items()
            if path == change["path"]
            or (change["path"].startswith("nozzles.") and entity(path) == entity(change["path"]))
        ]
        sources = [
            source for f in related for source in [f.source, *(a.source for a in f.alternatives)]
        ]
        points = []
        for source in sources:
            if source.page is not None and source.bbox is not None:
                point = {
                    "document_id": source.document_id,
                    "page": source.page,
                    "bbox": list(source.bbox),
                }
                if point not in points:
                    points.append(point)
        result.append({"path": change["path"], "locations": points})
    return result


def analyse(after, changes, originals):
    result = {
        "status": "missing_originals",
        "documents": [],
        "unmarked_changes": [],
        "marks_without_change": [],
        "unlocated_changes": [],
        "coordinate_frame": "after-page",
        "is_design_validation": False,
        "detail": (
            "Las marcas son pistas: no prueban cambios ni su ausencia. No conceden aprobación."
        ),
    }
    if originals is None:
        return result
    located = locations(after, changes)
    pdfs = [d for d in after.documents if d.filename.lower().endswith(".pdf")]
    result["unlocated_changes"] = [c["path"] for c in located if not c["locations"]]
    for document in pdfs:
        item = {
            "document_id": document.id,
            "filename": document.filename,
            "sha256": document.sha256,
            "marks": [],
            "unread_pages": [],
        }
        result["documents"].append(item)
        data = originals.get(document.sha256)
        if data is None:
            item["status"] = "missing_original"
            continue
        if hashlib.sha256(data).hexdigest() != document.sha256:
            item["status"] = "hash_mismatch"
            continue
        try:
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                count = len(pdf.pages)
                # Un encabezado vectorial no convierte el cuerpo escaneado en marcas legibles.
                raster = [
                    p.page_number
                    for p in pdf.pages[:100]
                    if any(
                        float(image.get("width", 0)) * float(image.get("height", 0))
                        >= 0.5 * float(p.width) * float(p.height)
                        for image in p.images
                    )
                ]
            reading = find_marks(data, pages=list(range(1, min(100, count) + 1)))
        except Exception as exc:
            item.update(
                status="unreadable", detail=f"No se pueden leer marcas: {type(exc).__name__}"
            )
            continue
        candidates = [
            {
                "path": c["path"],
                "locations": [p for p in c["locations"] if p["document_id"] == document.id],
            }
            for c in located
        ]
        unknown = sorted(set(reading.unread_pages) | set(raster) | set(range(101, count + 1)))
        checks = check_changes(
            candidates, MarkReading([m for m in reading.marks if m.page not in unknown], unknown)
        )
        item.update(
            status=checks["status"],
            unread_pages=unknown,
            page_count=count,
            pages_truncated=count > 100,
        )
        for mark in reading.marks:
            raw = asdict(mark)
            identity = hashlib.sha256(repr((document.sha256, raw)).encode()).hexdigest()[:20]
            item["marks"].append(
                {"id": identity, "document_id": document.id, **raw, "candidate": True}
            )
        result["unmarked_changes"].extend(
            {
                "path": path,
                "document_id": document.id,
                "locations": next(c["locations"] for c in candidates if c["path"] == path),
            }
            for path in checks["unmarked_changes"]
        )
        for mark in checks["marks_without_change"]:
            raw = asdict(mark)
            result["marks_without_change"].append(
                next(m for m in item["marks"] if all(m[key] == value for key, value in raw.items()))
            )
    statuses = [d["status"] for d in result["documents"]]
    usable = {"ok", "sin_marcas", "parcial", "sin_lectura"}
    result["status"] = (
        "not_applicable"
        if not statuses
        else "unavailable"
        if not any(s in usable for s in statuses)
        else "ok"
        if all(s in ("ok", "sin_marcas") for s in statuses)
        and not any(d.get("pages_truncated") for d in result["documents"])
        else "partial"
    )
    return result
