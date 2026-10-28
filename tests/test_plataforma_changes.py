import copy
import io
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import numpy as np
import pytest

from trazia.bcf import export_bcf
from trazia.families.change_detection import (
    geometry_delta,
    match_nozzles,
    preserve_nozzle_identity,
    visual_diff_images,
)
from trazia.ifc import build_ifc
from trazia.model import load_revision
from trazia.revisions import compare

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def revision():
    return load_revision(EXAMPLES / "vessel_rev_a.json")


@pytest.mark.parametrize(
    "path,disciplines,category",
    [
        ("attributes.design_pressure", ["Mecánica", "Procesos"], "attribute"),
        ("attributes.design_temperature", ["Mecánica", "Procesos"], "attribute"),
        ("attributes.operating_weight", ["Civil", "Estructuras"], "attribute"),
        ("skirt_height", ["Civil", "Estructuras"], "geometry"),
        ("height", ["Mecánica", "Piping"], "geometry"),
        ("nozzles.N1.elevation", ["Piping"], "geometry"),
    ],
)
def test_change_disciplines_have_reason_and_action(path, disciplines, category):
    from trazia.model import fields

    before = revision()
    original = before.model_dump_json()
    after = before.model_copy(deep=True)
    fields(after.equipment)[path].value += 5
    changes = compare(before, after)["changes"]
    change = next(c for c in changes if c["path"] == path)
    assert change["category"] == category
    assert change["disciplines"] == disciplines
    assert change["severity"] == "high"
    assert change["impact_reasons"] and change["suggested_action"]
    assert before.model_dump_json() == original


def test_instrument_nozzle_change_involves_instrumentation_and_piping():
    from trazia.model import Attribute

    before = revision()
    after = before.model_copy(deep=True)
    nozzle = after.equipment.nozzles[0]
    nozzle.service = Attribute(
        value="Termopozo / thermowell", unit="1", source=nozzle.diameter.source
    )
    nozzle.elevation.value += 5
    change = next(c for c in compare(before, after)["changes"] if c["path"].endswith(".elevation"))
    assert change["disciplines"] == ["Piping", "I&C"]
    assert "instrumentación" in change["suggested_action"]


def test_tag_and_evidence_changes_are_not_labelled_geometric():
    before = revision()
    after = before.model_copy(deep=True)
    after.equipment.tag.value = "V-102"
    after.equipment.height.source.locator = "Otra región con la misma cota"
    result = compare(before, after)
    assert next(c for c in result["changes"] if c["path"] == "tag")["category"] == "identity"
    provenance = next(c for c in result["provenance_changes"] if c["path"] == "height")
    assert provenance["category"] == "documentary"
    assert provenance["severity"] == "low" and provenance["disciplines"] == []


@pytest.mark.parametrize(
    "path,value,unit", [("design_pressure", 1000.0, "kPa"), ("design_temperature", 572.0, "degF")]
)
def test_equivalent_units_are_provenance_changes(path, value, unit):
    before = revision()
    after = before.model_copy(deep=True)
    # El fixture usa 10 bar y 300 C, respectivamente.
    old = before.equipment.attributes[path]
    if path == "design_pressure":
        value = old.value * 100
    else:
        value = old.value * 9 / 5 + 32
    after.equipment.attributes[path].value = value
    after.equipment.attributes[path].unit = unit
    report = compare(before, after)
    assert report["summary"]["changes"] == 0
    assert any(
        c["path"] == f"attributes.{path}" and c["value_equivalent"]
        for c in report["provenance_changes"]
    )


def test_incompatible_units_are_not_silently_equivalent():
    before = revision()
    after = before.model_copy(deep=True)
    after.equipment.attributes["design_pressure"].unit = "kg"
    assert compare(before, after)["summary"]["changes"] == 1


