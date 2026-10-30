import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from trazia.api import corrections, create_app
from trazia.api.repository import get_revision
from trazia.model import Interval, Revision

ROOT = Path(__file__).resolve().parents[1]
KEYS = {
    "revision_id",
    "equipment_tag",
    "revision",
    "path",
    "value_before",
    "value_after",
    "unit",
    "state_before",
    "state_after",
    "confidence",
    "confidence_raw",
    "channel",
    "strategy",
    "document_id",
    "page",
    "bbox",
    "actor",
    "at",
    "data_sha256",
}


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(root=ROOT, data_root=tmp_path)) as value:
        yield value


def patch(client, body, *, identity="A", etag='"1"', key=None):
    return client.patch(
        f"/revisions/{identity}/fields/diameter",
        json={"actor": "Javier", **body},
        headers={"If-Match": etag, "Idempotency-Key": key or str(uuid4())},
    )


def lines(client):
    path = client.app.state.corrections_file
    return (
        [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        if path.exists()
        else []
    )


@pytest.mark.parametrize("calibrated", [False, True])
def test_correction_preserves_prediction_metadata_with_or_without_calibration(client, calibrated):
    with Session(client.app.state.store.engine) as session:
        record = get_revision(session, "A")
        model = Revision.model_validate_json(record.payload)
        if calibrated:
            model.equipment.diameter.source = model.equipment.diameter.source.model_copy(
                update={
                    "confidence": 0.93,
                    "confidence_raw": 0.61,
                    "channel": "tabla",
                    "strategy": "b_reglas",
                }
            )
            model.equipment.diameter.interval = Interval(low=1999, high=2001, level=0.9)
            record.payload = model.model_dump_json()
            session.add(record)
            session.commit()
        before = model.equipment.diameter
    key = str(uuid4())
    body = {"state": "corrected", "value": 2100}
    response = patch(client, body, key=key)
    assert response.status_code == 200, response.text
    assert patch(client, body, key=key).json() == response.json()
    [row] = lines(client)
    assert set(row) == KEYS
    assert row["value_before"] == before.value and row["value_after"] == 2100
    assert row["confidence"] == before.source.confidence
    assert row["confidence_raw"] == before.source.confidence_raw
    assert row["channel"] == before.source.channel and row["strategy"] == before.source.strategy
    assert row["bbox"] == (list(before.source.bbox) if before.source.bbox else None)
    assert row["actor"] == "Javier" and row["state_before"] == before.state
    assert row["state_after"] == "corrected" and row["revision"] == "A"
    assert row["data_sha256"] == Revision.model_validate_json(response.text).fingerprint()
    assert datetime.fromisoformat(row["at"]).utcoffset() == timedelta(0)
    assert client.get("/correcciones").json()["correcciones"] == [row]


def test_state_change_is_logged_but_noop_or_rejected_edit_is_not(client):
    before = client.get("/equipment/V-101/revisions/A").json()["equipment"]["diameter"]
    noop = patch(client, {"state": before["state"]})
    assert noop.status_code == 200 and lines(client) == []
    accepted = patch(client, {"state": "accepted"}, etag=noop.headers["etag"])
    assert accepted.status_code == 200
    assert len(lines(client)) == 1
    assert lines(client)[0]["value_before"] == lines(client)[0]["value_after"]
    rejected = patch(client, {"state": "corrected", "value": 2200})
    assert rejected.status_code == 412 and len(lines(client)) == 1


def test_export_recovers_a_crash_after_write_without_duplicate_on_retry(client, monkeypatch):
    original = corrections.append_records
    calls = []

    def crash(*args):
        offset = original(*args)
        calls.append(1)
        if len(calls) == 1:
            raise OSError("fallo simulado tras escribir el archivo")
        return offset

    monkeypatch.setattr(corrections, "append_records", crash)
    key = str(uuid4())
    body = {"state": "corrected", "value": 2100}
    failed = patch(client, body, key=key)
    assert failed.status_code == 503 and "guardado" in failed.json()["detail"]
    assert (
        client.get("/equipment/V-101/revisions/A").json()["equipment"]["diameter"]["value"] == 2100
    )
    assert len(client.get("/correcciones").json()["correcciones"]) == 1
    recovered = patch(client, body, key=key)
    assert recovered.status_code == 200 and len(lines(client)) == 1
    assert len(client.get("/revisions/A/audit").json()["actions"]) == 1


def test_concurrent_edits_since_filter_and_file_recovery(client):
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda identity: patch(client, {"state": "accepted"}, identity=identity), ["A", "B"]
            )
        )
    assert all(result.status_code == 200 for result in results)
    rows = client.get("/correcciones").json()["correcciones"]
    assert len(rows) == 2 and len(lines(client)) == 2
    stamp = quote(rows[0]["at"], safe="")
    assert client.get(f"/correcciones?desde={stamp}").json()["correcciones"] == rows
    future = quote((datetime.now(timezone.utc) + timedelta(days=1)).isoformat(), safe="")
    assert client.get(f"/correcciones?desde={future}").json()["correcciones"] == []
    assert client.get("/correcciones?desde=sin-fecha").status_code == 422
    assert client.get("/correcciones?desde=2026-10-30T12:00:00").status_code == 422
    client.app.state.corrections_file.write_bytes(b"")
    corrections.flush(client.app.state.store, client.app.state.corrections_file)
    assert len(lines(client)) == 2
