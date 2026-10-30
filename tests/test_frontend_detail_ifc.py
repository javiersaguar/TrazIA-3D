"""Regresión de geometría de detalle: datos sintéticos y sin GPU."""

from pathlib import Path

import ifcopenshell.util.element
import numpy as np
import pytest

from trazia.families.detail import bolt_holes, flange_pattern
from trazia.ifc import build_ifc, validate_ifc
from trazia.model import Attribute, FlangeParameters, load_revision
from trazia.viewer import meshes_from_ifc

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@pytest.mark.parametrize("schema", ["IFC4", "IFC4X3", "IFC2X3"])
def test_details_validate_tessellate_and_keep_original_identity(schema):
    revision = load_revision(EXAMPLES / "vessel_rev_a.json")
    basic = build_ifc(revision, details=False, schema=schema)
    detailed = build_ifc(revision, schema=schema, details=True)
    assert not validate_ifc(detailed)
    products = {p.Name: p for p in detailed.by_type("IfcElement")}
    assert len(products) == 73
    for old in basic.by_type("IfcElement"):
        assert products[old.Name].GlobalId == old.GlobalId
    meshes = meshes_from_ifc(detailed.to_string())
    assert len(meshes) == 73
    assert all(m["faces"] and np.isfinite(m["vertices"]).all() for m in meshes)
    flange = products["V-101/nozzle-N1/flange"]
    profile = flange.Representation.Representations[0].Items[0].SweptArea
    assert profile.is_a("IfcArbitraryProfileDefWithVoids")
    assert len(profile.InnerCurves) == 9  # bore más ocho taladros reales, no marcas dibujadas.
    assert all(c.Radius > 0 for c in profile.InnerCurves)
    props = ifcopenshell.util.element.get_psets(flange)["Pset_TrazIA"]
    assert props["Origen"] == "derivado_de_norma" and not props["LeidoDelPlano"]
    assert props["ClaseOrigen"] == "supuesto_visual" and props["NumeroTaladros"] == 8
    skirt = products["V-101/skirt"].Representation.Representations[0].Items[0]
    assert skirt.is_a("IfcBooleanResult") and skirt.Operator == "DIFFERENCE"
    for product in detailed.by_type("IfcElement"):
        identity = ifcopenshell.util.element.get_psets(product)["TrazIA_Identity"]
        if identity["ParentComponentId"]:
            assert ifcopenshell.util.element.get_psets(product)["Pset_TrazIA"][
                "RequiereVerificacion"
            ]


def test_norm_table_exact_lookup_and_hole_centers():
    pattern = flange_pattern(100, "150")
    assert (pattern.pitch, pattern.count, pattern.hole) == (190.5, 8, 19)
    assert all(np.hypot(x, y) == pytest.approx(0.09525) for x, y, _ in bolt_holes(pattern))
    assert flange_pattern(100, "300").count == 8
    assert flange_pattern(101, "150") is None
    assert flange_pattern(100, "PN16") is None
    assert flange_pattern(100, "900") is None


def test_no_implicit_supplement_for_real_documents_and_unsupported_rating():
    revision = load_revision(EXAMPLES / "vessel_rev_a.json")
    revision.dataset = "real"
    assert len(build_ifc(revision).by_type("IfcElement")) == 7
    revision.dataset = "synthetic"
    # Sin tabla no se improvisa un patrón de brida.
    revision.equipment.nozzles[0].rating = revision.equipment.tag.model_copy(
        update={"value": "900"}
    )
    model = build_ifc(revision, details=True)
    assert "V-101/nozzle-N1/flange" not in {p.Name for p in model.by_type("IfcElement")}


def test_derived_guids_survive_revision_and_dimension_changes():
    left = load_revision(EXAMPLES / "vessel_rev_a.json")
    right = load_revision(EXAMPLES / "vessel_rev_b.json")
    a = {p.Name: p.GlobalId for p in build_ifc(left, details=True).by_type("IfcElement")}
    b = {p.Name: p.GlobalId for p in build_ifc(right, details=True).by_type("IfcElement")}
    assert all(b[name] == guid for name, guid in a.items())
    assert "V-101/nozzle-N4/flange" in b


def test_explicit_flange_keeps_read_dimensions_and_guid_with_derived_drilling():
    revision = load_revision(EXAMPLES / "vessel_rev_a.json")
    revision.equipment.lod = 3
    nozzle = revision.equipment.nozzles[0]
    nozzle.rating = Attribute(value="300", unit="1", source=nozzle.diameter.source)
    nozzle.flange = FlangeParameters(
        outer_diameter=nozzle.diameter.model_copy(update={"value": 400}).model_dump(),
        thickness=nozzle.projection.model_copy(update={"value": 45}).model_dump(),
    )
    basic = build_ifc(revision)
    detailed = build_ifc(revision, details=True)
    old = next(p for p in basic.by_type("IfcElement") if p.Name == "V-101/N1/flange")
    new = detailed.by_guid(old.GlobalId)
    plate = new.Representation.Representations[0].Items[0]
    assert plate.Depth == pytest.approx(0.045)
    assert plate.SweptArea.OuterCurve.Radius == pytest.approx(0.2)
    assert len(plate.SweptArea.InnerCurves) == 13
    assert not validate_ifc(detailed)
