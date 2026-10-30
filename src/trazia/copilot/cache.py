"""Respuestas verificadas para la demo sin red ni inferencia nueva."""

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path

from pydantic import ValidationError

from trazia.model import RunInfo
from trazia.runtime import offline

from .models import CopilotAnswer
from .service import CopilotUnavailable


def key_for(revision, question, options):
    # También se invalida al cambiar las reglas, herramientas o validación del copiloto.
    source = hashlib.sha256()
    for name in ("service.py", "tools.py", "models.py", "cache.py"):
        source.update(Path(__file__).with_name(name).read_bytes())
    previous = options.get("previous")
    identity = {
        "revision": revision.model_dump(mode="json"),
        "previous": previous.model_dump(mode="json") if previous else None,
        "question": question,
        "revision_id": options["revision_id"],
        "revision_version": options["revision_version"],
        "path": options.get("path"),
        "model": os.getenv("TRAZIA_OLLAMA_MODEL", "qwen3-vl:4b-instruct"),
        "host": os.getenv("TRAZIA_OLLAMA_URL", "http://127.0.0.1:11434"),
        "code": source.hexdigest(),
    }
    return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()


async def answer_cached(revision, question, *, cache_root: Path, call, **options):
    started = time.perf_counter()
    key = key_for(revision, question, options)
    path = cache_root / key[:2] / f"{key}.json"
    try:
        answer = CopilotAnswer.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, ValidationError):
        answer = None
    if answer:
        try:
            # La caché no evita comprobar que los originales citados siguen íntegros.
            for citation in answer.citations:
                if citation.original_verified and citation.sha256:
                    content = options["read_document"](citation.sha256)
                    if hashlib.sha256(content).hexdigest() != citation.sha256:
                        raise ValueError("Original modificado")
        except (OSError, ValueError) as failure:
            raise CopilotUnavailable(
                "No se puede verificar el original de la respuesta cacheada"
            ) from failure
        return answer.model_copy(
            update={
                "cached": True,
                "run": RunInfo(
                    strategy="copilot-cache",
                    providers=[],
                    seconds=time.perf_counter() - started,
                    gpu_seconds=0,
                    tokens_in=0,
                    tokens_out=0,
                    cost_eur=0,
                    external_calls=0,
                ),
            }
        )
    if offline():
        raise CopilotUnavailable(
            "Modo offline: no hay respuesta cacheada para estos datos y pregunta"
        )
    answer = await call(revision, question, **options)
    if not answer.abstained:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(answer.model_dump_json().encode())
            os.replace(temporary, path)
        finally:
            if temporary and temporary.exists():
                temporary.unlink()
    return answer
