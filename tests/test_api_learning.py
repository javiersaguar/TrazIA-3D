from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from trazia.api import create_app

ROOT = Path(__file__).resolve().parents[1]


def test_only_current_approved_corrections_are_exported_and_invalidation_removes_them(tmp_path):
    with TestClient(create_app(root=ROOT, data_root=tmp_path)) as client:
        assert client.get("/learning/corrections").json()["examples"] == []
        version = '"1"'

        def patch(path, body):
            nonlocal version
            response = client.patch(
                f"/revisions/A/fields/{path}",
                json={"actor": "Javier", **body},
                headers={"If-Match": version, "Idempotency-Key": str(uuid4())},
            )
            assert response.status_code == 200, response.text
            version = response.headers["etag"]

        patch("diameter", {"state": "corrected", "value": 2100})
        assert client.get("/learning/corrections").json()["examples"] == []
        for path in client.get("/revisions/A/fields").json():
            if path != "diameter":
                patch(path, {"state": "accepted"})
        approved = client.post(
            "/revisions/A/approve",
            json={"reviewer": "Javier"},
            headers={"If-Match": version, "Idempotency-Key": str(uuid4())},
        )
        assert approved.status_code == 200, approved.text
        version = approved.headers["etag"]
        result = client.get("/learning/corrections").json()
        assert not result["recalibrated"] and len(result["examples"]) == 1
        example = result["examples"][0]
        assert example["prediction"]["value"] == 2000
        assert example["correction"]["value"] == 2100
        assert example["approval"]["input_sha256"] == approved.json()["approval"]["input_sha256"]
        assert example["document"]["sha256"]
        assert client.get("/learning/corrections?limit=0").status_code == 422
        # El cursor recorre auditoría, sin perder registros que aún no eran ejemplos.
        cursor, ids = 0, set()
        while True:
            page = client.get(f"/learning/corrections?after={cursor}&limit=2").json()
            ids.update(e["id"] for e in page["examples"])
            if page["next_cursor"] is None:
                break
            cursor = page["next_cursor"]
        assert ids == {example["id"]}
        patch("height", {"state": "corrected", "value": 6100})
        assert client.get("/learning/corrections").json()["examples"] == []
