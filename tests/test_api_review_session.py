from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from trazia.api import create_app
from trazia.model import Alternative, Interval, Revision
from trazia.store import ReviewSessionRecord

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(root=ROOT, data_root=tmp_path)) as client:
        yield client


def change(client, path, body):
    etag = client.get("/equipment/V-101/revisions/A").headers["etag"]
    return client.patch(
        f"/revisions/A/fields/{path}",
        json={"actor": "Prueba API", **body},
        headers={"If-Match": etag, "Idempotency-Key": uuid4().hex},
    )


def test_undo_restores_entire_field_and_is_audited_and_idempotent(client):
    from trazia.api.repository import get_revision

    with Session(client.app.state.store.engine) as session:
        record = get_revision(session, "A")
        model = Revision.model_validate_json(record.payload)
        field = model.equipment.diameter
        field.interval = Interval(low=1990, high=2010, level=0.9)
        field.alternatives = [Alternative(value=1999, unit="mm", source=field.source)]
        field.explanation = "Dos lecturas sintéticas que deben contrastarse"
        record.payload = model.model_dump_json()
        session.add(record)
        session.commit()
    original = client.get("/equipment/V-101/revisions/A").json()["equipment"]["diameter"]
    source = {
        **original["source"],
        "locator": "Otra región sintética",
        "bbox": [0.1, 0.1, 0.2, 0.2],
    }
    corrected = change(
        client,
        "diameter",
        {
            "state": "corrected",
            "value": 2100,
            "source": source,
            "explanation": "Corrección de prueba",
        },
    )
    assert corrected.status_code == 200, corrected.text
    audit_id = corrected.headers["x-audit-id"]
    url = f"/revisions/A/audit/{audit_id}/undo"
    headers = {"If-Match": corrected.headers["etag"], "Idempotency-Key": uuid4().hex}
    result = client.post(url, json={"actor": "Prueba API"}, headers=headers)
    assert result.status_code == 200, result.text
    assert result.json()["equipment"]["diameter"] == original
    replay = client.post(url, json={"actor": "Prueba API"}, headers=headers)
    assert replay.json() == result.json() and replay.headers["etag"] == result.headers["etag"]
    audits = client.get("/revisions/A/audit").json()["actions"]
    assert len(audits) == 2 and audits[-1]["undo_of"] == int(audit_id)
    assert client.get("/correcciones").json()["count"] == 2


def test_undo_does_not_overwrite_a_later_field_edit(client):
    first = change(client, "diameter", {"state": "corrected", "value": 2100})
    second = change(client, "diameter", {"state": "corrected", "value": 2200})
    response = client.post(
        f"/revisions/A/audit/{first.headers['x-audit-id']}/undo",
        json={"actor": "Prueba API"},
        headers={"If-Match": second.headers["etag"], "Idempotency-Key": uuid4().hex},
    )
    assert response.status_code == 409
    assert (
        client.get("/equipment/V-101/revisions/A").json()["equipment"]["diameter"]["value"] == 2200
    )


def test_expected_snapshot_prevents_accepting_an_unseen_value(client):
    original = client.get("/revisions/A/fields").json()["diameter"]
    assert change(client, "diameter", {"state": "corrected", "value": 2100}).status_code == 200
    response = change(client, "diameter", {"state": "accepted", "expected": original})
    assert response.status_code == 412
    assert client.get("/revisions/A/fields").json()["diameter"]["state"] == "corrected"


def test_reject_is_a_human_abstention_and_does_not_approve(client):
    result = change(client, "diameter", {"state": "abstained", "action": "reject"})
    assert result.status_code == 200, result.text
    field = result.json()["equipment"]["diameter"]
    assert field["state"] == "abstained" and not field["source"]["reviewed"]
    assert field["explanation"].startswith("Rechazado por el revisor")
    assert change(client, "diameter", {"state": "accepted", "action": "reject"}).status_code == 422
    assert (
        client.post(
            "/revisions/A/approve",
            json={"reviewer": "Prueba API"},
            headers={"If-Match": result.headers["etag"], "Idempotency-Key": uuid4().hex},
        ).status_code
        == 409
    )


def test_validation_is_actionable_and_rolls_back(client):
    response = change(client, "diameter", {"state": "corrected", "value": -1})
    assert response.status_code == 422
    assert response.json()["issues"][0]["action"]
    assert "No se ha guardado" in response.json()["detail"]
    assert client.get("/equipment/V-101/revisions/A").headers["etag"] == '"1"'
    bad_unit = change(client, "diameter", {"state": "corrected", "value": 2, "unit": "m"})
    assert bad_unit.status_code == 422 and "mm" in bad_unit.json()["detail"]
    fields = client.get("/revisions/A/fields").json()
    a, b = fields["nozzles.N1.elevation"], fields["nozzles.N1.azimuth"]
    assert (
        change(
            client, "nozzles.N2.elevation", {"state": "corrected", "value": a["value"]}
        ).status_code
        == 200
    )
    assert (
        change(
            client, "nozzles.N2.azimuth", {"state": "corrected", "value": b["value"]}
        ).status_code
        == 200
    )
    diagnostics = client.get("/revisions/A/validation").json()
    assert not diagnostics["normative_check"]
    assert any(i["code"] == "possible_overlap" for i in diagnostics["issues"])


def test_sessions_separate_test_runs_and_unknown_time_and_check_clock(client):
    before = client.get("/revisions/A/review-metrics").json()
    assert before["active_seconds"] is None and before["completed_human_sessions"] == 0
    headers = {"Idempotency-Key": uuid4().hex}
    body = {"revision_id": "A", "actor": "Prueba API", "kind": "test"}
    created = client.post("/review-sessions", json=body, headers=headers)
    assert created.status_code == 201, created.text
    identity = created.json()["id"]
    assert client.post("/review-sessions", json=body, headers=headers).json()["id"] == identity
    timed = {"state": "accepted", "review_session_id": identity, "seconds": 500}
    assert change(client, "diameter", timed).status_code == 422
    with Session(client.app.state.store.engine) as session:
        record = session.get(ReviewSessionRecord, identity)
        record.started_at -= 10  # Reloj simulado dentro de una BD temporal de prueba.
        session.add(record)
        session.commit()
    assert change(client, "diameter", {**timed, "seconds": 0.5}).status_code == 200
    assert (
        client.post(f"/review-sessions/{identity}/finish", json={"active_seconds": 0.2}).status_code
        == 422
    )
    finished = client.post(f"/review-sessions/{identity}/finish", json={"active_seconds": 1.0})
    assert finished.status_code == 200, finished.text
    assert finished.json()["id"] == identity
    assert finished.json()["active_seconds"] == 1
    assert finished.json()["finished_at"] is not None
    assert change(client, "height", {**timed, "seconds": 0.1}).status_code == 409
    metrics = client.get("/revisions/A/review-metrics").json()
    assert metrics["active_seconds"] is None and metrics["test_sessions"] == 1
    assert metrics["sessions"][0]["active_seconds"] == 1
    assert metrics["dataset"] == "synthetic" and not metrics["approved"]
