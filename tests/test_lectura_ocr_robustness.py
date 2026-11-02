"""Regresiones con cabecera desplazada y caché OCR verificable, sin descargar modelos."""

import io
from types import SimpleNamespace

import pytest
from PIL import Image

from trazia.extractors.drawing import DrawingExtractor, _rows, document_context
from trazia.ingest import EvidenceLine
from trazia.model import Source
from trazia.ocr import engine


def line(text, x, y, width=0.035, height=0.012):
    return EvidenceLine(
        text=text,
        source=Source(
            document_id="GA",
            page=1,
            locator="OCR",
            confidence=0.9,
            bbox=(x, y, x + width, y + height),
        ),
    )


def test_nozzle_header_is_not_split_by_an_unrelated_dimension():
    # La cota de otra zona tiene una fuente mayor y atrae MARK a su fila global.
    lines = [
        line("1500", 0.15, 0.094, height=0.018),
        line("MARK", 0.59, 0.102),
        line("SIZE DN", 0.63, 0.102),
        line("PROJ.", 0.69, 0.106),
        line("ELEV.", 0.75, 0.106),
        line("ORIENT.", 0.82, 0.106),
        line("N1", 0.59, 0.13),
        line("200", 0.63, 0.13),
        line("500", 0.69, 0.13),
        line("4200", 0.75, 0.13),
        line("225°", 0.82, 0.13),
    ]
    candidates, region = DrawingExtractor()._nozzle_table(_rows(lines), document_context(lines))
    assert {c.path: c.value for c in candidates} == {
        "nozzles.N1.diameter": 200,
        "nozzles.N1.projection": 500,
        "nozzles.N1.elevation": 4200,
        "nozzles.N1.azimuth": 225,
    }
    assert region and all(c.source.page == 1 and c.source.bbox for c in candidates)


def test_ocr_profile_invalidates_cache_and_corruption_fails_closed(monkeypatch, tmp_path):
    calls = []

    def recognize(image):
        calls.append(1)
        return SimpleNamespace(
            boxes=[[[1, 1], [9, 1], [9, 3], [1, 3]]], txts=["ID 2000"], scores=[0.9]
        )

    monkeypatch.setattr(engine, "_rapidocr", lambda: recognize)
    monkeypatch.setenv("TRAZIA_OCR_CACHE", str(tmp_path))
    image = Image.new("RGB", (10, 10), "white")
    assert engine.ocr_image(image)[0].text == "ID 2000"
    engine.ocr_image(image)
    assert len(calls) == 1
    monkeypatch.setenv("TRAZIA_OCR_THREADS", "3")
    engine.ocr_image(image)
    assert len(calls) == 2
    for p in tmp_path.rglob("*.json"):
        p.write_text('{"sha256":"corrupt","lines":"[]"}')
    monkeypatch.setenv("TRAZIA_OCR_OFFLINE", "1")
    with pytest.raises(engine.OcrUnavailable, match="sin OCR en caché"):
        engine.ocr_image(image)
    assert len(calls) == 2


def test_ocr_threads_are_bounded_and_cpu_explicit(monkeypatch):
    monkeypatch.setenv("TRAZIA_OCR_THREADS", "2")
    params = engine.profile()["params"]
    assert params["EngineConfig.onnxruntime.intra_op_num_threads"] == 2
    assert params["EngineConfig.onnxruntime.use_cuda"] is False
    monkeypatch.setenv("TRAZIA_OCR_THREADS", "0")
    with pytest.raises(engine.OcrUnavailable):
        engine.profile()


