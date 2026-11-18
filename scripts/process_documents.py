"""Planos A3 vectoriales y libros de datos vinculados a la geometría sintética."""

from datetime import datetime

from make_industrial_designs import hull
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from process_geometry import PALETTE
from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfgen.canvas import Canvas

PAGE_W, PAGE_H = landscape(A3)
INK = "#18354b"
ACCENT = "#087a9f"
BORDER = "#aabfc9"


def text(pdf, x, y, value, size=10, bold=False):
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    pdf.drawString(x, y, str(value))


def path(pdf, points, *, fill=None, stroke=ACCENT, weight=0.7, closed=False):
    first, *rest = points
    route = pdf.beginPath()
    route.moveTo(*first)
    for p in rest:
        route.lineTo(*p)
    if closed:
        route.close()
    pdf.setLineWidth(weight)
    pdf.setStrokeColor(stroke)
    if fill is not None:
        pdf.setFillColor(fill)
    pdf.drawPath(route, stroke=1, fill=int(fill is not None))


def frame(pdf, project, revision, sheet, title, page):
    pdf.setStrokeColor(BORDER)
    pdf.setLineWidth(0.75)
    pdf.rect(27, 26, PAGE_W - 54, PAGE_H - 52)
    text(
        pdf,
        48,
        789,
        f"TRAZIA-3D    /    {project.code}    /    {project.setting.upper()}",
        12,
        True,
    )
    text(pdf, 48, 757, title, 24, True)
    text(pdf, 48, 735, f"{sheet}   |   REV. {revision}   |   CONJUNTO SINTÉTICO", 10, True)
    text(
        pdf,
        48,
        44,
        "Modelo conceptual. Coordenadas locales. Uso exclusivo en el ensayo de trazabilidad.",
        9,
    )
    text(pdf, PAGE_W - 198, 44, f"REV {revision}    /    A3    /    HOJA {page}", 9, True)


def chart(pdf, area, axes, parts, *, line_paths=None, equipment=None):
    x, y, width, height = area
    a, b = axes
    vertices = [p for part in parts for mesh in part.meshes.values() for p in mesh.vertices]
    low_a, high_a = min(v[a] for v in vertices), max(v[a] for v in vertices)
    low_b, high_b = min(v[b] for v in vertices), max(v[b] for v in vertices)
    scale = min((width - 50) / (high_a - low_a), (height - 70) / (high_b - low_b))
    ox, oy = (
        x + (width - scale * (high_a - low_a)) / 2,
        y + 23 + (height - 63 - scale * (high_b - low_b)) / 2,
    )

    def xy(pa, pb):
        return ox + (pa - low_a) * scale, oy + (pb - low_b) * scale

    pdf.setStrokeColor(BORDER)
    pdf.rect(x, y, width, height)
    header = "PLANTA · X/Y" if b == 1 else "ALZADO · X/Z"
    if a == 1:
        header = "PERFIL · Y/Z"
    text(pdf, x + 12, y + height - 22, header, 11, True)
    text(pdf, x + 12, y + 9, f"1:{1000 / (scale * 25.4 / 72):.0f}   ·   m en el modelo", 9)
    depth = ({0, 1, 2} - {a, b}).pop()
    for part in sorted(parts, key=lambda item: item.kind != "structure"):
        if part.kind == "pipe":
            continue
        faces = [
            (material, [mesh.vertices[i] for i in face])
            for material, mesh in part.meshes.items()
            for face in mesh.faces
        ]
        if equipment is not None and part.kind != "structure":
            faces = [
                (material, mesh.vertices) for material, mesh in part.meshes.items() if mesh.vertices
            ]
        for material, points in sorted(
            faces,
            key=lambda entry: sum(v[depth] for v in entry[1]) / len(entry[1]),
            reverse=b == 2 and a == 0,
        ):
            outline = hull((v[a], v[b]) for v in points)
            if len(outline) < 3:
                continue
            fill = "#e3ebef" if part.kind == "structure" else PALETTE[material]
            path(pdf, [xy(*p) for p in outline], fill=fill, stroke=INK, weight=0.32, closed=True)
    if line_paths:
        for line, coords in line_paths:
            points = [xy(p[a], p[b]) for p in coords]
            path(pdf, points, weight=1.35, stroke=PALETTE[line.fluid])
            if b == 1:
                mid = tuple((p + q) / 2 for p, q in zip(points[3], points[4]))
                text(pdf, mid[0] - 9, mid[1] + 3, line.tag, 7.5, True)
    if equipment and b == 1:
        for eq in equipment.values():
            cx, cy = xy(*eq.xy)
            pdf.setFillColor("#ffffff")
            pdf.roundRect(cx - 17, cy + 4, 34, 12, 2, fill=1, stroke=0)
            text(pdf, cx - 14, cy + 7, eq.tag, 8, True)


