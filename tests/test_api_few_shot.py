from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from trazia.api import create_app
from trazia.copilot.cache import key_for
from trazia.model import load_revision

ROOT = Path(__file__).resolve().parents[1]


def test_few_shot_needs_approval_has_original_and_excludes_target_and_revocation(tmp_path):
    with TestClient(create_app(root=ROOT, data_root=tmp_path)) as client:

        def patch(path, body):
            etag = client.get("/equipment/V-101/revisions/A").headers["etag"]
            result = client.patch(
                f"/revisions/A/fields/{path}",
                json={"actor": "Prueba sintética API", **body},
                headers={"If-Match": etag, "Idempotency-Key": uuid4().hex},
            )
            assert result.status_code == 200, result.text
            return result.headers["etag"]

        assert client.get("/learning/few-shot").json()["examples"] == []
        patch("diameter", {"state": "corrected", "value": 2100})
        assert client.get("/learning/few-shot").json()["examples"] == []
        for path in client.get("/revisions/A/fields").json():
            if path != "diameter":
                etag = patch(path, {"state": "accepted"})
        approved = client.post(
            "/revisions/A/approve",
            json={"reviewer": "Prueba sintética API"},
            headers={"If-Match": etag, "Idempotency-Key": uuid4().hex},
        )
        assert approved.status_code == 200
        result = client.get("/learning/few-shot?path=diameter").json()
        assert result["dataset"] == "synthetic" and not result["applied_to_extraction"]
        (example,) = result["examples"]
        assert example["approval_sha256"] == approved.json()["approval"]["input_sha256"]
        assert [m["role"] for m in example["messages"]] == ["user", "assistant"]
        evidence = client.get(example["evidence_url"])
        assert evidence.status_code == 200 and evidence.content.startswith(b"\x89PNG")
        assert client.get("/learning/few-shot?target_revision_id=B").json()["examples"] == []
        assert client.get("/learning/few-shot?path=height").json()["examples"] == []
        assert client.get("/learning/few-shot?strategy=otra").json()["examples"] == []
        patch("height", {"state": "corrected", "value": 6100})
        withdrawn = client.get("/learning/few-shot").json()
        assert withdrawn["examples"] == [] and withdrawn["sha256"] != result["sha256"]
        assert client.get(example["evidence_url"]).status_code == 404


def test_copilot_cache_changes_when_approved_examples_change():
    revision = load_revision(ROOT / "examples/vessel_rev_a.json")
    options = {"revision_id": "A", "revision_version": 1, "examples": {"sha256": "a"}}
    before = key_for(revision, "Explica la evidencia", options)
    options["examples"] = {"sha256": "b"}
    assert key_for(revision, "Explica la evidencia", options) != before