def test_rotated_ocr_boxes_return_to_original_and_cache_rebinds_document(monkeypatch, tmp_path):
    image = Image.new("RGB", (120, 80), "white")
    buffer = io.BytesIO()
    image.save(buffer, format="PDF")
    calls = []

    def recognize(image):
        calls.append(image.size)
        return [engine.OcrLine("750", (0.2, 0.1, 0.4, 0.3), 0.9)]

    monkeypatch.setattr(engine, "ocr_image", recognize)
    monkeypatch.setenv("TRAZIA_OCR_CACHE", str(tmp_path))
    original = engine.ocr_pdf_lines(buffer.getvalue(), "A")
    rotated = engine.ocr_pdf_lines(buffer.getvalue(), "A", rotation=90)
    assert original[0].source.bbox == (0.2, 0.1, 0.4, 0.3)
    assert rotated[0].source.bbox == pytest.approx((0.7, 0.2, 0.9, 0.4))
    assert calls[1] == calls[0][::-1]
    rebound = engine.ocr_pdf_lines(buffer.getvalue(), "B", rotation=90)
    assert len(calls) == 2 and rebound[0].source.document_id == "B"
    assert rebound[0].source.bbox == rotated[0].source.bbox


def test_mosaic_boxes_stay_on_the_original_page_and_reuse_cache(monkeypatch, tmp_path):
    image = Image.new("RGB", (120, 80), "white")
    buffer = io.BytesIO()
    image.save(buffer, format="PDF")
    calls = []

    def recognize(image):
        calls.append(image.size)
        return [engine.OcrLine("750", (0.2, 0.1, 0.4, 0.3), 0.9)]

    monkeypatch.setattr(engine, "ocr_image", recognize)
    monkeypatch.setenv("TRAZIA_OCR_CACHE", str(tmp_path))
    lines = engine.ocr_pdf_lines(buffer.getvalue(), "A", tiles=True)
    assert len(lines) == 4 and len(calls) == 4
    assert (
        len({(round(item.source.bbox[0], 1), round(item.source.bbox[1], 1)) for item in lines}) == 4
    )
    assert all(
        0 <= item.source.bbox[0] < item.source.bbox[2] <= 1
        and 0 <= item.source.bbox[1] < item.source.bbox[3] <= 1
        for item in lines
    )
    rebound = engine.ocr_pdf_lines(buffer.getvalue(), "B", tiles=True)
    assert len(calls) == 4 and all(item.source.document_id == "B" for item in rebound)


@pytest.mark.parametrize("old_diameter,expected", [(2100, 2100), (2000, 2000)])
def test_mosaic_never_overrides_reliable_dimensions_or_existing_nozzles(
    monkeypatch, old_diameter, expected
):
    import trazia.ocr
    from trazia.extraction import Candidate
    from trazia.ingest import Bundle
    from trazia.model import Document
    from trazia.strategies.b_reglas import ReglasStrategy

    lines = [
        line(text, 0.1, 0.1 + index * 0.04, width=0.5)
        for index, text in enumerate(
            [
                "DIAMETER: 2000 mm",
                "HEIGHT: 5000 mm",
                "HEAD_DEPTH: 500 mm",
                "SKIRT_HEIGHT: 1000 mm",
                "SKIRT_THICKNESS: 12 mm",
            ]
        )
    ]
    monkeypatch.setattr(trazia.ocr, "ocr_pdf_lines", lambda *args, **kwargs: lines)
    source = Source(
        document_id="GA", page=1, locator="OCR", bbox=(0.1, 0.1, 0.5, 0.2), confidence=0.95
    )
    old = Candidate(path="diameter", value=old_diameter, unit="mm", source=source)
    nozzle = Candidate(path="nozzles.N1.diameter", value=80, unit="mm", source=source)
    bundle = Bundle(
        document=Document(id="GA", filename="GAD_V-1_rev1.pdf", revision="1", sha256="0" * 64),
        media_type="pdf",
        lines=[],
    )
    ctx = SimpleNamespace(raw={"GA": b"fixture"}, emit=lambda event: None)
    _, drawing, _ = ReglasStrategy()._tiled_dimensions(bundle, ctx, [old, nozzle], [])
    result = {c.path: c.value for c in drawing}
    assert result["diameter"] == expected and result["nozzles.N1.diameter"] == 80
    assert ("height" in result) == (old_diameter == 2000)
