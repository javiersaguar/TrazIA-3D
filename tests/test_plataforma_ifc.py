import json
from pathlib import Path

import ifcopenshell.util.element
import ifcopenshell.util.placement
import pytest
from test_plataforma_families import family_data, validate

from trazia.cli import main
from trazia.ifc import build_ifc, stable_guid, validate_ifc
from trazia.model import load_revision
from trazia.review import approve
from trazia.viewer import meshes_from_ifc

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@pytest.mark.parametrize("schema", ["IFC4", "IFC4X3", "IFC2X3"])
@pytest.mark.parametrize(
    "kind,lod",
    [("horizontal_vessel", 2), ("column", 2), ("tank", 2), ("pump", 1), ("compressor", 1)],
)
def test_schema_families_are_valid_and_preserve_guid(schema, kind, lod):
    revision = validate(family_data(kind, lod))
    model = build_ifc(revision, schema=schema)
    assert not validate_ifc(model)
    meshes = meshes_from_ifc(model.to_string())
    root = model.by_guid(stable_guid("FAMILY-TEST/equipment/test-001"))
    assert root.Name == "T-001"
    assert root.is_a(
        "IfcFlowMovingDevice"
        if schema == "IFC2X3" and kind in ("pump", "compressor")
        else "IfcFlowStorageDevice"
        if schema == "IFC2X3"
        else "IfcPump"
        if kind == "pump"
        else "IfcCompressor"
        if kind == "compressor"
        else "IfcTank"
    )
    assert meshes and not model.by_type("IfcApproval")
    assert not any(m["name"].endswith("/port") for m in meshes)
    trace = ifcopenshell.util.element.get_psets(root)["TrazIA_Provenance"]
    assert trace["Draft"] and trace["LOD"] == lod


@pytest.mark.parametrize("schema", ["IFC4", "IFC4X3", "IFC2X3"])
def test_ports_documents_human_approval_and_stable_products(schema):
    revision = load_revision(EXAMPLES / "vessel_rev_a.json")
    draft = build_ifc(revision, schema=schema)
    assert not validate_ifc(draft)
    assert len(draft.by_type("IfcDistributionPort")) == 3
    port = next(p for p in draft.by_type("IfcDistributionPort") if p.Name == "V-101/N1/port")
    placement = ifcopenshell.util.placement.get_local_placement(port.ObjectPlacement)
    assert placement[:3, 3] == pytest.approx([1.4, 0, 2.5])
    assert placement[:3, 2] == pytest.approx([1, 0, 0])
    assert port.FlowDirection == "NOTDEFINED"
    docs = draft.by_type("IfcDocumentReference")
    assert {d.Location for d in docs} == {f"urn:sha256:{d.sha256}" for d in revision.documents}
    assert len(draft.by_type("IfcRelAssociatesDocument")) == 2
    assert not draft.by_type("IfcApproval")
    approved = approve(
        revision,
        "Revisor de prueba",
        {d.id: (EXAMPLES / "documents" / d.filename).read_bytes() for d in revision.documents},
    )
    final = build_ifc(approved, draft=False, schema=schema)
    assert not validate_ifc(final)
    assert len(final.by_type("IfcApproval")) == 1
    assert final.by_type("IfcApproval")[0].Identifier == approved.fingerprint()
    for name in ("V-101", "V-101/top_head", "V-101/bottom_head", "V-101/skirt", "V-101/N1"):
        before = next(p for p in draft.by_type("IfcElement") if p.Name == name)
        after = next(p for p in final.by_type("IfcElement") if p.Name == name)
        assert before.GlobalId == after.GlobalId
    root = next(p for p in final.by_type("IfcElement") if p.Name == "V-101")
    assert len(root.IsDecomposedBy[0].RelatedObjects) == 6
    data = json.loads(approved.model_dump_json())
    data["equipment"]["height"]["value"] += 1
    with pytest.raises(ValueError):
        validate(data)


def test_geometry_distances_measure_surface_and_units():
    trimesh = pytest.importorskip("trimesh")
    pytest.importorskip("rtree")
    from trazia.families.metrics import surface_distances

    cube = trimesh.creation.box(extents=(1, 1, 1))

    def data(mesh):
        return {
            "vertices": mesh.vertices.reshape(-1).tolist(),
            "faces": mesh.faces.reshape(-1).tolist(),
        }

    same = surface_distances(data(cube), data(cube), samples=64)
    assert same["hausdorff_sampled"] < 1e-12 and same["chamfer"] < 1e-12
    assert same["bbox_iou"] == 1
    moved = cube.copy()
    moved.apply_translation([0.2, 0, 0])
    shifted = surface_distances(data(cube), data(moved), samples=64)
    assert shifted["unit"] == "m" and shifted["hausdorff_sampled"] == pytest.approx(0.2)
    assert 0 < shifted["chamfer"] < 0.2
    assert shifted["bbox_iou"] == pytest.approx(2 / 3)
    assert shifted == surface_distances(data(cube), data(moved), samples=64)
    assert len(shifted["before_vertex_distances"]) == 8
    assert not shifted["hausdorff_is_continuous_bound"]


def test_ifc_validation_cli_detects_corrupt_file(tmp_path, capsys):
    model = build_ifc(load_revision(EXAMPLES / "vessel_rev_a.json"))
    path = tmp_path / "valid.ifc"
    model.write(str(path))
    assert main(["validate-ifc", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["valid"]
    root = model.by_type("IfcTank")[0]
    root.GlobalId = "invalid"
    model.write(str(path))
    assert main(["validate-ifc", str(path)]) == 1
    assert not json.loads(capsys.readouterr().out)["valid"]


def test_external_reference_can_match_unique_names_with_different_guids():
    pytest.importorskip("trimesh")
    pytest.importorskip("rtree")
    from trazia.families.metrics import compare_ifc

    data = family_data("pump", 1)
    a = build_ifc(validate(data)).to_string()
    data["project_id"] = "REFERENCE"
    b = build_ifc(validate(data)).to_string()
    assert len(compare_ifc(a, b, samples=16)["elements"]) == 2
    matched = compare_ifc(a, b, samples=16, match="name")
    assert len(matched["elements"]) == 1
    assert matched["elements"][0]["hausdorff_sampled"] < 1e-12
