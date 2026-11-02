import hashlib
import importlib
import json
from pathlib import Path

import pytest


@pytest.fixture
def batch(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    scorer = importlib.import_module("score_scale_quality")
    data = tmp_path / "data"
    fingerprint = hashlib.sha256()
    for dataset in scorer.SETS:
        root = data / dataset
        root.mkdir(parents=True)
        manifest = {"synthetic": True, "cases": [], "styles": ["vectorial"]}
        if dataset == "s-dev":
            manifest["cases"] = [{"tag": "V-1"}]
            folder = root / "vectorial/V-1"
            folder.mkdir(parents=True)
            for revision in ("1", "2"):
                file = folder / f"GAD_V-1_rev{revision}.pdf"
                file.write_bytes(b"public synthetic fixture")
                fingerprint.update(
                    file.relative_to(data).as_posix().encode()
                    + hashlib.sha256(file.read_bytes()).digest()
                )
            (root / "truth").mkdir()
            (root / "truth/V-1.json").write_text(
                json.dumps({"rev1": {"diameter": 1000}, "rev2": {"diameter": 1200}})
            )
        (root / "manifest.json").write_text(json.dumps(manifest))
    rows = [
        {
            "dataset": "s-dev",
            "tag": "V-1",
            "degradation": "vectorial",
            "revision": r,
            "status": "error",
            "run": None,
        }
        for r in ("1", "2")
    ]
    report = {
        "synthetic": True,
        "complete": True,
        "input_sha256": fingerprint.hexdigest(),
        "rows": rows,
    }
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report))
    return scorer, data, report, path, tmp_path / "quality.json"


def test_failed_exports_remain_missing_in_end_to_end_quality(batch):
    scorer, data, report, path, output = batch
    result = scorer.score(path, data, output)
    assert result["summary"]["revisions"] == 2
    assert result["summary"]["recall_correct_fields"] == 0
    assert result["summary"]["present_fields"] == 0
    assert result["summary"]["cost_for_1600_engineering_valid_ifc"] is None


def test_quality_rejects_changed_originals_and_missing_exported_json(batch):
    scorer, data, report, path, output = batch
    file = data / "s-dev/vectorial/V-1/GAD_V-1_rev1.pdf"
    original = file.read_bytes()
    file.write_bytes(b"changed")
    with pytest.raises(ValueError, match="huella"):
        scorer.score(path, data, output)
    file.write_bytes(original)
    report["rows"][0]["status"] = "done"
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="JSON exportado"):
        scorer.score(path, data, output)
