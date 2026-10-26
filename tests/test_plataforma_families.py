import copy
import hashlib
import json

import ifcopenshell.util.element
import ifcopenshell.validate
import numpy as np
import pytest
from pydantic import ValidationError

from trazia.ifc import build_ifc
from trazia.model import Revision, fields
from trazia.viewer import meshes_from_ifc


def traced(value, unit="mm"):
    return {
        "value": value,
        "unit": unit,
        "source": {
            "document_id": "FAMILY-TEST",
            "page": 1,
            "locator": "Parámetro sintético de prueba",
            "confidence": 1.0,
        },
    }


def vector(x, y, z, unit="mm"):
    return {axis: traced(value, unit) for axis, value in zip("xyz", (x, y, z))}


def family_data(kind, lod=2):
    equipment = {
        "id": "test-001",
        "tag": traced("T-001", "1"),
        "kind": kind,
        "lod": lod,
        "nozzles": [],
    }
    if lod == 1:
        equipment["envelope"] = {"origin": vector(-1000, 500, 0), "size": vector(2000, 3000, 4000)}
    elif kind == "horizontal_vessel":
        equipment["horizontal"] = {
            key: traced(value)
            for key, value in {
                "diameter": 2000,
                "length": 6000,
                "head_depth": 500,
                "support_height": 800,
                "saddle_width": 400,
                "saddle_span": 1400,
            }.items()
        }
        equipment["horizontal"]["saddle_positions"] = [traced(1200), traced(4800)]
    elif kind == "column":
        equipment["column"] = {
            "sections": [
                {"id": "lower", "diameter": traced(2000), "height": traced(3000)},
                {
                    "id": "transition",
                    "diameter": traced(2000),
                    "top_diameter": traced(1200),
                    "height": traced(1000),
                },
                {"id": "upper", "diameter": traced(1200), "height": traced(4000)},
            ]
        }
    elif kind == "tank":
        equipment["tank"] = {
            "diameter": traced(6000),
            "height": traced(7000),
            "roof": "conical",
            "roof_height": traced(1000),
        }
    return {
        "schema_version": "0.3",
        "project_id": "FAMILY-TEST",
        "revision": "A",
        "dataset": "synthetic",
        "documents": [
            {
                "id": "FAMILY-TEST",
                "filename": "synthetic-fixture.txt",
                "revision": "A",
                "sha256": hashlib.sha256(b"synthetic-family-parameters").hexdigest(),
                "page_count": 1,
            }
        ],
        "equipment": equipment,
    }


def validate(data):
    return Revision.model_validate_json(json.dumps(data))


def assert_valid(model):
    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(model, logger, express_rules=True)
    assert not logger.statements, logger.statements


@pytest.mark.parametrize(
    "kind",
    ["vertical_vessel", "horizontal_vessel", "column", "tank", "pump", "compressor", "generic"],
)
def test_level_one_all_kinds_roundtrip_bounds_and_trace(kind):
    revision = validate(family_data(kind, 1))
    model = build_ifc(revision)
    assert_valid(model)
    meshes = meshes_from_ifc(model.to_string())
    assert len(meshes) == 1
    points = np.asarray(meshes[0]["vertices"]).reshape(-1, 3)
    assert points.min(axis=0) == pytest.approx([-1, 0.5, 0])
    assert points.max(axis=0) == pytest.approx([1, 3.5, 4])
    product = model.by_guid(meshes[0]["guid"])
    trace = ifcopenshell.util.element.get_psets(product)["TrazIA_Traceability"]
    assert trace["LOD"] == 1 and trace["Family"] == kind and trace["Draft"]
    assert len(json.loads(trace["FieldsJSON"])) == 7


