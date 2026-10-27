import json
import time
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from trazia.api import create_app
from trazia.model import Revision
from trazia.store import DocumentRecord

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def client(tmp_path):
    app = create_app(data_root=tmp_path, root=ROOT)
    with TestClient(app) as client:
        yield client


def headers(etag=None, key=None):
    result = {"Idempotency-Key": key or str(uuid4())}
    if etag:
        result["If-Match"] = etag
    return result


def wait_job(client, identity):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        result = client.get(f"/jobs/{identity}").json()
        if result["status"] in ("done", "error", "cancelled", "timeout"):
            return result
        time.sleep(0.02)
    raise AssertionError("El trabajo no terminó")


def job_body(client, **options):
    with Session(client.app.state.store.engine) as session:
        documents = session.exec(select(DocumentRecord).where(DocumentRecord.revision == "A")).all()
    return {"documents": [d.id for d in documents], "revision": "C", **options}


def test_seed_schema_and_cors(client):
    assert client.get("/health").json()["schema_version"] == "0.3"
    rows = client.get("/equipment").json()
    assert len(rows) == 1 and rows[0]["illustrative"] is False
    response = client.get("/equipment/V-101/revisions/A")
    assert response.headers["etag"] == '"1"'
    assert Revision.model_validate_json(response.text).schema_version == "0.3"
    allowed = client.options(
        "/documents",
        headers={"Origin": "http://localhost:3100", "Access-Control-Request-Method": "POST"},
    )
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3100"
    denied = client.options(
        "/documents",
        headers={"Origin": "https://untrusted.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in denied.headers


def test_upload_hash_dedupe_and_idempotency(client):
    key = str(uuid4())
    params = {
        "files": {"file": ("drawing.pdf", b"original")},
        "data": {"document_id": "GA-X"},
        "headers": headers(key=key),
    }
    first = client.post("/documents", **params)
    assert first.status_code == 201
    assert client.post("/documents", **params).json() == first.json()
    changed = client.post(
        "/documents", files={"file": ("drawing.pdf", b"changed")}, headers=headers(key=key)
    )
    assert changed.status_code == 409
    second = client.post(
        "/documents", files={"file": ("other.pdf", b"original")}, headers=headers()
    )
    assert second.json()["sha256"] == first.json()["sha256"]
    assert second.json()["id"] != first.json()["id"]
    assert client.app.state.store.read(first.json()["sha256"]) == b"original"


def test_upload_limits_and_missing_key(client):
    assert client.post("/documents", files={"file": ("file.pdf", b"x")}).status_code == 428
    assert (
        client.post("/documents", files={"file": ("file.exe", b"x")}, headers=headers()).status_code
        == 415
    )
    assert (
        client.post("/documents", files={"file": ("file.pdf", b"")}, headers=headers()).status_code
        == 413
    )


def test_concurrency_idempotency_and_audit(client):
    etag = client.get("/equipment/V-101/revisions/A").headers["etag"]
    body = {"state": "accepted", "actor": "Javier Saguar Antona", "seconds": 1.25}
    key = str(uuid4())
    url = "/revisions/A/fields/diameter"
    response = client.patch(url, json=body, headers=headers(etag, key))
    assert response.status_code == 200, response.text
    assert response.headers["etag"] == '"2"'
    assert response.json()["equipment"]["diameter"]["source"]["reviewed"] is True
    replay = client.patch(url, json=body, headers=headers(etag, key))
    assert replay.json() == response.json()
    assert replay.headers["etag"] == response.headers["etag"]
    assert client.patch(url, json=body, headers=headers(etag)).status_code == 412
    assert client.patch(url, json=body, headers=headers()).status_code == 428
    assert (
        client.patch(url, json={**body, "state": "assumed"}, headers=headers(etag, key)).status_code
        == 409
    )
    audit = client.get("/revisions/A/audit").json()
    assert len(audit["actions"]) == 1
    assert audit["review_seconds"] == 1.25 and audit["timed_actions"] == 1


def test_bad_edit_rolls_back(client):
    body = {"state": "corrected", "value": -2, "actor": "Javier"}
    assert (
        client.patch("/revisions/A/fields/diameter", json=body, headers=headers('"1"')).status_code
        == 422
    )
    response = client.get("/equipment/V-101/revisions/A")
    assert response.headers["etag"] == '"1"'
    assert response.json()["equipment"]["diameter"]["value"] == 2000
    assert not client.get("/revisions/A/audit").json()["actions"]


def test_approval_gate_and_invalidation(client):
    assert client.get("/revisions/A/ifc").status_code == 409
    assert client.get("/revisions/A/ifc?draft=true").status_code == 200
    assert (
        client.post(
            "/revisions/A/approve", json={"reviewer": "Javier"}, headers=headers('"1"')
        ).status_code
        == 409
    )
    paths = client.get("/revisions/A/fields").json()
    version = '"1"'
    for path in paths:
        response = client.patch(
            f"/revisions/A/fields/{path}",
            json={"state": "accepted", "actor": "Javier"},
            headers=headers(version),
        )
        assert response.status_code == 200, response.text
        version = response.headers["etag"]
    response = client.post(
        "/revisions/A/approve", json={"reviewer": "Javier"}, headers=headers(version)
    )
    assert response.status_code == 200, response.text
    approved = Revision.model_validate_json(response.text)
    assert approved.approval and not approved.pending_review()
    assert client.get("/revisions/A/ifc").status_code == 200
    response = client.patch(
        "/revisions/A/fields/diameter",
        json={"state": "corrected", "value": 2001, "actor": "Javier"},
        headers=headers(response.headers["etag"]),
    )
    assert response.status_code == 200, response.text
    assert response.json()["approval"] is None
    assert client.get("/revisions/A/ifc").status_code == 409


def test_persistence_survives_restart(tmp_path):
    with TestClient(create_app(data_root=tmp_path, root=ROOT)) as first:
        response = first.patch(
            "/revisions/A/fields/diameter",
            json={"state": "accepted", "actor": "Javier"},
            headers=headers('"1"'),
        )
        assert response.status_code == 200
    with TestClient(create_app(data_root=tmp_path, root=ROOT)) as second:
        response = second.get("/equipment/V-101/revisions/A")
        assert response.headers["etag"] == '"2"'
        assert response.json()["equipment"]["diameter"]["state"] == "accepted"


def test_job_pipeline_events_and_replay(client):
    key, body = str(uuid4()), job_body(client)
    response = client.post("/equipment/V-101/jobs", json=body, headers=headers(key=key))
    assert response.status_code == 202, response.text
    identity = response.json()["job_id"]
    assert (
        client.post("/equipment/V-101/jobs", json=body, headers=headers(key=key)).json()
        == response.json()
    )
    job = wait_job(client, identity)
    assert job["status"] == "done", job
    assert job["run"]["seconds"] > 0 and job["run"]["external_calls"] == 0
    assert job["run"]["gpu_seconds"] is None
    revision = client.get("/equipment/V-101/revisions/C").json()
    assert revision["approval"] is None and revision["schema_version"] == "0.3"
    events = client.get(f"/jobs/{identity}/events")
    assert "event: stage" in events.text and '"stage":"ifc"' in events.text
    assert "event: complete" in events.text
    ids = [int(line[4:]) for line in events.text.splitlines() if line.startswith("id: ")]
    replay = client.get(f"/jobs/{identity}/events", headers={"Last-Event-ID": str(ids[-1])})
    assert "event: stage" not in replay.text
    assert client.post("/equipment/V-101/jobs", json=body, headers=headers()).status_code == 409


def test_adapter_refuses_unimplemented_strategy(client):
    response = client.post(
        "/equipment/V-101/jobs", json=job_body(client, strategy="z_no_existe"), headers=headers()
    )
    job = wait_job(client, response.json()["job_id"])
    # Con el motor de Lectura una estrategia aún no implementada se rechaza por su nombre;
    # sin él, el adaptador temporal lo dice.
    assert job["status"] == "error"
    assert "Estrategia desconocida" in job["error"] or "temporal" in job["error"]
    assert client.get("/equipment/V-101/revisions/C").status_code == 404


def test_empty_study_and_actual_diff(client, tmp_path):
    # Los resultados locales no deben cambiar lo que comprueba el caso de estado vacío.
    with TestClient(create_app(root=tmp_path, data_root=tmp_path / "data", seed=False)) as isolated:
        assert isolated.get("/estudio").json()["status"] == "empty"
        report = tmp_path / "generated/estudio/estudio.json"
        report.parent.mkdir(parents=True)
        measured = {"synthetic": True, "variants": [{"id": "b_reglas", "measured": True}]}
        report.write_text(json.dumps(measured), encoding="utf8")
        assert isolated.get("/estudio").json() == measured
    assert client.get("/diff?from=A&to=B").json()["summary"]["changes"] == 8
    assert client.get("/plant").json()["layout"] is None
    assert client.post("/estudio", headers=headers()).status_code == 503


def test_blob_integrity_and_no_path_traversal(client):
    store = client.app.state.store
    with pytest.raises(ValueError, match="SHA"):
        store.read("../../secret")
    digest = store.put(b"synthetic integrity fixture")
    (store.blobs / digest[:2] / digest).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="coincide"):
        store.read(digest)
    with pytest.raises(ValueError, match="dañado"):
        store.put(b"synthetic integrity fixture")


def test_upload_limit_without_content_length(client):
    def chunks():
        yield (
            b'--x\r\nContent-Disposition: form-data; name="file"; filename="file.pdf"'
            b"\r\nContent-Type: application/pdf\r\n\r\n"
        )
        for _ in range(28):
            yield b"x" * (1024 * 1024)
        yield b"\r\n--x--\r\n"

    response = client.post(
        "/documents",
        content=chunks(),
        headers={**headers(), "Content-Type": "multipart/form-data; boundary=x"},
    )
    assert response.status_code == 413


@pytest.mark.parametrize("schema", ["IFC4", "IFC4X3", "IFC2X3"])
def test_api_downloads_valid_multischema_ifc(client, schema):
    import ifcopenshell

    from trazia.ifc import validate_ifc

    response = client.get(f"/revisions/A/ifc?draft=true&schema={schema}")
    assert response.status_code == 200
    model = ifcopenshell.file.from_string(response.text)
    assert model.schema == schema
    assert len(model.by_type("IfcDistributionPort")) == 3
    assert not validate_ifc(model)


def test_diff_serves_three_layers_bcf_and_aligned_page(client):
    import io
    import zipfile

    report = client.get("/diff?layers=true").json()
    assert report["summary"]["changes"] == 8
    assert report["layers"]["visual"]["status"] == "ok"
    assert report["layers"]["geometry"]["status"] == "ok"
    image = client.get("/diff/visual?document_id=GA-V101&page=1")
    assert image.status_code == 200 and image.content.startswith(b"\x89PNG")
    assert client.get("/diff/visual?document_id=unknown").status_code == 404
    assert client.get("/diff/visual?document_id=GA-V101&page=999").status_code == 422
    bcf = client.get("/diff/bcf")
    assert bcf.status_code == 200
    with zipfile.ZipFile(io.BytesIO(bcf.content)) as archive:
        assert len([n for n in archive.namelist() if n.endswith("markup.bcf")]) == 8
