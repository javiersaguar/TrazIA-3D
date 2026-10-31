import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from trazia.api import create_app, job_cache
from trazia.model import load_revision
from trazia.store import DocumentRecord
from trazia.strategies.fusion import PACKAGED_PATH

ROOT = Path(__file__).resolve().parents[1]


def test_real_fusion_change_makes_a_persisted_result_unavailable(tmp_path, monkeypatch):
    with TestClient(create_app(root=ROOT, data_root=tmp_path / "store")) as client:
        store = client.app.state.store
        with Session(store.engine) as session:
            request = {
                "documents": [d.id for d in session.exec(select(DocumentRecord)).all()],
                "strategy": "d_hibrido",
                "providers": [],
                "dataset": "synthetic",
                "tag": "V-101",
            }
            before = job_cache.key_for(session, request)
            snapshot = {
                **request,
                "_cache_calibration": job_cache.calibration_fingerprint(),
                "_cache_fusion": job_cache.fusion_fingerprint(),
            }
            revision = load_revision(ROOT / "examples/vessel_rev_a.json")
            assert job_cache.remember(store, session, snapshot, revision, [])
            session.commit()
            assert job_cache.load(store, session, request)[1].equipment.tag.value == "V-101"
            model = json.loads(PACKAGED_PATH.read_text(encoding="utf8"))
            model["intercept"] += 0.25
            changed = tmp_path / "fusion.json"
            changed.write_text(json.dumps(model), encoding="utf8")
            monkeypatch.setenv("TRAZIA_FUSION", str(changed))
            assert job_cache.key_for(session, request) != before
            with pytest.raises(job_cache.CacheMiss):
                job_cache.load(store, session, request)
            assert job_cache.remember(store, session, snapshot, revision, []) is None
            monkeypatch.setenv("TRAZIA_FUSION", "off")
            assert job_cache.fusion_fingerprint() is None


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
