"""Ingesta robusta: un texto fuera de la página no tumba el PDF (hallazgo de docs/BENCH.md)."""

import io

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from trazia.ingest import ingest_bytes


def pdf_with_offpage_text() -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    pdf.drawString(72, height - 72, "DESIGN PRESSURE = 10 barg")
    pdf.drawString(width - 20, 300, "RECORTADO AL BORDE")  # se sale por la derecha
    pdf.drawString(width + 200, 300, "FUERA DEL TODO")  # completamente fuera
    pdf.drawString(72, -60, "DEBAJO DE LA PAGINA")  # fuera por abajo
    pdf.save()
    return buffer.getvalue()


def test_offpage_text_is_clipped_or_dropped_with_warning():
    bundle = ingest_bytes(pdf_with_offpage_text(), "GAD_X_rev1.pdf", "GA-X", "1")
    texts = [line.text for line in bundle.lines]
    assert "DESIGN PRESSURE = 10 barg" in texts
    assert not any("FUERA" in t or "DEBAJO" in t for t in texts)
    for line in bundle.lines:
        x0, y0, x1, y1 = line.source.bbox
        assert 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1
    assert any("descartado" in w for w in bundle.warnings)
    assert any("recortado" in w for w in bundle.warnings)


def test_corrupt_pdf_raises_value_error():
    with pytest.raises(ValueError, match="No es un PDF válido"):
        ingest_bytes(b"no es un pdf", "GAD_X_rev1.pdf", "GA-X", "1")
