"""Punto de entrada del motor de lectura (interfaz 1 de docs/COORDINACION-BACKEND.md).

`process` ingiere los documentos, ejecuta la estrategia elegida y aplica el postproceso común:
reconciliación, contrato, familia e IFC. No lanza excepciones por datos malos: devuelve `error`.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

from .extraction import Candidate, assemble
from .ingest import ingest_bytes
from .model import Revision
from .reconcile import resolve
from .strategies import STRATEGIES, StageEvent, StrategyContext, get_strategy

__all__ = ["InputDocument", "PipelineResult", "RunInfo", "StageEvent", "process"]


@dataclass(frozen=True)
class InputDocument:
    filename: str  # GAD_<TAG>_rev1.pdf, HDM_<TAG>_rev1.xlsx, VESOR_<TAG>.pdf…
    data: bytes
    document_id: str  # GA-<TAG>, HDM-<TAG>, VESOR-<TAG>


@dataclass
class RunInfo:
    """Metadatos de ejecución. Misma forma que `RunInfo` del contrato 0.3; cuando Plataforma
    la publique en `trazia.model`, este tipo pasará a ser un alias."""

    strategy: str
    providers: list[str] = field(default_factory=list)
    seconds: float = 0.0
    gpu_seconds: float | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_eur: float | None = None
    external_calls: int = 0


@dataclass
class PipelineResult:
    revision: Revision | None
    candidates: list[Candidate]
    warnings: list[str]
    error: str | None
    run: RunInfo
    conflicts: list[str] = field(default_factory=list)


KINDS = (
    ("GAD_", "plano de disposición general"),
    ("GA_", "plano de disposición general"),
    ("HDM_", "hoja de datos mecánicos"),
    ("VESOR_", "orientación de boquillas"),
    ("ESTRUCTURA_", "estructura auxiliar"),
)


def _classify(filename: str) -> str | None:
    upper = filename.upper()
    return next((label for prefix, label in KINDS if upper.startswith(prefix)), None)


def process(
    documents: list[InputDocument],
    *,
    project_id: str,
    equipment_id: str,
    revision: str,
    strategy: str = "d_hibrido",
    previous: Revision | None = None,
    providers: list[str] | None = None,
    dataset: Literal["synthetic", "real"] = "synthetic",
    on_event: Callable[[StageEvent], None] | None = None,
) -> PipelineResult:
    started = time.perf_counter()
    events: list[StageEvent] = []

    def emit(event: StageEvent) -> None:
        events.append(event)
        if on_event:
            on_event(event)

    run = RunInfo(strategy=strategy)
    warnings: list[str] = []

    def finish(rev, candidates, error, conflicts=()):
        run.seconds = time.perf_counter() - started
        return PipelineResult(rev, candidates, warnings, error, run, list(conflicts))

    if strategy == "d_hibrido" and strategy not in STRATEGIES:
        # Mientras D no exista, la API sigue funcionando con B y lo dice.
        warnings.append("La estrategia D aún no está implementada: se usa B (b_reglas).")
        run.strategy = strategy = "b_reglas"
    try:
        engine = get_strategy(strategy)
    except ValueError as exc:
        return finish(None, [], str(exc))

    bundles = []
    for doc in documents:
        try:
            bundle = ingest_bytes(doc.data, doc.filename, doc.document_id, revision)
        except Exception as exc:  # pdfminer lanza sus propias excepciones con bytes corruptos
            reason = str(exc).splitlines()[0] if str(exc) else type(exc).__name__
            warnings.append(f"Ingesta fallida de {doc.filename}: {reason}")
            emit(StageEvent("ingest", "error", doc.filename, f"No se pudo leer: {reason}"))
            continue
        warnings += bundle.warnings
        pages = bundle.document.page_count
        emit(
            StageEvent(
                "ingest",
                "ok",
                doc.filename,
                f"SHA-256 registrado · {pages} página(s)." if pages else "SHA-256 registrado.",
            )
        )
        kind = _classify(doc.filename)
        emit(
            StageEvent(
                "classify",
                "ok" if kind else "omitido",
                doc.filename,
                f"Clasificado como {kind} por su nombre."
                if kind
                else "Nombre fuera de la convención.",
            )
        )
        bundles.append(bundle)
    if not bundles:
        return finish(None, [], "No se pudo leer ningún documento.")

    ctx = StrategyContext(
        bundles=bundles, dataset=dataset, previous=previous, providers=providers, emit=emit
    )
    try:
        output = engine.run(ctx)
    except Exception as exc:  # una estrategia rota no debe tumbar la API
        emit(StageEvent("reconcile", "error", equipment_id, f"La estrategia falló: {exc}"))
        return finish(None, [], f"La estrategia {strategy} falló: {exc}")
    warnings += output.warnings
    run.providers = output.cost.providers
    run.gpu_seconds = output.cost.gpu_seconds
    run.tokens_in, run.tokens_out = output.cost.tokens_in, output.cost.tokens_out
    run.cost_eur, run.external_calls = output.cost.cost_eur, output.cost.external_calls

    resolution = resolve(output.candidates)
    warnings += resolution.warnings
    emit(
        StageEvent(
            "reconcile",
            "ok",
            equipment_id,
            f"{len(resolution.chosen)} campos · "
            f"{len(resolution.conflicts)} conflictos para revisión.",
        )
    )
    emit(StageEvent("calibrate", "omitido", equipment_id, "Calibración aún no aplicada."))

    try:
        model = assemble(
            bundles,
            resolution.chosen,
            project_id=project_id,
            equipment_id=equipment_id,
            revision=revision,
            dataset=dataset,
        )
    except ValueError as exc:
        reason = str(exc).splitlines()[0]
        emit(StageEvent("family", "error", equipment_id, reason))
        return finish(None, resolution.chosen, reason, resolution.conflicts)
    emit(
        StageEvent(
            "family",
            "ok",
            equipment_id,
            f"Recipiente vertical · {len(model.equipment.nozzles)} boquillas.",
        )
    )
    try:
        from .ifc import build_ifc

        build_ifc(model, draft=True)
        emit(StageEvent("ifc", "ok", equipment_id, "IFC4 DRAFT con GUID estables."))
        emit(
            StageEvent("validate", "ok", equipment_id, "Geometría válida · pendiente de revisión.")
        )
    except ValueError as exc:
        emit(StageEvent("ifc", "error", equipment_id, str(exc).splitlines()[0]))
        return finish(None, resolution.chosen, str(exc).splitlines()[0], resolution.conflicts)
    return finish(model, resolution.chosen, None, resolution.conflicts)
