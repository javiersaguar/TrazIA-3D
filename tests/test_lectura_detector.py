"""Canal `detector` de D (tarea 2.4): lee la caché del detector propio y nunca inventa lecturas."""

import hashlib

from trazia.ingest import Bundle
from trazia.model import Document
from trazia.ocr.detector import detector_pdf_lines, page_key, store_page
from trazia.strategies import ABLATIONS
from trazia.strategies.base import StrategyContext
from trazia.strategies.d_hibrido import HybridStrategy

PDF = b"%PDF-1.4 escaneado de prueba"


def context(events):
    document = Document(
        id="GA-T1",
        filename="GAD_T1_rev1.pdf",
        revision="1",
        sha256=hashlib.sha256(PDF).hexdigest(),
        page_count=1,
    )
    return StrategyContext(
        bundles=[Bundle(document=document, media_type="pdf")],
        dataset="synthetic",
        previous=None,
        providers=[],
        emit=events.append,
        raw={"GA-T1": PDF},
        equipment_id="t1",
    )


def test_without_cache_the_channel_is_skipped(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAZIA_DETECTOR_CACHE", str(tmp_path))
    events = []
    out = HybridStrategy()._detector(context(events))
    assert out.candidates == []
    assert [(e.stage, e.status) for e in events] == [("extract_detector", "omitido")]


def test_cached_lines_become_detector_candidates(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAZIA_DETECTOR_CACHE", str(tmp_path))
    store_page(
        page_key(PDF, 1),
        [{"text": "HEIGHT: 8000 mm", "bbox": [0.1, 0.1, 0.3, 0.12], "score": 0.8}],
    )
    [line] = detector_pdf_lines(PDF, "GA-T1", 1)
    assert line.source.channel == "detector" and line.source.page == 1
    events = []
    out = HybridStrategy()._detector(context(events))
    assert out.candidates and all(c.channel == "detector" for c in out.candidates)
    assert events[-1].status == "ok"


def test_detector_ablation_exists():
    assert "d_hibrido-detector" in ABLATIONS
    assert "detector" not in ABLATIONS["d_hibrido-detector"]().channels


def test_fusion_cites_the_verifiable_reading_when_the_detector_agrees():
    from trazia.extraction import Candidate
    from trazia.model import Source
    from trazia.strategies.d_hibrido import fuse

    def reading(channel, conf, bbox):
        source = Source(document_id="GA", page=1, locator="t", bbox=bbox, confidence=conf)
        return Candidate(path="diameter", value=1200.0, unit="mm", source=source, channel=channel)

    [chosen], _ = fuse(
        [
            reading("ocr", 0.7, (0.1, 0.1, 0.2, 0.12)),
            reading("detector", 0.85, (0.5, 0.5, 0.6, 0.52)),
        ]
    )
    assert chosen.channel == "ocr" and chosen.source.confidence > 0.85
