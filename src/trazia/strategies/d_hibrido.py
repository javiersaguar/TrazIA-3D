"""Estrategia D · híbrido (DEC-09 y DEC-11).

Cascada, de lo barato y explicable a lo caro:
1. B (texto, tablas, cotas, cajetín, hoja de datos; OCR si no hay capa de texto).
2. C: plantilla de un equipo aprobado parecido.
3. Memoria de revisión: con la revisión anterior aprobada, cada campo se lee donde estaba antes.
   Nunca se copia el valor anterior: solo se hereda dónde mirar.
4. A: la geometría del dibujo. No vota: confirma o desmiente lo leído.
5. Modelo de visión: solo si siguen faltando campos obligatorios.

Fusión: las lecturas iguales de canales distintos se refuerzan (probabilidad de que fallen todas a
la vez), la geometría confirma o penaliza y se aplican restricciones de ingeniería (fondo 2:1 ≈
D/4, DN normalizado, boquillas dentro de la virola). Cada campo sale con su explicación en español,
sus alternativas y una confianza fusionada.
"""

import time
from collections import defaultdict

from ..extraction import Alternative, Candidate
from ..extractors.units import DN_SERIES
from ..model import GEOMETRY_FIELDS, fields
from .base import Cost, StageEvent, StrategyContext, StrategyOutput

CHANNELS = ("reglas", "rag", "memoria", "geometria", "vision")
CHANNEL_NAMES = {
    "texto": "texto",
    "tabla": "tabla",
    "cota": "cota",
    "cajetin": "cajetín",
    "hoja_datos": "hoja de datos",
    "ocr": "OCR",
    "rag": "plantilla (C)",
    "memoria_revision": "revisión anterior",
    "vision": "modelo de visión",
    "geometria": "geometría",
}
REQUIRED = ("tag", *GEOMETRY_FIELDS)


class HybridStrategy:
    def __init__(
        self, *, without: set[str] | frozenset[str] = frozenset(), name: str = "d_hibrido"
    ):
        self.channels = [c for c in CHANNELS if c not in without]
        self.name = name

    def run(self, ctx: StrategyContext) -> StrategyOutput:
        from .a_vision import VisionGeometryStrategy
        from .b_reglas import ReglasStrategy
        from .c_rag import RagStrategy

        started = time.perf_counter()
        pool: list[Candidate] = []
        cost = Cost()
        warnings: list[str] = []
        evidence: dict[str, list] = {}

        def take(output: StrategyOutput):
            pool.extend(output.candidates)
            cost.add(output.cost)
            warnings.extend(output.warnings)
            for doc, lines in output.evidence.items():
                evidence.setdefault(doc, lines)

        if "reglas" in self.channels:
            take(ReglasStrategy(ocr=True, name=self.name).run(ctx))
        if "rag" in self.channels:
            take(RagStrategy().run(ctx))
        if "memoria" in self.channels and ctx.previous is not None:
            take(self._memory(ctx, evidence))
        if "geometria" in self.channels:
            take(VisionGeometryStrategy(reader="texto", name=self.name).run(ctx))
        chosen, conflicts = fuse(pool)
        missing = [p for p in REQUIRED if p not in {c.path for c in chosen}]
        if missing and "vision" in self.channels and ctx.providers:
            take(self._vision(ctx))
            chosen, conflicts = fuse(pool)
        for c in chosen:
            c.strategy = self.name
        ctx.emit(
            StageEvent(
                "reconcile",
                "ok",
                "",
                f"Fusión de {len(pool)} lecturas en {len(chosen)} campos · "
                f"{len(conflicts)} conflictos.",
            )
        )
        warnings += [f"Conflicto en {path}: {why}" for path, why in conflicts.items()]
        out = StrategyOutput(chosen, cost=cost, warnings=warnings, evidence=evidence)
        out.cost.seconds = time.perf_counter() - started
        return out

    # Memoria de revisión ---------------------------------------------------------------------
    def _memory(self, ctx: StrategyContext, evidence) -> StrategyOutput:
        from .c_rag import CELL, MOVING, _mark_text, _nearest, _parser

        previous = fields(ctx.previous.equipment)
        out: list[Candidate] = []
        for bundle in ctx.bundles:
            lines = bundle.lines or evidence.get(bundle.document.id, [])
            if not lines:
                continue
            for path, field in previous.items():
                source = field.source
                if source.document_id != bundle.document.id:
                    continue
                if not source.cell and (source.page is None or source.bbox is None):
                    continue
                if source.cell:
                    same = [line for line in lines if line.source.cell == source.cell]
                    line = same[0] if same else None
                    parser = _parser(path, ".")
                    if line is None or parser(line.text.split("=")[-1].strip()) is None:
                        continue
                else:
                    window = MOVING if path in ("height", "skirt_height", "head_depth") else CELL
                    parser = _parser(path, ".")
                    line = _nearest(lines, source.page, source.bbox, window, parser)
                    if line is None:
                        continue
                    if path.startswith("nozzles.") and _mark_text(path.split(".")[1]) is None:
                        continue
                value, unit = parser(line.text.split("=")[-1].strip() if source.cell else line.text)
                previous_value = field.value
                out.append(
                    Candidate(
                        path=path,
                        value=value,
                        unit=unit,
                        source=line.source.model_copy(
                            update={"confidence": 0.8, "locator": "Región de la revisión anterior"}
                        ),
                        channel="memoria_revision",
                        strategy=self.name,
                        text_original=line.text,
                        confidence_raw=0.8,
                        explanation=(
                            f"Leído donde estaba en la revisión anterior (antes {previous_value})."
                        ),
                    )
                )
        if out:
            ctx.emit(
                StageEvent(
                    "memory", "ok", "", f"{len(out)} lecturas guiadas por la revisión anterior."
                )
            )
        return StrategyOutput(out)

    # Modelo de visión, solo para lo que falta -------------------------------------------------
    def _vision(self, ctx: StrategyContext) -> StrategyOutput:
        from ..extractors import DrawingExtractor
        from ..ingest import Bundle
        from .a_vision import VisionGeometryStrategy

        reader = VisionGeometryStrategy(reader="vision", name=self.name)
        out: list[Candidate] = []
        for bundle in ctx.bundles:
            data = ctx.raw.get(bundle.document.id)
            if bundle.media_type != "pdf" or data is None:
                continue
            import io

            import pdfplumber

            with pdfplumber.open(io.BytesIO(data)) as pdf:
                pages = range(1, len(pdf.pages) + 1)
            lines = []
            for page in pages:
                lines += reader._reader_lines(bundle, data, page, ctx)
            seen = Bundle(document=bundle.document, media_type="pdf", lines=lines)
            for c in DrawingExtractor().extract([seen]):
                c.channel, c.strategy = "vision", self.name
                c.source = c.source.model_copy(update={"confidence": c.source.confidence * 0.85})
                out.append(c)
        return StrategyOutput(out)


