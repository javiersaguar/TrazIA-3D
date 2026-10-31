"""Fusión aprendida de D (tarea 3.4): señales por opción, elección y respaldo heurístico."""

import json

import pytest

from trazia.extraction import Candidate
from trazia.model import Source
from trazia.strategies import get_strategy
from trazia.strategies.d_hibrido import fuse
from trazia.strategies.fusion import FEATURES, FusionModel, load_fusion


def cand(value, channel, conf=0.8, bbox=(0.1, 0.1, 0.2, 0.12), text="x", path="height"):
    source = Source(document_id="GA", page=1, locator="t", bbox=bbox, confidence=conf)
    return Candidate(
        path=path, value=value, unit="mm", source=source, channel=channel, text_original=text
    )


def model(weights: dict[str, float], intercept=0.0, seen=None) -> FusionModel:
    meta = {} if seen is None else {"channels_seen": seen}
    return FusionModel(
        list(FEATURES), [weights.get(f, 0.0) for f in FEATURES], intercept, "S-dev", meta
    )


def test_record_gives_one_row_per_option_including_the_unconfirmed_measure():
    measured = cand(6000.0, "geometria", conf=0.6, text=None)
    record: list[dict] = []
    fuse(
        [cand(9000.0, "tabla"), cand(7000.0, "rag", bbox=(0.5, 0.5, 0.6, 0.6)), measured],
        None,
        record,
    )
    assert [r["value"] for r in record] == [9000.0, 7000.0, 6000.0]
    assert [r["measure"] for r in record] == [False, False, True]
    assert all(set(r["features"]) == set(FEATURES) for r in record)
    assert record[0]["features"]["geo_contradicts"] == 1.0
    assert record[2]["features"]["measure_vector"] == 1.0
    assert record[0]["features"]["rivals"] == pytest.approx(2 / 3)


def test_learned_model_can_prefer_the_drawing_and_its_probability_is_the_confidence():
    trust_drawing = model({"measure_vector": 4.0, "ch_tabla": 1.0}, intercept=-2.0)
    measured = cand(6000.0, "geometria", conf=0.6, text=None)
    [chosen], conflicts = fuse([cand(9000.0, "tabla"), measured], trust_drawing)
    assert chosen.value == 6000.0
    assert chosen.source.confidence == pytest.approx(
        trust_drawing.prob({"measure_vector": 1}), 1e-3
    )
    assert "Fusión aprendida" in chosen.explanation and chosen.alternatives[0].value == 9000.0
    assert "height" in conflicts or chosen.source.confidence > 0.5

    trust_table = model({"ch_tabla": 6.0}, intercept=-2.0)
    [chosen], _ = fuse([cand(9000.0, "tabla"), measured], trust_table)
    assert chosen.value == 9000.0


def test_unseen_channel_falls_back_to_the_heuristic():
    learned = model({"ch_tabla": 6.0}, intercept=-5.0, seen=["tabla"])
    [heuristic], _ = fuse([cand(9000.0, "texto", conf=0.75)])
    [chosen], _ = fuse([cand(9000.0, "texto", conf=0.75)], learned)
    assert chosen.source.confidence == heuristic.source.confidence == pytest.approx(0.75)
    assert "Fusión aprendida" not in chosen.explanation


def test_model_file_round_trip_and_off_switch(tmp_path, monkeypatch):
    path = tmp_path / "f.json"
    m = model({"ch_tabla": 2.0}, seen=["tabla"])
    path.write_text(json.dumps(m.to_dict()), encoding="utf-8")
    monkeypatch.setenv("TRAZIA_FUSION", str(path))
    loaded = load_fusion()
    assert (
        loaded.sha256 == m.sha256 and loaded.covers({"tabla": 1}) and not loaded.covers({"rag": 1})
    )
    monkeypatch.setenv("TRAZIA_FUSION", "off")
    assert load_fusion() is None


def test_strategy_without_model_warns_and_uses_the_heuristic(monkeypatch):
    monkeypatch.setenv("TRAZIA_FUSION", "off")
    strategy = get_strategy("d_hibrido+fusion")
    assert strategy.fusion == "aprendida" and strategy.name == "d_hibrido+fusion"
    assert get_strategy("a_detector").reader == "detector"
