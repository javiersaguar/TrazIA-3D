import asyncio
import json
import sys
import time
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from synthetic.sets import generate_set
from trazia.api import create_app, jobs, study_jobs
from trazia.store import JobRecord

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def synthetic_data(tmp_path_factory):
    root = tmp_path_factory.mktemp("api-study-input")
    generate_set("s-dev", root, cases=1, degradations=("vectorial",))
    return root


@pytest.fixture
def client(tmp_path, synthetic_data, monkeypatch):
    monkeypatch.setenv("TRAZIA_STUDY_DATA", str(synthetic_data))
    with TestClient(create_app(root=ROOT, data_root=tmp_path, seed=False)) as value:
        yield value


def submit(client, key=None, **overrides):
    return client.post(
        "/estudio",
        json={"casos": 1, "remuestreos": 20, "degradaciones": ["vectorial"], **overrides},
        headers={"Idempotency-Key": key or str(uuid4())},
    )


def finished(client, identity):
    until = time.monotonic() + 45
    while time.monotonic() < until:
        result = client.get(f"/jobs/{identity}").json()
        if result["status"] in jobs.TERMINAL:
            return result
        time.sleep(0.02)
    raise AssertionError("El estudio no termina")


def test_real_study_persists_result_idempotency_and_sse(client):
    key = str(uuid4())
    response = submit(client, key)
    assert response.status_code == 202, response.text
    identity = response.json()["job_id"]
    assert submit(client, key).json()["job_id"] == identity
    assert submit(client, key, semilla=7).status_code == 409
    result = finished(client, identity)
    assert result["status"] == "done", result
    assert result["kind"] == "study" and result["elapsed_seconds"] > 0
    assert result["run"] is None  # no se inventa contabilidad agregada
    study = client.get(f"/estudio?job_id={identity}").json()
    assert study["variants"][0]["id"] == "b_reglas"
    assert "ci95" in study["variants"][0]
    assert client.get("/estudio").json() == study
    events = client.get(f"/jobs/{identity}/events").text
    assert "Inicia el estudio" in events and "Estudio publicado" in events
    assert '"status": "done"' in events
    with Session(client.app.state.store.engine) as session:
        assert len(session.exec(select(JobRecord)).all()) == 1
    # Nueva aplicación/cola, misma base: el resultado no depende de memoria del proceso.
    with TestClient(
        create_app(root=ROOT, data_root=client.app.state.store.root, seed=False)
    ) as other:
        assert other.get(f"/estudio?job_id={identity}").json() == study


async def slow_process(_config, _output):
    return await asyncio.create_subprocess_exec(
        sys.executable,
        "-u",
        "-c",
        "import time;print('esperando',flush=True);time.sleep(60)",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )


def test_timeout_kills_subprocess_and_does_not_publish(client, monkeypatch):
    monkeypatch.setattr(study_jobs, "start_study", slow_process)
    identity = submit(client, timeout_seconds=0.2).json()["job_id"]
    result = finished(client, identity)
    assert result["status"] == "timeout" and result["result_sha256"] is None
    assert client.get(f"/estudio?job_id={identity}").status_code == 202
    assert not list(client.app.state.store.root.glob("study-*"))


def test_cancel_and_active_lease_prevent_publication_and_duplicates(client, monkeypatch):
    monkeypatch.setattr(study_jobs, "start_study", slow_process)
    identity = submit(client).json()["job_id"]
    until = time.monotonic() + 5
    while client.get(f"/jobs/{identity}").json()["status"] == "queued":
        assert time.monotonic() < until
        time.sleep(0.01)
    delay = asyncio.run(jobs.run_job(client.app.state.store, identity))
    assert delay > 0
    assert client.get(f"/jobs/{identity}").json()["attempts"] == 1
    response = client.post(f"/jobs/{identity}/cancel", headers={"Idempotency-Key": str(uuid4())})
    assert response.json()["status"] == "cancelled"
    assert finished(client, identity)["result_sha256"] is None
    assert not list(client.app.state.store.root.glob("study-*"))


def test_input_rejection_and_failure_are_explicit(client, synthetic_data, monkeypatch):
    assert client.post("/estudio", json={}).status_code == 428
    assert submit(client, conjuntos=["../../data"]).status_code == 422
    assert submit(client, conjuntos=["s-reservado"]).status_code == 422
    identity = submit(client, variantes=["no_existe"]).json()["job_id"]
    result = finished(client, identity)
    assert result["status"] == "error" and "variantes medidas" in result["error"]
    assert result["result_sha256"] is None
    assert client.get("/estudio?job_id=no-existe").status_code == 404
    root = client.app.state.store.root / "non-synthetic"
    (root / "s-dev").mkdir(parents=True)
    (root / "s-dev/manifest.json").write_text(json.dumps({"synthetic": False}))
    monkeypatch.setenv("TRAZIA_STUDY_DATA", str(root))
    assert submit(client).status_code == 422


def test_study_uses_stable_cli_arguments_without_shell(tmp_path, monkeypatch):
    config = {
        "datos": str(tmp_path / "datos con espacios"),
        "conjuntos": ["s-dev"],
        "variantes": ["b_reglas"],
        "remuestreos": 20,
        "semilla": 2026,
        "casos": 1,
        "degradaciones": ["vectorial"],
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    calls = []

    async def spawn(*args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setattr(study_jobs.asyncio, "create_subprocess_exec", spawn)
    asyncio.run(study_jobs.start_study(path, tmp_path / "estudio.json"))
    command, options = calls[0]
    assert command[:4] == (sys.executable, "-u", "-m", "bench.estudio")
    assert command[command.index("--datos") + 1] == config["datos"]
    for name, value in (("casos", "1"), ("remuestreos", "20"), ("semilla", "2026")):
        assert command[command.index("--" + name) + 1] == value
    assert command[command.index("--salida") + 1] == str(tmp_path)
    assert not options.get("shell")


def test_success_without_report_is_an_explicit_error(client, monkeypatch):
    async def empty_process(_config, _output):
        return await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            "print('sin resultados')",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

    monkeypatch.setattr(study_jobs, "start_study", empty_process)
    identity = submit(client).json()["job_id"]
    result = finished(client, identity)
    assert result["status"] == "error" and "sin producir estudio.json" in result["error"]
    assert client.get("/estudio").json()["status"] == "empty"