# Fusión ---------------------------------------------------------------------------------------
def _same(a: Candidate, b: Candidate) -> bool:
    if isinstance(a.value, str) or isinstance(b.value, str):
        return str(a.value).strip().upper() == str(b.value).strip().upper()
    if a.unit != b.unit:
        return False
    if a.unit == "deg":
        d = abs(float(a.value) - float(b.value)) % 360
        return min(d, 360 - d) <= 0.5
    if a.unit == "mm":
        return abs(float(a.value) - float(b.value)) <= 1.0
    return abs(float(a.value) - float(b.value)) <= max(0.5, 0.005 * abs(float(b.value)))


def _combine(confidences: list[float]) -> float:
    """Probabilidad de que acierte al menos una fuente independiente (por canal, la mejor)."""
    fail = 1.0
    for c in confidences:
        fail *= 1 - min(0.99, max(0.0, c))
    return 1 - fail


def fuse(pool: list[Candidate]) -> tuple[list[Candidate], dict[str, str]]:
    by_path: dict[str, list[Candidate]] = defaultdict(list)
    for c in pool:
        by_path[c.path].append(c)
    chosen: list[Candidate] = []
    conflicts: dict[str, str] = {}
    diameter = _best_numeric(by_path.get("diameter", []))
    for path, group in by_path.items():
        voters = [c for c in group if not (c.channel == "geometria" and not c.text_original)]
        measured = [c for c in group if c.channel == "geometria" and not c.text_original]
        clusters: list[list[Candidate]] = []
        for c in voters:
            for cluster in clusters:
                if _same(cluster[0], c):
                    cluster.append(c)
                    break
            else:
                clusters.append([c])
        if not clusters:
            if measured:  # solo hay medida: entra con poca confianza y se dice
                m = max(measured, key=lambda c: c.source.confidence)
                chosen.append(
                    m.model_copy(
                        update={
                            "source": m.source.model_copy(
                                update={"confidence": min(0.4, m.source.confidence)}
                            ),
                            "explanation": (m.explanation or "") + " Solo hay medida del dibujo.",
                        }
                    )
                )
            continue
        scored = []
        for cluster in clusters:
            per_channel: dict[str, float] = {}
            per_evidence: dict[tuple, float] = {}
            for c in cluster:
                per_channel[c.channel or "?"] = max(
                    per_channel.get(c.channel or "?", 0), c.source.confidence
                )
                # Dos canales que leen el mismo texto en el mismo sitio son una sola prueba.
                key = _evidence_key(c)
                per_evidence[key] = max(per_evidence.get(key, 0), c.source.confidence)
            score = _combine(list(per_evidence.values()))
            notes = []
            rep = max(cluster, key=lambda c: (bool(c.text_original), c.source.confidence))
            if measured and not isinstance(rep.value, str):
                g = max(measured, key=lambda c: c.source.confidence)
                rel = abs(float(rep.value) - float(g.value)) / max(1.0, abs(float(g.value)))
                tolerance = 0.005 if g.source.confidence >= 0.5 else 0.03  # vector / escaneado
                if rep.unit == "deg":
                    d = abs(float(rep.value) - float(g.value)) % 360
                    rel, tolerance = min(d, 360 - d) / 360, 2 / 360
                if rel <= tolerance:
                    score = _combine([score, g.source.confidence])
                    notes.append(f"la geometría del dibujo lo confirma ({rel * 100:.1f} %)")
                elif rel > 3 * tolerance:
                    score *= 0.6
                    notes.append(
                        f"la geometría del dibujo no cuadra ({rel * 100:.0f} % de diferencia)"
                    )
            score, rule = _constraints(path, rep, score, diameter)
            if rule:
                notes.append(rule)
            scored.append((score, cluster, rep, per_channel, notes))
        scored.sort(key=lambda s: s[0], reverse=True)
        exact = [m for m in measured if m.source.confidence >= 0.5]  # medida vectorial
        if exact and all(any("no cuadra" in n for n in s[4]) for s in scored):
            # Todas las lecturas contradicen un dibujo vectorial (medida exacta): gana el dibujo
            # y el campo queda en conflicto para revisión.
            g = max(exact, key=lambda c: c.source.confidence)
            why = (
                f"las lecturas ({', '.join(str(s[2].value) for s in scored)}) no cuadran con el "
                f"dibujo; se propone la medida ({g.value})"
            )
            conflicts[path] = why
            chosen.append(
                g.model_copy(
                    update={
                        "explanation": (g.explanation or "") + " " + why[0].upper() + why[1:] + ".",
                        "alternatives": [
                            Alternative(
                                value=s[2].value,
                                unit=s[2].unit,
                                source=s[2].source,
                                channel=s[2].channel,
                            )
                            for s in scored
                        ],
                    }
                )
            )
            continue
        score, cluster, rep, per_channel, notes = scored[0]
        sources = ", ".join(CHANNEL_NAMES.get(ch, ch) for ch in per_channel)
        agree = f"Coinciden: {sources}." if len(per_channel) > 1 else f"Fuente: {sources}."
        explanation = " ".join([agree] + [n[0].upper() + n[1:] + "." for n in notes])
        rivals = [s for s in scored[1:] if s[0] >= 0.5 * score]
        if rivals:
            why = (
                f"{len(rivals) + 1} lecturas distintas; se propone la de más apoyo "
                f"({rep.value} con {sources})."
            )
            conflicts[path] = why
            explanation += " " + why
        chosen.append(
            rep.model_copy(
                update={
                    "source": rep.source.model_copy(
                        update={"confidence": round(min(0.99, score), 4)}
                    ),
                    "confidence_raw": rep.source.confidence,
                    "explanation": explanation,
                    "alternatives": [
                        Alternative(
                            value=s[2].value,
                            unit=s[2].unit,
                            source=s[2].source,
                            channel=s[2].channel,
                        )
                        for s in scored[1:]
                    ],
                }
            )
        )
    return chosen, conflicts


