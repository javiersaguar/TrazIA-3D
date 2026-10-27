import asyncio
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

import trazia.api.app as api_module
from trazia.api import create_app
from trazia.copilot import CopilotUnavailable, ask
from trazia.copilot.tools import ReadTools, ToolViolation
from trazia.model import load_revision
from trazia.store import (
    AuditRecord,
    DocumentRecord,
    EventRecord,
    IdempotencyRecord,
    JobRecord,
    RevisionRecord,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(root=ROOT, data_root=tmp_path)) as value:
        yield value


def snapshot(client):
    with Session(client.app.state.store.engine) as session:
        return {
            table.__name__: sorted(
                row.model_dump_json() for row in session.exec(select(table)).all()
            )
            for table in (
                RevisionRecord,
                DocumentRecord,
                AuditRecord,
                JobRecord,
                EventRecord,
                IdempotencyRecord,
            )
        }


def ollama(mode="valid", requests=None):
    requests = requests if requests is not None else []

    final_calls = 0

    def handler(request):
        nonlocal final_calls
        requests.append(request)
        body = json.loads(request.content)
        if request.url.path == "/api/show":
            if mode == "unavailable":
                return httpx.Response(404, json={"error": "model missing"})
            info = {"details": {"format": "gguf"}, "capabilities": ["completion", "tools"]}
            if mode == "remote":
                info["remote_host"] = "https://example.invalid"
            return httpx.Response(200, json=info)
        if "format" not in body:
            if mode == "invalid_transport_json":
                return httpx.Response(200, text="broken-json")
            message = {"role": "assistant", "content": ""}
            if mode in ("native", "write"):
                message["tool_calls"] = [
                    {
                        "function": {
                            "name": "read_evidence" if mode == "native" else "approve_revision",
                            "arguments": {"path": "diameter"},
                        }
                    }
                ]
        else:
            final_calls += 1
            context = json.loads(body["messages"][1]["content"])
            citation = next(c for c in context["citations"] if c["kind"] == "evidence")
            result = {
                "answer": "El diámetro actual es 2000 mm.",
                "citations": [citation["id"]],
                "checks": [],
            }
            if mode in ("overconfident", "repaired") and (
                mode == "overconfident" or final_calls == 1
            ):
                result["answer"] = "El score indica certeza moderada."
            if mode == "contradicted_hash":
                result["answer"] = "No se ha verificado el original por SHA-256."
            if mode == "contradicted_hash_indirect":
                result["answer"] = (
                    "No hay evidencia de que el valor original esté verificado por SHA-256. "
                    "Su hash no ha sido verificado."
                )
            if mode == "claimed_write":
                result["answer"] = "He aprobado el diámetro."
            if mode == "invalid_citation":
                result["citations"] = ["evidence-inventada"]
            if mode == "no_citation":
                result["citations"] = []
            if mode == "abstain":
                result = {"answer": "", "citations": [], "checks": []}
            message = {
                "role": "assistant",
                "content": "invalid-json" if mode == "invalid_json" else json.dumps(result),
            }
        return httpx.Response(
            200, json={"message": message, "prompt_eval_count": 10, "eval_count": 5}
        )

    return httpx.MockTransport(handler)


def connect(monkeypatch, mode="valid", requests=None):
    async def fake(revision, question, **kwargs):
        return await ask(revision, question, transport=ollama(mode, requests), **kwargs)

    monkeypatch.setattr(api_module, "ask_copilot", fake)


def question(client):
    return client.post(
        "/copiloto",
        json={
            "question": "¿Cuál es el diámetro y su fuente?",
            "revision_id": "A",
            "path": "diameter",
        },
    )


def test_copilot_cites_verified_original_and_never_writes(client, monkeypatch):
    requests = []
    connect(monkeypatch, "native", requests)
    before = snapshot(client)
    result = question(client)
    assert result.status_code == 200, result.text
    data = result.json()
    assert data["read_only"] and not data["abstained"]
    assert data["revision_version"] == 1
    citation = data["citations"][0]
    assert citation["original_verified"] and citation["document_id"] == "GA-V101"
    assert citation["page"] == 1 and citation["bbox"]
    assert "2000" in citation["excerpt"]
    assert len(citation["sha256"]) == 64
    assert data["run"]["tokens_in"] == 20 and data["run"]["tokens_out"] == 10
    assert data["run"]["cost_eur"] == 0 and data["run"]["external_calls"] == 0
    assert snapshot(client) == before
    offered = json.loads(requests[1].content)["tools"]
    assert {t["function"]["name"] for t in offered} == {
        "read_fields",
        "read_evidence",
        "read_changes",
        "read_rules",
    }


@pytest.mark.parametrize(
    "mode",
    [
        "write",
        "invalid_citation",
        "no_citation",
        "invalid_json",
        "abstain",
        "overconfident",
        "contradicted_hash",
        "contradicted_hash_indirect",
        "claimed_write",
    ],
)
def test_invalid_or_unsupported_responses_abstain_without_effects(client, monkeypatch, mode):
    connect(monkeypatch, mode)
    before = snapshot(client)
    result = question(client)
    assert result.status_code == 200, result.text
    data = result.json()
    assert (
        data["abstained"]
        and not data["statements"]
        and not data["proposals"]
        and not data["citations"]
    )
    assert snapshot(client) == before


