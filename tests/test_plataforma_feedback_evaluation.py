import importlib
from pathlib import Path

import pytest


@pytest.fixture
def evaluator(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    return importlib.import_module("evaluate_synthetic_feedback")


def test_paired_bootstrap_uses_equipment_not_fields_as_independent_units(evaluator):
    rows = [
        {
            "tag": tag,
            "degradation": style,
            "revision": rev,
            "quality": {"recall_correct_fields": 0.5},
        }
        for tag in ["A", "B"]
        for style in ["vector", "scan"]
        for rev in ["1", "2"]
    ]
    result = evaluator.paired_bootstrap(rows, rows)
    assert result["equipment"] == 2 and result["ci95"] == [0, 0]
    assert result["mean_delta"] == 0


def test_paired_comparison_cannot_hide_failed_or_missing_cases(evaluator):
    row = {
        "tag": "A",
        "degradation": "scan",
        "revision": "1",
        "quality": {"recall_correct_fields": 0.5},
    }
    with pytest.raises(ValueError, match="mismos casos"):
        evaluator.paired_bootstrap([row], [])


def test_missing_predictions_do_not_create_fake_calibration_labels(evaluator):
    report = {
        "rows": [
            {
                "tag": "A",
                "quality": {
                    "rows": [{"present": False, "raw": None}, {"present": True, "raw": None}]
                },
            }
        ]
    }
    assert evaluator.labels(report) == []
