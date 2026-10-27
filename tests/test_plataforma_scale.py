import json

import pytest

from scripts.measure_scale import summarise, tasks


def test_scale_report_preserves_failures_and_unknown_cost():
    rows = [
        {
            "dataset": "s-dev",
            "tag": "V-1",
            "degradation": "vectorial",
            "revision": "1",
            "status": "done",
            "seconds_turnaround": 2,
            "run": {"cost_eur": 0.1, "external_calls": 1, "accounting_complete": True},
        },
        {
            "dataset": "s-dev",
            "tag": "V-1",
            "degradation": "vectorial",
            "revision": "2",
            "status": "error",
            "seconds_turnaround": 4,
            "run": None,
        },
    ]
    result = summarise(rows, 10, 1)
    assert result["equipment"] == 1 and result["conditions"] == 1
    assert result["statuses"] == {"done": 1, "error": 1}
    assert result["cost_eur"] is None and result["jobs_without_cost"] == 1
    assert result["jobs_with_incomplete_accounting"] == 1
    projection = result["projection_400x4"]
    assert projection["measured"] is False
    assert projection["seconds_for_1600_terminal_jobs"] == 8000
    assert projection["seconds_for_1600_valid_ifc"] is None and projection["cost_eur"] is None
    assert result["per_equipment_condition"][0]["cost_eur"] is None


def test_scale_projection_is_separate_from_measured_batch():
    row = {
        "dataset": "s-dev",
        "tag": "V-1",
        "degradation": "vectorial",
        "revision": "1",
        "status": "done",
        "seconds_turnaround": 2,
        "run": {"cost_eur": 0.1, "external_calls": 1, "accounting_complete": True},
    }
    result = summarise([row], 10, 1)
    assert result["seconds_batch"] == 10 and result["cost_eur"] == 0.1
    assert result["projection_400x4"]["cost_eur"] == 160


def test_scale_only_accepts_synthetic_manifests_and_requires_originals(tmp_path):
    root = tmp_path / "s-dev"
    root.mkdir()
    manifest = {"synthetic": False, "cases": [], "styles": []}
    path = root / "manifest.json"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="sintéticos"):
        tasks(tmp_path, ["s-dev"])
    manifest.update(synthetic=True, cases=[{"tag": "V-1"}], styles=["vectorial"])
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Falta"):
        tasks(tmp_path, ["s-dev"])
