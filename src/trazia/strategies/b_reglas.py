"""Estrategia B · datos + reglas: texto, tablas, cotas, cajetín, HDM y VESOR, sin aprendizaje."""

import time

from ..extraction import LabelExtractor
from ..extractors import DrawingExtractor
from ..extractors.vesor import is_vesor, plan_labels
from .base import StageEvent, StrategyContext, StrategyOutput, tag_candidates


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
