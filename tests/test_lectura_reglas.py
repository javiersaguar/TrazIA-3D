"""B completo (tarea 2.1): unidades de plano, cabeceras es/en, cotas giradas y datum."""

import json

import pytest

from bench.runner import EXTRACTORS, run_extraction
from synthetic.cases import flatten, spec_from_dict
from synthetic.sets import generate_set
from synthetic.vendors import PUBLIC
from trazia.extractors.units import (
    parse_length,
    parse_length_any_direction,
    parse_nominal_size,
    parse_number,
    parse_pressure,
    parse_temperature,
    parse_weight,
)


def test_lengths_as_drawn():
    assert parse_length('78 3/4"') == pytest.approx(2000.25)
    assert parse_length("6'-6 3/4\"") == pytest.approx(2000.25)
    assert parse_length('13/16"') == pytest.approx(20.6375)  # no es «1 3/16"»
    assert parse_length('1 3/16"') == pytest.approx(30.1625)
    assert parse_length("12.500", decimal=",") == 12500
    assert parse_length("2000") == 2000
    # Cota girada: pdfplumber entrega los caracteres al revés.
    assert parse_length_any_direction('"4/1 011') == [pytest.approx(2800.35)]
    assert parse_length_any_direction("0078") == [8700]


def test_numbers_sizes_and_attribute_units():
    assert parse_number("1,234.5") == 1234.5 and parse_number("2,5") == 2.5
    assert parse_nominal_size("DN150") == parse_nominal_size('6"') == 150
    assert parse_nominal_size("123") is None  # fuera de la serie normalizada
    assert parse_pressure("145.0 psig")[0] == pytest.approx(10, abs=0.01)
    assert parse_pressure("30 bar(g)") == (30, "bar(g)")
    assert parse_temperature("302 °F")[0] == pytest.approx(150)
    assert parse_weight("27,558 lb") is None  # Ambiguo sin contexto del documento.
    assert parse_weight("27,558 lb", decimal=".")[0] == pytest.approx(12500, abs=0.5)
    assert parse_weight("69.300 kg", decimal=",")[0] == 69300


@pytest.fixture(scope="module")
def dev_set(tmp_path_factory):
    root = tmp_path_factory.mktemp("v2")
    generate_set("s-dev", root, cases=6, degradations=("vectorial",))
    return root / "s-dev"


@pytest.mark.parametrize("index", range(len(PUBLIC)))
def test_b_reads_every_public_vendor(dev_set, index):
    manifest = json.loads((dev_set / "manifest.json").read_text(encoding="utf-8"))
    case = manifest["cases"][index]
    tag = case["tag"]
    truth = json.loads((dev_set / "truth" / f"{tag}.json").read_text(encoding="utf-8"))
    extraction = run_extraction(dev_set / "vectorial" / tag, tag, "1", EXTRACTORS["combinado"]())
    assert extraction.revision is not None, (case["vendor"], extraction.error)
    expected = flatten(spec_from_dict(truth["rev1"]))
    for path, (value, unit) in expected.items():
        candidate = extraction.candidates.get(path)
        assert candidate is not None, (case["vendor"], path)
        if isinstance(value, str):
            assert str(candidate.value).upper() == value.upper(), (case["vendor"], path)
        elif unit == "mm":
            assert candidate.value == pytest.approx(value, abs=1.0), (case["vendor"], path)
        else:
            assert candidate.value == pytest.approx(value, rel=0.005, abs=0.5), (
                case["vendor"],
                path,
            )
    if case["vendor"] == "levante":  # cotas desde la tangente inferior + faldón, explicado
        elevation = next(c for p, c in extraction.candidates.items() if p.endswith(".elevation"))
        assert "tangente inferior" in elevation.explanation and elevation.text_original
