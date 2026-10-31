import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.measure_scale import summarise, tasks
from scripts.run_scale import deployment_override


def test_scale_report_preserves_failures_and_unknown_cost():
    rows = [
        {
            "dataset": "s-dev",
            "tag": "V-1",
            "degradation": "vectorial",
            "revision": "1",
            "status": "done",
            "seconds_turnaround": 2,
            "run": {"cost_eur": 0.1, "external_calls": 1, "accounting_complete": True},
        },
        {
            "dataset": "s-dev",
            "tag": "V-1",
            "degradation": "vectorial",
            "revision": "2",
            "status": "error",
            "seconds_turnaround": 4,
            "run": None,
        },
    ]
    result = summarise(rows, 10, 1)
    assert result["equipment"] == 1 and result["conditions"] == 1
    assert result["statuses"] == {"done": 1, "error": 1}
    assert result["cost_eur"] is None and result["jobs_without_cost"] == 1
    assert result["jobs_with_incomplete_accounting"] == 1
    projection = result["projection_400x4"]
    assert projection["measured"] is False
    assert projection["seconds_for_1600_terminal_jobs"] == 8000
    assert projection["seconds_for_1600_valid_ifc"] is None and projection["cost_eur"] is None
    assert result["per_equipment_condition"][0]["cost_eur"] is None
    assert result["job_cache_hits"] is None and result["job_cache_observed"] == 0
    rows[0]["cache_hit"], rows[1]["cache_hit"] = True, False
    observed = summarise(rows, 10, 1)
    assert observed["job_cache_hits"] == 1 and observed["job_cache_hit_rate"] == 0.5


def test_scale_mounts_same_calibration_read_only_without_exposing_a_team_port():
    config = deployment_override("trazia:test", 8030, "/mnt/c/synthetic/calibracion.json")
    assert "127.0.0.1:8030:8000" in config
    assert config.count("TRAZIA_CALIBRATION: /run/trazia-calibracion.json") == 2
    assert config.count("read_only: true") == 2
    assert config.count("CUDA_VISIBLE_DEVICES: '-1'") == 2
    assert "TRAZIA_WORKER_CONCURRENCY: '1'" in config


def test_scale_projection_is_separate_from_measured_batch():
    row = {
        "dataset": "s-dev",
        "tag": "V-1",
        "degradation": "vectorial",
        "revision": "1",
        "status": "done",
        "seconds_turnaround": 2,
        "run": {"cost_eur": 0.1, "external_calls": 1, "accounting_complete": True},
    }
    result = summarise([row], 10, 1)
    assert result["seconds_batch"] == 10 and result["cost_eur"] == 0.1
    assert result["projection_400x4"]["cost_eur"] == 160


def test_scale_only_accepts_synthetic_manifests_and_requires_originals(tmp_path):
    root = tmp_path / "s-dev"
    root.mkdir()
    manifest = {"synthetic": False, "cases": [], "styles": []}
    path = root / "manifest.json"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="sintéticos"):
        tasks(tmp_path, ["s-dev"])
    manifest.update(synthetic=True, cases=[{"tag": "V-1"}], styles=["vectorial"])
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Falta"):
        tasks(tmp_path, ["s-dev"])


def test_probe_limits_keep_exact_cases_and_degradations(tmp_path):
    root = tmp_path / "s-dev"
    root.mkdir()
    manifest = {
        "synthetic": True,
        "cases": [{"tag": "V-1"}, {"tag": "V-2"}],
        "styles": ["vectorial", "escaneado_limpio"],
    }
    (root / "manifest.json").write_text(json.dumps(manifest))
    for style in manifest["styles"]:
        for case in manifest["cases"]:
            folder = root / style / case["tag"]
            folder.mkdir(parents=True)
            for revision in (1, 2):
                (folder / f"GAD_{case['tag']}_rev{revision}.pdf").write_bytes(b"synthetic fixture")
    assert len(tasks(tmp_path, ["s-dev"])) == 8
    probe = tasks(tmp_path, ["s-dev"], cases_limit=1, degradations=["vectorial"])
    assert len(probe) == 2
    assert {(row["tag"], row["degradation"]) for row in probe} == {("V-1", "vectorial")}


@pytest.mark.parametrize("port", [8010, 8011, 8020, 3100, 3125, 3300, 3295])
def test_scale_runner_rejects_other_teams_ports_before_docker(port):
    result = subprocess.run(
        [sys.executable, "scripts/run_scale.py", "--api-port", str(port)],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 2 and "Puerto no disponible" in result.stderr
