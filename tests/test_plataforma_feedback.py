import json
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session

from bench.recalibrar import main, propose
from trazia.api import create_app
from trazia.calibration.feedback import training_rows
from trazia.model import Revision, fields
from trazia.store import RevisionRecord

ROOT = Path(__file__).resolve().parents[1]


def test_ledger_requires_current_approval_and_deduplicates_predictions(tmp_path):
    with TestClient(create_app(root=ROOT, data_root=tmp_path)) as client:
        store = client.app.state.store
        identity = "DEMO-TR:v101:A"
        with Session(store.engine) as session:
            from sqlmodel import select

            record = session.exec(
                select(RevisionRecord).where(RevisionRecord.revision == "A")
            ).first()
            identity = record.id
            revision = Revision.model_validate_json(record.payload)
            for field in fields(revision.equipment).values():
                field.source.confidence_raw = field.source.confidence
                field.source.strategy = "b_reglas"
                field.source.channel = "tabla"
            record.payload = revision.model_dump_json()
            session.add(record)
            session.commit()
        etag = '"1"'

        def patch(path, **body):
            nonlocal etag
            response = client.patch(
                f"/revisions/{identity}/fields/{path}",
                json={"actor": "Prueba sintética", **body},
                headers={"If-Match": etag, "Idempotency-Key": str(uuid4())},
            )
            assert response.status_code == 200, response.text
            etag = response.headers["etag"]

        patch("diameter", state="corrected", value=2100)
        patch("diameter", state="corrected", value=2200)
        ledger = client.app.state.corrections_file
        assert training_rows(store, ledger)[0] == []
        for path in client.get(f"/revisions/{identity}/fields").json():
            if path != "diameter":
                patch(path, state="accepted")
        response = client.post(
            f"/revisions/{identity}/approve",
            json={"reviewer": "Prueba sintética"},
            headers={"If-Match": etag, "Idempotency-Key": str(uuid4())},
        )
        assert response.status_code == 200, response.text
        etag = response.headers["etag"]
        rows, provenance = training_rows(store, ledger)
        [diameter] = [r for r in rows if r["path"] == "diameter"]
        assert diameter["prediction"] == 2000 and diameter["value"] == 2200
        assert diameter["correct"] is False and diameter["residual"] > 0
        assert any(r["correct"] for r in rows)  # También confirmaciones, evita solo negativos.
        assert provenance["equipment"] == 1
        with ledger.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"revision_id": identity, "path": "height"}) + "\n")
        assert training_rows(store, ledger)[1]["unverified"] == 1
        patch("height", state="corrected", value=6100)
        assert training_rows(store, ledger)[0] == []


def test_recalibration_uses_disjoint_equipment_and_does_not_publish_small_sample(tmp_path):
    rows = []
    for tag in range(9):
        for field in range(60):
            correct = field % 2 == 0
            rows.append(
                {
                    "tag": str(tag),
                    "strategy": "b_reglas",
                    "channel": "tabla",
                    "media": "unknown",
                    "raw": 0.9,
                    "correct": correct,
                    "kind": "mm",
                    "residual": 0.0 if correct else 0.05,
                }
            )
    candidate, report = propose(rows, None)
    assert report["status"] == "candidate"
    assert not set(candidate.meta["fit_equipment"]) & set(candidate.meta["test_equipment"])
    assert report["after"]["b_reglas"]["ece_calibrated"] == 0
    from trazia.calibration import Calibration
    from trazia.calibration.scope import for_strategy

    assert for_strategy(candidate, "c_rag") is None
    base = Calibration({"c_rag|*": {"x": [0, 1], "y": [0, 0.8]}}, {"mm|*": 0.03}, {})
    with_base, _ = propose(rows, base)
    fallback = for_strategy(with_base, "c_rag")
    assert fallback.to_dict() == base.to_dict()
    assert for_strategy(with_base, "b_reglas-hdm") is with_base
    assert propose(rows[:60], None)[0] is None
    ledger = tmp_path / "empty.jsonl"
    ledger.write_text("")
    output = tmp_path / "output"
    output.mkdir()
    (output / "calibracion.json").write_text("stale proposal")
    assert (
        main(
            [
                "--almacen",
                str(tmp_path / "store"),
                "--correcciones",
                str(ledger),
                "--salida",
                str(output),
            ]
        )
        == 0
    )
    assert not (output / "calibracion.json").exists()
    report = json.loads((output / "informe.json").read_text(encoding="utf-8"))
    assert report["status"] == "insufficient" and report["activated"] is False
