"""Estrategia B · datos + reglas: texto, tablas, cotas, cajetín, HDM y VESOR, sin aprendizaje."""

import re
import time

from ..extraction import LabelExtractor
from ..extractors import DrawingExtractor
from ..extractors.vesor import is_vesor, plan_labels
from ..model import GEOMETRY_FIELDS
from .base import StageEvent, StrategyContext, StrategyOutput, tag_candidates


def complete_dimensions(candidates):
    paths = {c.path for c in candidates}
    if all(f"envelope.size.{axis}" in paths for axis in "xyz"):
        return True
    if not set(GEOMETRY_FIELDS).issubset(paths):
        return False
    values = {c.path: float(c.value) for c in candidates if c.path in GEOMETRY_FIELDS}
    return min(values.values()) > 0 and values["head_depth"] <= min(
        values["diameter"] / 2, values["skirt_height"]
    )


class ReglasStrategy:
    """`drawing` y `hdm` permiten las ablaciones del estudio (quitar un canal cada vez)."""

    name = "b_reglas"

    def __init__(
        self, *, drawing: bool = True, hdm: bool = True, ocr: bool = False, name: str | None = None
    ):
        self.drawing, self.hdm, self.ocr = drawing, hdm, ocr
        if name:
            self.name = name

    def run(self, ctx: StrategyContext) -> StrategyOutput:
        started = time.perf_counter()
        labels, drawing = LabelExtractor(), DrawingExtractor()
        candidates = []
        evidence: dict[str, list] = {}
        for bundle in ctx.bundles:
            name = bundle.document.filename
            if bundle.media_type == "xlsx" and not self.hdm:
                ctx.emit(StageEvent("extract_hdm", "omitido", name, "Canal desactivado."))
                continue
            if bundle.media_type == "xlsx":
                found = tag_candidates(
                    labels.extract([bundle]), channel="hoja_datos", strategy=self.name
                )
                ctx.emit(
                    StageEvent(
                        "extract_hdm", "ok", name, f"{len(found)} datos con celda de origen."
                    )
                )
                candidates += found
                continue
            if bundle.media_type != "pdf":
                ctx.emit(
                    StageEvent("extract_labels", "omitido", name, "Formato sin capa de texto.")
                )
                continue
            from_ocr = False
            if not bundle.lines:
                bundle, from_ocr = self._with_ocr(bundle, ctx)
                if not bundle.lines:
                    continue
                evidence[bundle.document.id] = bundle.lines
            rotulos = tag_candidates(
                labels.extract([bundle]), channel="ocr" if from_ocr else "texto", strategy=self.name
            )
            ctx.emit(
                StageEvent(
                    "extract_labels", "ok", name, f"{len(rotulos)} valores rotulados con región."
                )
            )
            if not self.drawing:
                ctx.emit(StageEvent("extract_tables", "omitido", name, "Canal desactivado."))
                candidates += rotulos
                continue
            dibujo = tag_candidates(drawing.extract([bundle]), channel="tabla", strategy=self.name)
            if from_ocr and not complete_dimensions(dibujo + rotulos) and not is_vesor(bundle):
                bundle = self._rotated_dimensions(bundle, ctx)
                evidence[bundle.document.id] = bundle.lines
                dibujo = tag_candidates(
                    drawing.extract([bundle]), channel="tabla", strategy=self.name
                )
                if not complete_dimensions(dibujo + rotulos):
                    bundle, dibujo, rotulos = self._tiled_dimensions(bundle, ctx, dibujo, rotulos)
                    evidence[bundle.document.id] = bundle.lines
            for c in dibujo:
                if from_ocr:
                    c.channel = "ocr"
                elif "Cota vertical" in c.source.locator:
                    c.channel = "cota"
                elif "Cajetín" in c.source.locator:
                    c.channel = "cajetin"
            ctx.emit(
                StageEvent(
                    "extract_tables",
                    "ok",
                    name,
                    f"{len(dibujo)} valores de tablas, cotas y cajetín.",
                )
            )
            if is_vesor(bundle):
                # Plano de orientación: lo leído en él se cita como VESOR, y sus rótulos de planta
                # («N3 135°») dan el ángulo aunque no haya tabla.
                planta = tag_candidates(plan_labels(bundle), channel="vesor", strategy=self.name)
                for c in rotulos + dibujo:
                    if not from_ocr:
                        c.channel = "vesor"
                ctx.emit(
                    StageEvent(
                        "extract_tables",
                        "ok",
                        name,
                        f"VESOR: {len(planta)} rótulos de orientación en planta.",
                    )
                )
                dibujo += planta
            candidates += rotulos + dibujo
        out = StrategyOutput(candidates, evidence=evidence)
        out.cost.seconds = time.perf_counter() - started
        return out

    def _with_ocr(self, bundle, ctx: StrategyContext):
        """Sin capa de texto: con OCR activado, se reconocen las páginas y B lee esas líneas."""
        name = bundle.document.filename
        if not self.ocr:
            ctx.emit(
                StageEvent("extract_labels", "omitido", name, "Sin capa de texto: necesita OCR.")
            )
            return bundle, False
        data = ctx.raw.get(bundle.document.id)
        if data is None:
            ctx.emit(StageEvent("ocr", "error", name, "No llegan los bytes del documento."))
            return bundle, False
        from ..ocr import OcrUnavailable, ocr_pdf_lines

        started = time.perf_counter()
        try:
            lines = ocr_pdf_lines(data, bundle.document.id)
        except OcrUnavailable as exc:
            ctx.emit(StageEvent("ocr", "error", name, str(exc)))
            return bundle, False
        ctx.emit(
            StageEvent(
                "ocr",
                "ok",
                name,
                f"{len(lines)} líneas reconocidas en {time.perf_counter() - started:.1f} s.",
            )
        )
        return bundle.model_copy(update={"lines": lines}), True

    def _rotated_dimensions(self, bundle, ctx):
        """Segunda lectura solo de números verticales ausentes, sin alterar la tabla.

        El motor pierde cotas giradas pequeñas. Girar la página no cambia la geometría:
        sus cajas vuelven al sistema normalizado del original antes de servir de evidencia.
        """
        from ..ocr import OcrUnavailable, ocr_pdf_lines

        try:
            rotated = ocr_pdf_lines(ctx.raw[bundle.document.id], bundle.document.id, rotation=90)
        except OcrUnavailable:
            return bundle
        added = []
        for line in rotated:
            box = line.source.bbox
            if box[3] - box[1] <= box[2] - box[0] or not re.fullmatch(
                r"\d{2,6}(?:[.,]\d{1,3})?", line.text.strip()
            ):
                continue

            def overlaps(other):
                a = other.source.bbox
                if other.source.page != line.source.page or a is None:
                    return False
                intersection = max(0, min(a[2], box[2]) - max(a[0], box[0])) * max(
                    0, min(a[3], box[3]) - max(a[1], box[1])
                )
                return intersection >= 0.4 * min(
                    (a[2] - a[0]) * (a[3] - a[1]), (box[2] - box[0]) * (box[3] - box[1])
                )

            if not any(overlaps(other) for other in bundle.lines + added):
                added.append(line)
        ctx.emit(
            StageEvent(
                "ocr",
                "ok",
                bundle.document.filename,
                f"Suplemento de cotas giradas: {len(added)} lecturas con caja original.",
            )
        )
        return bundle.model_copy(update={"lines": [*bundle.lines, *added]})

    def _tiled_dimensions(self, bundle, ctx, drawing, labels):
        from ..ocr import OcrUnavailable, ocr_pdf_lines

        try:
            lines = ocr_pdf_lines(ctx.raw[bundle.document.id], bundle.document.id, tiles=True)
        except OcrUnavailable:
            return bundle, drawing, labels
        detail = bundle.model_copy(update={"lines": lines})
        candidates = tag_candidates(
            LabelExtractor().extract([detail]) + DrawingExtractor().extract([detail]),
            channel="ocr",
            strategy=self.name,
        )
        if not complete_dimensions(candidates):
            return bundle, drawing, labels
        new = {c.path: c for c in candidates}
        # Una lectura más completa no autoriza contradecir una cota anterior de alta confianza.
        for old in drawing + labels:
            if old.path in GEOMETRY_FIELDS and old.source.confidence >= 0.8:
                if (
                    old.path not in new
                    or abs(float(old.value) - float(new[old.path].value)) > 0.001
                ):
                    return bundle, drawing, labels

        def geometry(c):
            return c.path in GEOMETRY_FIELDS or c.path.startswith("envelope.")

        selected = [c for c in candidates if geometry(c) or c.path == "attributes.equipment_type"]
        if not any(c.path == "tag" for c in drawing + labels):
            selected += [c for c in candidates if c.path == "tag"]
        ctx.emit(
            StageEvent(
                "ocr",
                "ok",
                bundle.document.filename,
                "Dimensiones recuperadas del mosaico, sin contradecir cotas fiables previas.",
            )
        )
        return (
            bundle.model_copy(update={"lines": [*bundle.lines, *lines]}),
            [c for c in drawing if not geometry(c)] + selected,
            [c for c in labels if not geometry(c)],
        )
