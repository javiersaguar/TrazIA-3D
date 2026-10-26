import copy
import io
import json
from collections import Counter
from pathlib import Path

import ifcopenshell
import ifcopenshell.util.element
import ifcopenshell.util.placement
import ifcopenshell.util.unit
import ifcopenshell.validate
import numpy as np
import pytest
from openpyxl import Workbook
from PIL import Image
from pydantic import ValidationError

from trazia.cli import main
from trazia.extraction import LabelExtractor, assemble
from trazia.ifc import build_ifc, export_ifc, head_mesh
from trazia.ingest import ingest_bytes, render_evidence
from trazia.model import Revision, load_revision
from trazia.review import approve, verify_originals
from trazia.revisions import compare
from trazia.viewer import figure, meshes_from_ifc

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def validate(data):
    return Revision.model_validate_json(json.dumps(data))


@pytest.fixture
def data():
    return json.loads((EXAMPLES / "vessel_rev_a.json").read_text(encoding="utf-8"))


@pytest.fixture
def revision():
    return load_revision(EXAMPLES / "vessel_rev_a.json")


def originals(revision):
    return {d.id: (EXAMPLES / "documents" / d.filename).read_bytes() for d in revision.documents}


@pytest.mark.parametrize("value", [0, -1, True, "2000", None])
def test_invalid_dimensions(data, value):
    data["equipment"]["diameter"]["value"] = value
    with pytest.raises(ValidationError):
        validate(data)


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_nonfinite_dimensions(revision, value):
    revision.equipment.diameter.value = value
    with pytest.raises(ValidationError):
        build_ifc(revision)


@pytest.mark.parametrize(
    "case", ["unit", "document", "duplicate", "height", "extra", "hash", "page", "skirt", "count"]
)
def test_invalid_contract(data, case):
    if case == "unit":
        data["equipment"]["diameter"]["unit"] = "m"
    elif case == "document":
        data["equipment"]["height"]["source"]["document_id"] = "unknown"
    elif case == "duplicate":
        data["equipment"]["nozzles"].append(copy.deepcopy(data["equipment"]["nozzles"][0]))
    elif case == "height":
        data["equipment"]["nozzles"][0]["elevation"]["value"] = 9000
    elif case == "extra":
        data["equipment"]["invented"] = 123
    elif case == "hash":
        del data["documents"][0]["sha256"]
    elif case == "page":
        data["equipment"]["height"]["source"]["page"] = 2
    elif case == "skirt":
        data["equipment"]["skirt_thickness"]["value"] = 1000
    else:
        data["equipment"]["nozzles"] = data["equipment"]["nozzles"][:2]
    with pytest.raises(ValidationError):
        validate(data)


def test_document_revisions_are_independent(data):
    data["documents"][1]["revision"] = "0"
    assert validate(data).documents[1].revision == "0"


def test_diff_values_units_order_and_document_hashes(data):
    before = validate(data)
    reordered = copy.deepcopy(data)
    reordered["equipment"]["nozzles"].reverse()
    assert compare(before, validate(reordered))["summary"]["changes"] == 0
    after = load_revision(EXAMPLES / "vessel_rev_b.json")
    report = compare(before, after)
    assert report["summary"]["changes"] == 8
    assert report["summary"]["geometry_changes"] == 7
    assert report["summary"]["document_changes"] == 2
    by_path = {c["path"]: c for c in report["changes"]}
    assert by_path["nozzles.N3.elevation"]["after"] == {"value": 3700.0, "unit": "mm"}
    assert by_path["attributes.operating_weight"]["before"]["value"] == 12000
    reverse = compare(after, before)
    assert sum(c["operation"] == "removed" for c in reverse["changes"]) == 4
    data["equipment"]["attributes"]["design_pressure"]["unit"] = "MPa"
    assert compare(before, validate(data))["summary"]["changes"] == 1


