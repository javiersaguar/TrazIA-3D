"""Mide OCR CPU real por página; no afirma que toda la ingestión sea incremental."""

import argparse
import hashlib
import io
import json
import os
import time
from collections import Counter
from pathlib import Path


def main():
    import numpy as np
    import onnxruntime
    import pdfplumber
    from PIL import Image, ImageDraw, ImageFont

    from trazia.geometry2d import page_cache as geometry_cache
    from trazia.ingest import ingest_bytes
    from trazia.ocr import engine
    from trazia.strategies import a_vision

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--documento", type=Path, required=True, help="PDF sintético público")
    parser.add_argument("--salida", type=Path, required=True)
    args = parser.parse_args()
    output = args.salida.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any((output / name).exists() for name in ("cache-ab", "cache-b")):
        parser.error("Usa un destino nuevo; la comprobación requiere cachés frías")
    if "CUDAExecutionProvider" in onnxruntime.get_available_providers():
        parser.error("Usa la imagen CPU para evitar una medición GPU accidental")
    with pdfplumber.open(args.documento) as pdf:
        first = pdf.pages[0].to_image(resolution=120).original.copy()
    font = ImageFont.load_default(size=42)

    def document(label):
        note = Image.new("RGB", (1100, 800), "white")
        draw = ImageDraw.Draw(note)
        for i, text in enumerate(
            (
                "TRAZIA - SYNTHETIC DATA",
                f"NOTE REVISION {label}",
                "No real engineering document",
                "Only this page changes",
            )
        ):
            draw.text((70, 100 + i * 120), text, fill="black", font=font)
        buffer = io.BytesIO()
        first.convert("RGB").save(
            buffer, format="PDF", save_all=True, append_images=[note], resolution=120
        )
        return buffer.getvalue()

    a, b = document("A"), document("B")
    (output / "sintetico-a.pdf").write_bytes(a)
    (output / "sintetico-b.pdf").write_bytes(b)

    def pixel_hash(array):
        return hashlib.sha256(str(array.shape).encode() + array.tobytes()).hexdigest()

    def page_hashes(content):
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            return [
                pixel_hash(np.array(p.to_image(resolution=engine.DPI).original.convert("RGB")))
                for p in pdf.pages
            ]

    pages_a, pages_b = page_hashes(a), page_hashes(b)
    assert pages_a[0] == pages_b[0] and pages_a[1] != pages_b[1]
    factory = engine._rapidocr
    started = time.perf_counter()
    actual = factory()
    init_seconds = time.perf_counter() - started
    calls = []
    renders = []
    text_pages, vector_pages, geometry_pages = [], [], []
    render_page = pdfplumber.page.Page.to_image
    text_reader = pdfplumber.page.Page.extract_text_lines
    vector_reader = geometry_cache.find_elevation
    geometry_reader = a_vision._uncached_raster_geometry

    def render_spy(page, *args, **kwargs):
        renders.append(page.page_number)
        return render_page(page, *args, **kwargs)

    def text_spy(page, *args, **kwargs):
        text_pages.append(page.page_number)
        return text_reader(page, *args, **kwargs)

    def vector_spy(page):
        vector_pages.append(page.page_number)
        return vector_reader(page)

    def geometry_spy(content, page):
        geometry_pages.append(page)
        return geometry_reader(content, page)

    def recognize(array):
        started = time.perf_counter()
        result = actual(array)
        calls.append({"pixels_sha256": pixel_hash(array), "seconds": time.perf_counter() - started})
        return result

    def measure(name, content, cache):
        calls.clear()
        renders.clear()
        text_pages.clear()
        vector_pages.clear()
        geometry_pages.clear()
        os.environ["TRAZIA_OCR_CACHE"] = str(output / cache)
        os.environ["TRAZIA_PAGE_CACHE"] = str(output / cache / "page-stages")
        started = time.perf_counter()
        ingest_bytes(
            content, "GAD_INCREMENTAL.pdf", "GA-INCREMENTAL", "B" if name.startswith("B") else "A"
        )
        lines = engine.ocr_pdf_lines(content, "GA-INCREMENTAL")
        with pdfplumber.open(io.BytesIO(content)) as document:
            for page in document.pages:
                geometry_cache.vector_geometry(page)
                a_vision._raster_geometry(content, page.page_number)
        return {
            "name": name,
            "seconds": time.perf_counter() - started,
            "recognizer_calls": list(calls),
            "rendered_pages": list(renders),
            "text_extraction_pages": list(text_pages),
            "vector_analysis_pages": list(vector_pages),
            "raster_analysis_pages": list(geometry_pages),
            "lines_per_page": dict(Counter(line.source.page for line in lines)),
        }

    engine._rapidocr = lambda: recognize
    pdfplumber.page.Page.to_image = render_spy
    pdfplumber.page.Page.extract_text_lines = text_spy
    geometry_cache.find_elevation = vector_spy
    a_vision._uncached_raster_geometry = geometry_spy
    try:
        phases = [
            measure("A_frio", a, "cache-ab"),
            measure("B_una_pagina_cambiada", b, "cache-ab"),
            measure("B_repetido", b, "cache-ab"),
            measure("B_frio_control", b, "cache-b"),
        ]
    finally:
        engine._rapidocr = factory
        pdfplumber.page.Page.to_image = render_page
        pdfplumber.page.Page.extract_text_lines = text_reader
        geometry_cache.find_elevation = vector_reader
        a_vision._uncached_raster_geometry = geometry_reader
    counts = [len(p["recognizer_calls"]) for p in phases]
    same_page_reused = counts == [2, 1, 0, 2] and (
        phases[1]["recognizer_calls"][0]["pixels_sha256"] == pages_b[1]
    )
    result = {
        "synthetic": True,
        "component": "Texto, render, OCR y geometría por página · CPU",
        "engine": engine.ENGINE,
        "onnx_available_providers": onnxruntime.get_available_providers(),
        "engine_initialization_seconds": init_seconds,
        "document_sha256": [hashlib.sha256(c).hexdigest() for c in (a, b)],
        "page_pixels_sha256": {"A": pages_a, "B": pages_b},
        "phases": phases,
        "only_changed_page_recognized": same_page_reused,
        "page_stages_incremental": all(
            [p[key] for p in phases] == [[1, 2], [2], [], [1, 2]]
            for key in (
                "rendered_pages",
                "text_extraction_pages",
                "vector_analysis_pages",
                "raster_analysis_pages",
            )
        ),
        "only_changed_page_rendered": [p["rendered_pages"] for p in phases]
        == [[1, 2], [2], [], [1, 2]],
        "warm_vs_cold_seconds_saved": phases[3]["seconds"] - phases[1]["seconds"],
        "whole_pipeline_incremental": False,
        "limit": (
            "Se ejercitan las etapas reales por página, incluida geometría, en una sola secuencia. "
            "Se sigue leyendo la estructura PDF para huellas; la reconciliación global y el IFC "
            "no son una edición incremental de mallas. No es precisión industrial."
        ),
    }
    (output / "incremental.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if same_page_reused and result["page_stages_incremental"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
