"""Lecturas del detector propio (Florence-2 ajustado, tarea 2.4) desde su caché.

El detector necesita PyTorch y GPU, que el producto no instala. Por eso se separa en dos pasos:

1. `python -m training.florence leer` (entorno con el extra `train`) recorre los PDF, lee cada
   página por mosaicos y deja las líneas en `generated/cache/detector` (o `TRAZIA_DETECTOR_CACHE`).
2. El canal `detector` de D solo lee esa caché. Si una página no está, el canal se omite y lo
   dice; nunca inventa lecturas.

La clave es el SHA-256 del PDF, la página, la resolución y el modelo, así que no depende de cómo
renderice cada entorno.
"""

import hashlib
import json
import os
from pathlib import Path

from ..ingest import EvidenceLine
from ..model import Source

DPI = 150
DEFAULT_MODEL = "florence2-trazia"


def cache_dir() -> Path:
    return Path(os.environ.get("TRAZIA_DETECTOR_CACHE", "generated/cache/detector"))


def model_name() -> str:
    return os.environ.get("TRAZIA_DETECTOR_MODEL", DEFAULT_MODEL)


def page_key(pdf: bytes, page: int, *, dpi: int = DPI, model: str | None = None) -> str:
    digest = hashlib.sha256(pdf).hexdigest()
    return hashlib.sha256(f"{digest}|{page}|{dpi}|{model or model_name()}".encode()).hexdigest()


def cache_path(key: str) -> Path:
    return cache_dir() / key[:2] / f"{key}.json"


def store_page(key: str, lines: list[dict]) -> Path:
    """Guarda las líneas de una página: [{"text", "bbox" (0–1), "score"}]."""
    path = cache_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(lines, ensure_ascii=False), encoding="utf-8")
    return path


def detector_pdf_lines(pdf: bytes, document_id: str, pages: int) -> list[EvidenceLine] | None:
    """Líneas de todas las páginas, o `None` si falta alguna en la caché."""
    out: list[EvidenceLine] = []
    model = model_name()
    for number in range(1, pages + 1):
        path = cache_path(page_key(pdf, number, model=model))
        if not path.exists():
            return None
        for row in json.loads(path.read_text(encoding="utf-8")):
            out.append(
                EvidenceLine(
                    text=row["text"],
                    source=Source(
                        document_id=document_id,
                        page=number,
                        locator=f"Detector propio, página {number}",
                        bbox=tuple(row["bbox"]),
                        confidence=row["score"],
                        channel="detector",
                        model=model,
                    ),
                )
            )
    return out
