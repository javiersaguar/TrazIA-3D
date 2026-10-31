import pytest

from scripts.export_review_session import summarise


def test_no_human_sample_never_becomes_zero_or_uses_automated_session_times():
    metrics = {
        "dataset": "synthetic",
        "revision_id": "P:vessel-001:A",
        "equipment_tag": "V-101",
        "pending_fields": 1,
        "approved": False,
        "sessions": [{"id": "automated", "kind": "test", "finished_at": 1, "active_seconds": 50}],
    }
    fields = {"diameter": {"state": "candidate"}}
    result = summarise(
        metrics, [{"path": "diameter", "review_session_id": "automated", "seconds": 25}], fields
    )
    assert result["active_seconds"] is None
    assert result["action_seconds"] is None
    assert result["unassigned_active_seconds"] is None
    assert result["completed_human_sessions_with_actions"] == 0
    assert result["resolved_fields_with_actions"] == 0
    assert result["fields_total"] == 1
    assert result["field_times"] == []
    assert result["equipment_identity"] == "P:vessel-001"
    metrics["sessions"] = [{"id": "open", "kind": "human", "finished_at": None}]
    assert summarise(metrics, [], fields)["active_seconds"] is None
    metrics["dataset"] = "real"
    with pytest.raises(ValueError, match="sintético"):
        summarise(metrics, [], fields)
