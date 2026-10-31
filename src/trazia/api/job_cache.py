"""Resultados de trabajos validados, por contenido y configuración de lectura."""

import hashlib
import json
import time

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlmodel import Session

from trazia.calibration import calibration_path, load_calibration
from trazia.model import Revision, RunInfo
from trazia.store import DocumentRecord, JobCacheRecord, RevisionRecord, Store

from .pipeline_adapter import PipelineResult


class CacheMiss(ValueError):
    pass


def calibration_fingerprint() -> str | None:
    try:
        calibration = load_calibration()
        return calibration.sha256 if calibration else None
    except (OSError, ValueError, KeyError):
        path = calibration_path()
        if path and path.is_file():
            return "invalid:" + hashlib.sha256(path.read_bytes()).hexdigest()
        return "invalid:unreadable"


def fusion_fingerprint() -> str | None:
    from trazia.strategies.fusion import fusion_path, load_fusion

    try:
        model = load_fusion()
        return model.sha256 if model else None
    except (OSError, ValueError, KeyError, TypeError):
        path = fusion_path()
        if path and path.is_file():
            return "invalid:" + hashlib.sha256(path.read_bytes()).hexdigest()
        return "invalid:unreadable"


def key_for(session: Session, request: dict) -> str:
    from .extraction_feedback import epoch

    documents = []
    for identity in request["documents"]:
        record = session.get(DocumentRecord, identity)
        if record is None:
            raise CacheMiss("No existe un documento del trabajo")
        documents.append(
            {
                "sha256": record.sha256,
                "document_id": record.document_id,
                "filename": record.filename,
                "revision": record.revision,
            }
        )
    previous = None
    if request.get("previous_id"):
        record = session.get(RevisionRecord, request["previous_id"])
        if record is None:
            raise CacheMiss("No existe la revisión anterior")
        previous = hashlib.sha256(record.payload.encode()).hexdigest()
    content = {
        "version": 4,
        "reading": "pint-v1/page-signature-v1/revisable-draft-v1",
        "feedback": epoch(session) if request.get("use_learning", True) else None,
        "calibration": request.get("_cache_calibration", calibration_fingerprint()),
        "fusion": request.get("_cache_fusion", fusion_fingerprint()),
        "documents": documents,
        "strategy": request["strategy"],
        "providers": request["providers"],
        "dataset": request["dataset"],
        "previous": previous,
    }
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


def load(store: Store, session: Session, request: dict):
    from .extraction_feedback import build_feedback

    if not build_feedback(store, request).verified:
        raise CacheMiss("No se pueden verificar los originales del aprendizaje aprobado")
    cached = session.get(JobCacheRecord, key_for(session, request))
    if cached is None:
        raise CacheMiss(
            "Modo offline: no hay un resultado cacheado para estos documentos y estrategia"
        )
    try:
        for identity in request["documents"]:
            store.read(session.get(DocumentRecord, identity).sha256)
        payload = json.loads(store.read(cached.result_sha256))
        revision = Revision.model_validate(payload["revision"])
    except (OSError, ValueError, KeyError) as failure:
        raise CacheMiss(
            "Modo offline: no se puede verificar la caché o sus documentos originales"
        ) from failure
    if revision.equipment.tag.value != request["tag"]:
        raise CacheMiss("El tag del resultado cacheado no coincide con el trabajo")
    return payload, revision


def restore(store: Store, job_id: str, request: dict):
    from .jobs import emit

    started = time.perf_counter()
    with Session(store.engine) as session:
        payload, revision = load(store, session, request)
    revision.project_id = request["project_id"]
    revision.equipment.id = request["equipment_id"]
    revision.revision = request["revision"]
    revision.approval = None
    revision.run = RunInfo(
        strategy=request["strategy"],
        providers=[],
        seconds=time.perf_counter() - started,
        gpu_seconds=0,
        tokens_in=0,
        tokens_out=0,
        cost_eur=0,
        external_calls=0,
    )
    revision = Revision.model_validate_json(revision.model_dump_json())
    emit(store, job_id, "job", "ok", "", "Resultado recuperado de la caché; pipeline no ejecutado")
    return PipelineResult(revision, [], payload["warnings"], None, revision.run), revision


def remember(store: Store, session: Session, request: dict, revision: Revision, warnings: list):
    from .extraction_feedback import epoch

    if request.get("_feedback_unverifiable"):
        return None
    if request.get("_cache_feedback_epoch", epoch(session)) != epoch(session):
        return None
    if request.get("_cache_calibration") != calibration_fingerprint():
        # Los parámetros cambiaron durante la ejecución: no asociar el resultado a otra curva.
        return None
    if request.get("_cache_fusion", fusion_fingerprint()) != fusion_fingerprint():
        return None
    digest = store.put(
        json.dumps(
            {
                "revision": revision.model_dump(mode="json"),
                "warnings": warnings,
            },
            ensure_ascii=False,
        ).encode()
    )
    insert = pg_insert if store.engine.dialect.name == "postgresql" else sqlite_insert
    session.exec(
        insert(JobCacheRecord)
        .values(
            key=key_for(session, request),
            result_sha256=digest,
            created_at=time.time(),
        )
        .on_conflict_do_nothing(index_elements=["key"])
    )
    return digest
