"""Estrategia A · visión + 3D (DEC-02 y DEC-07).

La geometría sale de los trazos del dibujo, no del texto: virola, fondos, faldón, boquillas del
alzado y muñones de la planta. Un «lector» aporta solo lo que el dibujo no dice por sí mismo:
- las cotas, para fijar la escala (y, si un número leído cuadra con una longitud medida, se usa
  ese número exacto y se cita);
- las etiquetas de las boquillas, para saber cuál es cuál;
- el tag y el espesor de faldón rotulados en la vista.

A no usa la tabla de boquillas ni los datos de diseño del GA. Los atributos salen de la hoja de
datos, que DEC-02 permite fuera de la geometría.

Lectores: «texto» (capa de texto del PDF u OCR si no la hay; es la variante a_geometria, que mide
el canal geométrico), «detector» (el detector propio en escaneados, desde su caché: a_detector) y
«vision» (modelo de visión por mosaicos: a_vision).
"""

import io
import math
import time

import pdfplumber

from ..extraction import Candidate, LabelExtractor
from ..extractors.drawing import DIMENSION_TEXT, MARK, DrawingExtractor, document_context
from ..extractors.units import DN_SERIES, parse_length_any_direction
from ..geometry2d.vector import Elevation, Plan, find_elevation, find_plan
from ..ingest import EvidenceLine
from ..model import Source
from .base import StageEvent, StrategyContext, StrategyOutput, tag_candidates

GEOMETRY_CONFIDENCE = 0.6  # medida sin cota que la confirme
READ_CONFIDENCE = 0.9  # cota leída que cuadra con la medida