def _evidence_key(c: Candidate) -> tuple:
    if c.text_original and c.source.bbox:
        box = tuple(round(v, 2) for v in c.source.bbox)
        return (c.source.document_id, c.source.page, box, c.text_original.strip().upper())
    if c.source.cell:
        return (c.source.document_id, c.source.cell)
    return (c.channel, id(c))


def _best_numeric(group: list[Candidate]) -> float | None:
    numeric = [c for c in group if not isinstance(c.value, str) and c.text_original]
    if not numeric:
        return None
    return float(max(numeric, key=lambda c: c.source.confidence).value)


def _constraints(path: str, rep: Candidate, score: float, diameter: float | None):
    """Restricciones de ingeniería (DEC-11): suben o bajan la puntuación y lo explican."""
    if isinstance(rep.value, str):
        return score, None
    value = float(rep.value)
    if path == "head_depth" and diameter:
        if abs(value - diameter / 4) <= 0.02 * diameter / 4:
            return _combine([score, 0.5]), "cuadra con un fondo 2:1 (D/4)"
        return score * 0.9, None
    if path.endswith(".diameter") and path.startswith("nozzles."):
        if int(round(value)) not in DN_SERIES:
            return score * 0.5, "no es un DN normalizado"
    if path.endswith(".azimuth") and not 0 <= value < 360:
        return score * 0.5, "orientación fuera de [0, 360)"
    return score, None
