"""GA sintéticos del generador v2: el estilo de cada proveedor, paquetes y degradación.

Un GA puede ocupar una o dos hojas (estilo «levante») e ir dentro de un paquete de proveedor:
portada, índice, GA y placa de características con valores distractores (prueba hidráulica,
sobreespesor de corrosión). Después se aplica la degradación: vectorial, escaneado limpio o
escaneado pobre.

Todo documento lleva el pie «SYNTHETIC TEST DOCUMENT»: nunca se confunde con uno real.
"""

import io
import math
import random
import zlib
from collections.abc import Callable
from dataclasses import dataclass

import pdfplumber
from PIL import Image, ImageEnhance, ImageFilter
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfgen.canvas import Canvas

from .cases import VesselSpec
from .vendors import (
    Vendor,
    fmt_angle,
    fmt_length,
    fmt_pressure,
    fmt_size,
    fmt_temperature,
    fmt_weight,
    printed_elevation,
)

INK = HexColor("#1b2a38")
FAINT = HexColor("#8a99a8")
ACCENT = HexColor("#0b6e8f")
REVISION = HexColor("#c2410c")
PAGE_W, PAGE_H = landscape(A3)
DEGRADATIONS = ("vectorial", "escaneado_limpio", "escaneado_pobre")

# Una función que dibuja trampas sobre la hoja indicada (corpus adversarial, DEC-32).
Overlay = Callable[[Canvas, int], None]


@dataclass(frozen=True)
class Layout:
    elev_x: float
    elev_base: float
    elev_budget: float
    plan: tuple[float, float]
    table: tuple[float, float]
    design: tuple[float, float] | None  # None: debajo de la tabla
    notes: tuple[float, float]


LAYOUTS = {
    "right": Layout(200, 110, 600, (520, 560), (700, 760), None, (700, 230)),
    "left": Layout(660, 150, 560, (1000, 560), (40, 770), None, (40, 230)),
    "bottom": Layout(200, 350, 370, (560, 610), (40, 270), (560, 270), (880, 790)),
    "page2": Layout(300, 110, 600, (820, 520), (100, 760), None, (700, 760)),
}


def render_ga(
    spec: VesselSpec,
    revision: str,
    vendor: Vendor,
    *,
    changed: set[str] | None = None,
    package: bool = False,
    overlay: Overlay | None = None,
) -> tuple[bytes, dict]:
    """PDF vectorial del GA (o del paquete). Devuelve los bytes y las páginas que ocupa el GA."""
    buffer = io.BytesIO()
    canvas = Canvas(buffer, pagesize=(PAGE_W, PAGE_H), invariant=1)
    canvas.setTitle(f"Synthetic GA {spec.tag} rev {revision}")
    canvas.setAuthor(vendor.name)
    sheets = 2 if vendor.table_position == "page2" else 1
    page = 1
    ga_pages = []
    if package:
        _cover(canvas, spec, revision, vendor, sheets)
        page = _next(canvas, overlay, page)
        _index(canvas, spec, vendor, sheets)
        page = _next(canvas, overlay, page)
    for sheet in range(1, sheets + 1):
        ga_pages.append(page)
        _ga_sheet(canvas, spec, revision, vendor, changed or set(), sheet, sheets)
        page = _next(canvas, overlay, page)
    if package:
        _nameplate(canvas, spec, revision, vendor)
        page = _next(canvas, overlay, page)
    canvas.save()
    return buffer.getvalue(), {"pages": page - 1, "ga_pages": ga_pages}


def _next(canvas: Canvas, overlay: Overlay | None, page: int) -> int:
    if overlay:
        overlay(canvas, page)
    _footer(canvas)
    canvas.showPage()
    return page + 1


def _footer(canvas: Canvas) -> None:
    canvas.setFillColor(FAINT)
    canvas.setFont("Helvetica", 6)
    canvas.drawString(26, 24, "SYNTHETIC TEST DOCUMENT · TRAZIA-3D · NOT A VENDOR DOCUMENT")


