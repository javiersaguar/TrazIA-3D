from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from trazia.api import create_app


def test_marks_only_endpoint_is_readonly_and_does_not_render_or_build_ifc(tmp_path, monkeypatch):
    import trazia.revisions as revisions

    def unexpected(*args, **kwargs):
        raise AssertionError("Las marcas vectoriales no necesitan ECC ni generar un IFC")

    monkeypatch.setattr(revisions, "visual_delta", unexpected)
    monkeypatch.setattr(revisions, "geometry_delta", unexpected)
    app = create_app(data_root=tmp_path, root=Path(__file__).resolve().parents[1])
    with TestClient(app) as client:
        before = client.get("/equipment/V-101/revisions/B")
        pdf = next(
            d["sha256"] for d in before.json()["documents"] if d["filename"].endswith(".pdf")
        )
        read = app.state.store.read

        def pdf_only(digest):
            assert digest == pdf, "El modo ligero no necesita abrir hojas de datos"
            return read(digest)

        monkeypatch.setattr(app.state.store, "read", pdf_only)
        response = client.get("/diff?from=A&to=B&marks=true")
        assert response.status_code == 200
        data = response.json()
        assert data["layers"]["visual"]["status"] == "not_requested"
        assert data["layers"]["geometry"]["status"] == "not_requested"
        assert data["layers"]["revision_marks"]["documents"]
        after = client.get("/equipment/V-101/revisions/B")
        assert after.json() == before.json() and after.headers["etag"] == before.headers["etag"]


@pytest.mark.parametrize(
    "failure", [FileNotFoundError("original ausente"), ValueError("SHA erróneo")]
)
def test_marks_unavailable_original_is_explicit_not_a_server_error(tmp_path, monkeypatch, failure):
    app = create_app(data_root=tmp_path, root=Path(__file__).resolve().parents[1])
    with TestClient(app) as client:

        def unavailable(_):
            raise failure

        monkeypatch.setattr(app.state.store, "read", unavailable)
        response = client.get("/diff?from=A&to=B&marks=true")
        assert response.status_code == 200
        report = response.json()["layers"]["revision_marks"]
        assert report["status"] == "unavailable"
        assert report["documents"][0]["status"] == "missing_original"
        assert not report["unmarked_changes"] and not report["marks_without_change"]
