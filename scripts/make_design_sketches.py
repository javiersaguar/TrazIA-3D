"""Láminas conceptuales del catálogo web, reproducibles y ajenas al banco de pruebas."""

import json
from dataclasses import dataclass
from pathlib import Path

from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

ROOT = Path(__file__).resolve().parents[1]
INK, ACCENT, MUTED = "#142c41", "#075985", "#40556a"


@dataclass(frozen=True)
class Sketch:
    tag: str
    family: str
    name: str
    variant: str
    width: int
    height: int
    depth: int
    notes: tuple[str, str]
    detail: tuple[tuple[str, str], ...] = ()


SKETCHES = (
    Sketch(
        "BC-V101",
        "vertical",
        "Separador vertical",
        "separador",
        1800,
        6300,
        1800,
        ("Faldón continuo con acceso inferior.", "Boquillas laterales a distinta altura."),
    ),
    Sketch(
        "BC-V102",
        "vertical",
        "Pulmón vertical compacto",
        "pulmon",
        2200,
        4300,
        2200,
        ("Virola corta con fondos curvos.", "Faldón corto y conexión superior."),
    ),
    Sketch(
        "BC-H101",
        "horizontal",
        "Tambor horizontal de separación",
        "tambor",
        7400,
        2900,
        2200,
        ("Dos silletas bajo la virola.", "Dos conexiones superiores y una inferior."),
        (("Largo entre tangencias", "6 300 mm"),),
    ),
    Sketch(
        "BC-H102",
        "horizontal",
        "Acumulador horizontal de retorno",
        "acumulador",
        5100,
        2200,
        1600,
        ("Configuración compacta sobre dos silletas.", "Conexión de retorno en un extremo."),
        (("Largo entre tangencias", "4 300 mm"),),
    ),
    Sketch(
        "BC-C101",
        "column",
        "Columna recta de destilación",
        "recta",
        1900,
        16500,
        1900,
        ("Virola de diámetro constante.", "Niveles de platos indicados en el alzado."),
    ),
    Sketch(
        "BC-C102",
        "column",
        "Columna con transición cónica",
        "transicion",
        2900,
        19100,
        2900,
        ("Tramo inferior ancho y superior estrecho.", "La transición se sitúa bajo el tramo alto."),
        (("Diámetro del tramo superior", "1 800 mm"),),
    ),
    Sketch(
        "BC-E101",
        "exchanger",
        "Intercambiador de carcasa y tubos",
        "carcasa",
        6600,
        1900,
        1500,
        ("Carcasa horizontal con dos canales.", "Bridas de unión en ambos extremos."),
    ),
    Sketch(
        "BC-E102",
        "exchanger",
        "Intercambiador de placas",
        "placas",
        1750,
        2400,
        980,
        ("Paquete de placas entre bastidores.", "Cuatro conexiones sobre placa fija."),
    ),
    Sketch(
        "BC-T101",
        "tank",
        "Tanque con techo cónico",
        "conico",
        8400,
        7100,
        8400,
        ("Techo fijo cónico y apoyo en losa.", "Boca lateral en el tramo inferior."),
        (("Altura de la virola", "6 050 mm"),),
    ),
    Sketch(
        "BC-T102",
        "tank",
        "Tanque con techo plano",
        "plano",
        7100,
        5000,
        7100,
        ("Tanque bajo con cubierta plana.", "Respiradero desplazado y boca lateral."),
        (("Altura de la virola", "5 000 mm"),),
    ),
    Sketch(
        "BC-P101",
        "pump",
        "Bomba centrífuga horizontal",
        "centrifuga",
        2100,
        1150,
        780,
        ("Carcasa y motor sobre bancada común.", "Acoplamiento entre ambos equipos."),
    ),
    Sketch(
        "BC-P102",
        "pump",
        "Bomba vertical en línea",
        "linea",
        1040,
        1840,
        650,
        ("Motor situado sobre el cuerpo de bomba.", "Conexiones enfrentadas en el mismo eje."),
    ),
    Sketch(
        "BC-K101",
        "compressor",
        "Compresor de tornillo",
        "tornillo",
        3050,
        1640,
        1250,
        ("Motor y bloque sobre bancada.", "Carcasa exterior mostrada de forma esquemática."),
    ),
    Sketch(
        "BC-K102",
        "compressor",
        "Compresor alternativo",
        "alternativo",
        3550,
        2350,
        1650,
        ("Dos cilindros sobre el bastidor.", "Motor y bancada incluidos en el alzado."),
    ),
    Sketch(
        "BC-G101",
        "generic",
        "Módulo rectangular de proceso",
        "modulo",
        4200,
        2850,
        2300,
        ("Volumen exterior reservado para implantación.", "Referencia de aproximación LOD 1."),
    ),
    Sketch(
        "BC-G102",
        "generic",
        "Armario vertical de servicios",
        "armario",
        1250,
        2410,
        850,
        ("Reserva compacta con acceso frontal.", "Referencia de aproximación LOD 1."),
    ),
)


