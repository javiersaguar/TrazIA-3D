"""Arnés del estudio: formato de la Interfaz 3, unidades, verificación de cita y estadística."""

import json

import pytest

from bench.estudio import main, run_study
from bench.stats import bootstrap_ci, mcnemar, pareto
from bench.support import is_supported, numbers_in
from bench.units import same, to_canonical
from synthetic.sets import generate_set
from trazia.extraction import Candidate
from trazia.ingest import Bundle, EvidenceLine
from trazia.model import Document, Source

METRIC_KEYS = {
    "score",
    "geometry",
    "attributes",
    "ece",
    "f1_delta",
    "hallucination_rate",
    "citation_coverage",
    "interval_coverage",
    "cost_eur_per_equipment",
    "seconds_per_revision",
}


def test_units_compare_after_conversion():
    assert to_canonical(145.0, "psig")[1] == "bar"
    assert same(145.0, "psig", 10, "bar")
    assert same(302, "F", 150, "C")
    assert same(78.75, "in", 2000.25, "mm")
    assert not same(2002, "mm", 2000, "mm")
    assert same(359.8, "deg", 0, "deg")
    assert same("sa-516-70", "1", "SA-516-70", "1")


def test_numbers_in_understands_drawing_formats():
    assert 78.75 in numbers_in("ID 6'-6 3/4\"")
    assert 12500 in numbers_in("12.500 kg")
    assert 8700 in numbers_in("0078")  # texto girado: dígitos invertidos
    assert 110.25 in numbers_in('110 1/4"')


def _bundle(text: str) -> Bundle:
    document = Document(id="GA-X", filename="GAD_X_rev1.pdf", revision="1", sha256="0" * 64)
    line = EvidenceLine(
        text=text,
        source=Source(
            document_id="GA-X", page=1, locator="t", bbox=(0.1, 0.1, 0.2, 0.12), confidence=0.75
        ),
    )
    return Bundle(document=document, media_type="pdf", lines=[line])


def _candidate(value, unit="mm", bbox=(0.1, 0.1, 0.2, 0.12), **extra):
    source = Source(document_id="GA-X", page=1, locator="t", bbox=bbox, confidence=0.9)
    return Candidate(path="diameter", value=value, unit=unit, source=source, **extra)


def test_support_check_detects_values_absent_from_the_cited_region():
    bundle = _bundle("ID 2000")
    assert is_supported(_candidate(2000.0), bundle) is True
    assert is_supported(_candidate(2100.0), bundle) is False  # inventado
    assert is_supported(_candidate(2000.0, bbox=(0.6, 0.6, 0.7, 0.7)), bundle) is False
    assert is_supported(_candidate(1.0, text_original="ID 2000"), bundle) is True
    scanned = Bundle(document=bundle.document, media_type="pdf", lines=[])
    assert is_supported(_candidate(2000.0), scanned) is None  # sin capa de texto


def test_statistics():
    assert mcnemar([True, True, False], [True, False, False]) == {
        "only_a": 1,
        "only_b": 0,
        "p": 1.0,
    }
    assert mcnemar([True] * 10, [False] * 10)["p"] < 0.01
    assert pareto({"a": (0, 1, -0.5), "b": (0, 2, -0.4), "c": (1, 0.5, -0.9)}) == ["c", "a"]
    ci = bootstrap_ci([1, 2, 3, 4], lambda s: sum(s) / len(s), resamples=200)
    assert ci[0] <= 2.5 <= ci[1]


@pytest.fixture(scope="module")
def small_sets(tmp_path_factory):
    root = tmp_path_factory.mktemp("v2")
    generate_set("s-dev", root, cases=2, degradations=("vectorial",))
    generate_set("s-adversarial", root, cases=1)
    generate_set("s-mecanico", root, cases=1, degradations=("vectorial",))
    return root


def test_study_writes_interface_3(small_sets, tmp_path):
    out = tmp_path / "estudio"
    code = main(
        [
            "--datos",
            str(small_sets),
            "--conjuntos",
            "s-dev",
            "s-adversarial",
            "s-mecanico",
            "s-reservado",
            "--variantes",
            "b_reglas",
            "b_reglas-hdm",
            "a_detector",
            "--remuestreos",
            "50",
            "--salida",
            str(out),
        ]
    )
    assert code == 0
    study = json.loads((out / "estudio.json").read_text(encoding="utf-8"))
    for key in ("generated_at", "seed", "datasets", "variants", "ablations", "pairwise", "pareto"):
        assert key in study
    assert set(study["recommendation"]) >= {"vectorial", "escaneado", "rationale"}
    ids = [v["id"] for v in study["variants"]]
    assert ids == ["b_reglas", "b_reglas-hdm"]
    for variant in study["variants"]:
        assert set(variant["metrics"]) == METRIC_KEYS
        assert set(variant) >= {"id", "strategy", "providers", "ci95", "by_dataset"}
        assert set(variant) >= {"by_style", "by_degradation"}
        assert len(variant["ci95"]["score"]) == 2
    assert study["ablations"][0]["id"] == "b_reglas-hdm"
    assert study["pairwise"][0]["a"] in ids and 0 <= study["pairwise"][0]["mcnemar_p"] <= 1
    reasons = {u["id"]: u["reason"] for u in study["unmeasured"]}
    assert "no implementada" in reasons["a_detector"]
    assert "S-mecánico" in reasons and "S-reservado" in reasons
    adversarial = study["variants"][0]["by_dataset"]["S-adversarial"]
    assert adversarial["poisoning_rate"] is not None
    assert "Datos sintéticos" in (out / "estudio.md").read_text(encoding="utf-8")


def test_study_is_deterministic_apart_from_timing(small_sets):
    def strip(study):
        for v in study["variants"]:
            v["metrics"].pop("seconds_per_revision")
            v["metrics"].pop("score")  # incluye la escala, que depende del tiempo
            v.pop("ci95")
            v["details"].pop("scale")
            v.pop("by_dataset"), v.pop("by_style"), v.pop("by_degradation")
        return study["variants"]

    kwargs = {"resamples": 20, "log": lambda *_: None}
    a = run_study(small_sets, ["s-dev"], ["b_reglas"], **kwargs)
    b = run_study(small_sets, ["s-dev"], ["b_reglas"], **kwargs)
    assert strip(a) == strip(b)