# Hoja del GA ---------------------------------------------------------------------------------
def _ga_sheet(canvas, spec, revision, vendor: Vendor, changed, sheet: int, sheets: int) -> None:
    layout = LAYOUTS[vendor.table_position]
    canvas.setStrokeColor(INK)
    canvas.setLineWidth(1.2)
    canvas.rect(20, 20, PAGE_W - 40, PAGE_H - 40)
    views = sheet == 1
    tables = sheets == 1 or sheet == 2
    if views:
        _elevation(canvas, spec, revision, vendor, layout, changed)
        _plan(canvas, spec, vendor, layout)
    if tables:
        bottom = _nozzle_table(canvas, spec, revision, vendor, layout, changed)
        dx, dy = layout.design or (layout.table[0], bottom - 50)
        _design_data(canvas, spec, revision, vendor, dx, dy, changed)
        canvas.setFillColor(INK)
        canvas.setFont("Helvetica", 8)
        for i, line in enumerate(vendor.notes):
            canvas.drawString(layout.notes[0], layout.notes[1] - 13 * i, line)
    _title_block(canvas, spec, revision, vendor, sheet, sheets)


def _fit_shell(spec: VesselSpec, budget: float) -> float:
    total = spec.skirt_height + spec.height + spec.head_depth * 1.333
    return spec.height * budget / total


def _dimension(canvas, vendor: Vendor, x: float, z0: float, z1: float, mm: float) -> None:
    canvas.setStrokeColor(INK)
    canvas.setFillColor(INK)
    canvas.setLineWidth(0.6)
    canvas.line(x, z0, x, z1)
    for z, d in ((z0, 1), (z1, -1)):
        canvas.line(x - 3, z + 6 * d, x, z)
        canvas.line(x + 3, z + 6 * d, x, z)
    text = fmt_length(mm, vendor)
    canvas.setFont("Helvetica", 9)
    if vendor.dim_text == "horizontal":
        canvas.drawRightString(x - 5, (z0 + z1) / 2 - 3, text)
        return
    canvas.saveState()
    canvas.translate(x - 4, (z0 + z1) / 2)
    canvas.rotate(90)
    canvas.drawCentredString(0, 0, text)
    canvas.restoreState()


def _delta(canvas: Canvas, x: float, y: float, revision: str) -> None:
    canvas.setStrokeColor(REVISION)
    canvas.setFillColor(REVISION)
    p = canvas.beginPath()
    p.moveTo(x, y)
    p.lineTo(x + 12, y)
    p.lineTo(x + 6, y + 10)
    p.close()
    canvas.drawPath(p, stroke=1, fill=0)
    canvas.setFont("Helvetica-Bold", 6)
    canvas.drawCentredString(x + 6, y + 2, revision)


def _elevation(canvas, spec: VesselSpec, revision, vendor: Vendor, layout: Layout, changed):
    x, base, width = layout.elev_x, layout.elev_base, 150
    shell = _fit_shell(spec, layout.elev_budget)
    scale = shell / spec.height
    head = spec.head_depth * scale
    skirt = spec.skirt_height * scale
    bottom = base + skirt
    top = bottom + shell
    canvas.setStrokeColor(INK)
    canvas.setLineWidth(1)
    canvas.setFillColor(HexColor("#f1f5f8"))
    canvas.rect(x, bottom, width, shell, fill=1)
    for z, sign in ((bottom, -1), (top, 1)):
        p = canvas.beginPath()
        p.moveTo(x, z)
        p.curveTo(x, z + sign * head * 1.333, x + width, z + sign * head * 1.333, x + width, z)
        p.close()
        canvas.drawPath(p, stroke=1, fill=1)
    canvas.setFillColor(HexColor("#dfe6ec"))
    canvas.rect(x + 6, base, 8, skirt, fill=1)
    canvas.rect(x + width - 14, base, 8, skirt, fill=1)
    canvas.line(x - 60, base, x + width + 60, base)
    canvas.setDash(6, 3)
    canvas.setStrokeColor(FAINT)
    canvas.line(x + width / 2, base - 10, x + width / 2, top + head + 20)
    canvas.line(x - 30, bottom, x + width + 30, bottom)
    canvas.line(x - 30, top, x + width + 30, top)
    canvas.setDash()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(FAINT)
    canvas.drawString(x + width + 34, bottom - 3, vendor.tl_label)
    canvas.drawString(x + width + 34, top - 3, vendor.tl_label)
    for n in spec.nozzles:
        z = base + n.elevation * scale
        c = math.cos(math.radians(n.azimuth))
        canvas.setStrokeColor(ACCENT)
        canvas.setFillColor(ACCENT)
        canvas.setFont("Helvetica", 8)
        if abs(c) < 0.3:
            canvas.circle(x + width / 2 + c * width * 0.4, z, 4, fill=0)
            canvas.drawString(x + width / 2 + c * width * 0.4 + 7, z + 4, n.id)
            continue
        start = x + width if c > 0 else x
        end = start + (36 if c > 0 else -36)
        canvas.line(start, z, end, z)
        canvas.line(end, z - 5, end, z + 5)
        canvas.drawString(end + (4 if c > 0 else -18), z + 4, n.id)

    _dimension(canvas, vendor, x - 80, base, bottom, spec.skirt_height)
    _dimension(canvas, vendor, x - 80, bottom, top, spec.height)
    _dimension(
        canvas, vendor, x - 120, base, top + head, spec.skirt_height + spec.height + spec.head_depth
    )
    _dimension(canvas, vendor, x - 40, top, top + head, spec.head_depth)
    if changed & {"height", "skirt_height"}:
        _delta(canvas, x - 100, (bottom + top) / 2, revision)

    canvas.setStrokeColor(INK)
    canvas.setFillColor(INK)
    canvas.setLineWidth(0.6)
    y = top + head + 40
    diameter = fmt_length(spec.diameter, vendor)
    canvas.setFont("Helvetica", 9)
    if vendor.diameter_style == "dim_line":
        canvas.line(x, y, x + width, y)
        for end, d in ((x, 1), (x + width, -1)):
            canvas.line(end, y, end + 6 * d, y + 3)
            canvas.line(end, y, end + 6 * d, y - 3)
            canvas.line(end, y - 6, end, y + 6)
        canvas.drawCentredString(x + width / 2, y + 6, f"Ø{diameter}")
    else:
        canvas.line(x, y, x + width, y)
        label = "I.D." if vendor.diameter_style == "id_dots" else "ID"
        canvas.drawCentredString(x + width / 2, y + 6, f"{label} {diameter}")
    canvas.drawCentredString(
        x + width / 2,
        base - 18,
        vendor.skirt_label.format(t=fmt_length(spec.skirt_thickness, vendor)),
    )
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(x - 50, base - 40, vendor.views[0])


