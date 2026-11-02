"""Detectar corrupciones métricas y de propiedades aunque el esquema siga siendo válido."""

import json
from pathlib import Path

import pytest

from trazia.families.audit import audit_ifc
from trazia.ifc import build_ifc
from trazia.model import load_revision


@pytest.fixture
def source():
    return load_revision(Path(__file__).resolve().parents[1] / "examples/vessel_rev_b.json")


@pytest.mark.parametrize("schema", ["IFC4", "IFC4X3", "IFC2X3"])
def test_audit_reopened_step_checks_geometry_units_properties_and_ports(source, schema):
    before = source.model_dump_json()
    report = audit_ifc(source, build_ifc(source, schema=schema))
    assert report["valid"], report["issues"]
    assert report["unit_scale_to_m"] == 1
    assert report["components"]["shell"]["max_bbox_error_m"] < 1e-9
    assert len(report["ports"]) == len(source.equipment.nozzles)
    assert not report["bimvision_measured"] and not report["tr_reference_available"]
    assert source.model_dump_json() == before


@pytest.mark.parametrize(
    "failure,code",
    [
        ("unit", "units"),
        ("missing_unit", "units"),
        ("draft", "traceability"),
        ("fields", "fields_roundtrip"),
        ("technical", "technical_property"),
        ("placement", "dimensions"),
        ("direction", "port_direction"),
    ],
)
def test_audit_rejects_semantic_or_metric_corruption(source, failure, code):
    model = build_ifc(source)
    if failure == "unit":
        next(u for u in model.by_type("IfcSIUnit") if u.UnitType == "LENGTHUNIT").Prefix = "MILLI"
    elif failure == "missing_unit":
        model.by_type("IfcProject")[0].UnitsInContext = None
    elif failure == "placement":
        model.by_type("IfcTank")[0].ObjectPlacement.RelativePlacement.Location.Coordinates = (
            0.0,
            0.0,
            1.0,
        )
    elif failure == "direction":
        model.by_type("IfcDistributionPort")[
            0
        ].ObjectPlacement.RelativePlacement.Axis.DirectionRatios = (0.0, 0.0, 1.0)
    else:
        pset_name = {
            "draft": "TrazIA_Traceability",
            "fields": "TrazIA_Traceability",
            "technical": "TrazIA_Technical",
        }[failure]
        pset = next(p for p in model.by_type("IfcPropertySet") if p.Name == pset_name)
        name = {"draft": "Draft", "fields": "FieldsJSON", "technical": "design_pressure"}[failure]
        prop = next(p for p in pset.HasProperties if p.Name == name)
        if failure == "draft":
            prop.NominalValue.wrappedValue = False
        elif failure == "technical":
            prop.NominalValue.wrappedValue = "1600 bar"
        else:
            value = json.loads(prop.NominalValue.wrappedValue)
            value["diameter"]["value"] = 1
            prop.NominalValue.wrappedValue = json.dumps(value)
    report = audit_ifc(source, model)
    assert not report["valid"]
    assert code in {i["code"] for i in report["issues"]}
