from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from trazia.api import create_app, job_cache
from trazia.model import load_revision
from trazia.store import DocumentRecord

ROOT = Path(__file__).resolve().parents[1]


def test_cache_depends_on_fusion_weights_and_avoids_storing_across_a_weight_change(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(job_cache, "calibration_fingerprint", lambda: None)
    monkeypatch.setattr(job_cache, "fusion_fingerprint", lambda: "1" * 64)
    with TestClient(create_app(root=ROOT, data_root=tmp_path)) as client:
        store = client.app.state.store
        with Session(store.engine) as session:
            documents = [d.id for d in session.exec(select(DocumentRecord)).all()]
            request = {
                "documents": documents,
                "strategy": "d_hibrido+fusion",
                "providers": [],
                "dataset": "synthetic",
                "_cache_calibration": None,
                "_cache_fusion": "1" * 64,
            }
            before = job_cache.key_for(session, request)
            monkeypatch.setattr(job_cache, "fusion_fingerprint", lambda: "2" * 64)
            current = {**request, "_cache_fusion": "2" * 64}
            assert before != job_cache.key_for(session, current)
            revision = load_revision(ROOT / "examples/vessel_rev_a.json")
            assert job_cache.remember(store, session, request, revision, []) is None
