"""Datos del detector propio (tarea 2.4): formato Florence-2, Label Studio y conjuntos vedados."""

import json

import pytest

from synthetic.sets import generate_set
from training.dataset import build, target_sequence
from training.florence import parse_regions
from training.label_studio import regions


def test_target_sequence_round_trips():
    items = [("ID 2000", (100, 50, 200, 70)), ("375", (10, 300, 30, 360))]
    sequence = target_sequence(items, (0, 0, 768, 768))
    parsed = parse_regions(sequence)
    assert [t for t, _ in parsed] == ["ID 2000", "375"]
    assert parsed[0][1] == pytest.approx((0.13, 0.065, 0.26, 0.091), abs=0.002)


def test_label_studio_export_regions():
    task = {
        "data": {"image": "/data/upload/1/abc-pagina1.png"},
        "annotations": [
            {
                "result": [
                    {
                        "id": "r1",
                        "type": "rectanglelabels",
                        "value": {
                            "x": 10,
                            "y": 20,
                            "width": 5,
                            "height": 2,
                            "rectanglelabels": ["cota"],
                        },
                    },
                    {"id": "r1", "type": "textarea", "value": {"text": ["2000"]}},
                ]
            }
        ],
    }
    assert regions(task) == [("2000", (10, 20, 15, 22))]


def test_reserved_set_is_refused_for_training(tmp_path):
    generate_set("s-reservado", tmp_path, cases=1, degradations=("vectorial",))
    with pytest.raises(ValueError, match="nunca se usa para entrenar"):
        build(tmp_path / "s-reservado", tmp_path / "train")
    rows = build(tmp_path / "s-reservado", tmp_path / "eval", copies=1, evaluation=True)
    assert rows and all(r["synthetic"] for r in rows)


def test_training_tiles_read_rotated_dimensions_in_reading_order(tmp_path):
    generate_set("s-dev", tmp_path, cases=1, degradations=("vectorial",))
    rows = build(tmp_path / "s-dev", tmp_path / "train", copies=1)
    truth = json.loads(next((tmp_path / "s-dev" / "truth").glob("*.json")).read_text("utf-8"))
    texts = {t for r in rows for t, _ in parse_regions(r["target"])}
    assert str(truth["rev1"]["height"]) in texts  # la cota girada, en su orden de lectura