def test_renamed_nozzle_keeps_product_and_port_guid_after_identity_reconciliation():
    before = revision()
    after = before.model_copy(deep=True)
    after.revision = "B"
    after.equipment.nozzles[0].id = "N101"
    mapping = match_nozzles(before.equipment, after.equipment)
    renamed = next(m for m in mapping if m["after_id"] == "N101")
    assert renamed["method"].startswith("hungarian") and not renamed["ambiguous"]
    result = preserve_nozzle_identity(before, after)
    assert result.equipment.nozzles[0].stable_id == "N1"
    assert after.equipment.nozzles[0].stable_id is None and result.approval is None
    a, b = build_ifc(before), build_ifc(result)
    for cls, old, new in (
        ("IfcPipeSegment", "V-101/N1", "V-101/N101"),
        ("IfcDistributionPort", "V-101/N1/port", "V-101/N101/port"),
    ):
        assert next(p.GlobalId for p in a.by_type(cls) if p.Name == old) == next(
            p.GlobalId for p in b.by_type(cls) if p.Name == new
        )
    report = compare(before, result, include_geometry=True)
    assert [c["operation"] for c in report["changes"]] == ["renamed"]
    assert report["layers"]["geometry"]["elements"] == []
    moved = result.model_copy(deep=True)
    moved.equipment.nozzles[0].elevation.value += 3000
    assert (
        next(
            m for m in match_nozzles(before.equipment, moved.equipment) if m["after_id"] == "N101"
        )["method"]
        == "stable-id"
    )


def test_ambiguous_hungarian_matches_do_not_assign_identity():
    before = revision()
    same = copy.deepcopy(before.equipment.nozzles[0])
    same.id = "N2"
    before.equipment.nozzles[1] = same
    after = before.model_copy(deep=True)
    after.equipment.nozzles[0].id = "X1"
    after.equipment.nozzles[1].id = "X2"
    matches = match_nozzles(before.equipment, after.equipment)
    assert all(m["ambiguous"] for m in matches if m["method"].startswith("hungarian"))
    result = preserve_nozzle_identity(before, after)
    assert all(n.stable_id is None for n in result.equipment.nozzles)


def test_numeric_tolerance_does_not_change_data_or_approval_fingerprint():
    before = revision()
    after = before.model_copy(deep=True)
    after.equipment.height.value += 0.05
    report = compare(before, after, include_geometry=True)
    assert report["summary"]["changes"] == 0
    assert report["layers"]["geometry"]["elements"] == []
    assert before.fingerprint() != after.fingerprint()
    assert compare(before, after, tolerances={"height": 0.001})["summary"]["changes"] == 1


