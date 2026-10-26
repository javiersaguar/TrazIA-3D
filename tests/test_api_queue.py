import asyncio
import threading
import time
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from trazia.api import create_app, jobs
from trazia.model import RunInfo
from trazia.queue import ProcessQueue
from trazia.queue.accounting import Accounting
from trazia.queue.redis import RedisQueue
from trazia.store import DocumentRecord, JobRecord


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(data_root=tmp_path, root=Path(__file__).resolve().parents[1])) as c:
        yield c


def submit(client, **options):
    with Session(client.app.state.store.engine) as session:
        docs = session.exec(select(DocumentRecord).where(DocumentRecord.revision == "A")).all()
    body = {
        "documents": [d.id for d in docs],
        "revision": "C",
        "retry_backoff_seconds": 0,
        **options,
    }
    response = client.post(
        "/equipment/V-101/jobs", json=body, headers={"Idempotency-Key": str(uuid4())}
    )
    assert response.status_code == 202, response.text
    return response.json()["job_id"]


def finished(client, identity):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        data = client.get(f"/jobs/{identity}").json()
        if data["status"] in jobs.TERMINAL:
            return data
        time.sleep(0.01)
    raise AssertionError("El trabajo no terminó")


def test_transient_retry_and_unknown_cost(client, monkeypatch):
    original = jobs.execute_pipeline
    calls = []

    def flaky(*args):
        calls.append(1)
        if len(calls) == 1:
            raise ConnectionError("Conexión interrumpida")
        return original(*args)

    monkeypatch.setattr(jobs, "execute_pipeline", flaky)
    result = finished(client, submit(client))
    assert result["status"] == "done" and result["attempts"] == 2
    assert len(calls) == 2
    assert result["run"]["cost_eur"] is None
    assert result["run"]["tokens_in"] is None
    assert result["run"]["accounting_complete"] is False


def test_invalid_input_is_not_retried(client, monkeypatch):
    def invalid(*_):
        raise ValueError("Documento incompatible")

    monkeypatch.setattr(jobs, "execute_pipeline", invalid)
    result = finished(client, submit(client))
    assert result["status"] == "error" and result["attempts"] == 1
    assert client.get("/equipment/V-101/revisions/C").status_code == 404


def test_transient_attempt_limit(client, monkeypatch):
    def unavailable(*_):
        raise ConnectionError("Proveedor no disponible")

    monkeypatch.setattr(jobs, "execute_pipeline", unavailable)
    result = finished(client, submit(client, max_attempts=2))
    assert result["status"] == "error" and result["attempts"] == 2


def test_timeout_discards_late_result(client, monkeypatch):
    completed = threading.Event()
    original = jobs.execute_pipeline

    def slow(*args):
        try:
            time.sleep(0.12)
            return original(*args)
        finally:
            completed.set()

    monkeypatch.setattr(jobs, "execute_pipeline", slow)
    identity = submit(client, timeout_seconds=0.03)
    assert finished(client, identity)["status"] == "timeout"
    assert completed.wait(2)
    assert client.get("/equipment/V-101/revisions/C").status_code == 404
    assert client.get(f"/jobs/{identity}").json()["status"] == "timeout"


def test_cancel_discards_late_result(client, monkeypatch):
    entered, release, completed = threading.Event(), threading.Event(), threading.Event()
    original = jobs.execute_pipeline

    def slow(*args):
        entered.set()
        release.wait(2)
        try:
            return original(*args)
        finally:
            completed.set()

    monkeypatch.setattr(jobs, "execute_pipeline", slow)
    identity = submit(client)
    assert entered.wait(2)
    response = client.post(f"/jobs/{identity}/cancel", headers={"Idempotency-Key": str(uuid4())})
    assert response.json()["status"] == "cancelled"
    release.set()
    assert completed.wait(2)
    assert client.get("/equipment/V-101/revisions/C").status_code == 404


def test_active_lease_prevents_second_execution(client, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    original = jobs.execute_pipeline

    def slow(*args):
        entered.set()
        release.wait(2)
        return original(*args)

    monkeypatch.setattr(jobs, "execute_pipeline", slow)
    identity = submit(client)
    assert entered.wait(2)
    delay = asyncio.run(jobs.run_job(client.app.state.store, identity))
    assert delay > 0
    with Session(client.app.state.store.engine) as session:
        assert session.get(JobRecord, identity).attempts == 1
    release.set()
    assert finished(client, identity)["status"] == "done"


def test_accounting_sums_known_attempts_and_preserves_unknown():
    accounting = Accounting("d_hibrido")
    for cost in (0.1, 0.2):
        accounting.add(
            RunInfo(
                strategy="d_hibrido",
                providers=["local"],
                seconds=1,
                tokens_in=10,
                tokens_out=5,
                cost_eur=cost,
                external_calls=1,
            )
        )
    result = accounting.finish(3)
    assert result.cost_eur == pytest.approx(0.3)
    assert result.external_calls == 2 and result.tokens_in == 20
    assert result.gpu_seconds is None and result.accounting_complete
    accounting.add(None)
    result = accounting.finish(4)
    assert result.cost_eur is None and not result.accounting_complete


def test_process_queue_enforces_concurrency():
    async def scenario():
        active, peak = 0, 0
        release = asyncio.Event()

        async def execute(_):
            nonlocal active, peak
            active += 1
            peak = max(active, peak)
            await release.wait()
            active -= 1

        queue = ProcessQueue(execute, concurrency=2)
        for i in range(5):
            await queue.enqueue(str(i))
        await asyncio.sleep(0.01)
        assert peak == 2
        release.set()
        await asyncio.gather(*list(queue.tasks.values()))
        await queue.close()
        assert peak == 2

    asyncio.run(scenario())


def test_redis_adapter_uses_stable_job_id():
    class FakePool:
        def __init__(self):
            self.calls = []
            self.closed = False

        async def enqueue_job(self, *args, **kwargs):
            self.calls.append((args, kwargs))

        async def aclose(self):
            self.closed = True

    async def scenario():
        pool = FakePool()
        queue = RedisQueue(pool)
        await queue.enqueue("job-123")
        await queue.close()
        assert pool.calls == [(("execute_job", "job-123"), {"_job_id": "job-123"})]
        assert pool.closed

    asyncio.run(scenario())
