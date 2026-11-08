"""Plano GA nuevo: proyecciones ortográficas de la geometría IFC, nunca del PDF original."""

import hashlib
import io
import math
from collections import defaultdict
from html import escape

import numpy as np
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from trazia.viewer import meshes_from_ifc

VERSION = "ga-ifc-1"
PAGE = (420.0, 297.0)
VIEWS = [
    ("Alzado · XZ", (0, 2), (0, 1, 0), (15, 153, 190, 108)),
    ("Perfil · YZ", (1, 2), (1, 0, 0), (215, 153, 190, 108)),
    ("Planta · XY", (0, 1), (0, 0, 1), (15, 32, 190, 108)),
]
SCALES = (1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 5000, 10000)


def geometry(content: bytes):
    meshes = meshes_from_ifc(content.decode("utf8"))
    if not meshes:
        raise ValueError("El IFC no contiene geometría para generar el plano")
    result, count = [], 0
    for mesh in meshes:
        vertices = np.asarray(mesh["vertices"], dtype=float).reshape(-1, 3) * 1000
        faces = np.asarray(mesh["faces"], dtype=int).reshape(-1, 3)
        count += len(faces)
        if count > 2000000 or not np.isfinite(vertices).all() or len(vertices) == 0:
            raise ValueError("Geometría no finita o demasiado grande para el plano GA")
        # Unificar vértices coincidentes para eliminar diagonales internas coplanares.
        _, inverse = np.unique(np.round(vertices, 5), axis=0, return_inverse=True)
        edges = defaultdict(list)
        normals = np.cross(
            vertices[faces[:, 1]] - vertices[faces[:, 0]],
            vertices[faces[:, 2]] - vertices[faces[:, 0]],
        )
        lengths = np.linalg.norm(normals, axis=1)
        valid = lengths > 1e-10
        normals[valid] /= lengths[valid, None]
        for indices, normal, keep in zip(faces, normals, valid):
            if not keep:
                continue
            for i, j in ((0, 1), (1, 2), (2, 0)):
                a, b = int(indices[i]), int(indices[j])
                key = tuple(sorted((int(inverse[a]), int(inverse[b]))))
                edges[key].append((a, b, normal))
        result.append(
            {
                "guid": mesh["guid"],
                "component": str(mesh["component"] or mesh["name"]),
                "vertices": vertices,
                "edges": edges,
            }
        )
    points = np.concatenate([item["vertices"] for item in result])
    return result, points.min(axis=0), points.max(axis=0)


class Sheet:
    """Dibuja los mismos trazos en PDF vectorial y SVG, usando milímetros de papel."""

    def __init__(self):
        self.buffer = io.BytesIO()
        self.pdf = canvas.Canvas(self.buffer, pagesize=tuple(v * mm for v in PAGE), invariant=1)
        self.svg = []

    def line(self, x1, y1, x2, y2, color="#334155", width=0.18):
        self.pdf.setStrokeColor(color)
        self.pdf.setLineWidth(width * mm)
        self.pdf.line(x1 * mm, y1 * mm, x2 * mm, y2 * mm)
        self.svg.append(
            f'<line x1="{x1:.4f}" y1="{PAGE[1] - y1:.4f}" x2="{x2:.4f}" '
            f'y2="{PAGE[1] - y2:.4f}" stroke="{color}" stroke-width="{width}"/>'
        )

    def text(self, x, y, text, size=2.7, color="#1e293b"):
        self.pdf.setFillColor(color)
        self.pdf.setFont("Helvetica", size * mm)
        self.pdf.drawString(x * mm, y * mm, str(text))
        self.svg.append(
            f'<text x="{x:.4f}" y="{PAGE[1] - y:.4f}" '
            f'font-family="Arial,sans-serif" font-size="{size}" '
            f'fill="{color}">{escape(str(text))}</text>'
        )

    def rect(self, x, y, w, h):
        for a, b, c, d in (
            (x, y, x + w, y),
            (x + w, y, x + w, y + h),
            (x + w, y + h, x, y + h),
            (x, y + h, x, y),
        ):
            self.line(a, b, c, d, color="#cbd5e1", width=0.2)

    def dimension(self, x0, y0, x1, y1, label, vertical=False):
        self.line(x0, y0, x1, y1, color="#0369a1", width=0.23)
        if vertical:
            for y in (y0, y1):
                self.line(x0 - 1.2, y - 1, x0 + 1.2, y + 1, color="#0369a1")
            self.text(x0 + 2, (y0 + y1) / 2, label, size=2.4, color="#0369a1")
        else:
            for x in (x0, x1):
                self.line(x - 1, y0 - 1.2, x + 1, y0 + 1.2, color="#0369a1")
            self.text((x0 + x1) / 2 - 10, y0 + 2, label, size=2.4, color="#0369a1")


