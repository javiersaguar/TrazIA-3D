from pathlib import Path

import ifcopenshell.util.element
import pytest

from trazia.ifc import build_ifc
from trazia.model import load_revision
from trazia.reference import internal_azimuth, metadata, nozzle_position, web_coordinates


def test_declared_north_cardinal_positions_and_ifc_metadata():
    revision = load_revision(Path(__file__).resolve().parents[1] / "examples/vessel_rev_a.json")
    assert internal_azimuth(90, north_deg=90) == 0
    assert internal_azimuth(0, north_deg=90) == 90
    assert web_coordinates(nozzle_position(1000, 2000, 90)) == pytest.approx((0, 2, -1))
    with pytest.raises(ValueError, match="Norte"):
        internal_azimuth(90, north_deg=None)
    assert not metadata()["TRReferenceVerified"]
    model = build_ifc(revision, plant_north_deg=90)
    north = model.by_type("IfcGeometricRepresentationContext", include_subtypes=False)[0].TrueNorth
    assert north.DirectionRatios == pytest.approx((0, 1))
    frame = ifcopenshell.util.element.get_psets(model.by_type("IfcBuildingStorey")[0])[
        "TrazIA_ReferenceFrame"
    ]
    assert frame["PlantNorthDeclared"] and not frame["TRReferenceVerified"]