def table(pdf, x, top, headers, rows, widths, height=24):
    width = sum(widths)
    pdf.setFillColor("#e7f0f3")
    pdf.rect(x, top - height, width, height, fill=1, stroke=0)
    for i, row in enumerate((headers, *rows)):
        y = top - (i + 1) * height
        pdf.setStrokeColor(BORDER)
        pdf.line(x, y, x + width, y)
        left = x
        for j, (value, span) in enumerate(zip(row, widths)):
            text(pdf, left + 6, y + height * 0.33, value, 9, i == 0 or j == 0)
            left += span


def changes(project, revision):
    return [
        (
            c.tag,
            c.label,
            f"{c.before:g}",
            f"{c.after:g}",
            c.unit,
            "Aplicado" if revision == "B" else "Base A",
        )
        for c in project.changes
    ]


def project_pdf(target, project, revision, equipment, lines, paths, parts):
    pdf = Canvas(str(target), pagesize=(PAGE_W, PAGE_H), invariant=1, pageCompression=1)
    pdf.setTitle(f"{project.code} · GA de implantación · Rev {revision}")
    frame(pdf, project, revision, "GA-001", project.name, "01 / 02")
    text(pdf, 48, 713, project.description, 10)
    chart(
        pdf,
        (46, 373, 1099, 319),
        (0, 1),
        parts,
        line_paths=[(line, paths[tag]) for tag, line in lines.items()],
        equipment=equipment,
    )
    chart(
        pdf,
        (46, 87, 1099, 265),
        (0, 2),
        parts,
        line_paths=[(line, paths[tag]) for tag, line in lines.items()],
        equipment=equipment,
    )
    pdf.showPage()
    frame(pdf, project, revision, "GA-002", "Equipos, interfaces y revisión", "02 / 02")
    table(
        pdf,
        48,
        714,
        ("Tag", "Equipo", "Servicio", "X / Y (m)", "Envolvente X · Y · Z (m)"),
        [
            (
                item.tag,
                item.name,
                item.service,
                f"{item.xy[0]:g} / {item.xy[1]:g}",
                " × ".join(f"{n:g}" for n in item.size),
            )
            for item in equipment.values()
        ],
        (67, 260, 211, 111, 449),
        23,
    )
    table(
        pdf,
        48,
        512,
        ("Línea", "Desde", "Hasta", "Servicio", "DN (mm)", "Cota de rack (m)"),
        [
            (
                line.tag,
                line.start,
                line.end,
                line.fluid,
                line.dn,
                f"{line.rack_z + project.deck:.2f}",
            )
            for line in lines.values()
        ],
        (95, 115, 115, 213, 111, 449),
        23,
    )
    text(pdf, 48, 302, "CAMBIOS DE REV. B", 12, True)
    table(
        pdf,
        48,
        285,
        ("Tag", "Modificación", "A", "B", "Unidad", "Estado"),
        changes(project, revision),
        (95, 488, 102, 102, 121, 190),
        26,
    )
    text(
        pdf,
        48,
        172,
        "NORTE DE DIBUJO +Y     ·     +Z ELEVACIÓN     ·     DATUM DE EQUIPOS = PISO DE PROCESO",
        10,
        True,
    )
    text(
        pdf,
        48,
        150,
        "Cada línea tiene dos uniones de puerto en el IFC. "
        "El libro incluye las coordenadas de los nodos del recorrido.",
        9,
    )
    text(
        pdf,
        48,
        128,
        "Los planos por tag incluyen cotas exteriores, componentes y ubicación de las interfaces.",
        9,
    )
    pdf.save()


def equipment_pdf(target, project, revision, eq, part, lines, routes):
    pdf = Canvas(str(target), pagesize=(PAGE_W, PAGE_H), invariant=1, pageCompression=1)
    pdf.setTitle(f"{eq.tag} · GA de equipo · Rev {revision}")
    frame(pdf, project, revision, eq.tag, eq.name, "01 / 01")
    text(pdf, 48, 711, f"TAG = {eq.tag}", 13, True)
    text(pdf, 490, 711, f"{eq.service}   |   Cota del piso: {project.deck:g} m", 10)
    chart(pdf, (46, 347, 545, 345), (0, 2), [part])
    chart(pdf, (606, 347, 539, 345), (0, 1), [part])
    text(pdf, 46, 315, "ENVOLVENTE EXTERIOR MEDIDA EN EL IFC", 10, True)
    for index, (label, value, unit) in enumerate(envelope_rows(part)):
        text(pdf, 46, 294 - index * 15, f"{label} = {value:.1f} {unit}", 10)
    own = [line for line in lines.values() if eq.tag in (line.start, line.end)]
    table(
        pdf,
        606,
        324,
        ("Interfaz", "DN (mm)", "X / Y / Z (m)"),
        [
            (
                line.tag,
                line.dn,
                " / ".join(
                    f"{value:.2f}" for value in routes[line.tag][0 if eq.tag == line.start else -1]
                ),
            )
            for line in own
        ],
        (192, 92, 255),
    )
    table(
        pdf,
        46,
        190,
        ("Componente", "Acabado de referencia", "Función"),
        part.details,
        (360, 265, 474),
        height=15,
    )
    pdf.save()


