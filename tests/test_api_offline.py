from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import trazia.api.app as api_module
from trazia.api import create_app
from trazia.copilot.models import Citation, CopilotAnswer, Statement
from trazia.model import RunInfo
from trazia.runtime import configure_offline
from trazia.vision import TASKS, OllamaProvider, ProviderResult, VisionUnavailable, cache

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAZIA_OFFLINE", "0")
    with TestClient(create_app(root=ROOT, data_root=tmp_path)) as value:
        yield value


def install_answer(monkeypatch):
    calls = []

    async def model(revision, question, **options):
        calls.append(question)
        doc = revision.documents[0]
        return CopilotAnswer(
            abstained=False,
            statements=[Statement(text="El valor candidato es 2000 mm.", citations=["c1"])],
            proposals=[],
            citations=[
                Citation(
                    id="c1",
                    kind="evidence",
                    title="GA sintético",
                    excerpt="2000 mm",
                    document_id=doc.id,
                    sha256=doc.sha256,
                    original_verified=True,
                )
            ],
            model="fixture-local",
            revision_id=options["revision_id"],
            revision_version=options["revision_version"],
            input_sha256=revision.fingerprint(),
            prompt_sha256="0" * 64,
            tools_used=["read_evidence"],
            run=RunInfo(strategy="fixture", providers=[], seconds=0, external_calls=0),
        )

    monkeypatch.setattr(api_module, "ask_copilot", model)
    return calls


def ask(client, question="diámetro"):
    return client.post("/copiloto", json={"question": question, "revision_id": "A"})


def test_offline_serves_cached_answer_without_call_and_refuses_miss(client, monkeypatch):
    calls = install_answer(monkeypatch)
    online = ask(client)
    assert online.status_code == 200 and not online.json()["cached"]
    monkeypatch.setenv("TRAZIA_OFFLINE", "1")
    offline = ask(client)
    assert offline.status_code == 200 and offline.json()["cached"]
    assert offline.json()["statements"] == online.json()["statements"]
    run = offline.json()["run"]
    assert run["gpu_seconds"] == 0 and run["tokens_in"] == 0 and run["external_calls"] == 0
    assert ask(client, "otra consulta").status_code == 503
    assert len(calls) == 1
    assert client.get("/health").json()["offline"]
    monkeypatch.setenv("TRAZIA_OLLAMA_MODEL", "otro-modelo")
    assert ask(client).status_code == 503
    assert len(calls) == 1


def test_cache_is_invalidated_by_revision_or_corrupt_original(client, monkeypatch):
    calls = install_answer(monkeypatch)
    answer = ask(client).json()
    digest = answer["citations"][0]["sha256"]
    store = client.app.state.store
    blob = store.blobs / digest[:2] / digest
    content = blob.read_bytes()
    blob.write_bytes(b"modified synthetic document")
    monkeypatch.setenv("TRAZIA_OFFLINE", "1")
    assert ask(client).status_code == 503
    blob.write_bytes(content)
    response = client.patch(
        "/revisions/A/fields/diameter",
        json={"value": 2100, "state": "corrected", "actor": "Javier"},
        headers={"If-Match": '"1"', "Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 200
    assert ask(client).status_code == 503 and len(calls) == 1


def test_global_offline_uses_existing_vision_cache_without_network(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAZIA_OFFLINE", "1")
    monkeypatch.setenv("TRAZIA_VISION_OFFLINE", "0")
    monkeypatch.setenv("TRAZIA_VISION_CACHE", str(tmp_path))
    configure_offline()
    provider = OllamaProvider()
    task = next(iter(TASKS))
    schema = {"type": "object"}
    key = cache.cache_key(
        b"synthetic-image", TASKS[task].prompt_sha256, schema, provider.cache_identity
    )
    cache.store(key, ProviderResult({}, provider.name, provider.model, TASKS[task].prompt_sha256))

    def forbidden(*_):
        raise AssertionError("No debe ejecutar inferencia ni red")

    monkeypatch.setattr(provider, "_call", forbidden)
    assert provider.read(b"synthetic-image", task, schema, page_ref="0" * 64).cached
    with pytest.raises(VisionUnavailable, match="caché"):
        provider.read(b"another-image", task, schema, page_ref="0" * 64)
