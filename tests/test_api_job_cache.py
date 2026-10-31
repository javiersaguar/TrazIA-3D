import time
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from trazia.api import create_app, jobs
from trazia.store import DocumentRecord, JobCacheRecord, JobRecord

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAZIA_OFFLINE", "0")
    with TestClient(create_app(root=ROOT, data_root=tmp_path)) as value:
        yield value


def body_for(client, revision="CACHE-WARM", **options):
    with Session(client.app.state.store.engine) as session:
        docs = session.exec(select(DocumentRecord).where(DocumentRecord.revision == "A")).all()
    return {"documents": [d.id for d in docs], "revision": revision, **options}


def submit(client, body, key=None):
    return client.post(
        "/equipment/V-101/jobs",
        json=body,
        headers={"Idempotency-Key": key or str(uuid4())},
    )


def finished(client, response):
    assert response.status_code == 202, response.text
    identity = response.json()["job_id"]
    until = time.monotonic() + 30
    while time.monotonic() < until:
        result = client.get(f"/jobs/{identity}").json()
        if result["status"] in jobs.TERMINAL:
            return result
        time.sleep(0.01)
    raise AssertionError("El trabajo no termina")


def test_offline_hit_rebinds_draft_without_pipeline_and_survives_restart(client, monkeypatch):
    warm = finished(client, submit(client, body_for(client)))
    assert warm["status"] == "done" and not warm["cache_hit"]
    with Session(client.app.state.store.engine) as session:
        assert len(session.exec(select(JobCacheRecord)).all()) == 1

    def forbidden(*_):
        raise AssertionError("El pipeline no se puede ejecutar en modo offline")

    monkeypatch.setattr(jobs, "execute_pipeline", forbidden)
    monkeypatch.setenv("TRAZIA_OFFLINE", "1")
    monkeypatch.setenv("TRAZIA_VISION_OFFLINE", "1")
    body = body_for(
        client, "CACHE-OFFLINE", project_id="CACHE-PROJECT", equipment_id="cache-vessel"
    )
    key = str(uuid4())
    first = submit(client, body, key)
    assert submit(client, body, key).json() == first.json()
    result = finished(client, first)
    assert result["status"] == "done" and result["cache_hit"]
    revision = client.get(
        "/equipment/V-101/revisions/CACHE-OFFLINE?project_id=CACHE-PROJECT"
    ).json()
    assert revision["project_id"] == "CACHE-PROJECT"
    assert revision["equipment"]["id"] == "cache-vessel" and revision["approval"] is None
    assert revision["equipment"]["diameter"]["value"] == 2000
    assert result["run"]["external_calls"] == 0 and result["run"]["tokens_in"] == 0
    assert result["run"]["gpu_seconds"] == 0 and result["run"]["cost_eur"] == 0
    assert "pipeline no ejecutado" in client.get(f"/jobs/{result['id']}/events").text
    with TestClient(create_app(root=ROOT, data_root=client.app.state.store.root)) as other:
        response = submit(other, body_for(other, "CACHE-RESTART"))
        assert finished(other, response)["cache_hit"]


def test_offline_miss_is_explicit_and_does_not_enqueue(client, monkeypatch):
    monkeypatch.setenv("TRAZIA_OFFLINE", "1")
    response = submit(client, body_for(client))
    assert response.status_code == 409 and "Modo offline" in response.json()["detail"]
    with Session(client.app.state.store.engine) as session:
        assert not session.exec(select(JobRecord)).all()


def test_recalibration_invalidates_cached_results(client, monkeypatch, tmp_path):
    from trazia.calibration import Calibration

    monkeypatch.setenv("TRAZIA_CALIBRATION", "off")
    assert finished(client, submit(client, body_for(client)))["status"] == "done"
    path = tmp_path / "calibration.json"
    import json

    path.write_text(json.dumps(Calibration({}, {}, {}).to_dict()), encoding="utf-8")
    monkeypatch.setenv("TRAZIA_CALIBRATION", str(path))
    monkeypatch.setenv("TRAZIA_OFFLINE", "1")
    response = submit(client, body_for(client, "RECALIBRATED"))
    assert response.status_code == 409


def test_key_distinguishes_documents_strategy_and_providers(client, monkeypatch):
    assert finished(client, submit(client, body_for(client)))["status"] == "done"
    monkeypatch.setenv("TRAZIA_OFFLINE", "1")
    for options in ({"strategy": "d_hibrido"}, {"providers": ["ollama:no-ejecutar"]}):
        response = submit(client, body_for(client, "OTHER", **options))
        assert response.status_code == 409
    with Session(client.app.state.store.engine) as session:
        changed = session.exec(select(DocumentRecord).where(DocumentRecord.revision == "A")).first()
        changed.sha256 = client.app.state.store.put(b"different synthetic bytes")
        session.add(changed)
        session.commit()
    assert submit(client, body_for(client, "CHANGED")).status_code == 409


def test_corrupt_cache_is_not_served_and_failed_work_is_not_cached(client, monkeypatch):
    original = jobs.execute_pipeline

    def fail(*_):
        raise ValueError("entrada incompatible")

    monkeypatch.setattr(jobs, "execute_pipeline", fail)
    assert finished(client, submit(client, body_for(client, "ERROR")))["status"] == "error"
    with Session(client.app.state.store.engine) as session:
        assert not session.exec(select(JobCacheRecord)).all()
    monkeypatch.setattr(jobs, "execute_pipeline", original)
    assert finished(client, submit(client, body_for(client)))["status"] == "done"
    with Session(client.app.state.store.engine) as session:
        cached = session.exec(select(JobCacheRecord)).first()
    store = client.app.state.store
    (store.blobs / cached.result_sha256[:2] / cached.result_sha256).write_bytes(b"broken")
    monkeypatch.setenv("TRAZIA_OFFLINE", "1")
    response = submit(client, body_for(client, "INVALID"))
    assert response.status_code == 409 and "verificar" in response.json()["detail"]
