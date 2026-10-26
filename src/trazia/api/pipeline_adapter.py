"""Puente temporal: firma de Lectura, sin editar su implementación."""

import importlib
import time
from dataclasses import dataclass
from typing import Callable

from trazia.model import Revision, RunInfo


@dataclass(frozen=True)
class InputDocument:
    filename: str
    data: bytes
    document_id: str
    revision: str | None = None


@dataclass(frozen=True)
class StageEvent:
    stage: str
    status: str
    file: str
    detail: str


@dataclass(frozen=True)
class PipelineResult:
    revision: Revision | None
    candidates: list
    warnings: list[str]
    error: str | None
    run: RunInfo


def process(
    documents: list[InputDocument],
    *,
    project_id: str,
    equipment_id: str,
    revision: str,
    strategy: str = "d_hibrido",
    previous: Revision | None = None,
    providers: list[str] | None = None,
    dataset: str = "synthetic",
    on_event: Callable[[StageEvent], None] | None = None,
) -> PipelineResult:
    try:
        module = importlib.import_module("trazia.pipeline")
    except ModuleNotFoundError as error:
        if error.name != "trazia.pipeline":
            raise
    else:
        inputs = [module.InputDocument(d.filename, d.data, d.document_id) for d in documents]
        return module.process(
            inputs,
            project_id=project_id,
            equipment_id=equipment_id,
            revision=revision,
            strategy=strategy,
            previous=previous,
            providers=providers,
            dataset=dataset,
            on_event=on_event,
        )

    from trazia.extraction import LabelExtractor, assemble
    from trazia.ingest import ingest_bytes

    started = time.perf_counter()
    candidates, warnings, result, error = [], [], None, None
    emit = on_event or (lambda _: None)
    if strategy != "b_reglas" or providers:
        error = "El adaptador temporal solo ejecuta b_reglas sin proveedores; falta Lectura"
    else:
        bundles = []
        try:
            for document in documents:
                bundle = ingest_bytes(
                    document.data,
                    document.filename,
                    document.document_id,
                    document.revision or revision,
                )
                bundles.append(bundle)
                warnings.extend(bundle.warnings)
                emit(StageEvent("ingest", "ok", document.filename, "Original catalogado por hash"))
                emit(
                    StageEvent(
                        "classify",
                        "ok",
                        document.filename,
                        "Formato reconocido por el baseline de etiquetas",
                    )
                )
            candidates = LabelExtractor().extract(bundles)
            emit(
                StageEvent(
                    "extract_labels",
                    "ok",
                    "",
                    f"{sum(c.source.page is not None for c in candidates)} candidatos del plano",
                )
            )
            hdm_count = sum(c.source.sheet is not None for c in candidates)
            if hdm_count:
                emit(StageEvent("extract_hdm", "ok", "", f"{hdm_count} atributos de hoja de datos"))
            result = assemble(
                bundles,
                candidates,
                project_id=project_id,
                equipment_id=equipment_id,
                revision=revision,
                dataset=dataset,
            )
            result.approval = None
            emit(StageEvent("reconcile", "ok", "", "Contrato validado; salida DRAFT"))
            warnings.append("Adaptador temporal de etiquetas: no ejecuta visión, OCR ni RAG")
        except (ValueError, OSError) as problem:
            error = str(problem)
    run = RunInfo(
        strategy=strategy,
        providers=[],
        seconds=time.perf_counter() - started,
        external_calls=0,
        cost_eur=0.0,
        tokens_in=0,
        tokens_out=0,
    )
    if result:
        result.run = run
    return PipelineResult(result, candidates, warnings, error, run)
