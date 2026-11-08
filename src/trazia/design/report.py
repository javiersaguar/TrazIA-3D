"""Plano derivado de una revisión de diseño (K.6).

Genera un PDF aparte, identificado como documento derivado, con la tabla de cambios y las
páginas del plano original anotadas solo donde la ubicación es verificable (página y región
de la evidencia de lectura). El original y su SHA-256 no se modifican. Una anotación no
redibuja el recipiente: si cambia la geometría, el dibujo deja de estar a escala y se avisa.
"""

import io

from PIL import Image, ImageDraw, ImageFont

from trazia.model import Revision

INK = (28, 31, 36)
MUTED = (96, 102, 112)
MARK = (214, 92, 36)  # color de revisión
PAGE = (1754, 1240)  # A4 apaisado a 150 ppp
GEOMETRY = ("diameter", "height", "total_height", "head_depth", "skirt_height", "skirt_thickness")


def _font(size: int, bold: bool = False):
    for name in ("DejaVuSans-Bold.ttf", "arialbd.ttf") if bold else ("DejaVuSans.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def _value(item: dict) -> str:
    value, unit = item["value"], item["unit"]
    if isinstance(value, float):
        value = f"{value:g}"
    return f"{value} {'°' if unit == 'deg' else '' if unit == '1' else unit}".strip()


def locations(revision: Revision, content: dict) -> list[dict]:
    """Ubicación verificable de cada operación en el plano, o el motivo de que falte."""
    documents = {d.id: d for d in revision.documents}
    result = []
    for index, operation in enumerate(content["operations"], start=1):
        source = operation.get("before_source") or {}
        document = documents.get(source.get("document_id"))
        reason = None
        if source.get("channel") == "diseno":
            reason = "el valor anterior ya era una orden de diseño, sin región del plano"
        elif document is None or document.role is not None:
            reason = "sin documento original"
        elif not document.filename.lower().endswith(".pdf"):
            reason = "la evidencia no es un PDF"
        elif source.get("page") is None or source.get("bbox") is None:
            reason = "la lectura no tiene región delimitada"
        result.append(
            {
                "mark": f"Δ{index}",
                "operation": operation,
                "document": document if reason is None else None,
                "page": source.get("page"),
                "bbox": source.get("bbox"),
                "pending": reason,
            }
        )
    return result


def _render(data: bytes, page: int) -> Image.Image:
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(data)
    try:
        if not 1 <= page <= len(document):
            raise ValueError("Página fuera del PDF")
        source = document[page - 1]
        try:
            width, height = source.get_size()
            scale = min(PAGE[0] / width, (PAGE[1] - 120) / height)
            bitmap = source.render(scale=scale)
            try:
                return bitmap.to_pil().convert("RGB")
            finally:
                bitmap.close()
        finally:
            source.close()
    finally:
        document.close()


def _banner(draw: ImageDraw.ImageDraw, width: int, lines: list[str]):
    draw.rectangle((0, 0, width, 34 + 26 * len(lines)), fill=(255, 241, 230))
    for index, line in enumerate(lines):
        draw.text(
            (24, 16 + 26 * index),
            line,
            fill=MARK if index == 0 else INK,
            font=_font(20, bold=index == 0),
        )


def _annotated(data: bytes, page: int, marks: list[dict], document, scale_warning: bool):
    drawing = _render(data, page)
    image = Image.new("RGB", PAGE, "white")
    image.paste(drawing, ((PAGE[0] - drawing.width) // 2, 110))
    draw = ImageDraw.Draw(image)
    lines = [
        f"DOCUMENTO DERIVADO · anotaciones sobre {document.filename} p. {page} · DRAFT",
        f"Original intacto, SHA-256 {document.sha256[:16]}…",
    ]
    if scale_warning:
        lines.append("El dibujo ya no está a escala para las cotas marcadas: ver el IFC publicado.")
    _banner(draw, PAGE[0], lines)
    left = (PAGE[0] - drawing.width) // 2
    for mark in marks:
        x0, y0, x1, y1 = mark["bbox"]
        box = (
            left + x0 * drawing.width,
            110 + y0 * drawing.height,
            left + x1 * drawing.width,
            110 + y1 * drawing.height,
        )
        draw.rectangle(box, outline=MARK, width=4)
        operation = mark["operation"]
        label = (
            f"{mark['mark']} {operation['label']}: {_value(operation['before'])} → "
            f"{_value(operation['after'])}"
        )
        font = _font(20, bold=True)
        tx, ty = box[0], max(box[1] - 30, 112)
        width = draw.textlength(label, font=font)
        draw.rectangle((tx - 4, ty - 2, tx + width + 6, ty + 26), fill="white", outline=MARK)
        draw.text((tx, ty), label, fill=MARK, font=font)
    return image


def design_report(
    revision: Revision,
    content: dict,
    originals: dict[str, bytes],
    *,
    meta: dict,
) -> bytes:
    """PDF derivado. `originals` va indexado por SHA-256 y se lee, nunca se reescribe."""
    if revision.derived_from is None:
        raise ValueError("Solo una revisión derivada de una orden de diseño tiene informe")
    marks = locations(revision, content)
    for mark in marks:
        document = mark["document"]
        if document is not None and document.sha256 not in originals:
            mark["document"], mark["pending"] = None, "original no disponible para verificar"
    geometric = any(
        "collection" in m["operation"]
        or m["operation"]["target"].startswith(
            ("horizontal.", "column.", "tank.", "envelope.", "platforms.", "ladders.")
        )
        or m["operation"]["target"] in GEOMETRY
        or m["operation"]["target"].endswith((".elevation", ".azimuth", ".diameter", ".projection"))
        for m in marks
    )
    return _paginated_report(revision, content, marks, originals, meta, geometric)


def _paginated_report(revision, content, marks, originals, meta, geometric):
    """Tablas largas con repetición de cabecera; ninguna operación queda fuera de página."""
    from html import escape

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Image as PDFImage
    from reportlab.platypus import (
        LongTable,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        TableStyle,
    )

    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        title=f"DERIVADO · {revision.equipment.tag.value} Rev {revision.revision} · DRAFT",
        author=content["actor"],
        subject="trazia-derivado; no es un original",
    )
    styles = getSampleStyleSheet()
    cell = ParagraphStyle("celda", parent=styles["Normal"], fontSize=8, leading=11)

    def paragraph(text):
        return Paragraph(escape(str(text)), cell)

    story = [Paragraph("DOCUMENTO DERIVADO - REVISION DE DISEÑO - DRAFT", styles["Heading1"])]
    for line in [
        f"{revision.equipment.tag.value} · {content['base']['revision']} → {revision.revision}",
        f"Autor: {content['actor']} · fecha: {meta['generated_at']}",
        f"Motivo: {content['reason']}",
        f"Orden SHA-256: {meta['order_sha256']}",
        f"IFC SHA-256: {meta.get('ifc_sha256', '—')}",
        f"Dataset: {revision.dataset}. Original conservado. Pendiente de revisión técnica.",
    ]:
        story += [paragraph(line), Spacer(1, 3 * mm)]
    rows = [[paragraph(t) for t in ("Marca", "Campo", "Antes", "Después", "Ubicación")]]
    for index, mark in enumerate(marks, 1):
        op = mark["operation"]
        where = (
            f"{mark['document'].id} p. {mark['page']}"
            if mark["document"]
            else f"Pendiente de delineación: {mark['pending']}"
        )
        rows.append(
            [
                paragraph(t)
                for t in (
                    f"D{index}",
                    op["label"],
                    _value(op["before"]),
                    _value(op["after"]),
                    where,
                )
            ]
        )
    table = LongTable(
        rows, colWidths=[14 * mm, 72 * mm, 40 * mm, 40 * mm, 103 * mm], repeatRows=1, splitInRow=1
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f7")),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story += [table, Spacer(1, 5 * mm)]
    if geometric:
        story += [
            paragraph(
                "Aviso: cambian cotas o posiciones. El dibujo original ya "
                "no representa a escala la geometría nueva; las anotaciones no lo redibujan."
            )
        ]
    story += [
        paragraph(
            "No certifica fabricación ni cálculo resistente. La geometría "
            "vigente es la del IFC asociado."
        )
    ]
    grouped = {}
    for mark in marks:
        if mark["document"]:
            grouped.setdefault((mark["document"].id, mark["page"]), []).append(mark)
    for (_, page), items in sorted(grouped.items()):
        doc = items[0]["document"]
        image = _annotated(originals[doc.sha256], page, items, doc, geometric)
        stream = io.BytesIO()
        image.save(stream, format="PNG")
        stream.seek(0)
        story += [
            PageBreak(),
            PDFImage(stream, width=250 * mm, height=250 * PAGE[1] / PAGE[0] * mm),
        ]

    def footer(canvas, doc):
        canvas.setFont("Helvetica", 8)
        canvas.drawString(
            12 * mm, 6 * mm, f"TrazIA-3D · documento derivado DRAFT · página {doc.page}"
        )

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