def test_provenance_and_identity(data):
    before = validate(data)
    data["equipment"]["height"]["source"]["locator"] = "Otra zona"
    report = compare(before, validate(data))
    assert report["summary"]["changes"] == 0
    assert report["summary"]["provenance_changes"] == 1
    data["project_id"] = "other-project"
    with pytest.raises(ValueError, match="mismo proyecto"):
        compare(before, validate(data))


def test_review_hashes_and_approval_invalidation(revision, tmp_path):
    with pytest.raises(ValueError, match="sin revisar"):
        export_ifc(revision, tmp_path / "blocked.ifc")
    assert not (tmp_path / "blocked.ifc").exists()
    draft = build_ifc(revision)
    trace = ifcopenshell.util.element.get_psets(draft.by_type("IfcTank")[0])
    assert trace["TrazIA_Traceability"]["Draft"] is True
    with pytest.raises(ValueError, match="falta el original"):
        approve(revision, "Test reviewer", {})
    wrong = originals(revision)
    wrong["GA-V101"] = b"modified document"
    assert verify_originals(revision, wrong)
    approved = approve(revision, "Test reviewer", originals(revision))
    assert approved.approval and approved.pending_review() == []
    assert not revision.approval and revision.pending_review()
    path = export_ifc(approved, tmp_path / "approved.ifc")
    assert path.exists()
    data = json.loads(approved.model_dump_json())
    data["equipment"]["height"]["value"] += 100
    with pytest.raises(ValidationError, match="no corresponde"):
        validate(data)


def test_ifc_schema_geometry_trace_and_stable_ids():
    identifiers = []
    for suffix in ("a", "b"):
        revision = load_revision(EXAMPLES / f"vessel_rev_{suffix}.json")
        model = build_ifc(revision)
        logger = ifcopenshell.validate.json_logger()
        ifcopenshell.validate.validate(model, logger, express_rules=True)
        assert not logger.statements, logger.statements
        assert model.schema == "IFC4"
        assert ifcopenshell.util.unit.calculate_unit_scale(model) == 1.0
        tank = model.by_type("IfcTank")[0]
        solid = tank.Representation.Representations[0].Items[0]
        assert solid.SweptArea.Radius == 1.0
        assert solid.Depth == revision.equipment.height.value / 1000
        trace = ifcopenshell.util.element.get_psets(tank)["TrazIA_Traceability"]
        assert trace["Dataset"] == "synthetic"
        assert json.loads(trace["FieldsJSON"])["height"]["source"]["document_id"] == "GA-V101"
        n1 = next(n for n in model.by_type("IfcPipeSegment") if n.Tag == "N1")
        placement = ifcopenshell.util.placement.get_local_placement(n1.ObjectPlacement)
        assert placement[:3, 3] == pytest.approx([1.0, 0.0, 2.5])
        assert placement[:3, 2] == pytest.approx([1.0, 0.0, 0.0])
        meshes = meshes_from_ifc(model.to_string())
        assert len(meshes) == 7 if suffix == "a" else len(meshes) == 8
        assert all(m["vertices"] and m["faces"] for m in meshes)
        points = np.concatenate([np.array(m["vertices"]).reshape(-1, 3) for m in meshes])
        assert points[:, 2].min() == pytest.approx(0.0)
        assert points[:, 2].max() == pytest.approx(revision.equipment.total_height / 1000)
        assert len(figure(meshes).data) == len(meshes)
        identifiers.append({m["component"]: m["guid"] for m in meshes})
    for component, guid in identifiers[0].items():
        assert identifiers[1][component] == guid


def test_heads_are_closed_and_have_positive_volume():
    for direction in (-1, 1):
        vertices, triangles = head_mesh(1.0, 0.5, 2.0, direction)
        edges = Counter(tuple(sorted((t[i], t[(i + 1) % 3]))) for t in triangles for i in range(3))
        assert set(edges.values()) == {2}
        points = np.array(vertices)
        volume = (
            sum(
                np.dot(points[a - 1], np.cross(points[b - 1], points[c - 1]))
                for a, b, c in triangles
            )
            / 6
        )
        assert volume == pytest.approx(2 * np.pi / 3 * 0.5, rel=0.02)


