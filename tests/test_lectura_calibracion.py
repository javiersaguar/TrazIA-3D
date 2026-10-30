"""Calibración isotónica, intervalos conformes y abstención (tarea 3.3)."""

import json
import random

import pytest

from bench.calibrar import abstention_threshold, fit
from trazia.calibration import Calibration, conformal, load_calibration
from trazia.calibration.isotonic import apply_curve, fit_curve
from trazia.extraction import Candidate
from trazia.model import Source


def cand(value, unit="mm", conf=0.6, channel="tabla", path="height"):
    source = Source(
        document_id="GA", page=1, locator="t", bbox=(0.1, 0.1, 0.2, 0.12), confidence=conf
    )
    return Candidate(path=path, value=value, unit=unit, source=source, channel=channel)


def test_isotonic_curve_is_monotone_and_interpolates():
    rng = random.Random(1)
    scores = [rng.random() for _ in range(400)]
    hits = [rng.random() < s * 0.8 for s in scores]  # sobreconfiada: acierta menos de lo que dice
    curve = fit_curve(scores, hits)
    assert curve["y"] == sorted(curve["y"])
    assert apply_curve(curve, 0.9) < 0.9
    assert apply_curve(curve, -1) == curve["y"][0] and apply_curve(curve, 2) == curve["y"][-1]


def test_conformal_quantile_is_the_finite_sample_one():
    residuals = [i / 100 for i in range(1, 20)]  # 19 residuos: ⌈20·0,9⌉ = 18
    assert conformal.quantile(residuals, 0.9) == pytest.approx(0.18)
    assert conformal.quantile(residuals[:5], 0.9) is None  # muy pocos para garantizar el 90 %
    assert conformal.residual("mm", 1000.0, 1000.8) == 0.0  # dentro de la tolerancia
    assert conformal.residual("deg", 359.0, 1.0) == pytest.approx(1.5)


def test_conformal_coverage_holds_on_exchangeable_data():
    rng = random.Random(7)
    errors = [abs(rng.gauss(0, 30)) for _ in range(2000)]
    q = conformal.quantile([conformal.residual("mm", 5000.0, 5000.0 + e) for e in errors[:1000]])
    hits = [conformal.residual("mm", 5000.0, 5000.0 + e) <= q for e in errors[1000:]]
    assert sum(hits) / len(hits) >= 0.88


def calibration():
    return Calibration(
        curves={"b_reglas|*": {"x": [0.0, 1.0], "y": [0.0, 0.5], "n": 100}},
        quantiles={"mm|*": 0.01, "deg|*": 2.0},
        thresholds={"b_reglas": 0.4},
    )


def test_apply_fills_raw_confidence_interval_and_abstention():
    out, summary = calibration().apply(
        [cand(8000.0, conf=0.6), cand(90.0, "deg", conf=0.9, path="nozzles.N1.azimuth")],
        "b_reglas",
    )
    low, high = out[0], out[1]
    assert low.source.confidence == pytest.approx(0.3) and low.source.confidence_raw == 0.6
    assert low.state == "abstained" and "Abstención" in low.explanation
    assert low.interval.low == pytest.approx(8000 - 1 - 80) and low.interval.level == 0.9
    assert high.state is None and high.interval.high == pytest.approx(90 + 0.5 + 2.0)
    assert summary == {"fields": 2, "intervals": 2, "abstained": 1}


def test_ablation_falls_back_to_its_strategy_and_text_has_no_interval():
    [out], _ = calibration().apply([cand("V-101", unit="-", conf=1.0, path="tag")], "b_reglas-hdm")
    assert out.source.confidence == pytest.approx(0.5) and out.interval is None


def test_load_respects_the_environment(tmp_path, monkeypatch):
    path = tmp_path / "c.json"
    path.write_text(json.dumps(calibration().to_dict()), encoding="utf-8")
    monkeypatch.setenv("TRAZIA_CALIBRATION", str(path))
    assert load_calibration().thresholds == {"b_reglas": 0.4}
    monkeypatch.setenv("TRAZIA_CALIBRATION", "off")
    assert load_calibration() is None


def test_threshold_and_fit_from_rows():
    assert abstention_threshold([(0.9, True)] * 19 + [(0.2, False)] * 5) == 0.9
    assert abstention_threshold([(0.9, False)] * 5) is None
    rng = random.Random(3)
    rows = []
    for i in range(400):
        raw = rng.random()
        ok = rng.random() < raw
        rows.append(
            {
                "tag": f"T{i % 20}",
                "strategy": "b_reglas",
                "channel": "tabla",
                "media": "scan" if i % 3 else "vector",
                "raw": raw,
                "correct": ok,
                "kind": "mm",
                "residual": 0.0 if ok else rng.random(),
            }
        )
    fitted = fit(rows)
    assert {"b_reglas|tabla|scan", "b_reglas|tabla", "b_reglas|*", "*|*"} <= fitted.curves.keys()
    assert "mm|*" in fitted.quantiles and fitted.fitted_on == "S-dev"


def test_pipeline_calibrates_and_carries_it_into_the_contract(tmp_path, monkeypatch):
    from synthetic.sets import generate_set
    from trazia.model import fields
    from trazia.pipeline import InputDocument, process

    generate_set("s-dev", tmp_path, cases=1, degradations=("vectorial",))
    tag = json.loads((tmp_path / "s-dev" / "manifest.json").read_text(encoding="utf-8"))
    tag = tag["cases"][0]["tag"]
    paths = sorted((tmp_path / "s-dev" / "vectorial" / tag).glob("*_rev1.*"))
    docs = [
        InputDocument(p.name, p.read_bytes(), ("GA-" if p.name.startswith("GAD") else "HDM-") + tag)
        for p in paths
    ]
    params = calibration()
    params.thresholds = {"b_reglas": 1.01}  # todo en abstención, para verlo en el contrato
    path = tmp_path / "c.json"
    path.write_text(json.dumps(params.to_dict()), encoding="utf-8")
    monkeypatch.setenv("TRAZIA_CALIBRATION", str(path))
    events = []
    result = process(
        docs,
        project_id="P",
        equipment_id=tag.lower(),
        revision="1",
        strategy="b_reglas",
        on_event=events.append,
    )
    assert result.revision is not None, result.error
    [stage] = [e for e in events if e.stage == "calibrate"]
    assert stage.status == "ok" and "abstenciones" in stage.detail
    traced = fields(result.revision.equipment)
    assert all(f.state == "abstained" for f in traced.values())
    assert all(f.source.confidence_raw is not None for f in traced.values())
    assert traced["height"].interval is not None and traced["height"].interval.level == 0.9

    monkeypatch.setenv("TRAZIA_CALIBRATION", "off")
    events.clear()
    plain = process(
        docs,
        project_id="P",
        equipment_id=tag.lower(),
        revision="1",
        strategy="b_reglas",
        on_event=events.append,
    )
    assert [e.status for e in events if e.stage == "calibrate"] == ["omitido"]
    assert all(f.state == "candidate" for f in fields(plain.revision.equipment).values())
