"""Plano de orientación de boquillas (VESOR) sintético, para probar su lectura (ROADMAP 2.1).

Una planta con cada boquilla dibujada en su ángulo y rotulada («N3 135°») y, si se pide, la
tabla de orientación del proveedor (marca, tamaño y orientación). Los ángulos se escriben con el
convenio del proveedor, igual que en su GA. No forma parte de los conjuntos S-*: no cambia el
estudio. Lleva el pie «SYNTHETIC TEST DOCUMENT».
"""

import io
import math

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfgen.canvas import Canvas

from .cases import VesselSpec
from .vendors import Vendor, fmt_angle, fmt_size, printed_azimuth

INK = HexColor("#1b2a38")
PAGE_W, PAGE_H = landscape(A3)
TITLES = {"en": "NOZZLE ORIENTATION", "es": "ORIENTACIÓN DE TOBERAS"}


def render_vesor(
    spec: VesselSpec,
    vendor: Vendor,
    revision: str = "1",
    *,
    table: bool = True,
    azimuths: dict[str, float] | None = None,
) -> bytes:
    """PDF vectorial del VESOR. `azimuths` sustituye ángulos (para provocar discrepancias)."""
    azimuths = azimuths or {}
    buffer = io.BytesIO()
    canvas = Canvas(buffer, pagesize=(PAGE_W, PAGE_H))
    canvas.setTitle(f"VESOR {spec.tag} rev {revision}")
    canvas.setStrokeColor(INK)
    canvas.setFillColor(INK)
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(40, PAGE_H - 50, f"{TITLES[vendor.lang]} · {spec.tag} · REV {revision}")

    # Planta: el ángulo impreso se dibuja con el convenio del proveedor.
    cx, cy, radius = 380.0, 420.0, 170.0
    canvas.circle(cx, cy, radius)
    canvas.line(cx, cy + radius + 10, cx, cy + radius + 40)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawCentredString(cx, cy + radius + 46, "N")
    canvas.setFont("Helvetica", 9)
    stacked: dict[float, int] = {}  # boquillas en el mismo ángulo: rótulos apilados hacia fuera
    for nozzle in spec.nozzles:
        truth = azimuths.get(nozzle.id, nozzle.azimuth)
        angle = math.radians(truth)  # antihorario desde +X, como la verdad
        x1, y1 = cx + radius * math.cos(angle), cy + radius * math.sin(angle)
        x2, y2 = cx + (radius + 30) * math.cos(angle), cy + (radius + 30) * math.sin(angle)
        canvas.line(x1, y1, x2, y2)
        level = stacked.get(truth % 360, 0)
        stacked[truth % 360] = level + 1
        label = f"{nozzle.id} {fmt_angle(truth, vendor)}"
        reach = radius + 48 + 16 * level
        lx, ly = cx + reach * math.cos(angle), cy + reach * math.sin(angle) - 14 * level
        canvas.drawCentredString(lx, ly - 3, label)

    if table:
        columns = [c for c in vendor.columns if c.key in ("mark", "size", "azimuth")]
        tx, ty, row_h = 760.0, 640.0, 18
        total_w = sum(c.width for c in columns)
        rows = len(spec.nozzles) + 1
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(tx, ty + 14, TITLES[vendor.lang])
        canvas.setLineWidth(0.6)
        canvas.rect(tx, ty - row_h * rows, total_w, row_h * rows)
        x = tx
        canvas.setFont("Helvetica-Bold", 7.5)
        for column in columns:
            canvas.drawString(x + 4, ty - 12, column.header)
            x += column.width
            canvas.line(x, ty, x, ty - row_h * rows)
        canvas.setFont("Helvetica", 8)
        for i, nozzle in enumerate(spec.nozzles):
            y = ty - row_h * (i + 1)
            canvas.line(tx, y, tx + total_w, y)
            values = {
                "mark": nozzle.id,
                "size": fmt_size(nozzle.diameter, vendor),
                "azimuth": fmt_angle(azimuths.get(nozzle.id, nozzle.azimuth), vendor),
            }
            x = tx
            for column in columns:
                canvas.drawString(x + 4, y - 12, values[column.key])
                x += column.width

    canvas.setFont("Helvetica", 7)
    canvas.drawString(40, 24, "SYNTHETIC TEST DOCUMENT · no es un plano real")
    canvas.showPage()
    canvas.save()
    return buffer.getvalue()


def printed(spec: VesselSpec, vendor: Vendor) -> dict[str, float]:
    """Ángulo impreso por boquilla: lo que debe leer B."""
    return {n.id: printed_azimuth(n.azimuth, vendor) for n in spec.nozzles}
