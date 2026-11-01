"""Marcas de revisión de un GA: triángulos Δ y nubes (ROADMAP F.5).

Un plano revisado suele marcar lo que cambia con un triángulo con la letra de la revisión junto a
la fila o la cota, o con una nube alrededor de la zona. Aquí solo se leen las marcas; con ellas,
`check_changes` señala los cambios detectados fuera de toda marca y las marcas sin cambio.

- PDF vectorial: por la forma del trazo (triángulo cerrado pequeño, o contorno de muchos arcos),
  nunca por el color, que cambia de un proveedor a otro.
- PDF escaneado: sin lectura. Con contornos de OpenCV no se encontró ninguno de los 47 Δ de los
  escaneados sintéticos de S-dev (el trazo fino y en color se aclara y se parte al escanear), así
  que esas páginas se devuelven como no leídas en vez de inventar marcas. Queda para el detector
  propio (2.4) o la visión.

Son pistas, no lecturas certificadas: una marca no prueba un cambio y su ausencia tampoco prueba
que no lo haya.
"""

import io
import math
from dataclasses import dataclass
from typing import Literal

import pdfplumber

DELTA_SIZE_PT = (5.0, 30.0)  # lado de un triángulo de revisión
CLOUD_MIN_ARCS = 8  # una nube es un contorno cerrado de muchos arcos
# Una marca Δ va junto a la fila o la cota que cambia: misma altura y a poca distancia.
ROW_TOLERANCE = 0.02  # fracción de la altura de la página
ROW_REACH = 0.35  # fracción de la anchura de la página


@dataclass(frozen=True)
class RevisionMark:
    kind: Literal["delta", "cloud"]
    page: int
    bbox: tuple[float, float, float, float]  # normalizada, origen arriba a la izquierda
    label: str | None  # texto dentro del triángulo (la revisión), si lo hay
    method: Literal["vector"]


@dataclass(frozen=True)
class MarkReading:
    marks: list[RevisionMark]
    unread_pages: list[int]  # páginas escaneadas: no se sabe si llevan marcas


def find_marks(pdf: bytes, *, pages: list[int] | None = None) -> MarkReading:
    """Marcas de revisión de las páginas indicadas (todas por defecto)."""
    marks: list[RevisionMark] = []
    unread: list[int] = []
    with pdfplumber.open(io.BytesIO(pdf)) as document:
        for number in pages or range(1, len(document.pages) + 1):
            page = document.pages[number - 1]
            if page.chars or page.curves or page.lines:
                marks += _vector_marks(page, number)
            else:
                unread.append(number)
    return MarkReading(marks, unread)


def _vector_marks(page, number: int) -> list[RevisionMark]:
    width, height = float(page.width), float(page.height)
    out = []
    for curve in page.curves:
        path = curve.get("path") or []
        box = (curve["x0"], curve["top"], curve["x1"], curve["bottom"])
        if _is_triangle(curve.get("pts") or [], path):
            label = _label_inside(page, box)
            out.append(
                RevisionMark("delta", number, _normalise(box, width, height), label, "vector")
            )
        elif sum(1 for op in path if op[0] == "c") >= CLOUD_MIN_ARCS and _closed(path, curve):
            out.append(
                RevisionMark("cloud", number, _normalise(box, width, height), None, "vector")
            )
    return out


def _closed(path, curve) -> bool:
    if any(op[0] == "h" for op in path):
        return True
    pts = curve.get("pts") or []
    return len(pts) > 2 and math.dist(pts[0], pts[-1]) < 2.0


def _is_triangle(pts, path) -> bool:
    if any(op[0] == "c" for op in path):
        return False
    vertices = []
    for point in pts:
        if not any(math.dist(point, v) < 0.5 for v in vertices):
            vertices.append(point)
    if len(vertices) != 3:
        return False
    sides = [math.dist(vertices[i], vertices[(i + 1) % 3]) for i in range(3)]
    low, high = DELTA_SIZE_PT
    if not all(low <= s <= high for s in sides):
        return False
    return max(sides) / min(sides) < 1.6  # casi equilátero: no es una flecha ni una punta de cota


