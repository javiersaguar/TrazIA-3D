"""Estrategia C · RAG (DEC-02 y DEC-08).

1. Recupera de la biblioteca el GA aprobado más parecido (huella visual + vocabulario), nunca
   el mismo equipo. Con `TRAZIA_RAG_RETRIEVAL=colqwen2` lo elige ColQwen2 (`rag.visual`, 2.5);
   si no se puede usar, vuelve a la huella. La confianza sale siempre de la huella del par
   elegido, para que la curva de calibración de C siga valiendo.
2. Hereda su plantilla de lectura: para cada campo, la región donde estaba.
3. Lee el valor en la región equivalente del documento actual. Si allí no hay nada legible, el
   campo queda vacío: un valor de la biblioteca nunca entra sin evidencia del documento actual.

No lee toda la página ni usa vocabulario de cabeceras: el «qué es cada cosa» lo pone la plantilla.
Por eso funciona con proveedores conocidos y falla con estilos sin un caso parecido (H3).
"""

import io
import math
import os
import re
import time
from pathlib import Path

import pdfplumber

from ..extraction import Candidate, LabelExtractor
from ..extractors.drawing import MARK
from ..extractors.units import (
    parse_angle,
    parse_length,
    parse_length_any_direction,
    parse_nominal_size,
    parse_pressure,
    parse_temperature,
    parse_weight,
)
from ..rag import visual as colqwen
from ..rag.fingerprint import similarity, visual, words
from ..rag.library import load
from .base import StageEvent, StrategyContext, StrategyOutput, tag_candidates

MIN_SIMILARITY = 0.55
MIN_VISUAL_SIMILARITY = 0.63  # MaxSim de ColQwen2: Youden en S-dev sin el proveedor (2.5)
CELL = (0.012, 0.008)  # ventana (x, y) para celdas fijas: tabla, datos de diseño, cajetín
MOVING = (0.05, 0.25)  # cotas y rótulos que se mueven con las proporciones del equipo
LENGTH_TAIL = re.compile(
    r"(\d+'\s*-?\s*\d*(?:\s+\d+/\d+)?\"?|\d+(?:\s+\d+/\d+)?\"|\d[\d.,]*)\s*(?:mm|THK\.?)?$", re.I
)


def library_path() -> Path:
    return Path(os.environ.get("TRAZIA_RAG_LIBRARY", "generated/rag/biblioteca.json"))


def _page_words(lines, page) -> list[str]:
    return words([line.text for line in lines if line.source.page == page])


def light_score(data: bytes, page: int, lines, entry: dict) -> float:
    """Similitud de la huella ligera entre una página y un caso de la biblioteca."""
    return similarity(visual(data, page), _page_words(lines, page), entry["visual"], entry["words"])


def light_best(data: bytes, pages: int, lines, entries: list[dict]):
    """(similitud, página, caso) más parecido según la huella ligera."""
    best = None
    for page in range(1, pages + 1):
        page_visual, page_words = visual(data, page), _page_words(lines, page)
        for entry in entries:
            score = similarity(page_visual, page_words, entry["visual"], entry["words"])
            if best is None or score > best[0]:
                best = (score, page, entry)
    return best


def visual_best(data: bytes, pages: int, entries: list[dict]):
    """(MaxSim, página, caso) más parecido según ColQwen2. Lanza VisualUnavailable si no puede."""
    library = [(e, colqwen.entry_vectors(e)) for e in entries]
    if not library or any(vectors is None for _, vectors in library):
        raise colqwen.VisualUnavailable("La biblioteca no tiene los PDF de sus casos")
    best = None
    for page in range(1, pages + 1):
        page_vectors = colqwen.embed_page(data, page)
        for entry, vectors in library:
            score = colqwen.maxsim(page_vectors, vectors)
            if best is None or score > best[0]:
                best = (score, page, entry)
    return best