class VisionGeometryStrategy:
    def __init__(self, *, reader: str = "texto", name: str = "a_geometria"):
        self.reader, self.name = reader, name

    def run(self, ctx: StrategyContext) -> StrategyOutput:
        started = time.perf_counter()
        out = StrategyOutput([])
        for bundle in ctx.bundles:
            name = bundle.document.filename
            if bundle.media_type == "xlsx":
                found = tag_candidates(
                    LabelExtractor().extract([bundle]), channel="hoja_datos", strategy=self.name
                )
                out.candidates += found
                ctx.emit(StageEvent("extract_hdm", "ok", name, f"{len(found)} atributos."))
                continue
            data = ctx.raw.get(bundle.document.id)
            if bundle.media_type != "pdf" or data is None:
                continue
            found, evidence, warnings = self._read_drawing(bundle, data, ctx)
            out.candidates += found
            out.warnings += warnings
            if evidence:
                out.evidence[bundle.document.id] = evidence
        out.cost.seconds = time.perf_counter() - started
        return out

    # -------------------------------------------------------------------------------------
    def _read_drawing(self, bundle, data: bytes, ctx: StrategyContext):
        name = bundle.document.filename
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages = [
                (n, page, float(page.width), float(page.height))
                for n, page in enumerate(pdf.pages, 1)
            ]
            for number, page, w, h in pages:
                elevation = find_elevation(page)
                if elevation is None:
                    continue
                plan = find_plan(page, elevation.shell)
                return self._finish(bundle, data, ctx, number, (w, h), elevation, plan, "vectorial")
        # Sin trazos vectoriales (escaneado): geometría por imagen.
        for number, _, w, h in pages:
            measured = _raster_geometry(data, number)
            if measured is None:
                continue
            elevation, plan = measured
            return self._finish(bundle, data, ctx, number, (w, h), elevation, plan, "escaneado")
        ctx.emit(StageEvent("geometry2d", "omitido", name, "Sin alzado reconocible."))
        return [], [], [f"{name}: sin geometría reconocible"]

    def _finish(self, bundle, data, ctx, number, size, elevation, plan, kind):
        lines = self._reader_lines(bundle, data, number, ctx)
        ctx.emit(
            StageEvent(
                "geometry2d",
                "ok",
                bundle.document.filename,
                f"Alzado {kind} con {len(elevation.stubs)} boquillas"
                + (f" · planta con {len(plan.stubs)} muñones." if plan else " · sin planta."),
            )
        )
        found = self._measure(bundle.document.id, number, size, elevation, plan, lines)
        if kind == "escaneado":  # medida sobre imagen: menos precisa que sobre trazos
            found = [
                c
                if c.text_original
                else c.model_copy(
                    update={
                        "source": c.source.model_copy(
                            update={"confidence": c.source.confidence * 0.7}
                        )
                    }
                )
                for c in found
            ]
        return tag_candidates(found, channel="geometria", strategy=self.name), lines, []

    def _reader_lines(self, bundle, data, page, ctx) -> list[EvidenceLine]:
        if self.reader == "vision":
            from ..vision import get_provider, read_page, render_page

            spec = (ctx.providers or ["ollama:qwen3-vl:4b-instruct"])[0]
            provider = get_provider(spec, dataset=ctx.dataset)
            reading = read_page(
                provider,
                render_page(data, page),
                page_ref=f"{bundle.document.sha256}#p{page}",
            )
            ctx.emit(
                StageEvent(
                    "extract_vision",
                    "ok" if not reading.errors else "error",
                    bundle.document.filename,
                    f"{len(reading.items)} textos · {reading.tiles} mosaicos · "
                    f"{reading.seconds:.0f} s de modelo.",
                )
            )
            return [
                EvidenceLine(
                    text=item["text"],
                    source=Source(
                        document_id=bundle.document.id,
                        page=page,
                        locator=f"Visión ({provider.name}) · página {page}",
                        bbox=tuple(item["bbox"]),
                        confidence=0.8,
                    ),
                )
                for item in reading.items
            ]
        own = [line for line in bundle.lines if line.source.page == page]
        if own:
            return own
        if self.reader == "detector":
            # Detector propio (tarea 2.4): solo su caché; sin ella, el OCR de siempre.
            from ..ocr.detector import detector_pdf_lines

            lines = detector_pdf_lines(data, bundle.document.id, bundle.document.page_count or 1)
            if lines is not None:
                ctx.emit(
                    StageEvent(
                        "extract_detector",
                        "ok",
                        bundle.document.filename,
                        f"{len(lines)} textos del detector propio.",
                    )
                )
                return [line for line in lines if line.source.page == page]
        from ..ocr import OcrUnavailable, ocr_pdf_lines

        try:
            return ocr_pdf_lines(data, bundle.document.id, pages=[page])
        except OcrUnavailable:
            return []

    # -------------------------------------------------------------------------------------
    def _measure(
        self, doc_id, page, size, e: Elevation, plan: Plan | None, lines
    ) -> list[Candidate]:
        width, height = size

        def norm_box(x0, y0, x1, y1):
            return (
                max(0.0, min(x0, x1) / width),
                max(0.0, min(y0, y1) / height),
                min(1.0, max(x0, x1) / width),
                min(1.0, max(y0, y1) / height),
            )

        def source(box, confidence, locator):
            return Source(
                document_id=doc_id, page=page, locator=locator, bbox=box, confidence=confidence
            )

        ctx_doc = document_context(lines)
        lengths = {
            "skirt_height": e.skirt,
            "height": e.shell_height,
            "head_depth": e.head_top,
            "overall": e.overall,
        }
        readings = []
        for line in lines:
            text = line.text.strip()
            if sum(ch.isdigit() for ch in text) >= 2 and DIMENSION_TEXT.match(text):
                for value in parse_length_any_direction(text, decimal=ctx_doc.decimal):
                    readings.append((line, value))
        scale, matches = _consensus_scale(readings, lengths)
        if scale is None:
            return []
        x0, top, x1, bottom = e.shell
        out: list[Candidate] = []
        boxes = {
            "skirt_height": norm_box(x0, bottom, x1, e.ground),
            "height": norm_box(x0, top, x1, bottom),
            "head_depth": norm_box(x0, top - e.head_top, x1, top),
        }
        for key in ("skirt_height", "height", "head_depth"):
            if key in matches:
                line, value = matches[key]
                out.append(
                    Candidate(
                        path=key,
                        value=round(value, 3),
                        unit="mm",
                        source=line.source.model_copy(
                            update={
                                "confidence": READ_CONFIDENCE,
                                "locator": "Cota leída · geometría",
                            }
                        ),
                        text_original=line.text,
                        explanation="Cota leída y asignada por la medida del dibujo.",
                    )
                )
            else:
                out.append(
                    Candidate(
                        path=key,
                        value=round(lengths[key] / scale, 1),
                        unit="mm",
                        source=source(boxes[key], GEOMETRY_CONFIDENCE, "Medida sobre el alzado"),
                        explanation=f"Medido en el dibujo a escala 1:{1 / scale * 2.835:.0f}.",
                    )
                )
        diameter = e.width / scale
        labels = DrawingExtractor()._labels(lines, ctx_doc)
        read_d = next((c for c in labels if c.path == "diameter"), None)
        if read_d is not None and abs(float(read_d.value) - diameter) <= 0.01 * diameter:
            diameter = float(read_d.value)
            out.append(
                read_d.model_copy(
                    update={"explanation": "Diámetro leído, confirmado por el ancho dibujado."}
                )
            )
        else:
            out.append(
                Candidate(
                    path="diameter",
                    value=round(diameter, 1),
                    unit="mm",
                    source=source(
                        norm_box(x0, top, x1, bottom), GEOMETRY_CONFIDENCE, "Ancho de la virola"
                    ),
                    explanation="Medido en el dibujo con la escala de las cotas verticales.",
                )
            )
        out += [c for c in labels if c.path in ("tag", "skirt_thickness")]
        out += self._nozzles(e, plan, scale, diameter, lines, size, source, norm_box)
        return out

    def _nozzles(self, e, plan, scale, diameter, lines, size, source, norm_box) -> list[Candidate]:
        """Cruce alzado ↔ planta (DEC-07).

        El alzado da cota, lado y DN de cada boquilla etiquetada. La planta da orientación y
        saliente. Cada etiqueta se asigna a un solo trazo; los muñones de planta sin etiqueta
        legible (etiquetas superpuestas) se emparejan con boquillas del alzado por lado y DN.
        """
        width, height = size
        ends = [stub.end for stub in e.stubs] + ([stub.end for stub in plan.stubs] if plan else [])

        def near_a_stub(line):
            bx0, by0, bx1, by1 = line.source.bbox
            cx, cy = (bx0 + bx1) / 2 * width, (by0 + by1) / 2 * height
            return any(math.hypot(cx - x, cy - y) <= 40 for x, y in ends)

        # Solo cuentan como etiquetas las marcas junto a un trazo de boquilla: «DN150» de una
        # tabla también parece una marca.
        marks = [
            (line, line.text.strip().upper().replace(" ", ""))
            for line in lines
            if MARK.match(line.text.strip().upper().replace(" ", "")) and near_a_stub(line)
        ]

        def assign(points):
            """Etiqueta más cercana a cada punto, sin repetir etiqueta ni punto."""
            pairs = []
            for i, (px, py) in enumerate(points):
                for line, mark in marks:
                    bx0, by0, bx1, by1 = line.source.bbox
                    d = math.hypot((bx0 + bx1) / 2 - px / width, (by0 + by1) / 2 - py / height)
                    if d <= 0.035:
                        pairs.append((d, i, mark))
            taken_points, taken_marks, out = set(), set(), {}
            for d, i, mark in sorted(pairs):
                if i not in taken_points and mark not in taken_marks:
                    taken_points.add(i)
                    taken_marks.add(mark)
                    out[i] = mark
            return out

        def snap_dn(drawn):
            dn = min(DN_SERIES, key=lambda d: abs(d - drawn))
            return dn, abs(dn - drawn) <= 0.2 * dn

        elevation = {}
        # La etiqueta va justo después de la brida y por encima del eje.
        anchors = [
            (stub.end[0] + (12 if stub.side >= 0 else -12), stub.z - stub.neck - 6)
            for stub in e.stubs
        ]
        for i, mark in assign(anchors).items():
            stub = e.stubs[i]
            elevation[mark] = (stub, snap_dn(2 * stub.neck / scale)[0])
        out: list[Candidate] = []
        for mark, (stub, _) in elevation.items():
            box = norm_box(
                stub.end[0] - 4, stub.z - stub.neck - 2, stub.end[0] + 4, stub.z + stub.neck + 2
            )
            out.append(
                Candidate(
                    path=f"nozzles.{mark}.elevation",
                    value=round((e.ground - stub.z) / scale, 1),
                    unit="mm",
                    source=source(box, GEOMETRY_CONFIDENCE + 0.2, f"Alzado · eje de {mark}"),
                    explanation="Altura del eje de la boquilla medida en el alzado.",
                )
            )
        if plan is None:
            return out
        sp = plan.radius / (diameter / 2)
        labelled, matched = _match_plan(plan, elevation, marks, sp, size, snap_dn, e, scale)
        for i, stub in enumerate(plan.stubs):
            mark = labelled.get(i) or matched.get(i)
            if not mark:
                continue
            via = "etiqueta" if i in labelled else "cruce con el alzado (lado y DN)"
            confidence = GEOMETRY_CONFIDENCE + (0.2 if i in labelled else 0.0)
            box = norm_box(stub.end[0] - 6, stub.end[1] - 6, stub.end[0] + 6, stub.end[1] + 6)
            dn, good = snap_dn(2 * stub.neck / sp)
            out += [
                Candidate(
                    path=f"nozzles.{mark}.azimuth",
                    value=round(stub.angle, 1),
                    unit="deg",
                    source=source(box, confidence, f"Planta · muñón de {mark}"),
                    explanation=f"Ángulo del muñón medido en la planta; identificado por {via}.",
                ),
                Candidate(
                    path=f"nozzles.{mark}.projection",
                    value=round(stub.length / sp, 1),
                    unit="mm",
                    source=source(box, confidence - 0.1, f"Planta · muñón de {mark}"),
                    explanation="Saliente medido en la planta a la escala del diámetro.",
                ),
                Candidate(
                    path=f"nozzles.{mark}.diameter",
                    value=float(dn),
                    unit="mm",
                    source=source(
                        box, confidence - 0.1 if good else 0.3, f"Planta · cuello de {mark}"
                    ),
                    explanation=f"Cuello dibujado de {2 * stub.neck / sp:.0f} mm; DN normalizado.",
                ),
            ]
        return out