def generate_ga(ifc: bytes, revision, *, scale: int | None = None):
    meshes, low, high = geometry(ifc)
    extents = high - low
    required = max(
        max(extents[a] / (box[2] - 65), extents[b] / (box[3] - 24)) for _, (a, b), _, box in VIEWS
    )
    if scale is None:
        scale = next((value for value in SCALES if value >= required), None)
    if scale is None or scale not in SCALES or scale < required:
        raise ValueError("La escala no cabe en A3; elige una escala admitida mayor")
    sheet = Sheet()
    for title, axes, view_direction, (x, y, w, h) in VIEWS:
        sheet.rect(x, y, w, h)
        sheet.text(x + 4, y + h - 6, title, size=3.2)
        a, b = axes
        offset = (x + (w - extents[a] / scale) / 2, y + (h - extents[b] / scale) / 2 - 2)

        def project(point):
            return (
                offset[0] + (point[a] - low[a]) / scale,
                offset[1] + (point[b] - low[b]) / scale,
            )

        for item in meshes:
            for edge in item["edges"].values():
                normals = [record[2] for record in edge]
                dots = [float(np.dot(n, view_direction)) for n in normals]
                crease = len(normals) > 1 and float(np.dot(normals[0], normals[1])) < math.cos(
                    math.radians(25)
                )
                silhouette = min(dots) < -1e-8 and max(dots) > 1e-8
                if len(edge) == 1 or crease or silhouette:
                    i, j, _ = edge[0]
                    p, q = project(item["vertices"][i]), project(item["vertices"][j])
                    sheet.line(*p, *q)
        p0 = project(low)
        p1 = project(high)
        for px in (p0[0], p1[0]):
            sheet.line(px, p0[1], px, y + 3, color="#94a3b8", width=0.12)
        for py in (p0[1], p1[1]):
            sheet.line(p1[0], py, x + w - 33, py, color="#94a3b8", width=0.12)
        sheet.dimension(p0[0], y + 5, p1[0], y + 5, f"{extents[a]:.1f} mm")
        sheet.dimension(x + w - 35, p0[1], x + w - 35, p1[1], f"{extents[b]:.1f} mm", True)
        sheet.text(x + 3, y + 2, "Extensiones de toda la geometría, incluidas conexiones.", size=2)
    sheet.rect(215, 32, 190, 108)
    sheet.text(220, 131, "PIEZAS DEL IFC / PREFIJO GUID", size=3.2)
    # Índice separado y completo en el manifiesto; la hoja declara su propio límite.
    for index, item in enumerate(meshes[:14]):
        name = item["component"][:33]
        sheet.text(220, 124 - index * 5.5, f"{name}  {item['guid'][:12]}", size=2.4)
    sheet.text(
        220, 39, f"{len(meshes)} piezas. Índice completo y cotas: manifiesto JSON.", size=2.3
    )
    sha = hashlib.sha256(ifc).hexdigest()
    sheet.text(
        15,
        281,
        f"TrazIA-3D | {revision.equipment.tag.value} | Rev {revision.revision} | GA NUEVO - DRAFT",
        size=4.5,
    )
    sheet.text(
        15,
        273,
        "Generado desde IFC. Proyección ortográfica sin ocultación de "
        "líneas. No es plano de fabricación.",
        size=2.8,
    )
    sheet.line(15, 269, 405, 269, width=0.35)
    sheet.rect(15, 8, 390, 19)
    sheet.text(
        19,
        21,
        f"A3 apaisado | Escala 1:{scale} | Unidades: mm | Sistema local IFC "
        f"| Dataset: {revision.dataset}",
        size=2.7,
    )
    sheet.text(19, 15, f"IFC SHA-256: {sha}", size=2.1)
    sheet.text(
        19,
        10,
        "Cotas de envolvente teselada; imprimir al 100 %. Pendiente de "
        "revisión técnica. Originales conservados.",
        size=2.2,
    )
    sheet.pdf.setTitle(f"GA DERIVADO DRAFT {revision.equipment.tag.value} {revision.revision}")
    sheet.pdf.setSubject("trazia-derivado; GA nuevo desde IFC; no original de extracción")
    sheet.pdf.save()
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="420mm" '
        'height="297mm" viewBox="0 0 420 297"><title>GA DERIVADO DRAFT</title>'
        '<rect width="420" height="297" fill="white"/>' + "".join(sheet.svg) + "</svg>"
    )
    manifest = {
        "schema": "ga-1",
        "generator": VERSION,
        "dataset": revision.dataset,
        "draft": True,
        "input_sha256": revision.fingerprint(),
        "ifc_sha256": sha,
        "scale": scale,
        "paper_mm": list(PAGE),
        "units": "mm",
        "world_bounds_mm": {"min": low.tolist(), "max": high.tolist(), "size": extents.tolist()},
        "views": [{"name": v[0], "axes": list(v[1])} for v in VIEWS],
        "pieces": [{"guid": p["guid"], "component": p["component"]} for p in meshes],
        "limits": "Proyección sin líneas ocultas; cotas exteriores "
        "teseladas. No certifica fabricación ni cálculo resistente.",
    }
    return {"pdf": sheet.buffer.getvalue(), "svg": svg.encode("utf8"), "manifest": manifest}