def _plan(canvas, spec: VesselSpec, vendor: Vendor, layout: Layout) -> None:
    cx, cy = layout.plan
    r = 90
    canvas.setStrokeColor(INK)
    canvas.setLineWidth(1)
    canvas.circle(cx, cy, r)
    canvas.setStrokeColor(FAINT)
    canvas.setDash(4, 3)
    canvas.line(cx - r - 30, cy, cx + r + 30, cy)
    canvas.line(cx, cy - r - 30, cx, cy + r + 30)
    canvas.setDash()
    canvas.setFillColor(INK)
    canvas.setFont("Helvetica", 8)
    if vendor.azimuth_convention == "cw_north":
        labels = ((90, "N 0°"), (0, "E 90°"), (270, "S 180°"), (180, "W 270°"))
    else:
        labels = ((0, "0°"), (90, "90°"), (180, "180°"), (270, "270°"))
    for angle, label in labels:
        a = math.radians(angle)
        canvas.drawCentredString(
            cx + (r + 44) * math.cos(a), cy + (r + 44) * math.sin(a) - 3, label
        )
    for n in spec.nozzles:
        a = math.radians(n.azimuth)
        x0, y0 = cx + r * math.cos(a), cy + r * math.sin(a)
        x1, y1 = cx + (r + 22) * math.cos(a), cy + (r + 22) * math.sin(a)
        canvas.setStrokeColor(ACCENT)
        canvas.line(x0, y0, x1, y1)
        canvas.setFillColor(ACCENT)
        canvas.drawCentredString(cx + (r + 30) * math.cos(a), cy + (r + 30) * math.sin(a) + 6, n.id)
    canvas.setFillColor(INK)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(cx - 50, cy - r - 72, vendor.views[1])


def _nozzle_table(canvas, spec: VesselSpec, revision, vendor: Vendor, layout: Layout, changed):
    tx, ty = layout.table
    row_h = 18
    rows = len(spec.nozzles) + 1
    total_w = sum(c.width for c in vendor.columns)
    canvas.setFillColor(INK)
    canvas.setStrokeColor(INK)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(tx, ty + 14, vendor.table_title)
    canvas.setLineWidth(0.6)
    canvas.rect(tx, ty - row_h * rows, total_w, row_h * rows)
    x = tx
    canvas.setFont("Helvetica-Bold", 7.5)
    for column in vendor.columns:
        canvas.drawString(x + 4, ty - 12, column.header)
        x += column.width
        canvas.line(x, ty, x, ty - row_h * rows)
    canvas.setFont("Helvetica", 8)
    for i, n in enumerate(spec.nozzles):
        y = ty - row_h * (i + 1)
        canvas.setFillColor(INK)
        canvas.setStrokeColor(INK)
        canvas.setFont("Helvetica", 8)
        canvas.line(tx, y, tx + total_w, y)
        values = {
            "mark": n.id,
            "size": fmt_size(n.diameter, vendor),
            "projection": fmt_length(n.projection, vendor),
            "elevation": fmt_length(
                printed_elevation(n.elevation, spec.skirt_height, vendor), vendor
            ),
            "azimuth": fmt_angle(n.azimuth, vendor),
            "service": vendor.services[i % len(vendor.services)],
            "rating": "150#" if spec.design_pressure < 19 else "300#",
        }
        x = tx
        for column in vendor.columns:
            canvas.drawString(x + 4, y - 12, values[column.key])
            x += column.width
        if any(p.startswith(f"nozzles.{n.id}.") for p in changed):
            _delta(canvas, tx + total_w + 6, y - 14, revision)
    return ty - row_h * rows


