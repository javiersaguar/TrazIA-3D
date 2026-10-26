"""Generador v2 (DEC-21): proveedores, conjuntos con semilla, trampas y degradación."""

import io
import json
import random

import pdfplumber
import pytest

from synthetic.cases import random_case
from synthetic.render_v2 import degrade, render_ga
from synthetic.sets import SETS, generate_set
from synthetic.vendors import (
    PUBLIC,
    RESERVED,
    VENDORS,
    fmt_length,
    fmt_pressure,
    fmt_weight,
    printed_azimuth,
    snap_imperial,
)


def test_eight_vendors_two_reserved_and_sets_never_mix_them():
    assert len(VENDORS) == 8
    assert len(RESERVED) == 2 and not set(PUBLIC) & set(RESERVED)
    for name, spec in SETS.items():
        if name == "s-reservado":
            assert set(spec.vendors) == set(RESERVED)
        else:
            assert not set(spec.vendors) & set(RESERVED), name
    assert {VENDORS[k].lang for k in PUBLIC} == {"en", "es"}
    assert {VENDORS[k].length_unit for k in PUBLIC} == {"mm", "in", "ftin"}


def test_vendor_formats():
    assert fmt_length(snap_imperial(2000), VENDORS["gulf"]) == '78 3/4"'
    assert fmt_length(snap_imperial(2000), VENDORS["prairie"]) == "6'-6 3/4\""
    assert fmt_length(snap_imperial(30), VENDORS["prairie"]) == '1 3/16"'
    assert fmt_weight(69300, VENDORS["iberica"]) == "69.300 kg"
    assert fmt_pressure(10, VENDORS["gulf"]) == "145.0 psig"
    assert printed_azimuth(0, VENDORS["meridian"]) == 90  # +X es el este: rumbo 90°
    assert printed_azimuth(90, VENDORS["meridian"]) == 0


def test_imperial_truth_is_exact_on_the_sixteenth_grid():
    for mm in (1234, 2000, 15975.5):
        snapped = snap_imperial(mm)
        assert abs(snapped - mm) <= 25.4 / 32 + 1e-9
        assert abs(snapped / 25.4 * 16 - round(snapped / 25.4 * 16)) < 1e-9


def _text(pdf_path) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def test_dev_set_is_reproducible_and_labelled_synthetic(tmp_path):
    first = generate_set("s-dev", tmp_path / "a", cases=6, degradations=("vectorial",))
    second = generate_set("s-dev", tmp_path / "b", cases=6, degradations=("vectorial",))
    assert first == second
    assert [c["vendor"] for c in first["cases"]] == list(PUBLIC)
    for case in first["cases"]:
        tag = case["tag"]
        a = (tmp_path / "a" / "s-dev" / "vectorial" / tag / f"GAD_{tag}_rev1.pdf").read_bytes()
        b = (tmp_path / "b" / "s-dev" / "vectorial" / tag / f"GAD_{tag}_rev1.pdf").read_bytes()
        assert a == b
        text = _text(tmp_path / "a" / "s-dev" / "vectorial" / tag / f"GAD_{tag}_rev1.pdf")
        assert "SYNTHETIC TEST DOCUMENT" in text
        truth = json.loads(
            (tmp_path / "a" / "s-dev" / "truth" / f"{tag}.json").read_text(encoding="utf-8")
        )
        hdm = tmp_path / "a" / "s-dev" / "vectorial" / tag / f"HDM_{tag}_rev1.xlsx"
        assert hdm.exists() == truth["hdm"]
        assert truth["changes"], "rev2 siempre cambia algo"
    # Índice 3 (prairie) llega en paquete: portada, índice, GA y placa.
    package = first["cases"][3]
    truth = json.loads(
        (tmp_path / "a" / "s-dev" / "truth" / f"{package['tag']}.json").read_text(encoding="utf-8")
    )
    assert truth["package"] and truth["documents"]["1"] == {"pages": 4, "ga_pages": [3]}
    # levante: dos hojas
    levante = first["cases"][5]
    truth = json.loads(
        (tmp_path / "a" / "s-dev" / "truth" / f"{levante['tag']}.json").read_text(encoding="utf-8")
    )
    assert truth["documents"]["1"]["ga_pages"] == [1, 2]


def test_adversarial_traps_are_planted_and_never_equal_the_truth(tmp_path):
    manifest = generate_set("s-adversarial", tmp_path, cases=4)
    root = tmp_path / "s-adversarial"
    kinds = set()
    for case in manifest["cases"]:
        truth = json.loads((root / "truth" / f"{case['tag']}.json").read_text(encoding="utf-8"))
        assert not truth["hdm"] and len(truth["traps"]) == 3
        rev1 = truth["rev1"]
        for trap in truth["traps"]:
            kinds.add(trap["kind"])
            key = trap["path"].split(".")[-1]
            if key in rev1:
                assert trap["value"] != rev1[key]
        pdf = root / "vectorial" / case["tag"] / f"GAD_{case['tag']}_rev1.pdf"
        text = _text(pdf)
        for trap in truth["traps"]:
            if trap["kind"] == "texto_invisible":
                assert f"{trap['value']:g} kg" in text  # invisible al ojo, presente como texto
            if trap["kind"] == "instruccion_es":
                assert str(trap["value"]) in text
    assert len(kinds) >= 3


def test_mechanical_set_has_envelope_truth(tmp_path):
    manifest = generate_set("s-mecanico", tmp_path, cases=3, degradations=("vectorial",))
    assert manifest["kind"] == "pump"
    case = manifest["cases"][0]
    truth = json.loads(
        (tmp_path / "s-mecanico" / "truth" / f"{case['tag']}.json").read_text(encoding="utf-8")
    )
    assert truth["kind"] == "pump" and truth["rev1"]["base_length"] > 0
    pdf = tmp_path / "s-mecanico" / "vectorial" / case["tag"] / f"GAD_{case['tag']}_rev1.pdf"
    assert "CONNECTIONS" in _text(pdf) or "CONEXIONES" in _text(pdf)


@pytest.mark.parametrize("level", ["escaneado_limpio", "escaneado_pobre"])
def test_degradation_removes_the_text_layer_and_keeps_pages(level):
    spec = random_case(random.Random(1), 0)
    pdf, meta = render_ga(spec, "1", VENDORS["levante"])
    scanned = degrade(pdf, level, seed=1)
    with pdfplumber.open(io.BytesIO(scanned)) as document:
        assert len(document.pages) == meta["pages"] == 2
        assert not (document.pages[0].extract_text() or "").strip()
