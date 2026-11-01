import io

import pdfplumber
from PIL import Image, ImageDraw

from trazia.ocr import engine
from trazia.ocr.page_signature import page_signature


def document(label):
    images = [Image.new("RGB", (200, 200), "white") for _ in range(2)]
    ImageDraw.Draw(images[0]).text((20, 20), "SYNTHETIC - SAME", fill="black")
    ImageDraw.Draw(images[1]).text((20, 20), label, fill="black")
    buffer = io.BytesIO()
    images[0].save(buffer, format="PDF", save_all=True, append_images=images[1:])
    return buffer.getvalue()


def test_new_revision_reuses_unchanged_page_before_raster_and_rebinds_evidence(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("TRAZIA_OCR_CACHE", str(tmp_path))
    a, b = document("REV A"), document("REV B")
    with pdfplumber.open(io.BytesIO(a)) as first, pdfplumber.open(io.BytesIO(b)) as second:
        assert page_signature(first.pages[0], 200) == page_signature(second.pages[0], 200)
        assert page_signature(first.pages[1], 200) != page_signature(second.pages[1], 200)
        assert page_signature(first.pages[0], 200) != page_signature(first.pages[0], 300)
    renders, recognitions = [], []
    original = pdfplumber.page.Page.to_image

    def render(page, **options):
        renders.append(page.page_number)
        return original(page, **options)

    def recognize(image):
        recognitions.append(image.size)
        return [engine.OcrLine("Synthetic unit fixture", (0.1, 0.1, 0.5, 0.2), 0.8)]

    monkeypatch.setattr(pdfplumber.page.Page, "to_image", render)
    monkeypatch.setattr(engine, "ocr_image", recognize)
    engine.ocr_pdf_lines(a, "GA-A")
    assert renders == [1, 2] and len(recognitions) == 2
    renders.clear()
    recognitions.clear()
    lines = engine.ocr_pdf_lines(b, "GA-B")
    assert renders == [2] and len(recognitions) == 1
    assert {line.source.document_id for line in lines} == {"GA-B"}
    renders.clear()
    recognitions.clear()
    engine.ocr_pdf_lines(b, "GA-B")
    assert renders == [] and recognitions == []
    cached = next((tmp_path / "pages-v1").rglob("*.json"))
    cached.write_text("{broken", encoding="utf8")
    engine.ocr_pdf_lines(b, "GA-B")
    assert renders == [] and len(recognitions) == 1  # Se rehace OCR usando el raster íntegro.


def test_positive_raster_geometry_with_numpy_scalars_roundtrips(tmp_path, monkeypatch):
    import numpy as np
    import pytest

    from trazia.geometry2d.page_cache import raster_geometry
    from trazia.geometry2d.vector import Elevation, ElevationStub, Plan, PlanStub

    monkeypatch.setenv("TRAZIA_PAGE_CACHE", str(tmp_path))
    data = document("GEOMETRY")
    expected = (
        Elevation(
            tuple(np.float32(x) for x in (1, 2, 3, 4)),
            np.float32(1),
            np.float32(5),
            np.float32(6),
            [ElevationStub("left", np.float32(2.5), np.float32(0.1), (1, 2))],
        ),
        Plan(
            (np.float32(1), np.float32(2)),
            np.float32(3),
            [PlanStub(np.float32(0.5), np.float32(1), np.float32(0.2), (4, 5))],
        ),
    )
    first = raster_geometry(data, 1, lambda: expected, dpi=200)

    def unexpected():
        raise AssertionError("La geometría positiva debía reutilizarse")

    second = raster_geometry(data, 1, unexpected, dpi=200)
    assert second[0].shell == first[0].shell
    assert second[0].stubs[0].neck == pytest.approx(0.1)
    assert second[1].stubs[0].angle == 0.5
    assert isinstance(second[1].radius, float)


def test_unwritable_cache_does_not_break_computation(tmp_path, monkeypatch):
    from trazia import page_cache

    blocked = tmp_path / "file"
    blocked.write_text("not a directory", encoding="utf8")
    monkeypatch.setattr(page_cache, "path_for", lambda *args: blocked / "cache")
    assert page_cache.memo_page(None, "fixture", lambda: {"value": 3}) == {"value": 3}
