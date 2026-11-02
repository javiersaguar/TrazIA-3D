"""El informe debe reflejar la revisión que devuelve la API, incluidas sus omisiones."""

import io
import json
from urllib.parse import urlparse

from scripts import measure_scale


def test_measurement_keeps_root_level_unplaced_nozzles_and_archives_response(tmp_path, monkeypatch):
    root = tmp_path / "synthetic/s-dev"
    root.mkdir(parents=True)
    (root / "manifest.json").write_text(
        json.dumps({"synthetic": True, "cases": [{"tag": "V-1"}], "styles": ["vectorial"]})
    )
    folder = root / "vectorial/V-1"
    folder.mkdir(parents=True)
    for revision in (1, 2):
        (folder / f"GAD_V-1_rev{revision}.pdf").write_bytes(b"synthetic public fixture")
    response = {
        "dataset": "synthetic",
        "equipment": {"kind": "vertical_vessel", "lod": 2},
        "unplaced_nozzles": ["N3", "N4"],
    }

    class Opener:
        jobs = 0

        def open(self, request, timeout):
            path = urlparse(request.full_url).path
            if path == "/documents":
                result = {"id": "synthetic-document"}
            elif path.endswith("/jobs"):
                self.jobs += 1
                result = {"job_id": str(self.jobs)}
            elif path.startswith("/jobs/"):
                result = {
                    "status": "done",
                    "error": None,
                    "run": {"cost_eur": 0, "external_calls": 0, "accounting_complete": True},
                }
            else:
                result = response
            return io.BytesIO(json.dumps(result).encode())

    monkeypatch.setattr(measure_scale.urllib.request, "build_opener", lambda *_: Opener())
    output = tmp_path / "measured.json"
    result = measure_scale.run(
        "http://synthetic.invalid",
        root.parent,
        ["s-dev"],
        output,
        save_models=True,
    )
    assert result["acceptance"]["drafts_with_unplaced_nozzles"] == 2
    assert [r["unplaced_nozzles"] for r in result["rows"]] == [2, 2]
    for row in result["rows"]:
        assert json.loads((tmp_path / row["model_artifact"]).read_text()) == response
