import importlib
from pathlib import Path

import pytest

from trazia.extraction import Candidate
from trazia.model import Source


@pytest.fixture
def quality(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    return importlib.import_module("cpu_quality")


def candidate(path, value, unit="mm"):
    return Candidate(
        path=path,
        value=value,
        unit=unit,
        source=Source(document_id="SYNTHETIC", page=1, locator="fixture", confidence=0.9),
        channel="ocr",
    )


def test_extra_nozzles_reduce_precision_and_missing_fields_reduce_recall(quality):
    result = quality.evaluate_prediction(
        None,
        [candidate("diameter", 1000), candidate("nozzles.FAKE.diameter", 200)],
        {"diameter": 1000, "height": 6000},
    )
    assert result["precision_returned_fields"] == 0.5
    assert result["recall_correct_fields"] == 0.5
    assert result["extra_nozzle_fields"] == ["nozzles.FAKE.diameter"]
    assert not result["all_geometry_correct"]


def test_angles_are_circular_but_unit_mismatch_is_not_a_hit(quality):
    truth = {"nozzles": [{"id": "N1", "azimuth": 0}], "diameter": 1000}
    result = quality.evaluate_prediction(
        None,
        [candidate("nozzles.N1.azimuth", 359.8, "deg"), candidate("diameter", 1000, "m")],
        truth,
    )
    assert result["correct_fields"] == 1


def test_mechanical_truth_evaluates_envelope_and_connection_coverage(quality):
    truth = {
        "tag": "P-1",
        "base_length": 2000,
        "base_width": 700,
        "shaft_height": 600,
        "motor_half": 200,
        "discharge_z": 900,
        "suction_dn": 80,
        "suction_x": 100,
        "discharge_dn": 50,
        "discharge_x": 500,
    }
    fields = quality.expected_fields(truth)
    assert fields["envelope.size.z"] == (900, "mm")
    assert fields["nozzles.S.z"] == (600, "mm")
    assert len(fields) == 12


def test_missing_instrumentation_does_not_become_zero_cost_or_seconds(quality):
    result = quality.evaluate_prediction(None, [], {"diameter": 1000})
    report = quality.summary([{"quality": result, "status": "error", "run": {}}])
    assert report["pipeline_seconds_sum"] is None and report["external_calls"] is None


def test_calibration_uses_fusion_input_confidence_instead_of_original_extractor(quality):
    field = candidate("diameter", 1000)
    field.confidence_raw = 0.85
    field.source.confidence_raw = 0.99
    field.source.confidence = 0.9975
    row = quality.evaluate_prediction(None, [field], {"diameter": 1000})["rows"][0]
    assert row["raw"] == 0.99 and row["extractor_raw"] == 0.85
    assert row["confidence"] == 0.9975