RASTER_DPI = 200


def _raster_geometry(data: bytes, page: int):
    """Alzado y planta de una página escaneada, en puntos del marco original de la página."""
    from dataclasses import replace

    from ..geometry2d import raster
    from ..vision.reader import render_page

    try:
        image = render_page(data, page, dpi=RASTER_DPI)
        ink, angle = raster.binarize(image, with_angle=True)
    except ImportError:
        return None
    k = RASTER_DPI / 72
    elevation = raster.find_elevation(ink, k)
    if elevation is None:
        return None
    plan = raster.find_plan(ink, k, (elevation.shell[0], elevation.shell[2]))

    def back(point):  # puntos → marco sin enderezar, para casar con las cajas del lector
        x, y = raster.unrotate((point[0] * k, point[1] * k), angle, ink.shape)
        return (x / k, y / k)

    elevation.stubs = [replace(s, end=back(s.end)) for s in elevation.stubs]
    if plan is not None:
        plan.stubs = [replace(s, end=back(s.end)) for s in plan.stubs]
    return elevation, plan


def _side_of(angle: float) -> int:
    c = math.cos(math.radians(angle))
    return 0 if abs(c) < 0.3 else (1 if c > 0 else -1)


def _match_plan(plan, elevation, marks, sp, size, snap_dn, e, scale):
    """Asignación global óptima muñón ↔ boquilla (algoritmo húngaro).

    Coste: distancia a la etiqueta de esa boquilla (si se lee cerca), más penalización si el lado
    o el DN no cuadran con el alzado. Devuelve (asignados con etiqueta, asignados por cruce).
    """
    from scipy.optimize import linear_sum_assignment

    width, height = size
    names = sorted(set(elevation) | {m for _, m in marks})
    if not names or not plan.stubs:
        return {}, {}
    cost = []
    near = {}
    for i, stub in enumerate(plan.stubs):
        row = []
        px, py = stub.end[0] / width, stub.end[1] / height
        dn_plan = snap_dn(2 * stub.neck / sp)[0]
        for name in names:
            label_d = min(
                (
                    math.hypot((b[0] + b[2]) / 2 - px, (b[1] + b[3]) / 2 - py)
                    for line, m in marks
                    if m == name
                    for b in [line.source.bbox]
                ),
                default=1.0,
            )
            c = label_d if label_d <= 0.035 else 0.06
            if label_d <= 0.035:
                near[(i, name)] = True
            if name in elevation:
                estub, dn_elev = elevation[name]
                c += 0.5 * (_side_of(stub.angle) != estub.side) + 0.2 * (dn_plan != dn_elev)
                cos = abs(math.cos(math.radians(stub.angle)))
                if estub.side != 0 and cos >= 0.3:
                    # Saliente visto de lado en el alzado = saliente · |cos θ|: debe cuadrar.
                    edge = e.shell[2] if estub.side > 0 else e.shell[0]
                    proj_elev = abs(estub.end[0] - edge) / scale / cos
                    proj_plan = stub.length / sp
                    c += 0.1 * (abs(proj_elev - proj_plan) > 0.05 * proj_plan)
            row.append(c)
        cost.append(row)
    rows, cols = linear_sum_assignment(cost)
    labelled, matched = {}, {}
    for i, j in zip(rows, cols, strict=True):
        if cost[i][j] >= 0.5:
            continue  # incoherente con el alzado: mejor no asignar
        (labelled if near.get((i, names[j])) else matched)[i] = names[j]
    return labelled, matched


def _consensus_scale(readings, lengths) -> tuple[float | None, dict]:
    """Escala (pt/mm) que hace coincidir más números leídos con longitudes medidas."""
    best: tuple[int, float, dict] | None = None
    for line, value in readings:
        for key, measured in lengths.items():
            if value <= 0:
                continue
            scale = measured / value
            matches = {}
            for other_line, other_value in readings:
                for other_key, other_measured in lengths.items():
                    if other_key in matches:
                        continue
                    if abs(other_value * scale - other_measured) <= 0.004 * other_measured + 0.2:
                        matches[other_key] = (other_line, other_value)
                        break
            if best is None or len(matches) > best[0]:
                best = (len(matches), scale, matches)
    if best is None or best[0] < 2:
        return None, {}
    _, scale, matches = best
    # Escala final: media ponderada de las cotas que cuadran (más precisa que una sola).
    pairs = [(lengths[k], v) for k, (_, v) in matches.items()]
    scale = sum(m for m, _ in pairs) / sum(v for _, v in pairs)
    return scale, matches