class RagStrategy:
    name = "c_rag"

    def run(self, ctx: StrategyContext) -> StrategyOutput:
        started = time.perf_counter()
        out = StrategyOutput([])
        library = load(library_path())
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
            if not library or not library["entries"]:
                ctx.emit(StageEvent("rag", "omitido", name, "Sin biblioteca de equipos aprobados."))
                out.warnings.append("C sin biblioteca: genera generated/rag/biblioteca.json")
                continue
            found, lines = self._read(bundle, data, library, ctx)
            out.candidates += found
            if lines:
                out.evidence[bundle.document.id] = lines
        out.cost.seconds = time.perf_counter() - started
        return out

    def _read(self, bundle, data, library, ctx):
        name = bundle.document.filename
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages = len(pdf.pages)
        lines = bundle.lines
        if not lines:
            from ..ocr import OcrUnavailable, ocr_pdf_lines

            try:
                lines = ocr_pdf_lines(data, bundle.document.id)
            except OcrUnavailable:
                lines = []
        candidates = [
            e
            for e in library["entries"]
            if not (ctx.equipment_id and e["equipment_id"] == ctx.equipment_id)
        ]  # el mismo equipo no es «otro caso parecido»

        best, by_visual = None, False
        if colqwen.enabled():
            try:
                best = visual_best(data, pages, candidates)
            except colqwen.VisualUnavailable as exc:
                ctx.emit(StageEvent("rag", "error", name, f"{exc}: se usa la huella ligera."))
            if best is not None:
                visual_score, page, entry = best
                if visual_score < MIN_VISUAL_SIMILARITY:
                    ctx.emit(
                        StageEvent(
                            "rag",
                            "omitido",
                            name,
                            f"Ningún caso parecido según ColQwen2 (MaxSim {visual_score:.2f}).",
                        )
                    )
                    return [], lines
                # ColQwen2 ya decidió que hay caso parecido; la huella solo da la confianza.
                best, by_visual = (light_score(data, page, lines, entry), page, entry), True
        if best is None:
            best = light_best(data, pages, lines, candidates)
        if best is None or (not by_visual and best[0] < MIN_SIMILARITY):
            ctx.emit(
                StageEvent(
                    "rag",
                    "omitido",
                    name,
                    "Ningún caso parecido en la biblioteca "
                    f"(similitud {best[0] if best else 0:.2f}).",
                )
            )
            return [], lines
        score, page, entry = best
        ctx.emit(
            StageEvent(
                "rag",
                "ok",
                name,
                f"Plantilla de {entry['tag']} ({entry.get('vendor', '?')}) · "
                f"similitud {score:.2f}.",
            )
        )
        found = self._apply(entry, page, lines, score)
        return tag_candidates(found, channel="rag", strategy=self.name), lines

    def _apply(self, entry, page, lines, score) -> list[Candidate]:
        entry = {**entry, "fields": _extend_rows(entry["fields"])}
        shift = page - entry["page"]
        confidence = round(min(0.85, 0.5 + 0.4 * score), 3)
        values: dict[str, Candidate] = {}
        datum: list[str] = []
        for path, field in entry["fields"].items():
            target_page = field["page"] + shift
            window = MOVING if field["moving"] else CELL
            if path.startswith("nozzles."):
                mark_line = _nearest(lines, target_page, field["mark_bbox"], CELL, _mark_text)
                if mark_line is None:
                    continue
                mark = _mark_text(mark_line.text)
                path = ".".join(["nozzles", mark, path.split(".")[-1]])
            parser = _parser(path, entry["decimal"], field.get("reversed"))
            line = _nearest(lines, target_page, field["bbox"], window, parser)
            if line is None:
                continue
            value, unit = parser(line.text)
            values[path] = Candidate(
                path=path,
                value=value,
                unit=unit,
                source=line.source.model_copy(
                    update={
                        "confidence": confidence,
                        "locator": f"Región equivalente a la plantilla de {entry['tag']}",
                    }
                ),
                text_original=line.text,
                explanation=(
                    f"Leído donde la plantilla de {entry['tag']} tenía este dato "
                    f"(similitud {score:.2f})."
                ),
            )
            if field.get("datum") == "btl":
                datum.append(path)
        skirt = values.get("skirt_height")
        for path in datum:
            if path in values and skirt is not None:
                c = values[path]
                values[path] = c.model_copy(
                    update={
                        "value": round(float(c.value) + float(skirt.value), 3),
                        "explanation": c.explanation
                        + f" Cota desde la tangente inferior + faldón ({skirt.value:g} mm).",
                    }
                )
            else:
                values.pop(path, None)
        return list(values.values())


