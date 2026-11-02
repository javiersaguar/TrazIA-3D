"""Motor de OCR con caché. La salida ya está en el formato de `trazia.ingest.EvidenceLine`."""

import hashlib
import io
import json
import logging
import os
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

import pdfplumber
from PIL import Image

from ..ingest import EvidenceLine
from ..model import Source
from .page_signature import page_signature

ENGINE = "rapidocr-4-tableanchor"  # cambia la clave de caché si cambia el motor o sus modelos
DPI = 200
# Normalización de símbolos que el reconocedor devuelve como un solo carácter.
REPLACEMENTS = {"℃": "°C", "℉": "°F", "º": "°", "″": '"', "′": "'"}


class OcrUnavailable(RuntimeError):
    """No hay motor de OCR instalado ni respuesta en caché."""


@dataclass(frozen=True)
class OcrLine:
    text: str
    bbox: tuple[float, float, float, float]  # normalizada 0–1, origen arriba a la izquierda
    score: float


def _cache_dir() -> Path:
    return Path(os.environ.get("TRAZIA_OCR_CACHE", "generated/cache/ocr"))


def _offline() -> bool:
    return os.environ.get("TRAZIA_OCR_OFFLINE", "").strip() in ("1", "true", "yes")


def _write_lines(path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps([asdict(line) for line in lines], ensure_ascii=False)
    envelope = {"sha256": hashlib.sha256(content.encode()).hexdigest(), "lines": content}
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    try:
        temporary.write_text(json.dumps(envelope), encoding="utf8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _read_lines(path):
    try:
        data = json.loads(path.read_text(encoding="utf8"))
        content = data["lines"]
        if hashlib.sha256(content.encode()).hexdigest() != data["sha256"]:
            return None
        lines = [OcrLine(r["text"], tuple(r["bbox"]), r["score"]) for r in json.loads(content)]
        if any(
            not isinstance(r.text, str)
            or len(r.bbox) != 4
            or not (0 <= r.score <= 1)
            or not (0 <= r.bbox[0] < r.bbox[2] <= 1)
            or not (0 <= r.bbox[1] < r.bbox[3] <= 1)
            for r in lines
        ):
            return None
        return lines
    except (OSError, ValueError, TypeError, KeyError):
        return None


def profile() -> dict:
    """Configuración CPU explícita y parte de la huella de la caché."""
    try:
        threads = int(os.environ.get("TRAZIA_OCR_THREADS", "2"))
    except ValueError as exc:
        raise OcrUnavailable("TRAZIA_OCR_THREADS debe ser un entero entre 1 y 8") from exc
    if not 1 <= threads <= 8:
        raise OcrUnavailable("TRAZIA_OCR_THREADS debe estar entre 1 y 8")
    return {
        "engine": ENGINE,
        "params": {
            "Global.max_side_len": 2000,
            "Global.log_level": "warning",
            "Det.limit_side_len": 736,
            "Det.limit_type": "min",
            "EngineConfig.onnxruntime.intra_op_num_threads": threads,
            "EngineConfig.onnxruntime.inter_op_num_threads": 1,
            "EngineConfig.onnxruntime.use_cuda": False,
            "EngineConfig.onnxruntime.use_dml": False,
        },
    }


def _signature() -> str:
    return json.dumps(profile(), sort_keys=True)


@lru_cache(maxsize=1)
def _rapidocr_for(signature: str):
    try:
        from rapidocr import RapidOCR
    except ImportError as exc:  # el extra `ocr` no está instalado
        raise OcrUnavailable("Instala el extra OCR: uv sync --extra ocr") from exc
    logging.getLogger("RapidOCR").setLevel(logging.WARNING)
    return RapidOCR(params=json.loads(signature)["params"])


def _rapidocr():
    return _rapidocr_for(_signature())


def _normalise(text: str) -> str:
    for old, new in REPLACEMENTS.items():
        text = text.replace(old, new)
    return text.strip()


def _tiled_lines(image):
    """Cuatro recortes solapados; las cajas se expresan en la página completa."""
    width, height = image.size
    lines = []
    for x0, y0, x1, y1 in (
        (0, 0, 0.56, 0.56),
        (0.44, 0, 1, 0.56),
        (0, 0.44, 0.56, 1),
        (0.44, 0.44, 1, 1),
    ):
        left, top, right, bottom = (
            round(x0 * width),
            round(y0 * height),
            round(x1 * width),
            round(y1 * height),
        )
        crop = image.crop((left, top, right, bottom))
        try:
            for line in ocr_image(crop):
                a, b, c, d = line.bbox
                lines.append(
                    OcrLine(
                        line.text,
                        (
                            (left + a * (right - left)) / width,
                            (top + b * (bottom - top)) / height,
                            (left + c * (right - left)) / width,
                            (top + d * (bottom - top)) / height,
                        ),
                        line.score,
                    )
                )
        finally:
            crop.close()
    kept = []
    for line in sorted(lines, key=lambda r: r.score, reverse=True):
        box = line.bbox

        def duplicate(other):
            a = other.bbox
            overlap = max(0, min(a[2], box[2]) - max(a[0], box[0])) * max(
                0, min(a[3], box[3]) - max(a[1], box[1])
            )
            return overlap >= 0.5 * min(
                (a[2] - a[0]) * (a[3] - a[1]), (box[2] - box[0]) * (box[3] - box[1])
            )

        if not any(duplicate(other) for other in kept):
            kept.append(line)
    return kept


def ocr_image(image: Image.Image) -> list[OcrLine]:
    """Reconoce una página. Cada caja se pasa a su rectángulo envolvente normalizado."""
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    key = hashlib.sha256(buffer.getvalue() + _signature().encode()).hexdigest()
    path = _cache_dir() / key[:2] / f"{key}.json"
    cached = _read_lines(path)
    if cached is not None:
        return cached
    if _offline():
        raise OcrUnavailable("Modo sin conexión y página sin OCR en caché")
    import numpy as np

    result = _rapidocr()(np.array(image.convert("RGB")))
    width, height = image.size
    lines = []
    boxes = [] if result.boxes is None else list(result.boxes)
    texts = [] if result.txts is None else list(result.txts)
    scores = [] if result.scores is None else list(result.scores)
    for box, text, score in zip(boxes, texts, scores, strict=False):
        xs = [float(p[0]) for p in box]
        ys = [float(p[1]) for p in box]
        bbox = (
            max(0.0, min(xs) / width),
            max(0.0, min(ys) / height),
            min(1.0, max(xs) / width),
            min(1.0, max(ys) / height),
        )
        clean = _normalise(text)
        if clean and bbox[2] > bbox[0] and bbox[3] > bbox[1]:
            lines.append(OcrLine(clean, bbox, round(float(score), 4)))
    _write_lines(path, lines)
    return lines


def ocr_pdf_lines(
    pdf: bytes,
    document_id: str,
    *,
    pages: list[int] | None = None,
    dpi: int = DPI,
    rotation: int = 0,
    tiles: bool = False,
) -> list[EvidenceLine]:
    """Líneas de evidencia de las páginas indicadas (todas por defecto) de un PDF."""
    if rotation not in (0, 90):
        raise ValueError("El suplemento OCR solo admite 0 o 90 grados")
    if rotation and tiles:
        raise ValueError("Los suplementos de giro y mosaico se leen por separado")
    out: list[EvidenceLine] = []
    with pdfplumber.open(io.BytesIO(pdf)) as document:
        numbers = pages or list(range(1, len(document.pages) + 1))
        for number in numbers:
            page = document.pages[number - 1]
            signature = page_signature(page, dpi)
            suffix = f":rotation={rotation}" if rotation else ""
            if tiles:
                suffix = ":tiles=2x2-overlap12-v1"
            key = hashlib.sha256(f"{signature}:{_signature()}{suffix}".encode()).hexdigest()
            path = _cache_dir() / "pages-v1" / key[:2] / f"{key}.json"
            lines = _read_lines(path) if signature else None
            if lines is None:
                from ..page_cache import render_page

                image = render_page(page, dpi)
                try:
                    if tiles:
                        lines = _tiled_lines(image)
                    elif rotation:
                        rotated = image.transpose(Image.Transpose.ROTATE_90)
                        try:
                            lines = [
                                OcrLine(
                                    line.text,
                                    (
                                        1 - line.bbox[3],
                                        line.bbox[0],
                                        1 - line.bbox[1],
                                        line.bbox[2],
                                    ),
                                    line.score,
                                )
                                for line in ocr_image(rotated)
                            ]
                        finally:
                            rotated.close()
                    else:
                        lines = ocr_image(image)
                finally:
                    image.close()
                if signature:
                    _write_lines(path, lines)
            for line in lines:
                out.append(
                    EvidenceLine(
                        text=line.text,
                        source=Source(
                            document_id=document_id,
                            page=number,
                            locator=f"OCR de página {number}"
                            + (" · giro 90°" if rotation else "")
                            + (" · mosaico 2×2" if tiles else ""),
                            bbox=line.bbox,
                            confidence=line.score,
                        ),
                    )
                )
    return out