def sheet(workbook, name, header, rows, widths):
    ws = workbook.create_sheet(name)
    ws.append(header)
    for row in rows:
        ws.append(row)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="18354B")
        cell.alignment = Alignment(wrap_text=True)
    for i, width in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = width
    return ws


def workbook(path_, project, revision, equipment, lines, routes, parts):
    book = Workbook()
    book.remove(book.active)
    date = datetime(2026, 1, 1)
    book.properties.created = book.properties.modified = date
    book.properties.title = f"{project.code} / Rev {revision} / Datos sintéticos"
    sheet(
        book,
        "Proyecto",
        ("Campo", "Valor"),
        (
            ("Procedencia", "Datos sintéticos · DRAFT"),
            ("Proyecto", project.name),
            ("Entorno base", project.setting),
            ("Revisión", revision),
            ("Elevación de piso (m)", project.deck),
            ("Ejes", "+X Este, +Y Norte de dibujo, +Z Elevación"),
            ("Alcance", "Envolventes y conexiones conceptuales"),
        ),
        (30, 74),
    )
    sheet(
        book,
        "Equipos",
        (
            "Tag",
            "Descripción",
            "Familia",
            "Servicio",
            "X (m)",
            "Y (m)",
            "Largo (mm)",
            "Ancho (mm)",
            "Alto (mm)",
            "Plano",
        ),
        [
            (
                eq.tag,
                eq.name,
                eq.family,
                eq.service,
                *eq.xy,
                *(int(round(value * 1000)) for value in eq.size),
                f"GAD_{eq.tag}_rev{revision}.pdf",
            )
            for eq in equipment.values()
        ],
        (15, 43, 22, 29, 12, 12, 16, 16, 16, 28),
    )
    sheet(
        book,
        "Líneas",
        ("Línea", "Origen", "Destino", "Servicio", "DN (mm)", "Rack Y (m)", "Rack Z (m)"),
        [
            (
                line.tag,
                line.start,
                line.end,
                line.fluid,
                line.dn,
                line.rack_y,
                line.rack_z + project.deck,
            )
            for line in lines.values()
        ],
        (18, 18, 18, 20, 18, 18, 18),
    )
    sheet(
        book,
        "Nodos",
        ("Línea", "Punto", "X (m)", "Y (m)", "Z (m)"),
        [
            (tag, i, *(round(axis, 4) for axis in point))
            for tag, route in routes.items()
            for i, point in enumerate(route, 1)
        ],
        (18, 12, 18, 18, 18),
    )
    sheet(
        book,
        "Componentes",
        ("Tag", "Tipo", "Componente", "Acabado", "Función"),
        [(part.tag, part.kind, *detail) for part in parts for detail in part.details],
        (18, 20, 44, 25, 44),
    )
    sheet(
        book,
        "Cambios",
        ("Tag", "Descripción", "Valor A", "Valor B", "Unidad", "Estado"),
        changes(project, revision),
        (18, 72, 18, 18, 14, 18),
    )
    book.save(path_)


def equipment_workbook(path_, project, revision, eq, part, lines, routes):
    book = Workbook()
    book.remove(book.active)
    date = datetime(2026, 1, 1)
    book.properties.created = book.properties.modified = date
    sheet(
        book,
        "Ficha",
        ("Campo", "Valor", "Unidad"),
        (
            ("Procedencia", "Datos sintéticos · DRAFT", "—"),
            ("Proyecto", project.code, "—"),
            ("Tag", eq.tag, None),
            ("Revisión", revision, "—"),
            ("Familia", eq.family, "—"),
            ("Servicio", eq.service, "—"),
            ("X local", eq.xy[0], "m"),
            ("Y local", eq.xy[1], "m"),
            ("Z de piso", project.deck, "m"),
            *(
                (label, round(value * 1000), "mm")
                for label, value in zip(("Largo", "Ancho", "Alto"), eq.size)
            ),
        ),
        (24, 55, 13),
    )
    sheet(
        book,
        "Interfaces",
        ("Línea", "Servicio", "DN (mm)", "X (m)", "Y (m)", "Z (m)"),
        [
            (
                line.tag,
                line.fluid,
                line.dn,
                *(round(axis, 4) for axis in routes[line.tag][0 if eq.tag == line.start else -1]),
            )
            for line in lines.values()
            if eq.tag in (line.start, line.end)
        ],
        (16, 24, 16, 18, 18, 18),
    )
    sheet(book, "Piezas", ("Componente", "Acabado", "Función"), part.details, (44, 24, 44))
    sheet(book, "Envolvente", ("PARAMETER", "VALUE", "UNIT"), envelope_rows(part), (29, 19, 13))
    book.save(path_)


def envelope_rows(part):
    vertices = [point for mesh in part.meshes.values() for point in mesh.vertices]
    for index, axis in enumerate("XYZ"):
        values = [point[index] for point in vertices]
        origin = min(values)
        yield f"ENVELOPE_ORIGIN_{axis}", round(origin * 1000, 1), "mm"
        yield f"ENVELOPE_SIZE_{axis}", round((max(values) - origin) * 1000, 1), "mm"
