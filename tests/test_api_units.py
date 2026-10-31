from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from trazia.api import create_app

ROOT = Path(__file__).resolve().parents[1]


def test_correction_converts_before_contract_and_ambiguous_input_is_atomic(tmp_path):
    with TestClient(create_app(root=ROOT, data_root=tmp_path)) as client:

        def patch(value, **options):
            revision = client.get("/equipment/V-101/revisions/A")
            return client.patch(
                "/revisions/A/fields/diameter",
                headers={"If-Match": revision.headers["etag"], "Idempotency-Key": uuid4().hex},
                json={"actor": "Ensayo sintético", "state": "corrected", "value": value, **options},
            )

        converted = patch(2.5, unit="m")
        assert converted.status_code == 200, converted.text
        field = converted.json()["equipment"]["diameter"]
        assert (field["value"], field["unit"]) == (2500, "mm")
        assert field["source"]["unit_original"] == "m"
        assert field["source"]["channel"] == "humano"
        before = client.get("/revisions/A/audit").json()
        rejected = patch("2.000", unit="mm")
        assert rejected.status_code == 422 and "ambiguo" in rejected.text
        assert client.get("/revisions/A/audit").json() == before
        assert patch("2.000", unit="mm", decimal_separator=",").status_code == 200
        assert patch(1, unit="kg").status_code == 422