def _extend_rows(fields: dict, rows: int = 10) -> dict:
    """Más filas de la tabla de boquillas que las del caso plantilla, con su mismo paso."""
    by_mark: dict[str, dict] = {}
    for path, field in fields.items():
        if path.startswith("nozzles."):
            by_mark.setdefault(path.split(".")[1], {})[path.split(".")[2]] = field
    ordered = sorted(by_mark.values(), key=lambda f: next(iter(f.values()))["mark_bbox"][1])
    if len(ordered) < 2:
        return fields
    ys = [next(iter(f.values()))["mark_bbox"][1] for f in ordered]
    pitch = sorted(b - a for a, b in zip(ys, ys[1:], strict=False))[len(ys) // 2 - 1]
    if pitch <= 0:
        return fields
    out = dict(fields)
    last = ordered[-1]
    for k in range(1, rows - len(ordered) + 1):
        for key, field in last.items():
            moved = {
                **field,
                "bbox": [v + (k * pitch if i % 2 else 0) for i, v in enumerate(field["bbox"])],
                "mark_bbox": [
                    v + (k * pitch if i % 2 else 0) for i, v in enumerate(field["mark_bbox"])
                ],
            }
            out[f"nozzles.__extra{k}.{key}"] = moved
    return out


def _mark_text(text: str) -> str | None:
    mark = text.strip().upper().replace(" ", "")
    return mark if MARK.match(mark) else None


def _nearest(lines, page, bbox, window, parser):
    cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
    best = None
    for line in lines:
        if line.source.page != page or line.source.bbox is None:
            continue
        lx = (line.source.bbox[0] + line.source.bbox[2]) / 2
        ly = (line.source.bbox[1] + line.source.bbox[3]) / 2
        if abs(lx - cx) > window[0] or abs(ly - cy) > window[1]:
            continue
        if parser(line.text) is None:
            continue
        d = math.hypot((lx - cx) / window[0], (ly - cy) / window[1])
        if best is None or d < best[0]:
            best = (d, line)
    return best[1] if best else None


def _parser(path: str, decimal: str, reversed_: bool | None = None):
    key = path.split(".")[-1]

    def length(text):
        readings = parse_length_any_direction(text.strip(), decimal=decimal)
        if reversed_ is not None and len(readings) == 2:
            readings = readings[1:] if reversed_ else readings[:1]
        if not readings and (m := LENGTH_TAIL.search(text.strip())):
            value = parse_length(m[1], decimal=decimal)
            readings = [value] if value else []
        return (round(readings[0], 3), "mm") if readings else None

    if path == "tag":
        return lambda t: (t.strip(), "1") if re.fullmatch(r"[A-Za-z0-9_-]{3,}", t.strip()) else None
    if key == "material":
        return lambda t: (t.strip(), "1") if t.strip() and t.strip()[0].isalpha() else None
    if key == "design_pressure":
        return lambda t: (lambda r: (round(r[0], 4), "bar") if r else None)(
            parse_pressure(t, decimal=decimal)
        )
    if key == "design_temperature":
        return lambda t: (lambda r: (round(r[0], 4), "C") if r else None)(
            parse_temperature(t, decimal=decimal)
        )
    if key == "operating_weight":
        return lambda t: (lambda r: (round(r[0], 4), "kg") if r else None)(
            parse_weight(t, decimal=decimal)
        )
    if path.startswith("nozzles.") and key == "diameter":
        return lambda t: (lambda d: (float(d), "mm") if d else None)(parse_nominal_size(t))
    if key == "azimuth":
        return lambda t: (lambda a: (a, "deg") if a is not None else None)(parse_angle(t))
    return length
