"""El diagnóstico no filtra la verdad al extractor ni mezcla documentos de otro lote."""

import hashlib
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


def setup_case(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    triage = importlib.import_module("triage_scale")
    data = tmp_path / "synthetic"
    data.mkdir()
    document = data / "drawing.pdf"
    document.write_bytes(b"synthetic-document")
    task = dict(dataset="s-dev", tag="V-TEST", degradation="limpio", revision="1")
    monkeypatch.setattr(triage, "tasks", lambda *_: [{**task, "files": [(document, "GA")]}])
    digest = hashlib.sha256(
        b"drawing.pdf" + hashlib.sha256(document.read_bytes()).digest()
    ).hexdigest()
    report = tmp_path / "report.json"
    report.write_text(
        json.dumps(
            dict(
                synthetic=True,
                complete=True,
                input_sha256=digest,
                rows=[{**task, "status": "error", "error": "Faltan datos"}],
            )
        )
    )
    return triage, report, data


def test_truth_only_read_after_extraction(tmp_path, monkeypatch):
    triage, report, data = setup_case(tmp_path, monkeypatch)
    truth = data / "s-dev/truth/V-TEST.json"

    def extract(documents, **kwargs):
        assert not truth.exists()
        assert documents[0].data == b"synthetic-document"
        assert kwargs["providers"] == []
        truth.parent.mkdir(parents=True)
        truth.write_text('{"rev1":{"diameter":1000}}')
        return SimpleNamespace(
            revision=None,
            candidates=[],
            warnings=[],
            error="Faltan datos",
            run=SimpleNamespace(model_dump=lambda **_: {}),
        )

    monkeypatch.setattr("trazia.pipeline.process", extract)
    result = triage.replay(report, data, tmp_path / "out")
    assert result["complete"]
    assert result["gt_used_for_prediction"] is False
    assert result["rows"][0]["ground_truth_after_extraction"] == {"diameter": 1000}


def test_changed_documents_rejected_before_extraction(tmp_path, monkeypatch):
    triage, report, data = setup_case(tmp_path, monkeypatch)
    (data / "drawing.pdf").write_bytes(b"changed")
    monkeypatch.setattr("trazia.pipeline.process", lambda *_: pytest.fail("No debe extraer"))
    with pytest.raises(ValueError, match="no coinciden"):
        triage.replay(report, data, tmp_path / "out")


def test_private_root_rejected_before_reading(tmp_path, monkeypatch):
    triage, report, _ = setup_case(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="datos privados"):
        triage.replay(report, tmp_path / "private", tmp_path / "out")
