import json
from pathlib import Path

import pytest

from scripts.scale_pitch import analyse
from trazia.api.validation import REFERENCE_SYSTEM
from trazia.families import nozzle_frame
from trazia.ifc import build_ifc
from trazia.model import load_revision

ROOT = Path(__file__).resolve().parents[1]


def test_pitch_keeps_every_failure_and_does_not_price_unknown_human_work():
    report = json.loads((ROOT / "docs/evidencias/fase3/31oct/d-workers-4.json").read_text())
    result, failures = analyse(report, worker_rate=0.25)
    assert len(failures) == 163
    assert not result["acceptance"]["all_revisions_have_draft_ifc"]
    scenario = result["project_scenario"]
    assert scenario["terminal_seconds"] == pytest.approx(4929.38449837619)
    assert scenario["components"]["compute_eur"] == pytest.approx(1.36927347177116)
    assert scenario["valid_ifc_seconds"] is None
    assert scenario["components"]["human_eur"] is None and scenario["total_scenario_eur"] is None
    incomplete = {**report, "complete": False}
    assert analyse(incomplete)[0]["project_scenario"]["terminal_seconds"] is None


def test_reference_matches_cardinal_nozzle_frames_and_export_units():
    revision = load_revision(ROOT / "examples/vessel_rev_a.json")
    equipment = revision.equipment
    nozzle = equipment.nozzles[0]
    radius = equipment.diameter.value / 2000
    z = nozzle.elevation.value / 1000
    for angle, expected in (
        (0, (radius, 0, z)),
        (90, (0, radius, z)),
        (180, (-radius, 0, z)),
        (270, (0, -radius, z)),
    ):
        nozzle.azimuth.value = angle
        position, _ = nozzle_frame(equipment, nozzle)
        assert position == pytest.approx(expected)
    model = build_ifc(revision, draft=True)
    (length,) = [unit for unit in model.by_type("IfcSIUnit") if unit.UnitType == "LENGTHUNIT"]
    assert length.Name == "METRE" and length.Prefix is None
    assert REFERENCE_SYSTEM["azimuth_zero_axis"] == "+X"
    assert REFERENCE_SYSTEM["azimuth_90_axis"] == "+Y"
    assert REFERENCE_SYSTEM["plant_north"] is None
    assert not REFERENCE_SYSTEM["tr_reference_verified"]
