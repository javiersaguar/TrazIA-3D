"""Marcas de revisión: Δ y nubes en el GA y su cruce con los cambios (ROADMAP F.5)."""

import io
import math

from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfgen.canvas import Canvas

from trazia.extractors.revision_marks import MarkReading, RevisionMark, check_changes, find_marks
from trazia.ingest import image_to_pdf


def _pdf(draw) -> bytes:
    buffer = io.BytesIO()
    canvas = Canvas(buffer, pagesize=landscape(A3))
    canvas.setFont("Helvetica", 8)
    canvas.drawString(100, 700, "N1 DN 50 EL 9150")  # texto normal del plano
    draw(canvas)
    canvas.showPage()
    canvas.save()
    return buffer.getvalue()


def _delta(canvas, x, y, label="2"):
    path = canvas.beginPath()
    path.moveTo(x, y)
    path.lineTo(x + 12, y)
    path.lineTo(x + 6, y + 10)
    path.close()
    canvas.drawPath(path, stroke=1, fill=0)
    canvas.setFont("Helvetica-Bold", 6)
    canvas.drawCentredString(x + 6, y + 2, label)


def _cloud(canvas, cx, cy, radius, scallops=12):
    path = canvas.beginPath()
    step = 2 * math.pi / scallops
    path.moveTo(cx + radius, cy)
    for i in range(scallops):
        a0, a1 = i * step, (i + 1) * step
        mid = (a0 + a1) / 2
        x1, y1 = cx + radius * math.cos(a1), cy + radius * math.sin(a1)
        bulge = radius * 1.25
        path.curveTo(
            cx + bulge * math.cos(mid - step / 4),
            cy + bulge * math.sin(mid - step / 4),
            cx + bulge * math.cos(mid + step / 4),
            cy + bulge * math.sin(mid + step / 4),
            x1,
            y1,
        )
    path.close()
    canvas.drawPath(path, stroke=1, fill=0)


def test_deltas_and_clouds_are_read_by_shape_with_their_label():
    def draw(canvas):
        _delta(canvas, 300, 400, label="B")
        _cloud(canvas, 700, 500, 60)
        canvas.line(100, 100, 400, 100)  # una línea suelta no es una marca
        arrow = canvas.beginPath()  # punta de flecha alargada de una cota
        arrow.moveTo(500, 200)
        arrow.lineTo(520, 203)
        arrow.lineTo(500, 206)
        arrow.close()
        canvas.drawPath(arrow, stroke=1, fill=1)

    reading = find_marks(_pdf(draw))
    assert reading.unread_pages == []
    kinds = sorted(m.kind for m in reading.marks)
    assert kinds == ["cloud", "delta"]
    [delta] = [m for m in reading.marks if m.kind == "delta"]
    assert delta.label == "B" and delta.page == 1 and delta.method == "vector"
    x0, y0, x1, y1 = delta.bbox
    assert 0 < x0 < x1 < 1 and 0 < y0 < y1 < 1


def test_a_scanned_page_is_reported_as_unread_instead_of_guessing():
    from PIL import Image

    blank = io.BytesIO()
    Image.new("RGB", (800, 600), "white").save(blank, "PNG")
    reading = find_marks(image_to_pdf(blank.getvalue()))
    assert reading.marks == [] and reading.unread_pages == [1]
    result = check_changes([{"path": "height", "page": 1, "bbox": (0.1, 0.1, 0.2, 0.2)}], reading)
    assert result["status"] == "sin_lectura" and result["unmarked_changes"] == []


def _mark(bbox, kind="delta"):
    return RevisionMark(kind, 1, bbox, "2", "vector")


def test_changes_outside_marks_and_marks_without_changes_are_flagged():
    row = _mark((0.60, 0.40, 0.61, 0.41))  # Δ al final de la fila de N7
    lonely = _mark((0.60, 0.80, 0.61, 0.81))  # Δ sin ningún cambio
    reading = MarkReading([row, lonely], [])
    changes = [
        # Leído en el dibujo, pero otra lectura del mismo campo está en la fila marcada.
        {
            "path": "nozzles.N7.elevation",
            "page": 1,
            "bbox": (0.90, 0.10, 0.92, 0.12),
            "locations": [{"page": 1, "bbox": (0.40, 0.40, 0.45, 0.41)}],
        },
        # Otro campo de la misma boquilla: lo cubre el Δ de su fila.
        {"path": "nozzles.N7.azimuth", "page": 1, "bbox": (0.90, 0.60, 0.92, 0.62)},
        # Un cambio sin marca cerca.
        {"path": "skirt_height", "page": 1, "bbox": (0.20, 0.70, 0.25, 0.71)},
        # Sin caja no se puede juzgar.
        {"path": "attributes.operating_weight"},
    ]
    result = check_changes(changes, reading)
    assert result["status"] == "ok"
    assert result["unmarked_changes"] == ["skirt_height"]
    assert result["marks_without_change"] == [lonely]


def test_a_cloud_marks_what_it_surrounds():
    cloud = _mark((0.30, 0.30, 0.50, 0.50), kind="cloud")
    inside = {"path": "height", "page": 1, "bbox": (0.35, 0.35, 0.40, 0.36)}
    outside = {"path": "diameter", "page": 1, "bbox": (0.70, 0.35, 0.75, 0.36)}
    result = check_changes([inside, outside], MarkReading([cloud], []))
    assert result["unmarked_changes"] == ["diameter"]
    assert result["marks_without_change"] == []


def test_a_plan_without_marks_flags_nothing():
    changes = [{"path": "height", "page": 1, "bbox": (0.1, 0.1, 0.2, 0.2)}]
    result = check_changes(changes, MarkReading([], []))
    assert result == {"status": "sin_marcas", "unmarked_changes": [], "marks_without_change": []}
