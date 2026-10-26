"""Bench y generador sintético: la cadena completa con verdad conocida."""

import json
import random

import pytest

from bench.metrics import angle_error, box_iou, ece, prf
from bench.report import summarize, to_markdown
from bench.runner import run_bench
from synthetic.cases import expected_changes, flatten, mutate, random_case, spec_to_revision
from synthetic.generate import generate


def test_random_cases_are_valid_for_the_core_contract():
    rng = random.Random(11)
    for i in range(25):
        spec = random_case(rng, i)
        assert spec.valid()
        revision = spec_to_revision(spec, "1")
        assert revision.equipment.tag.value == spec.tag
        assert len(revision.equipment.nozzles) == len(spec.nozzles) >= 3


def test_mutations_are_known_and_valid():
    rng = random.Random(3)
    for i in range(25):
        before = random_case(rng, i)
        after = mutate(rng, before)
        changes = expected_changes(before, after)
        assert after.valid()
        assert 1 <= len(changes)
        assert {c["path"] for c in changes} <= flatten(before).keys() | flatten(after).keys()


def test_metrics_basics():
    assert angle_error(350, 10) == 20
    assert prf(3, 1, 0)["precision"] == 0.75
    assert ece([(0.75, True)] * 4) == pytest.approx(0.25)
    assert ece([(0.8, True)] * 8 + [(0.8, False)] * 2) == pytest.approx(0.0)
    assert box_iou(((0, 0, 0), (1, 1, 1)), ((0, 0, 0), (1, 1, 1))) == pytest.approx(1.0)
    assert box_iou(((0, 0, 0), (1, 1, 1)), ((2, 2, 2), (3, 3, 3))) == 0.0


@pytest.fixture(scope="module")
def bench_summary(tmp_path_factory):
    dataset = tmp_path_factory.mktemp("synthetic")
    generate(dataset, cases=2, seed=5)
    return summarize(run_bench(dataset))


def test_labelled_style_is_read_exactly(bench_summary):
    s = bench_summary["styles"]["rotulado"]
    assert s["models_built"] == s["revisions"] == 4
    assert s["geometry"]["field_accuracy"] == 1.0
    assert s["geometry"]["nozzle_position_mae_mm"] == pytest.approx(0.0)
    assert s["geometry"]["ifc_mean_iou"] == pytest.approx(1.0)
    assert s["attributes"]["accuracy_value_unit"] == 1.0
    assert s["delta"]["f1"] == 1.0


def test_drawn_and_scanned_styles_show_the_gap_honestly(bench_summary):
    for style in ("plano", "escaneado"):
        s = bench_summary["styles"][style]
        assert s["models_built"] == 0
        assert s["geometry"]["field_coverage"] == 0.0
        assert s["delta"]["evaluable_equipment"] == 0
        assert s["scale"]["seconds_per_revision"] is None


def test_report_is_written_in_spanish_and_labels_synthetic(bench_summary):
    text = to_markdown(bench_summary)
    assert "Datos sintéticos" in text
    assert "Fidelidad geométrica · 35 %" in text
    json.dumps(bench_summary)


@pytest.fixture(scope="module")
def combined_summary(tmp_path_factory):
    dataset = tmp_path_factory.mktemp("synthetic-combined")
    generate(dataset, cases=3, seed=21, styles=("plano",))
    return summarize(run_bench(dataset, "combinado"))


def test_drawing_extractor_reads_drawn_ga(combined_summary):
    s = combined_summary["styles"]["plano"]
    assert s["models_built"] == s["revisions"] == 6
    assert s["geometry"]["field_accuracy"] == 1.0
    assert s["geometry"]["ifc_mean_iou"] == pytest.approx(1.0)
    assert s["delta"]["f1"] == 1.0


def test_vertical_dimensions_are_checked_by_the_chain():
    from trazia.extractors.drawing import DrawingExtractor
    from trazia.ingest import Bundle, EvidenceLine
    from trazia.model import Document, Source

    def line(text, bbox):
        source = Source(document_id="GA", page=1, locator="t", bbox=bbox, confidence=0.75)
        return EvidenceLine(text=text, source=source)

    doc = Document(id="GA", filename="ga.pdf", revision="1", sha256="0" * 64, page_count=1)
    lines = [
        line("T.L.", (0.32, 0.18, 0.33, 0.19)),
        line("T.L.", (0.32, 0.70, 0.33, 0.71)),
        line("05611", (0.05, 0.50, 0.06, 0.53)),  # 11650 al revés: total
        line("0078", (0.08, 0.43, 0.09, 0.46)),  # 8700: virola
        line("0562", (0.08, 0.77, 0.09, 0.80)),  # 2650: faldón
        line("003", (0.11, 0.16, 0.12, 0.18)),  # 300: fondo
    ]
    bundle = Bundle(document=doc, media_type="pdf", lines=lines)
    found = {c.path: c for c in DrawingExtractor().extract([bundle])}
    assert found["height"].value == 8700
    assert found["skirt_height"].value == 2650
    assert found["head_depth"].value == 300
    assert found["height"].source.confidence == 0.95