def draw_body(canvas: Canvas, item: Sketch) -> None:
    """Alzado en una cuadrícula 0–100, escalada con las dimensiones nominales."""
    line, rect, ellipse = canvas.line, canvas.rect, canvas.ellipse

    def outline(points):
        path = canvas.beginPath()
        path.moveTo(*points[0])
        for point in points[1:]:
            path.lineTo(*point)
        path.close()
        canvas.drawPath(path)

    if item.family == "vertical":
        skirt = 20 if item.variant == "separador" else 16
        canvas.roundRect(0, skirt - 5, 100, 90 - skirt, 12)
        rect(4, 0, 92, skirt)
        canvas.roundRect(36, 0, 28, 12, 4)
        line(0, skirt, 100, skirt)
        line(0, 76, 100, 76)
        rect(41, 85, 18, 15)
        x, width = (85, 15) if item.variant == "pulmon" else (0, 15)
        ellipse(x, 40, x + width, 48)
        if item.variant == "separador":
            ellipse(85, 63, 100, 69)
    elif item.family == "horizontal":
        head = 550 / 7400 * 100 if item.variant == "tambor" else 400 / 5100 * 100
        radius = item.depth / item.height * 50
        bottom = 91 - 2 * radius
        path = canvas.beginPath()
        path.moveTo(head, bottom)
        path.lineTo(100 - head, bottom)
        path.curveTo(100 + head / 3, bottom, 100 + head / 3, 91, 100 - head, 91)
        path.lineTo(head, 91)
        path.curveTo(-head / 3, 91, -head / 3, bottom, head, bottom)
        path.close()
        canvas.drawPath(path)
        for x in (23, 77):
            outline([(x - 6, 0), (x + 6, 0), (x + 4, bottom), (x - 4, bottom)])
        for x in (head, 100 - head):
            line(x, bottom, x, 91)
        rect(30, 91, 5, 9)
        if item.variant == "tambor":
            rect(65, 91, 5, 9)
            rect(47, bottom - 8, 6, 8)
        else:
            ellipse(1, 49, 11, 66)
    elif item.family == "column":
        step = (100 - 1800 / 2900 * 100) / 2 if item.variant == "transicion" else 0
        outline(
            [
                (0, 0),
                (100, 0),
                (100, 52),
                (100 - step, 61),
                (100 - step, 100),
                (step, 100),
                (step, 61),
                (0, 52),
            ]
        )
        for y in (18, 31, 44, 68, 81, 94):
            edge = step if y > 60 else 0
            line(edge, y, 100 - edge, y)
        line(0, 8, 100, 8)
    elif item.family == "tank":
        roofline = 6050 / 7100 * 100 if item.variant == "conico" else 100
        rect(0, 0, 100, roofline)
        if item.variant == "conico":
            outline([(0, roofline), (50, 100), (100, roofline)])
        else:
            rect(63, 85, 7, 15)
        for y in (21, 42, 63):
            line(0, y, 100, y)
        ellipse(14, 7, 24, 19)
        line(4, 4, 96, 4)
    elif item.variant == "carcasa":
        rect(0, 25, 100, 62)
        rect(12, 20, 3, 72)
        rect(85, 20, 3, 72)
        rect(27, 0, 8, 25)
        rect(67, 0, 8, 25)
        rect(32, 87, 6, 13)
        rect(65, 87, 6, 13)
    elif item.variant == "placas":
        rect(8, 6, 8, 94)
        rect(83, 6, 9, 94)
        rect(0, 85, 100, 5)
        rect(0, 13, 100, 5)
        rect(16, 22, 67, 59)
        for x in range(20, 83, 5):
            line(x, 22, x, 81)
        for x, y in ((25, 66), (25, 33), (74, 66), (74, 33)):
            ellipse(x - 4, y - 3, x + 4, y + 3)
    elif item.variant == "linea":
        rect(29, 60, 42, 40)
        rect(42, 38, 16, 22)
        rect(0, 16, 100, 18)
        ellipse(23, 0, 77, 48)
        for x in (36, 44, 52, 60):
            line(x, 66, x, 93)
    elif item.family in {"pump", "compressor"}:
        rect(0, 0, 100, 9)
        rect(57, 17, 43, 57)
        rect(45, 26, 12, 21)
        for x in (65, 71, 77, 83, 89):
            line(x, 23, x, 68)
        if item.variant == "centrifuga":
            ellipse(3, 9, 46, 88)
            rect(15, 88, 16, 12)
        else:
            rect(3, 9, 42, 66)
            if item.variant == "alternativo":
                rect(6, 75, 14, 25)
                rect(27, 75, 14, 25)
            else:
                rect(18, 75, 13, 25)
    else:
        canvas.setDash(3, 2)
        rect(0, 0, 100, 100)
        canvas.setDash()
        if item.variant == "armario":
            line(50, 0, 50, 100)
            line(44, 43, 44, 53)
            line(56, 43, 56, 53)
        else:
            line(0, 20, 100, 20)


