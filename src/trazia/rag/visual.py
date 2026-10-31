"""Recuperación visual con ColQwen2 (ROADMAP 2.5), alternativa a la huella ligera.

Cada página se convierte en una imagen y ColQwen2 la describe con un vector de 128 valores por
trozo de imagen (unos cientos por página). Dos páginas se comparan con MaxSim: para cada trozo de
una se busca el más parecido de la otra y se promedia, en los dos sentidos. Sale un número entre
0 y 1 que mide si las dos láminas tienen la misma composición (vistas, tabla y cajetín).

- Va detrás del extra `train` (torch y transformers) y se activa con
  `TRAZIA_RAG_RETRIEVAL=colqwen2`. Si falta torch, el modelo o la GPU, C vuelve a la huella.
- Los vectores se guardan por huella sha256 del PDF y número de página
  (`TRAZIA_RAG_VISUAL_CACHE`, por defecto `generated/rag/colqwen2/`): el modelo solo se carga
  si falta alguna página en la caché.
"""

import hashlib
import io
import os
from functools import lru_cache
from pathlib import Path

import numpy as np

MODEL = "vidore/colqwen2-v1.0-hf"
DPI = 60  # una A3 apaisada a 60 ppp son unos 990×700 px: el procesador la reduce a su tamaño


class VisualUnavailable(RuntimeError):
    """No se puede usar ColQwen2 aquí (falta torch, el modelo o la memoria)."""


def enabled() -> bool:
    return os.environ.get("TRAZIA_RAG_RETRIEVAL", "huella").lower() == "colqwen2"


def cache_dir() -> Path:
    return Path(os.environ.get("TRAZIA_RAG_VISUAL_CACHE", "generated/rag/colqwen2"))


def page_key(pdf: bytes, page: int) -> str:
    return f"{hashlib.sha256(pdf).hexdigest()[:24]}-p{page}-{DPI}"


def _cached(key: str) -> np.ndarray | None:
    path = cache_dir() / f"{key}.npy"
    return np.load(path) if path.exists() else None


def _store(key: str, vectors: np.ndarray) -> None:
    folder = cache_dir()
    folder.mkdir(parents=True, exist_ok=True)
    tmp = folder / f"{key}.tmp.npy"
    np.save(tmp, vectors)
    tmp.replace(folder / f"{key}.npy")


@lru_cache(maxsize=1)
def _model():
    try:
        import torch
        from transformers import ColQwen2ForRetrieval, ColQwen2Processor
    except ImportError as exc:
        raise VisualUnavailable("Falta el extra train (torch y transformers)") from exc
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if device == "cuda" else torch.float32
    try:
        model = ColQwen2ForRetrieval.from_pretrained(MODEL, dtype=dtype, device_map=device)
        processor = ColQwen2Processor.from_pretrained(MODEL)
    except OSError as exc:  # sin red y sin el modelo descargado
        raise VisualUnavailable(f"No está el modelo {MODEL}") from exc
    return model.eval(), processor


def _render(pdf: bytes, page: int):
    import pdfplumber

    with pdfplumber.open(io.BytesIO(pdf)) as document:
        return document.pages[page - 1].to_image(resolution=DPI).original.convert("RGB")


def embed_page(pdf: bytes, page: int) -> np.ndarray:
    """Vectores ColQwen2 de una página (n × 128, float16, cada fila de norma 1)."""
    key = page_key(pdf, page)
    hit = _cached(key)
    if hit is not None:
        return hit
    import torch

    model, processor = _model()
    batch = processor(images=[_render(pdf, page)], return_tensors="pt").to(model.device)
    with torch.inference_mode():
        out = model(**batch).embeddings[0]
    vectors = out.float().cpu().numpy()
    vectors = vectors[np.linalg.norm(vectors, axis=1) > 1e-6]  # sin relleno
    vectors = (vectors / np.linalg.norm(vectors, axis=1, keepdims=True)).astype(np.float16)
    _store(key, vectors)
    return vectors


def maxsim(a: np.ndarray, b: np.ndarray) -> float:
    """MaxSim simétrico normalizado, de 0 a 1."""
    sims = a.astype(np.float32) @ b.astype(np.float32).T
    score = 0.5 * (sims.max(axis=1).mean() + sims.max(axis=0).mean())
    return float(max(0.0, score))


def entry_vectors(entry: dict) -> np.ndarray | None:
    """Vectores de la página GA de un caso de la biblioteca, si se pueden obtener."""
    sha, page = entry.get("sha256"), entry.get("page")
    if not sha or not page:
        return None  # biblioteca anterior a 2.5: sin huella del PDF
    hit = _cached(f"{sha[:24]}-p{page}-{DPI}")
    if hit is not None:
        return hit
    source = Path(entry.get("source", ""))
    if not source.is_file():
        return None
    data = source.read_bytes()
    if hashlib.sha256(data).hexdigest() != sha:
        return None  # el PDF cambió desde que se construyó la biblioteca
    return embed_page(data, page)