def test_ingest_extract_and_render_from_originals(revision):
    bundles = [
        ingest_bytes(content, document.filename, document.id, document.revision)
        for document in revision.documents
        for content in [originals(revision)[document.id]]
    ]
    assert all(not b.warnings for b in bundles)
    candidates = LabelExtractor().extract(bundles)
    assert len(candidates) == 22
    output = assemble(
        bundles,
        candidates,
        project_id=revision.project_id,
        equipment_id=revision.equipment.id,
        revision=revision.revision,
        dataset="synthetic",
    )
    assert output.fingerprint() == revision.fingerprint()
    height = next(c for c in candidates if c.path == "height")
    assert height.source.bbox and height.source.page == 1
    pressure = next(c for c in candidates if c.path == "attributes.design_pressure")
    assert pressure.source.sheet == "HDM" and pressure.source.cell == "A2:C2"
    image = render_evidence(originals(revision)["GA-V101"], "drawing.pdf", 1, height.source.bbox)
    assert image.width > 1000 and image.height > 600


def test_conflicts_missing_values_and_length_conversion(revision):
    bundle = ingest_bytes(originals(revision)["GA-V101"], "drawing.pdf", "GA-V101", "A")
    candidates = LabelExtractor().extract([bundle])
    conflict = candidates[1].model_copy(deep=True)
    conflict.value = 999.0
    with pytest.raises(ValueError, match="Conflicto"):
        assemble(
            [bundle], candidates + [conflict], project_id="DEMO", equipment_id="V101", revision="A"
        )
    with pytest.raises(ValueError, match="Faltan datos"):
        assemble([bundle], [], project_id="DEMO", equipment_id="V101", revision="A")
    line = bundle.lines[0].model_copy(deep=True)
    line.text = "DIAMETER = 2 m"
    bundle.lines = [line]
    assert LabelExtractor().extract([bundle])[0].value == 2000


def test_formulas_and_images_require_review():
    workbook = Workbook()
    workbook.active.append(["DESIGN_PRESSURE", "=8*2", "bar"])
    data = io.BytesIO()
    workbook.save(data)
    bundle = ingest_bytes(data.getvalue(), "formula.xlsx", "HDM", "A")
    assert bundle.warnings and not bundle.lines
    image = io.BytesIO()
    Image.new("RGB", (100, 100), "white").save(image, format="PNG")
    bundle = ingest_bytes(image.getvalue(), "scan.png", "SCAN", "A")
    assert bundle.warnings and not LabelExtractor().extract([bundle])
    with pytest.raises(ValueError, match="Formato"):
        ingest_bytes(b"data", "unsupported.txt", "DOC", "A")


def test_cli_errors_schema_and_ingestion(tmp_path, capsys):
    assert main(["validate", str(tmp_path / "missing.json")]) == 2
    assert "Error:" in capsys.readouterr().err
    schema = tmp_path / "schema.json"
    assert main(["schema", "-o", str(schema)]) == 0
    assert json.loads(schema.read_text(encoding="utf-8"))["title"] == "Revision"
    assert main(["validate", str(EXAMPLES / "vessel_rev_a.json")]) == 0
    assert json.loads(capsys.readouterr().out)["approved"] is False
    bundle = tmp_path / "bundle.json"
    assert (
        main(
            [
                "ingest",
                str(EXAMPLES / "documents" / "GAD_V-101_revA.pdf"),
                "--id",
                "GA-V101",
                "--revision",
                "A",
                "-o",
                str(bundle),
            ]
        )
        == 0
    )
    assert json.loads(bundle.read_text(encoding="utf-8"))["document"]["page_count"] == 1