@pytest.mark.parametrize("mode", ["unavailable", "remote"])
def test_copilot_does_not_fall_back_or_send_to_remote_model(client, monkeypatch, mode):
    requests = []
    connect(monkeypatch, mode, requests)
    assert question(client).status_code == 503
    assert len(requests) == 1 and requests[0].url.path == "/api/show"


@pytest.mark.parametrize(
    "host,model",
    [
        ("https://example.invalid", "qwen3-vl:4b-instruct"),
        ("http://127.0.0.1:11434", "qwen3:235b-cloud"),
        ("http://user:pass@localhost:11434", "qwen3"),
    ],
)
def test_local_configuration_is_checked_before_reading_documents(host, model):
    revision = load_revision(ROOT / "examples/vessel_rev_a.json")
    reads = []
    with pytest.raises(CopilotUnavailable):
        asyncio.run(
            ask(
                revision,
                "Pregunta",
                revision_id="A",
                revision_version=1,
                read_document=lambda sha: reads.append(sha),
                host=host,
                model=model,
                transport=ollama(),
            )
        )
    assert not reads


def test_stale_copilot_answer_is_rejected(client, monkeypatch):
    async def modified(revision, question, **kwargs):
        result = await ask(revision, question, transport=ollama(), **kwargs)
        with Session(client.app.state.store.engine) as session:
            row = session.get(RevisionRecord, kwargs["revision_id"])
            row.version += 1
            session.add(row)
            session.commit()
        return result

    monkeypatch.setattr(api_module, "ask_copilot", modified)
    assert question(client).status_code == 409


def test_read_tools_cannot_read_arbitrary_paths_or_mutate():
    revision = load_revision(ROOT / "examples/vessel_rev_a.json")
    reads = []
    tools = ReadTools(revision, lambda sha: reads.append(sha))
    assert "error" in tools.call("read_evidence", {"path": "../../private"})
    with pytest.raises(ToolViolation):
        tools.call("approve_revision", {})
    with pytest.raises(ToolViolation):
        tools.call("read_fields", {"paths": ["diameter"], "url": "https://example.invalid"})
    assert not reads and revision.approval is None


def test_tool_evidence_checks_hash_and_reads_sheet_cell():
    revision = load_revision(ROOT / "examples/vessel_rev_a.json")
    bad = ReadTools(revision, lambda sha: b"corrupt")
    assert "error" in bad.read_evidence("diameter") and not bad.citations

    def missing(sha):
        raise FileNotFoundError(sha)

    absent = ReadTools(revision, missing)
    assert "no está disponible" in absent.read_evidence("diameter")["error"]
    assert not absent.citations

    def original(sha):
        document = next(d for d in revision.documents if d.sha256 == sha)
        return (ROOT / "examples/documents" / document.filename).read_bytes()

    tools = ReadTools(revision, original)
    result = tools.read_evidence("attributes.design_pressure")
    assert result["original_verified"] and result["sheet"] == "HDM" and result["cell"]
    assert tools.citations[result["citation_id"]].original_verified


def test_empty_question_and_unknown_field_do_not_call_model(client, monkeypatch):
    requests = []
    connect(monkeypatch, "valid", requests)
    assert client.post("/copiloto", json={"question": " ", "revision_id": "A"}).status_code == 422
    assert (
        client.post(
            "/copiloto", json={"question": "Pregunta", "revision_id": "A", "path": "missing"}
        ).status_code
        == 422
    )
    assert not requests


def test_change_tool_can_filter_a_field_without_changing_revisions():
    before = load_revision(ROOT / "examples/vessel_rev_a.json")
    after = load_revision(ROOT / "examples/vessel_rev_b.json")
    tools = ReadTools(after, lambda sha: b"unused", before)
    result = tools.call("read_changes", {"path": "nozzles.N3.elevation"})
    assert len(result["changes"]) == 1
    assert result["changes"][0]["before"]["value"] == 3500
    assert result["changes"][0]["after"]["value"] == 3700
    assert before.equipment.nozzles[2].elevation.value == 3500


def test_uncalibrated_certainty_is_reformulated_and_accounted(client, monkeypatch):
    requests = []
    connect(monkeypatch, "repaired", requests)
    result = question(client)
    assert result.status_code == 200, result.text
    data = result.json()
    assert not data["abstained"]
    assert "certeza moderada" not in data["statements"][0]["text"]
    assert data["run"]["tokens_in"] == 30 and data["run"]["tokens_out"] == 15
    assert len([r for r in requests if r.url.path == "/api/chat"]) == 3


def test_invalid_provider_json_does_not_report_zero_tokens_as_complete(client, monkeypatch):
    connect(monkeypatch, "invalid_transport_json")
    result = question(client)
    assert result.status_code == 200
    data = result.json()
    assert data["abstained"]
    assert data["run"]["tokens_in"] is None and data["run"]["tokens_out"] is None
    assert data["run"]["accounting_complete"] is False
