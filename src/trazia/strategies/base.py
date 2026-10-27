"""Interfaz común de las estrategias de lectura (DEC-02).

Una estrategia recibe los documentos ya ingeridos y devuelve candidatos con su evidencia y su coste.
El postproceso (reconciliación, calibración, contrato, familia e IFC) es común y vive en
`trazia.pipeline`, para que la comparación entre estrategias sea justa.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

from ..extraction import Candidate
from ..ingest import Bundle
from ..model import Revision


@dataclass(frozen=True)
class StageEvent:
    stage: str  # ids de la web: ingest, classify, extract_*, geometry2d, rag, memory, reconcile…
    status: str  # "ok" | "omitido" | "error"
    file: str
    detail: str  # frase en español para la tabla de eventos


@dataclass
class Cost:
    seconds: float = 0.0
    gpu_seconds: float | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_eur: float | None = None
    external_calls: int = 0
    providers: list[str] = field(default_factory=list)

    def add(self, other: "Cost") -> None:
        self.seconds += other.seconds
        for name in ("gpu_seconds", "tokens_in", "tokens_out", "cost_eur"):
            mine, theirs = getattr(self, name), getattr(other, name)
            if theirs is not None:
                setattr(self, name, (mine or 0) + theirs)
        self.external_calls += other.external_calls
        self.providers += [p for p in other.providers if p not in self.providers]


@dataclass
class StrategyContext:
    bundles: list[Bundle]
    dataset: str  # "synthetic" | "real"
    previous: Revision | None = None
    providers: list[str] | None = None
    emit: Callable[[StageEvent], None] = lambda event: None
    # Bytes originales por document_id: OCR, visión y geometría necesitan la página, no el texto.
    raw: dict[str, bytes] = field(default_factory=dict)
    # Equipo que se procesa: C no se usa a sí mismo como plantilla (eso es memoria de revisión).
    equipment_id: str | None = None


@dataclass
class StrategyOutput:
    candidates: list[Candidate]
    cost: Cost = field(default_factory=Cost)
    warnings: list[str] = field(default_factory=list)
    # Evidencia generada por la estrategia (p. ej. líneas de OCR) por document_id: la comprobación
    # de cita del pipeline la usa cuando el documento no tiene capa de texto.
    evidence: dict[str, list] = field(default_factory=dict)


class Strategy(Protocol):
    name: str

    def run(self, ctx: StrategyContext) -> StrategyOutput: ...


def tag_candidates(candidates: list[Candidate], *, channel: str, strategy: str) -> list[Candidate]:
    """Marca canal y estrategia sin perder la confianza original como confianza bruta."""
    return [
        c.model_copy(
            update={
                "channel": c.channel or channel,
                "strategy": strategy,
                "confidence_raw": c.confidence_raw
                if c.confidence_raw is not None
                else c.source.confidence,
            }
        )
        for c in candidates
    ]