def drawing():
    import cv2

    image = np.full((512, 512, 3), 255, dtype=np.uint8)
    for y in (80, 160, 240, 400):
        cv2.putText(image, f"V101 TEST {y}", (100, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cv2.rectangle(image, (30, 30), (480, 480), (0, 0, 0), 2)
    return image


def test_ecc_removes_page_translation_and_preserves_actual_change():
    import cv2

    before = drawing()
    after = cv2.warpAffine(
        before,
        np.array([[1, 0, 6], [0, 1, 4]], dtype=np.float32),
        (512, 512),
        borderValue=(255, 255, 255),
    )
    cv2.rectangle(after, (300, 300), (320, 320), (0, 0, 0), -1)
    result, image = visual_diff_images(before, after, return_png=True)
    assert result["status"] == "ok"
    assert np.asarray(result["warp"])[:, 2] == pytest.approx([6, 4], abs=0.4)
    assert 0 < result["changed_pixel_fraction"] < 0.02
    assert result["regions"] and image.startswith(b"\x89PNG")


def test_unalignable_page_is_reported_instead_of_attributing_pixel_changes():
    blank = np.full((512, 512, 3), 255, dtype=np.uint8)
    result, image = visual_diff_images(blank, drawing(), return_png=True)
    assert result["status"] == "unaligned" and image is None


def test_revision_marker_candidates_are_explicitly_heuristic():
    import cv2

    image = drawing()
    cv2.polylines(
        image, [np.array([[40, 350], [60, 310], [80, 350]], dtype=np.int32)], True, (0, 0, 0), 2
    )
    angles = np.linspace(0, 2 * np.pi, 360)
    radii = 40 + 6 * np.cos(12 * angles)
    points = np.column_stack((400 + radii * np.cos(angles), 330 + radii * np.sin(angles))).astype(
        np.int32
    )
    cv2.polylines(image, [points], True, (0, 0, 0), 2)
    result, _ = visual_diff_images(image, image)
    kinds = {m["kind"] for m in result["markers"]}
    assert "delta_triangle_candidate" in kinds and "revision_cloud_candidate" in kinds
    assert all(m["method"] == "heuristic" for m in result["markers"])
    assert not result["regions"]


def test_three_layers_compare_actual_demo_originals():
    before = revision()
    after = load_revision(EXAMPLES / "vessel_rev_b.json")
    originals = {
        d.sha256: (EXAMPLES / "documents" / d.filename).read_bytes()
        for r in (before, after)
        for d in r.documents
    }
    report = compare(before, after, include_geometry=True, originals=originals)
    assert report["summary"]["changes"] == 8
    assert report["layers"]["geometry"]["status"] == "ok"
    assert report["layers"]["geometry"]["elements"]
    pages = report["layers"]["visual"]["pages"]
    assert pages and any(p["status"] == "ok" and p["changed_pixel_fraction"] > 0 for p in pages)


def test_bcf_topics_reference_real_guids_and_orthogonal_cameras():
    before = revision()
    after = load_revision(EXAMPLES / "vessel_rev_b.json")
    guids = {p.GlobalId for r in (before, after) for p in build_ifc(r).by_type("IfcElement")}
    with zipfile.ZipFile(io.BytesIO(export_bcf(before, after))) as archive:
        assert ElementTree.fromstring(archive.read("bcf.version")).get("VersionId") == "2.1"
        markups = [p for p in archive.namelist() if p.endswith("markup.bcf")]
        assert len(markups) == 8
        for path in markups:
            markup = ElementTree.fromstring(archive.read(path))
            assert markup.findtext("Topic/Labels") == "DRAFT"
            view = ElementTree.fromstring(
                archive.read(path.replace("markup.bcf", "viewpoint.bcfv"))
            )
            assert view.find("Components/Selection/Component").get("IfcGuid") in guids
            camera = view.find("OrthogonalCamera")
            direction = np.array([float(camera.findtext(f"CameraDirection/{a}")) for a in "XYZ"])
            up = np.array([float(camera.findtext(f"CameraUpVector/{a}")) for a in "XYZ"])
            assert np.linalg.norm(direction) == pytest.approx(1) and np.dot(
                direction, up
            ) == pytest.approx(0, abs=1e-12)


def test_geometry_layer_reports_added_removed_and_moved_guids():
    before = revision()
    after = load_revision(EXAMPLES / "vessel_rev_b.json")
    result = geometry_delta(before, after)
    assert any(e["operation"] == "added" for e in result["elements"])
    assert any(
        e["operation"] == "modified" and e["vertex_hausdorff_m"] > 0 for e in result["elements"]
    )
    assert any(e["operation"] == "removed" for e in geometry_delta(after, before)["elements"])


def test_crosscheck_transforms_evidence_to_aligned_page_frame():
    import cv2

    from trazia.families.change_detection import crosscheck

    before = drawing()
    after = cv2.warpAffine(
        before,
        np.array([[1, 0, 6], [0, 1, 4]], dtype=np.float32),
        (512, 512),
        borderValue=(255, 255, 255),
    )
    after[300:302, 400:402] = 0
    result, _ = visual_diff_images(before, after)
    assert result["status"] == "ok"
    changes = [
        {
            "path": "small",
            "after_source": {
                "document_id": "GA",
                "page": 1,
                "bbox": [400 / 512, 300 / 512, 402 / 512, 302 / 512],
            },
        }
    ]
    cross = crosscheck(changes, {"pages": [{"document_id": "GA", "page": 1, **result}]})
    assert not any(c["kind"] == "field_without_visual_region" for c in cross)


def test_visual_layer_rejects_mismatched_original_hash():
    from trazia.families.change_detection import visual_delta

    before = revision()
    after = load_revision(EXAMPLES / "vessel_rev_b.json")
    originals = {
        d.sha256: (EXAMPLES / "documents" / d.filename).read_bytes()
        for r in (before, after)
        for d in r.documents
    }
    originals[after.documents[0].sha256] = b"different original"
    assert visual_delta(before, after, originals)["pages"][0]["status"] == "hash_mismatch"
