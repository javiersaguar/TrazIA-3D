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

    from trazia.ocr import engine

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

    def recognize(array):
        started = time.perf_counter()
        result = actual(array)
        calls.append({"pixels_sha256": pixel_hash(array), "seconds": time.perf_counter() - started})
        return result

    def measure(name, content, cache):
        calls.clear()
        os.environ["TRAZIA_OCR_CACHE"] = str(output / cache)
        started = time.perf_counter()
        lines = engine.ocr_pdf_lines(content, "GA-INCREMENTAL")
        return {
            "name": name,
            "seconds": time.perf_counter() - started,
            "recognizer_calls": list(calls),
            "lines_per_page": dict(Counter(line.source.page for line in lines)),
        }

    engine._rapidocr = lambda: recognize
    try:
        phases = [
            measure("A_frio", a, "cache-ab"),
            measure("B_una_pagina_cambiada", b, "cache-ab"),
            measure("B_repetido", b, "cache-ab"),
            measure("B_frio_control", b, "cache-b"),
        ]
    finally:
        engine._rapidocr = factory
    counts = [len(p["recognizer_calls"]) for p in phases]
    same_page_reused = counts == [2, 1, 0, 2] and (
        phases[1]["recognizer_calls"][0]["pixels_sha256"] == pages_b[1]
    )
    result = {
        "synthetic": True,
        "component": "OCR CPU",
        "engine": engine.ENGINE,
        "onnx_available_providers": onnxruntime.get_available_providers(),
        "engine_initialization_seconds": init_seconds,
        "document_sha256": [hashlib.sha256(c).hexdigest() for c in (a, b)],
        "page_pixels_sha256": {"A": pages_a, "B": pages_b},
        "phases": phases,
        "only_changed_page_recognized": same_page_reused,
        "warm_vs_cold_seconds_saved": phases[3]["seconds"] - phases[1]["seconds"],
        "whole_pipeline_incremental": False,
        "limit": (
            "El OCR se reutiliza por imagen; se renderizan todas las páginas para obtener su hash."
        ),
    }
    (output / "incremental.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if same_page_reused else 2


if __name__ == "__main__":
    raise SystemExit(main())