def _design_data(canvas, spec: VesselSpec, revision, vendor: Vendor, tx, dy, changed) -> None:
    labels = vendor.design_labels
    heads = "2:1 SEMIELÍPTICOS" if vendor.lang == "es" else "2:1 SEMI-ELLIPSOIDAL"
    data = (
        (labels["design_pressure"], fmt_pressure(spec.design_pressure, vendor), "design_pressure"),
        (
            labels["design_temperature"],
            fmt_temperature(spec.design_temperature, vendor),
            "design_temperature",
        ),
        (labels["material"], spec.material, "material"),
        (labels["operating_weight"], fmt_weight(spec.operating_weight, vendor), "operating_weight"),
        (labels["heads"], heads, "head_depth"),
    )
    canvas.setFillColor(INK)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(tx, dy + 14, vendor.design_title)
    for i, (label, value, path) in enumerate(data):
        y = dy - 16 * i
        canvas.setStrokeColor(INK)
        canvas.setFillColor(INK)
        canvas.setFont("Helvetica", 8)
        canvas.line(tx, y - 4, tx + 300, y - 4)
        canvas.drawString(tx + 4, y, label)
        canvas.drawString(tx + 170, y, value)
        if path in changed or f"attributes.{path}" in changed:
            _delta(canvas, tx + 306, y - 2, revision)


def _title_block(canvas, spec, revision, vendor: Vendor, sheet: int, sheets: int) -> None:
    w = PAGE_W
    canvas.setStrokeColor(INK)
    canvas.setLineWidth(0.8)
    canvas.rect(w - 360, 30, 330, 90)
    canvas.line(w - 360, 75, w - 30, 75)
    canvas.line(w - 200, 30, w - 200, 120)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(FAINT)
    tb = vendor.title_block
    canvas.drawString(w - 355, 110, tb["equipment"])
    canvas.drawString(w - 195, 110, tb["document"])
    canvas.drawString(w - 355, 65, tb["title"])
    canvas.drawString(w - 195, 65, "REV")
    canvas.drawString(w - 110, 65, vendor.sheet_label)
    canvas.setFillColor(INK)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(w - 355, 88, spec.tag)
    canvas.drawString(w - 195, 88, f"GAD-{spec.tag}")
    canvas.setFont("Helvetica", 9)
    title = "PLANO DE CONJUNTO" if vendor.lang == "es" else "GENERAL ARRANGEMENT"
    canvas.drawString(w - 355, 42, title)
    canvas.drawString(w - 110, 42, f"{sheet}/{sheets}")
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(w - 195, 42, revision)


# Paquete de proveedor ------------------------------------------------------------------------
def _cover(canvas, spec, revision, vendor: Vendor, sheets: int) -> None:
    es = vendor.lang == "es"
    canvas.setFillColor(INK)
    canvas.setFont("Helvetica-Bold", 30)
    canvas.drawString(80, 700, vendor.name.upper())
    canvas.setFont("Helvetica", 16)
    canvas.drawString(
        80, 650, "DOSSIER DE DOCUMENTACIÓN DEL FABRICANTE" if es else "VENDOR DOCUMENT PACKAGE"
    )
    canvas.setFont("Helvetica", 12)
    rows = (
        ("EQUIPO" if es else "ITEM", spec.tag),
        (
            "PEDIDO" if es else "PURCHASE ORDER",
            f"PO-{zlib.crc32(spec.tag.encode()) % 90000 + 10000}",
        ),
        ("REVISIÓN" if es else "REVISION", revision),
    )
    for i, (k, v) in enumerate(rows):
        canvas.drawString(80, 580 - 24 * i, f"{k}:")
        canvas.drawString(260, 580 - 24 * i, v)


