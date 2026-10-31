"""Lector de la verdad de referencia (G.1): IFC propios con los nombres borrados, nunca reales."""

import random

import ifcopenshell
import pytest

from bench.ifc_geometry import compare_models
from bench.referencia import compare_revision, read_reference
from synthetic.cases import random_case, spec_to_revision
from trazia.ifc import build_ifc


@pytest.fixture(scope="module")
def spec():
    return random_case(random.Random(2026), 0)


@pytest.fixture(scope="module")
def revision(spec):
    return spec_to_revision(spec, "1")


def anonymous(model: ifcopenshell.file) -> ifcopenshell.file:
    """Como un IFC externo: nuestros nombres no dicen nada."""
    for index, element in enumerate(model.by_type("IfcElement")):
        element.Name = f"Solid {index}"
        element.Tag = None
    return model


def test_reads_dimensions_and_nozzles_without_relying_on_names(spec, revision):
    reference = read_reference(anonymous(build_ifc(revision, draft=True)))
    assert reference["axis"] == "z"
    assert reference["diameter"] == pytest.approx(spec.diameter, abs=1)
    assert reference["shell_length"] == pytest.approx(spec.height, abs=1)
    assert reference["overall_height"] == pytest.approx(
        spec.skirt_height + spec.height + spec.head_depth, abs=1
    )
    radial = [n for n in reference["nozzles"] if n["type"] == "radial"]
    assert len(radial) == len(spec.nozzles)
    expected = sorted((n.elevation, n.azimuth, n.projection, n.diameter) for n in spec.nozzles)
    for got, (elevation, azimuth, projection, diameter) in zip(radial, expected, strict=True):
        assert got["elevation"] == pytest.approx(elevation, abs=1)
        assert got["azimuth"] == pytest.approx(azimuth, abs=0.5)
        assert got["projection"] == pytest.approx(projection, abs=2)
        assert got["diameter"] == pytest.approx(diameter, abs=2)


def test_a_perfect_revision_scores_zero_error(revision):
    reference = read_reference(anonymous(build_ifc(revision, draft=True)))
    result = compare_revision(revision, reference)
    assert result["dimensions"]["diameter"]["error_mm"] < 1
    assert result["convention"] == {"sign": 1, "offset": 0.0, "fitted": True}
    nozzles = result["nozzles"]
    assert nozzles["missing"] == nozzles["extra"] == 0
    assert nozzles["position_error_max_mm"] < 5


def test_a_wrong_reading_is_measured_and_a_lost_nozzle_is_counted(revision):
    reference = read_reference(anonymous(build_ifc(revision, draft=True)))
    wrong = revision.model_copy(deep=True)
    wrong.equipment.diameter.value += 40.0
    wrong.equipment.nozzles[0].elevation.value += 100.0
    del wrong.equipment.nozzles[-1]
    result = compare_revision(wrong, reference, convention={"sign": 1, "offset": 0.0})
    assert result["dimensions"]["diameter"]["error_mm"] == pytest.approx(40, abs=1)
    assert result["convention"]["fitted"] is False
    assert result["nozzles"]["missing"] == 1
    assert result["nozzles"]["position_error_max_mm"] == pytest.approx(100, abs=25)


def test_another_azimuth_convention_is_found_and_flagged_as_fitted(revision):
    reference = read_reference(anonymous(build_ifc(revision, draft=True)))
    clockwise = revision.model_copy(deep=True)
    for nozzle in clockwise.equipment.nozzles:
        nozzle.azimuth.value = (90.0 - nozzle.azimuth.value) % 360  # horario desde +Y
    result = compare_revision(clockwise, reference)
    assert result["convention"] == {"sign": -1, "offset": 90.0, "fitted": True}
    assert result["nozzles"]["position_error_max_mm"] < 5


def test_a_model_in_one_solid_leaves_nozzles_unmeasured_not_zero(revision):
    model = anonymous(build_ifc(revision, draft=True))
    for element in model.by_type("IfcElement")[1:]:
        element.Representation = None
    reference = read_reference(model)
    assert reference["nozzles"] is None
    assert any("Un solo elemento" in note for note in reference["notes"])
    result = compare_revision(revision, reference)
    assert result["nozzles"] is None and "sin medir" in result["nozzle_note"]


def test_external_names_no_longer_collapse_into_a_single_element(revision):
    ours = build_ifc(revision, draft=True)
    result = compare_models(ours, anonymous(build_ifc(revision, draft=True)))
    assert len(result["elements"]) == len(ours.by_type("IfcElement"))
    assert sum(row["found"] for row in result["elements"]) <= 1
