"""Borradores paramétricos y aislamiento del catálogo sintético."""

import ifcopenshell
from fastapi import FastAPI
from fastapi.testclient import TestClient
from ifcopenshell.util.element import get_psets

from trazia.api.process_previews import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)
ENDPOINT = "/proyectos-proceso/plataforma-marina/borrador"


def test_process_preview_regenerates_ifc_and_connected_nozzles():
    response = client.post(
        ENDPOINT,
        json={
            "applied": ["GS-04"],
            "adjustments": [
                {"tag": "V-110", "field": "width", "value": 3.8},
                {"tag": "GS-04", "field": "dn", "value": 475},
            ],
        },
    )
    assert response.status_code == 200, response.text[:500]
    assert "ENSAYO-DRAFT.ifc" in response.headers["Content-Disposition"]
    assert response.headers["Cache-Control"] == "no-store"
    model = ifcopenshell.file.from_string(response.text)
    by_tag = {entity.Tag: entity for entity in model.by_type("IfcElement") if entity.Tag}
    vessel = get_psets(by_tag["V-110"])["TrazIA_Traceability"]
    line = get_psets(by_tag["GS-04"])["TrazIA_Traceability"]
    assert vessel["NominalWidthM"] == 3.8
    assert vessel["Dataset"] == "synthetic" and vessel["Draft"] is True
    assert line["NominalDiameterMM"] == 475
    assert line["RackHeightM"] == 6.2
    for connection in model.by_type("IfcRelConnectsPorts"):
        assert (
            connection.RelatingPort.ObjectPlacement.RelativePlacement.Location.Coordinates
            == connection.RelatedPort.ObjectPlacement.RelativePlacement.Location.Coordinates
        )


def test_process_preview_rejects_fields_and_values_outside_the_fixture():
    for edit in (
        {"tag": "V-110", "field": "width", "value": 77.0},
        {"tag": "V-110/virola", "field": "width", "value": 3.7},
        {"tag": "GS-04", "field": "dn", "value": 474.2},
        {"tag": "V-110", "field": "rack_z", "value": 3},
    ):
        assert client.post(ENDPOINT, json={"adjustments": [edit]}).status_code == 422