def _label_inside(page, box) -> str | None:
    x0, top, x1, bottom = box
    chars = [
        c
        for c in page.chars
        if x0 <= (c["x0"] + c["x1"]) / 2 <= x1 and top <= (c["top"] + c["bottom"]) / 2 <= bottom
    ]
    text = "".join(c["text"] for c in sorted(chars, key=lambda c: c["x0"])).strip()
    return text or None


def _normalise(box, width: float, height: float) -> tuple[float, float, float, float]:
    x0, top, x1, bottom = box
    return (
        max(0.0, x0 / width),
        max(0.0, top / height),
        min(1.0, x1 / width),
        min(1.0, bottom / height),
    )


def _area(box) -> float:
    return (box[2] - box[0]) * (box[3] - box[1])


def _overlap(a, b) -> bool:
    return max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])


def covers(mark: RevisionMark, page: int, bbox) -> bool:
    """¿La marca señala el campo de esa caja? Nube: lo rodea. Δ: está en su fila, cerca."""
    if mark.page != page or bbox is None:
        return False
    cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
    if mark.kind == "cloud":
        x0, y0, x1, y1 = mark.bbox
        return x0 <= cx <= x1 and y0 <= cy <= y1
    my = (mark.bbox[1] + mark.bbox[3]) / 2
    gap = max(mark.bbox[0] - bbox[2], bbox[0] - mark.bbox[2], 0.0)
    return abs(my - cy) <= ROW_TOLERANCE and gap <= ROW_REACH


def _entity(path: str) -> str:
    """Lo que señala una marca: el Δ de una fila de boquilla vale para todos sus campos."""
    parts = path.split(".")
    return ".".join(parts[:2]) if parts[0] == "nozzles" and len(parts) > 2 else path


def _locations(change: dict) -> list[tuple[int, tuple]]:
    """Dónde se leyó el campo: la lectura elegida y las demás (`locations`), si las hay."""
    found = [(loc.get("page"), loc.get("bbox")) for loc in change.get("locations", [])]
    if change.get("bbox") is not None:
        found.insert(0, (change.get("page"), change["bbox"]))
    return [(page, box) for page, box in found if box is not None]


def check_changes(changes: list[dict], reading: MarkReading) -> dict:
    """Cruza los cambios detectados con las marcas de la revisión nueva.

    Cada cambio trae `path` y, si se conocen, `page` y `bbox` de su lectura en la revisión nueva, y
    en `locations` las otras lecturas del mismo campo: el plano puede marcar la fila de la tabla y
    el valor haberse leído en el dibujo. Un cambio está marcado si alguna de sus lecturas, o la de
    otro campo de la misma boquilla, está junto a una marca.

    Si el plano no lleva ninguna marca no se señala nada: muchos proveedores no las usan. Un cambio
    en una página escaneada tampoco se señala: allí no se han podido leer las marcas.
    """
    marks = reading.marks
    status = "parcial" if reading.unread_pages else "ok"
    if not marks:
        status = "sin_lectura" if reading.unread_pages else "sin_marcas"
        return {"status": status, "unmarked_changes": [], "marks_without_change": []}
    used: set[int] = set()
    marked_entities: set[str] = set()
    located = []
    for change in changes:
        places = [(pg, box) for pg, box in _locations(change) if pg not in reading.unread_pages]
        if not places:
            continue
        hits = {i for i, m in enumerate(marks) for pg, box in places if covers(m, pg, box)}
        used |= hits
        if hits:
            marked_entities.add(_entity(change["path"]))
        located.append(change["path"])
    unmarked = [path for path in located if _entity(path) not in marked_entities]
    orphans = [m for i, m in enumerate(marks) if i not in used]
    return {"status": status, "unmarked_changes": unmarked, "marks_without_change": orphans}
