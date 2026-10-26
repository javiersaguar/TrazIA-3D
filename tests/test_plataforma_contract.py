import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from trazia.model import Revision, fields, migrate_revision

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/vessel_rev_a.json"


def example():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def test_migration_is_non_mutating_and_removes_approval():
    old = example()
    old["schema_version"] = "0.2"
    old["approval"] = {"legacy": True}
    saved = copy.deepcopy(old)
    migrated = migrate_revision(old)
    assert old == saved
    assert migrated["schema_version"] == "0.3"
    assert migrated["approval"] is None
    model = Revision.model_validate_json(json.dumps(migrated))
    assert all(f.state == "candidate" for f in fields(model.equipment).values())
    assert migrate_revision(migrated) == migrated


def test_extended_provenance_states_and_intervals():
    data = example()
    data["schema_version"] = "0.3"
    field = data["equipment"]["diameter"]
    field.update(state="corrected", interval={"low": 1999.0, "high": 2001.0, "level": 0.9})
    field["source"].update(
        channel="humano",
        strategy="d_hibrido",
        grounded=True,
        confidence_raw=0.8,
        unit_original="m",
        text_original="2 m",
    )
    model = Revision.model_validate_json(json.dumps(data))
    assert model.equipment.diameter.source.reviewed is True
    dumped = model.model_dump(mode="json")
    dumped["equipment"]["diameter"]["state"] = "conflict"
    assert (
        Revision.model_validate_json(json.dumps(dumped)).equipment.diameter.source.reviewed is False
    )
    field["interval"]["high"] = 1990.0
    with pytest.raises(ValidationError, match="inferior"):
        Revision.model_validate_json(json.dumps(data))


def test_alternative_sources_are_validated():
    data = example()
    data["schema_version"] = "0.3"
    field = data["equipment"]["diameter"]
    alternative = {"value": 1900.0, "unit": "mm", "source": copy.deepcopy(field["source"])}
    alternative["source"]["document_id"] = "UNKNOWN"
    field["alternatives"] = [alternative]
    with pytest.raises(ValidationError, match="desconocido"):
        Revision.model_validate_json(json.dumps(data))


def test_lod1_envelope_signed_origin_and_positive_size():
    data = example()
    source = data["equipment"]["tag"]["source"]

    def vector(values):
        return {
            axis: {"value": float(v), "unit": "mm", "source": source}
            for axis, v in zip("xyz", values)
        }

    data["schema_version"] = "0.3"
    data["equipment"] = {
        "id": "P101",
        "tag": data["equipment"]["tag"],
        "kind": "pump",
        "nozzles": [],
        "lod": 1,
        "envelope": {"origin": vector([-100, 0, 0]), "size": vector([2000, 1000, 800])},
    }
    model = Revision.model_validate_json(json.dumps(data))
    assert len(fields(model.equipment)) == 7
    assert model.equipment.envelope.origin.x.value == -100
    data["equipment"]["envelope"]["size"]["x"]["value"] = 0.0
    with pytest.raises(ValidationError, match="positivos"):
        Revision.model_validate_json(json.dumps(data))


def test_vertical_requires_geometry_and_nozzles():
    data = example()
    data["schema_version"] = "0.3"
    data["equipment"]["diameter"] = None
    with pytest.raises(ValidationError, match="cinco dimensiones"):
        Revision.model_validate_json(json.dumps(data))
