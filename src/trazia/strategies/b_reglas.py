"""Estrategia B · datos + reglas: texto, tablas, cotas, cajetín y hoja de datos, sin aprendizaje."""

import time

from ..extraction import LabelExtractor
from ..extractors import DrawingExtractor
from .base import StageEvent, StrategyContext, StrategyOutput, tag_candidates


class ReglasStrategy:
    """`drawing` y `hdm` permiten las ablaciones del estudio (quitar un canal cada vez)."""

    name = "b_reglas"

    def __init__(self, *, drawing: bool = True, hdm: bool = True, name: str | None = None):
        self.drawing, self.hdm = drawing, hdm
        if name:
            self.name = name

    def run(self, ctx: StrategyContext) -> StrategyOutput:
        started = time.perf_counter()
        labels, drawing = LabelExtractor(), DrawingExtractor()
        candidates = []
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
            if not bundle.lines:
                ctx.emit(
                    StageEvent(
                        "extract_labels", "omitido", name, "Sin capa de texto: necesita OCR."
                    )
                )
                continue
            rotulos = tag_candidates(labels.extract([bundle]), channel="texto", strategy=self.name)
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
                if "Cota vertical" in c.source.locator:
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
            candidates += rotulos + dibujo
        out = StrategyOutput(candidates)
        out.cost.seconds = time.perf_counter() - started
        return out
