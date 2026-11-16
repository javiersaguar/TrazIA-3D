"""Genera los PDF y la geometría que se exporta a IFC con WebIFC."""

import json
import math
from pathlib import Path

from industrial_designs import FAMILIES, Design, Part, Point
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web/public/demo/industriales"
INDICES = {"x": (1, 2, 0), "y": (2, 0, 1), "z": (0, 1, 2)}
COLORS = ("#dceaf3", "#d1e2ec", "#b9d4e4", "#ecf1f4")


def mesh(part: Part, size: Point) -> dict:
    a, b, c = INDICES[part.axis or "z"]
    w, h, d = size
    spans = (w, d, h)
    low, high = part.low, part.high
    if any(not 0 <= lo < hi <= 100 for lo, hi in zip(low, high)):
        raise ValueError(f"Límites inválidos: {part.name}")
    ring = (
        [(math.cos(i * math.tau / 32), math.sin(i * math.tau / 32)) for i in range(32)]
        if part.axis
        else [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    )
    n = len(ring)
    vertices = []
    for level, ratio in zip((low[c], high[c]), part.ends):
        for u, v in ring:
            point = [0.0, 0.0, 0.0]
            point[a] = (low[a] + high[a] + u * ratio * (high[a] - low[a])) / 2
            point[b] = (low[b] + high[b] + v * ratio * (high[b] - low[b])) / 2
            point[c] = level
            vertices.append([round(value * span / 100, 4) for value, span in zip(point, spans)])
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.extend(((i, j, j + n), (i, j + n, i + n)))
    for i in range(1, n - 1):
        faces.extend(((0, i + 1, i), (n, n + i, n + i + 1)))
    return {"name": part.name, "vertices": vertices, "triangles": faces}


def hull(points):
    points = sorted(set(points))

    def chain(source):
        result = []
        for x, y in source:
            while len(result) > 1:
                a, b = result[-2:]
                if (b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0]) > 0:
                    break
                result.pop()
            result.append((x, y))
        return result[:-1]

    return chain(points) + chain(reversed(points))


def render_pdf(path: Path, family: str, design: Design, parts: list[dict]):
    pdf = Canvas(str(path), pagesize=(420 * mm, 297 * mm), invariant=1)
    pdf.setTitle(f"{design.tag} - {design.name}")
    pdf.setSubject("Geometría industrial conceptual sintética")

    def label(x, y, value, size=11, bold=False):
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        pdf.setFillColor("#15344c")
        pdf.drawString(x * mm, y * mm, value)

    vertices = [v for part in parts for v in part["vertices"]]
    low = [min(p[i] for p in vertices) for i in range(3)]
    high = [max(p[i] for p in vertices) for i in range(3)]
    extent = [hi - lo for hi, lo in zip(high, low)]
    label(16, 280, f"TRAZIA-3D   /   {family.upper()}", 11, True)
    label(16, 263, design.name, 25, True)
    label(16, 252, f"{design.tag}   /   REV A   /   DISEÑO CONCEPTUAL SINTÉTICO", 11)
    # Ambas vistas comparten escala y usan directamente los vértices del modelo IFC.
    scale = min(158 / extent[0], 132 / extent[1], 132 / extent[2])
    for x, title, axes in ((16, "ALZADO", (0, 2, 1)), (216, "PLANTA", (0, 1, 2))):
        a, b, depth = axes
        pdf.setStrokeColor("#a9c1d2")
        pdf.setLineWidth(0.6)
        pdf.rect(x * mm, 66 * mm, 188 * mm, 175 * mm)
        label(x + 5, 232, title, 10, True)
        ox, oy = x + (188 - scale * extent[a]) / 2, 147 - scale * extent[b] / 2
        layers = sorted(
            enumerate(parts),
            key=lambda item: max(v[depth] for v in item[1]["vertices"]),
            reverse=title == "ALZADO",
        )
        for index, part in layers:
            outline = hull((v[a], v[b]) for v in part["vertices"])
            path_2d = pdf.beginPath()
            for j, (u, v) in enumerate(outline):
                fn = path_2d.lineTo if j else path_2d.moveTo
                fn((ox + (u - low[a]) * scale) * mm, (oy + (v - low[b]) * scale) * mm)
            path_2d.close()
            pdf.setFillColor(COLORS[index % len(COLORS)])
            pdf.setStrokeColor("#205474")
            pdf.setLineWidth(0.85)
            pdf.drawPath(path_2d, stroke=1, fill=1)
    label(16, 52, "ENVOLVENTE DEL MODELO", 11, True)
    width, depth, height = (f"{value:,.0f}".replace(",", " ") for value in extent)
    label(16, 44, f"Ancho {width} mm    Fondo {depth} mm    Alto {height} mm", 12)
    label(216, 52, "DETALLE GEOMÉTRICO", 11, True)
    label(216, 44, f"{len(parts)} componentes exteriores esquemáticos", 12)
    label(16, 21, "Dimensiones de referencia. Sin cálculo de proceso. No apto para fabricación.")
    label(16, 13, "Ejemplos propios de TrazIA-3D. Fuera del dataset y del banco de pruebas.")
    label(372, 13, "A3 / 1 de 1", 10, True)
    pdf.save()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    work = ROOT / "generated"
    work.mkdir(exist_ok=True)
    families = []
    designs = []
    solids = {}
    for family in FAMILIES:
        families.append({"id": family.id, "name": family.name, "parts": family.parts})
        for design in family.designs:
            if design.tag in solids:
                raise ValueError(f"Etiqueta repetida: {design.tag}")
            parts = [mesh(part, design.size) for part in design.parts]
            filename = f"{design.tag}-A.pdf"
            render_pdf(OUT / filename, family.name, design, parts)
            designs.append(
                {
                    "tag": design.tag,
                    "family": family.id,
                    "name": design.name,
                    "filename": filename,
                    "ifc": f"{design.tag}-A.ifc",
                }
            )
            solids[design.tag] = parts
    indexed = {"families": families, "designs": designs}
    (work / "industrial-meshes.json").write_text(json.dumps(solids), encoding="utf8")
    # El exportador publica el índice después de validar los archivos IFC.
    (work / "industrial-designs.json").write_text(
        json.dumps(indexed, indent=2, ensure_ascii=False) + "\n", encoding="utf8"
    )


if __name__ == "__main__":
    main()
