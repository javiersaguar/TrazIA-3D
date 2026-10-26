"""Caché de respuestas de visión por (hash de imagen, prompt, esquema, modelo).

- `TRAZIA_VISION_CACHE`: carpeta de la caché (por defecto `generated/cache/vision`).
- `TRAZIA_VISION_OFFLINE=1`: no se llama a ningún modelo; sin respuesta en caché, el proveedor
  lanza `VisionUnavailable`. Así corren las pruebas en CI, con respuestas versionadas en
  `tests/fixtures/vision_cache/`.
"""

import hashlib
import json
import os
from pathlib import Path

from .base import ProviderResult


def cache_dir() -> Path:
    return Path(os.environ.get("TRAZIA_VISION_CACHE", "generated/cache/vision"))


def offline() -> bool:
    return os.environ.get("TRAZIA_VISION_OFFLINE", "").strip() in ("1", "true", "yes")


def sha256(data: bytes | str) -> str:
    raw = data.encode("utf-8") if isinstance(data, str) else data
    return hashlib.sha256(raw).hexdigest()


def cache_key(image: bytes, prompt: str, schema: dict, model: str) -> str:
    schema_text = json.dumps(schema, sort_keys=True, ensure_ascii=False)
    return sha256("|".join((sha256(image), sha256(prompt), sha256(schema_text), model)))


def load(key: str) -> ProviderResult | None:
    path = cache_dir() / key[:2] / f"{key}.json"
    if not path.exists():
        return None
    return ProviderResult.from_cache(json.loads(path.read_text(encoding="utf-8")))


def store(key: str, result: ProviderResult) -> None:
    path = cache_dir() / key[:2] / f"{key}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result.to_cache(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
