"""Lectura de una página completa con un proveedor de visión: render, mosaicos y reproyección."""

import io
from dataclasses import dataclass, field

import pdfplumber
from PIL import Image

from .base import VisionError
from .tiling import merge_duplicates, tiles


@dataclass
class PageReading:
    items: list[dict]  # {"text", "bbox"} en coordenadas de página 0–1
    provider: str
    model: str
    prompt_sha256: str
    seconds: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_eur: float = 0.0
    tiles: int = 0
    cached_tiles: int = 0
    external_calls: int = 0
    errors: list[str] = field(default_factory=list)


def render_page(pdf: bytes, page: int, dpi: int = 150) -> Image.Image:
    from ..page_cache import render_page as cached_render

    with pdfplumber.open(io.BytesIO(pdf)) as document:
        return cached_render(document.pages[page - 1], dpi)


def read_page(
    provider,
    image: Image.Image,
    *,
    page_ref: str,
    task: str = "lineas",
    tile_size: int = 1280,
    overlap: float = 0.15,
) -> PageReading:
    """Lee la página por mosaicos. Un mosaico que falla no tumba la página: queda en `errors`."""
    reading = None
    collected: list[dict] = []
    parts = tiles(image, size=tile_size, overlap=overlap)
    for index, tile in enumerate(parts):
        try:
            result = provider.read(tile.png(), task, page_ref=f"{page_ref}/t{index}")
        except VisionError as exc:
            if reading is None:
                reading = PageReading([], provider.name, getattr(provider, "model", ""), "")
            reading.errors.append(f"mosaico {index}: {exc}")
            continue
        if reading is None:
            reading = PageReading([], result.provider, result.model, result.prompt_sha256)
        reading.seconds += result.seconds
        reading.tokens_in += result.tokens_in or 0
        reading.tokens_out += result.tokens_out or 0
        reading.cost_eur += result.cost_eur
        reading.cached_tiles += result.cached
        reading.external_calls += int(result.external and not result.cached)
        key = "items" if task == "lineas" else "fields"
        for item in result.data.get(key, []):
            if "bbox" in item:
                collected.append(
                    {
                        **item,
                        "bbox": list(tile.to_page(tuple(item["bbox"]))),
                        "box": tile.to_page(tuple(item["bbox"])),
                        "tile": index,
                    }
                )
    if reading is None:
        reading = PageReading([], provider.name, getattr(provider, "model", ""), "")
    reading.tiles = len(parts)
    merged = merge_duplicates(collected)
    for item in merged:
        item.pop("box", None)
    reading.items = merged
    return reading