@pytest.mark.parametrize(
    "kind,bounds,products",
    [
        ("horizontal_vessel", ([-0.5, -1, 0], [6.5, 1, 2.8]), 5),
        ("column", ([-1, -1, 0], [1, 1, 8]), 3),
        ("tank", ([-3, -3, 0], [3, 3, 8]), 2),
    ],
)
def test_parametric_families_shapes_ids_trace(kind, bounds, products):
    revision = validate(family_data(kind))
    model = build_ifc(revision)
    assert_valid(model)
    meshes = meshes_from_ifc(model.to_string())
    assert len(meshes) == products
    points = np.concatenate([np.asarray(m["vertices"]).reshape(-1, 3) for m in meshes])
    assert points.min(axis=0) == pytest.approx(bounds[0], abs=0.002)
    assert points.max(axis=0) == pytest.approx(bounds[1], abs=0.002)
    assert revision.equipment.total_height / 1000 == pytest.approx(bounds[1][2])
    revision.revision = "B"
    assert {m["name"]: m["guid"] for m in meshes} == {
        m["name"]: m["guid"] for m in meshes_from_ifc(build_ifc(revision).to_string())
    }
    for product in model.by_type("IfcElement"):
        trace = ifcopenshell.util.element.get_psets(product)["TrazIA_Traceability"]
        assert trace["LOD"] == 2
    if kind == "column":
        assert "column.sections.transition.top_diameter" in fields(revision.equipment)


@pytest.mark.parametrize(
    "mutation",
    ["missing", "negative", "saddles", "gap", "level3", "pump2", "port", "zero_direction"],
)
def test_reject_missing_or_inconsistent_family_evidence(mutation):
    data = family_data("horizontal_vessel")
    eq = data["equipment"]
    if mutation == "missing":
        del eq["horizontal"]
    if mutation == "negative":
        eq["horizontal"]["length"]["value"] = -1
    if mutation == "saddles":
        eq["horizontal"]["saddle_positions"][1]["value"] = 6100
    if mutation == "gap":
        data = family_data("column")
        data["equipment"]["column"]["sections"][1]["diameter"]["value"] = 1500
    if mutation == "level3":
        eq["lod"] = 3
    if mutation == "pump2":
        data = family_data("pump")
    if mutation in ("port", "zero_direction"):
        nozzle = {
            "id": "N1",
            "diameter": traced(100),
            "projection": traced(300),
            "elevation": traced(2000),
            "azimuth": traced(0, "deg"),
        }
        if mutation == "zero_direction":
            nozzle.update(position=vector(1000, 0, 2000), direction=vector(0, 0, 0, "1"))
        eq["nozzles"] = [nozzle]
    with pytest.raises(ValidationError):
        validate(data)


def test_level_three_flange_platform_ladder_and_nonradial_nozzle():
    data = family_data("tank", 3)
    eq = data["equipment"]
    eq["nozzles"] = [
        {
            "id": "N1",
            "diameter": traced(100),
            "projection": traced(300),
            "elevation": traced(8000),
            "azimuth": traced(0, "deg"),
            "position": vector(0, 0, 8000),
            "direction": vector(0, 0, 1, "1"),
            "nozzle_type": "top",
            "rating": traced("150", "1"),
            "flange": {"outer_diameter": traced(230), "thickness": traced(25)},
        }
    ]
    eq["platforms"] = [
        {"id": "P1", "origin": vector(3000, -1000, 6000), "size": vector(1000, 2000, 100)}
    ]
    eq["ladders"] = [
        {
            "id": "L1",
            "origin": vector(4000, 0, 0),
            "width": traced(500),
            "height": traced(6000),
            "rail_diameter": traced(30),
            "rung_spacing": traced(300),
        }
    ]
    revision = validate(data)
    assert "nozzles.N1.direction.z" in fields(revision.equipment)
    assert "platforms.P1.size.z" in fields(revision.equipment)
    model = build_ifc(revision)
    assert_valid(model)
    meshes = meshes_from_ifc(model.to_string())
    assert len(meshes) == 6
    assert all(m["faces"] for m in meshes)
    # Los campos de detalles también bloquean la aprobación.
    assert "nozzles.N1.flange.thickness" in revision.pending_review()
    new = copy.deepcopy(data)
    new["equipment"]["nozzles"][0]["direction"]["x"]["value"] = 1
    assert validate(new).fingerprint() != revision.fingerprint()
