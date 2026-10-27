"""Estrategia A (tarea 2.3): geometría desde los trazos y cruce alzado–planta."""

import io
import json

import pdfplumber
import pytest

from synthetic.cases import flatten, spec_from_dict
from synthetic.sets import generate_set
from trazia.geometry2d.vector import find_elevation, find_plan
from trazia.pipeline import InputDocument, process


@pytest.fixture(scope="module")
def dev_set(tmp_path_factory):
    root = tmp_path_factory.mktemp("v2")
    generate_set("s-dev", root, cases=6, degradations=("vectorial",))
    return root / "s-dev"


def _case(dev_set, index):
    manifest = json.loads((dev_set / "manifest.json").read_text(encoding="utf-8"))
    tag = manifest["cases"][index]["tag"]
    truth = json.loads((dev_set / "truth" / f"{tag}.json").read_text(encoding="utf-8"))
    return tag, truth


def test_strokes_give_the_drawing_geometry_without_reading_text(dev_set):
    tag, truth = _case(dev_set, 4)  # nordic
    spec = truth["rev1"]
    pdf = (dev_set / "vectorial" / tag / f"GAD_{tag}_rev1.pdf").read_bytes()
    with pdfplumber.open(io.BytesIO(pdf)) as document:
        page = document.pages[0]
        elevation = find_elevation(page)
        plan = find_plan(page, elevation.shell)
    scale = elevation.shell_height / spec["height"]  # escala de referencia para la prueba
    assert elevation.width / scale == pytest.approx(spec["diameter"], abs=1)
    assert elevation.skirt / scale == pytest.approx(spec["skirt_height"], abs=1)
    assert elevation.head_top / scale == pytest.approx(spec["head_depth"], abs=1)
    heights = sorted(round((elevation.ground - s.z) / scale) for s in elevation.stubs)
    assert heights == sorted(n["elevation"] for n in spec["nozzles"])
    angles = sorted(round(s.angle) % 360 for s in plan.stubs)
    assert angles == sorted(n["azimuth"] for n in spec["nozzles"])


@pytest.mark.parametrize("index", [0, 3, 4])
def test_strategy_a_builds_the_model_without_the_nozzle_table(dev_set, index):
    tag, truth = _case(dev_set, index)
    folder = dev_set / "vectorial" / tag
    docs = [
        InputDocument(p.name, p.read_bytes(), ("GA-" if p.name.startswith("GAD") else "HDM-") + tag)
        for p in sorted(folder.glob("*_rev1.*"))
    ]
    result = process(
        docs, project_id="P", equipment_id=tag.lower(), revision="1", strategy="a_geometria"
    )
    assert result.revision is not None, result.error
    assert not any("Tabla" in c.source.locator for c in result.candidates)
    expected = flatten(spec_from_dict(truth["rev1"]))
    found = {c.path: c for c in result.candidates}
    for path, (value, unit) in expected.items():
        if path.startswith("attributes.") or path == "tag" or path not in found:
            continue
        tolerance = 0.5 if unit == "deg" else 1.0
        assert float(found[path].value) == pytest.approx(value, abs=tolerance), path
    nozzle_fields = [p for p in expected if p.startswith("nozzles.")]
    # Si varias boquillas comparten orientación sus etiquetas se superponen en la planta: A deja
    # sin asignar lo que no puede decidir (nunca lo inventa). Por eso el umbral no es 100 %.
    assert sum(p in found for p in nozzle_fields) >= 0.75 * len(nozzle_fields)