def _index(canvas, spec, vendor: Vendor, sheets: int) -> None:
    es = vendor.lang == "es"
    canvas.setFillColor(INK)
    canvas.setFont("Helvetica-Bold", 18)
    canvas.drawString(80, 740, "ÍNDICE" if es else "INDEX")
    canvas.setFont("Helvetica", 11)
    ga = "PLANO DE CONJUNTO" if es else "GENERAL ARRANGEMENT DRAWING"
    plate = "PLACA DE CARACTERÍSTICAS" if es else "NAMEPLATE AND DATA SUMMARY"
    entries = (
        ("1", "PORTADA" if es else "COVER"),
        ("2", "ÍNDICE" if es else "INDEX"),
        (f"3-{2 + sheets}" if sheets > 1 else "3", ga),
        (str(3 + sheets), plate),
    )
    for i, (page, title) in enumerate(entries):
        canvas.drawString(80, 700 - 22 * i, title)
        canvas.drawRightString(700, 700 - 22 * i, page)


def _nameplate(canvas, spec: VesselSpec, revision, vendor: Vendor) -> None:
    """Placa con valores coherentes y distractores con nombre parecido."""
    es = vendor.lang == "es"
    canvas.setFillColor(INK)
    canvas.setFont("Helvetica-Bold", 18)
    canvas.drawString(80, 740, "PLACA DE CARACTERÍSTICAS" if es else "NAMEPLATE DATA")
    rows = (
        ("EQUIPO" if es else "ITEM", spec.tag),
        (
            "PRESIÓN DE PRUEBA HIDRÁULICA" if es else "HYDROTEST PRESSURE",
            fmt_pressure(round(spec.design_pressure * 1.3, 1), vendor),
        ),
        (
            "SOBREESPESOR DE CORROSIÓN" if es else "CORROSION ALLOWANCE",
            fmt_length(3.175 if vendor.imperial else 3, vendor),
        ),
        ("EFICIENCIA DE JUNTA" if es else "JOINT EFFICIENCY", "0,85" if es else "0.85"),
        (
            "PESO EN VACÍO" if es else "EMPTY WEIGHT",
            fmt_weight(spec.operating_weight * 0.6, vendor),
        ),
        ("AÑO DE FABRICACIÓN" if es else "YEAR BUILT", "2026"),
    )
    canvas.setFont("Helvetica", 11)
    for i, (k, v) in enumerate(rows):
        canvas.drawString(80, 700 - 22 * i, k)
        canvas.drawString(420, 700 - 22 * i, v)


# Degradación ---------------------------------------------------------------------------------
DEGRADATION_PARAMS = {
    "escaneado_limpio": {"dpi": 200, "angle": 0.3, "blur": 0.3, "noise": 0.04, "jpeg": None},
    "escaneado_pobre": {"dpi": 120, "angle": 1.5, "blur": 0.9, "noise": 0.14, "jpeg": 30},
}


def degrade(pdf: bytes, level: str, seed: int) -> bytes:
    """Rasteriza todas las hojas como un escáner; «vectorial» devuelve el PDF tal cual."""
    if level == "vectorial":
        return pdf
    params = DEGRADATION_PARAMS[level]
    rng = random.Random(seed)
    pages = []
    with pdfplumber.open(io.BytesIO(pdf)) as document:
        for page in document.pages:
            image = page.to_image(resolution=params["dpi"]).original.convert("L")
            image = image.rotate(
                rng.uniform(-params["angle"], params["angle"]),
                resample=Image.Resampling.BICUBIC,
                expand=False,
                fillcolor=255,
            )
            image = image.filter(ImageFilter.GaussianBlur(params["blur"]))
            noise = Image.effect_noise(image.size, 40).convert("L")
            image = Image.blend(image, noise, params["noise"])
            if level == "escaneado_pobre":
                image = ImageEnhance.Contrast(image).enhance(0.75)
                image = ImageEnhance.Brightness(image).enhance(1.08)
            if params["jpeg"]:
                buffer = io.BytesIO()
                image.save(buffer, "JPEG", quality=params["jpeg"])
                image = Image.open(io.BytesIO(buffer.getvalue())).convert("L")
            pages.append(image)
    out = io.BytesIO()
    pages[0].save(out, "PDF", resolution=params["dpi"], save_all=True, append_images=pages[1:])
    return out.getvalue()


def hidden_text(canvas: Canvas, x: float, y: float, text: str, size: float = 8) -> None:
    """Texto blanco sobre blanco: invisible al ojo, presente en la capa de texto."""
    canvas.setFillColor(white)
    canvas.setFont("Helvetica", size)
    canvas.drawString(x, y, text)
