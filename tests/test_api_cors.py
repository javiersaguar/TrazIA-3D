import pytest
from fastapi.testclient import TestClient

from trazia.api import create_app


def preflight(client, origin):
    return client.options(
        "/documents",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Idempotency-Key,If-Match",
        },
    )


def test_defaults_keep_existing_ports_and_reject_other_origins(tmp_path, monkeypatch):
    monkeypatch.delenv("TRAZIA_CORS_ORIGINS", raising=False)
    client = TestClient(create_app(root=tmp_path, data_root=tmp_path, seed=False))
    for port in (3000, 3100, 3200, 3300, 3310, 3311):
        origin = f"http://127.0.0.1:{port}"
        assert preflight(client, origin).headers["access-control-allow-origin"] == origin
    assert "access-control-allow-origin" not in preflight(client, "http://localhost:3120").headers


def test_configured_origins_replace_defaults_and_normalize_spaces(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "TRAZIA_CORS_ORIGINS",
        " http://localhost:3120/ , https://REVIEW.example:443, http://localhost:3120 ",
    )
    client = TestClient(create_app(root=tmp_path, data_root=tmp_path, seed=False))
    for origin in ("http://localhost:3120", "https://review.example"):
        assert preflight(client, origin).headers["access-control-allow-origin"] == origin
    assert "access-control-allow-origin" not in preflight(client, "http://localhost:3100").headers
    assert (
        "access-control-allow-origin" not in preflight(client, "https://elsewhere.example").headers
    )


@pytest.mark.parametrize(
    "value",
    [
        "*",
        "https://example.test/path",
        "http://user:pass@host",
        "file://host",
        "http://host:bad",
        ",,,",
    ],
)
def test_invalid_origins_fail_explicitly(tmp_path, monkeypatch, value):
    monkeypatch.setenv("TRAZIA_CORS_ORIGINS", value)
    with pytest.raises(ValueError, match="TRAZIA_CORS_ORIGINS"):
        create_app(root=tmp_path, data_root=tmp_path, seed=False)