def fmt(n: int) -> str:
    return f"{n:,}".replace(",", " ") + " mm"


def draw_pdf(path: Path, item: Sketch) -> None:
    pdf = Canvas(str(path), pagesize=(420 * mm, 297 * mm), invariant=1)
    pdf.setTitle(f"{item.tag} - {item.name}")
    pdf.setSubject("Boceto sintético conceptual de TrazIA-3D")

    def text(x, y, value, *, size=11, color=INK, bold=False):
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        pdf.setFillColor(color)
        pdf.drawString(x * mm, y * mm, value)

    def line(x1, y1, x2, y2):
        pdf.line(x1 * mm, y1 * mm, x2 * mm, y2 * mm)

    text(18, 279, "TRAZIA-3D   /   CATÁLOGO DE BOCETOS", size=12, color=ACCENT, bold=True)
    text(18, 260, item.name, size=28, bold=True)
    text(18, 250, f"{item.tag}   /   REV A   /   BOCETO SINTÉTICO", size=11, color=ACCENT)
    pdf.setStrokeColor("#bed1df")
    pdf.setLineWidth(0.7)
    pdf.rect(18 * mm, 44 * mm, 251 * mm, 196 * mm)
    line(282, 240, 402, 240)
    text(23, 232, "ALZADO ESQUEMÁTICO", size=10, color=MUTED, bold=True)
    text(282, 230, "DIMENSIONES NOMINALES", size=12, bold=True)
    pdf.saveState()
    scale = min(184 / item.width, 142 / item.height)
    width, height = item.width * scale, item.height * scale
    x, y = (143.5 - width / 2), (144 - height / 2)
    pdf.translate(x * mm, y * mm)
    pdf.scale(width * mm / 100, height * mm / 100)
    pdf.setStrokeColor(INK)
    pdf.setLineWidth(0)  # Línea fina uniforme aunque el alzado tenga escala anisótropa.
    draw_body(pdf, item)
    pdf.restoreState()
    pdf.setStrokeColor(ACCENT)
    pdf.setLineWidth(0.55)
    x2, y2 = x + width, y + height
    line(x, y - 9, x2, y - 9)
    line(x, y - 12, x, y - 2)
    line(x2, y - 12, x2, y - 2)
    text(x + width / 2 - 8, y - 16, fmt(item.width), size=9, color=ACCENT)
    line(x2 + 8, y, x2 + 8, y2)
    line(x2 + 3, y, x2 + 11, y)
    line(x2 + 3, y2, x2 + 11, y2)
    text(x2 + 11, y + height / 2, fmt(item.height), size=9, color=ACCENT)

    dims = (
        ("Ancho en alzado", fmt(item.width)),
        ("Alto en alzado", fmt(item.height)),
        ("Fondo nominal", fmt(item.depth)),
        *item.detail,
    )
    for i, (label, value) in enumerate(dims):
        row = 216 - i * 20
        text(282, row, label, size=10, color=MUTED)
        text(282, row - 7, value, size=14, bold=True)
    text(282, 124, "CONFIGURACIÓN CONCEPTUAL", size=12, bold=True)
    for i, note in enumerate(item.notes):
        text(282, 113 - i * 8, note, size=10, color=MUTED)
    pdf.setStrokeColor("#bed1df")
    line(18, 34, 402, 34)
    text(
        18,
        25,
        "Ejemplo propio de TrazIA-3D. Cotas de referencia en mm. Sin escala de impresión.",
        size=10,
        color=MUTED,
    )
    text(
        18,
        17,
        "Documento conceptual para demostración. No válido para fabricación.",
        size=10,
        color=MUTED,
    )
    text(380, 17, "A3 / 1 de 1", size=10, color=ACCENT, bold=True)
    pdf.save()


def main() -> None:
    folder = ROOT / "web/public/demo/bocetos"
    folder.mkdir(parents=True, exist_ok=True)
    entries = []
    for sketch in SKETCHES:
        filename = f"BOC_{sketch.tag}_revA.pdf"
        draw_pdf(folder / filename, sketch)
        entries.append(
            {
                "tag": sketch.tag,
                "family": sketch.family,
                "name": sketch.name,
                "filename": filename,
            }
        )
    manifest = ROOT / "web/src/features/documents/sketches.json"
    manifest.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
