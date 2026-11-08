"""Plano derivado de una revisión de diseño (K.6).

Genera un PDF aparte, identificado como documento derivado, con la tabla de cambios y las
páginas del plano original anotadas solo donde la ubicación es verificable (página y región
de la evidencia de lectura). El original y su SHA-256 no se modifican. Una anotación no
redibuja el recipiente: si cambia la geometría, el dibujo deja de estar a escala y se avisa.
"""

import io
import textwrap
from datetime import datetime

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


def _cover(revision: Revision, content: dict, marks: list[dict], meta: dict) -> Image.Image:
    image = Image.new("RGB", PAGE, "white")
    draw = ImageDraw.Draw(image)
    _banner(
        draw,
        PAGE[0],
        [
            "DOCUMENTO DERIVADO · PROPUESTA DE REVISIÓN DE DISEÑO · DRAFT",
            "No es un plano original ni de fabricación. El original se conserva intacto.",
        ],
    )
    y = 110
    title = (
        f"{revision.equipment.tag.value} · Rev {content['base']['revision']} → Rev "
        f"{revision.revision}"
    )
    draw.text((60, y), title, fill=INK, font=_font(40, bold=True))
    y += 64
    kind = "Deshacer una orden anterior" if content["kind"] == "reversion" else "Cambio de diseño"
    for line in (
        f"{kind} · propuesta {content['proposal_id'][:12]} · origen {content['origin']}",
        f"Autor: {content['actor']} · preparada {content['created_at']} · "
        f"informe {meta['generated_at']}",
        f"Motivo: {content['reason']}",
        f"Revisión base {content['base']['revision_id']} · huella "
        f"{content['base']['input_sha256'][:16]}",
        f"IFC publicado {meta.get('ifc_sha256', '—')[:16]} · orden {meta['order_sha256'][:16]}",
        f"Conjunto de datos: {revision.dataset}"
        + (" (sintético, no procede de TR)" if revision.dataset == "synthetic" else ""),
    ):
        for wrapped in textwrap.wrap(line, 120) or [""]:
            draw.text((60, y), wrapped, fill=MUTED, font=_font(22))
            y += 32
    y += 18
    columns = (60, 160, 700, 960, 1220)
    for x, head in zip(columns, ("Marca", "Campo", "Antes", "Después", "Ubicación en el plano")):
        draw.text((x, y), head, fill=INK, font=_font(22, bold=True))
    y += 38
    draw.line((60, y - 6, PAGE[0] - 60, y - 6), fill=MUTED, width=1)
    for mark in marks:
        operation = mark["operation"]
        where = (
            f"{mark['document'].id} p. {mark['page']}"
            if mark["document"] is not None
            else f"Pendiente de delineación: {mark['pending']}"
        )
        cells = (
            mark["mark"],
            operation["label"],
            _value(operation["before"]),
            _value(operation["after"]),
            where,
        )
        height = 1
        for x, text, width in zip(columns, cells, (8, 40, 18, 18, 38)):
            lines = textwrap.wrap(text, width) or [""]
            height = max(height, len(lines))
            for row, line in enumerate(lines):
                draw.text((x, y + 30 * row), line, fill=MARK if x == 60 else INK, font=_font(22))
        y += 30 * height + 12
        if operation.get("resolution"):
            draw.text((160, y - 8), operation["resolution"][:150], fill=MUTED, font=_font(18))
            y += 26
    geometric = [
        m
        for m in marks
        if m["operation"]["target"] in GEOMETRY
        or m["operation"]["target"].endswith((".elevation", ".azimuth", ".diameter", ".projection"))
    ]
    y += 20
    notes = []
    if geometric:
        notes.append(
            "Aviso de escala: cambian cotas o posiciones, así que el dibujo original ya no "
            "representa a escala la geometría nueva. Las marcas señalan dónde cambia el dato; "
            "no redibujan el recipiente. La geometría vigente es la del IFC publicado."
        )
    if any(m["document"] is None for m in marks):
        notes.append(
            "Los cambios sin región verificable en el plano figuran solo en esta tabla; "
            "no se dibuja una ubicación supuesta."
        )
    notes.append(
        "La coherencia de parámetros e IFC no acredita cálculo resistente, proceso ni "
        "cumplimiento normativo. La aprobación técnica es una acción humana posterior."
    )
    for note in notes:
        for wrapped in textwrap.wrap(note, 130):
            draw.text((60, y), wrapped, fill=INK, font=_font(20))
            y += 28
        y += 10
    return image


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
        m["operation"]["target"] in GEOMETRY
        or m["operation"]["target"].endswith((".elevation", ".azimuth", ".diameter", ".projection"))
        for m in marks
    )
    pages = [_cover(revision, content, marks, meta)]
    grouped: dict[tuple, list[dict]] = {}
    for mark in marks:
        if mark["document"] is not None:
            grouped.setdefault((mark["document"].id, mark["page"]), []).append(mark)
    for (_, page), items in sorted(grouped.items()):
        document = items[0]["document"]
        pages.append(_annotated(originals[document.sha256], page, items, document, geometric))
    buffer = io.BytesIO()
    created = datetime.fromisoformat(meta["generated_at"].replace("Z", "+00:00"))
    pages[0].save(
        buffer,
        "PDF",
        save_all=True,
        append_images=pages[1:],
        resolution=150,
        title=f"DERIVADO · {revision.equipment.tag.value} Rev {revision.revision} · DRAFT",
        author=content["actor"],
        subject="Propuesta de revisión de diseño; no es un original",
        keywords=f"trazia-derivado;propuesta={content['proposal_id']}",
        creator="TrazIA-3D",
        creationDate=created.utctimetuple(),
        modDate=created.utctimetuple(),
    )
    return buffer.getvalue()
