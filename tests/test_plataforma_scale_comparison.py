import pytest

from scripts.compare_scale import by_equipment, compare


def report(status):
    return {
        "synthetic": True,
        "complete": True,
        "input_sha256": "a" * 64,
        "planned_revisions": 1,
        "rows": [
            {
                "dataset": "s-dev",
                "tag": "V-1",
                "degradation": "vectorial",
                "revision": "1",
                "status": status,
                "error": "falta evidencia" if status == "error" else None,
                "lod": 2 if status == "done" else None,
                "run": None,
                "seconds_turnaround": 3,
                "cache_hit": None,
            }
        ],
    }


def test_comparison_pairs_each_revision_and_rejects_incomparable_inputs():
    old, new = report("error"), report("done")
    result = compare(old, new)
    assert result["transitions"] == {"error -> done": 1}
    assert result["changes"][0]["tag"] == "V-1"
    assert not result["same_status_lod_error"]
    assert compare(new, new)["same_status_lod_error"]
    changed = report("done")
    changed["rows"][0]["inspection_error"] = "HTTP 500 al inspeccionar"
    assert not compare(new, changed)["same_status_lod_error"]
    new["input_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="No coincide"):
        compare(old, new)
    with pytest.raises(ValueError, match="incompletos"):
        compare(old, {**old, "complete": False})


def test_equipment_accounting_does_not_invent_unknown_times_or_costs():
    (equipment,) = by_equipment(report("error"))
    assert equipment["pipeline_seconds_sum"] is None
    assert equipment["job_elapsed_seconds_sum"] is None
    assert equipment["provider_cost_eur"] is None and equipment["cache_hits"] is None
    assert equipment["turnaround_seconds_sum"] == 3
