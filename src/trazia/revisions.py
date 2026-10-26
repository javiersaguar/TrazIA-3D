from .families.change_detection import (
    crosscheck,
    equal_value,
    geometry_delta,
    match_nozzles,
    visual_delta,
)
from .model import GEOMETRY_FIELDS, Revision, fields


def compare(
    before: Revision,
    after: Revision,
    *,
    tolerances=None,
    include_geometry=False,
    originals: dict[str, bytes] | None = None,
) -> dict:
    if (before.project_id, before.equipment.id) != (after.project_id, after.equipment.id):
        raise ValueError("Solo se pueden comparar revisiones del mismo proyecto y equipo")
    old, new = fields(before.equipment), fields(after.equipment)
    try:
        matches = match_nozzles(before.equipment, after.equipment)
        matching_status = "ok"
    except ImportError:
        matches = []
        matching_status = "requires-geo"
    changes, provenance = [], []
    renames = {
        m["before_id"]: m["after_id"]
        for m in matches
        if not m["ambiguous"] and m["before_id"] != m["after_id"]
    }
    old = {
        f"nozzles.{renames[key.split('.')[1]]}." + key.split(".", 2)[2]
        if key.startswith("nozzles.") and key.split(".")[1] in renames
        else key: value
        for key, value in old.items()
    }
    for match in matches:
        if match["ambiguous"] or match["before_id"] == match["after_id"]:
            continue
        changes.append(
            {
                "path": f"nozzles.{match['after_id']}.id",
                "operation": "renamed",
                "before": {"value": match["before_id"], "unit": "1"},
                "after": {"value": match["after_id"], "unit": "1"},
                "affects_geometry": False,
                "impact": "Revisar identidad y referencias de piping.",
                "before_source": None,
                "after_source": None,
                "identity_proposal": match,
            }
        )
    for path in sorted(old.keys() | new.keys()):
        left, right = old.get(path), new.get(path)
        evidence = {
            "before_source": left.source.model_dump(mode="json") if left else None,
            "after_source": right.source.model_dump(mode="json") if right else None,
        }
        previous = {"value": left.value, "unit": left.unit} if left else None
        current = {"value": right.value, "unit": right.unit} if right else None
        if not equal_value(left, right, path, tolerances=tolerances):
            geometry = (
                path in GEOMETRY_FIELDS
                or path.startswith(
                    ("envelope.", "horizontal.", "column.", "tank.", "platforms.", "ladders.")
                )
                or (path.startswith("nozzles.") and path.split(".")[2] not in ("service", "rating"))
            )
            impact = (
                "Actualizar boquilla; revisar interfaces con piping."
                if path.startswith("nozzles.")
                else "Actualizar envolvente o soporte; revisar interfaces de civil y piping."
                if geometry
                else "Actualizar propiedades IFC; revisar el dato técnico."
            )
            changes.append(
                {
                    "path": path,
                    "operation": "added" if not left else "removed" if not right else "modified",
                    "before": previous,
                    "after": current,
                    "affects_geometry": geometry,
                    "impact": impact,
                    **evidence,
                }
            )
        elif left and right and (left.source != right.source or previous != current):
            provenance.append({"path": path, "value_equivalent": previous != current, **evidence})
    for key in ("kind", "lod", "support"):
        a, b = getattr(before.equipment, key), getattr(after.equipment, key)
        if a != b:
            changes.append(
                {
                    "path": key,
                    "operation": "modified",
                    "before": {"value": a, "unit": "1"} if a is not None else None,
                    "after": {"value": b, "unit": "1"} if b is not None else None,
                    "affects_geometry": True,
                    "impact": "Revisar familia y detalle.",
                    "before_source": None,
                    "after_source": None,
                }
            )
    if (
        before.equipment.tank
        and after.equipment.tank
        and before.equipment.tank.roof != after.equipment.tank.roof
    ):
        changes.append(
            {
                "path": "tank.roof",
                "operation": "modified",
                "before": {"value": before.equipment.tank.roof, "unit": "1"},
                "after": {"value": after.equipment.tank.roof, "unit": "1"},
                "affects_geometry": True,
                "impact": "Revisar techo.",
                "before_source": None,
                "after_source": None,
            }
        )
    old_docs = {d.id: d.model_dump(mode="json") for d in before.documents}
    new_docs = {d.id: d.model_dump(mode="json") for d in after.documents}
    documents = [
        {"id": key, "before": old_docs.get(key), "after": new_docs.get(key)}
        for key in sorted(old_docs.keys() | new_docs.keys())
        if old_docs.get(key) != new_docs.get(key)
    ]
    visual = (
        visual_delta(before, after, originals)
        if originals is not None
        else {"status": "missing_originals", "pages": []}
    )
    geometry = (
        geometry_delta(before, after)
        if include_geometry
        else {"status": "not_requested", "elements": []}
    )
    return {
        "layers": {
            "visual": visual,
            "geometry": geometry,
            "crosschecks": crosscheck(changes, visual),
        },
        "nozzle_matching": {
            "status": matching_status,
            "matches": matches,
            "cost_is_probability": False,
        },
        "project_id": after.project_id,
        "equipment_id": after.equipment.id,
        "from_revision": before.revision,
        "to_revision": after.revision,
        "summary": {
            "changes": len(changes),
            "geometry_changes": sum(c["affects_geometry"] for c in changes),
            "provenance_changes": len(provenance),
            "document_changes": len(documents),
        },
        "changes": changes,
        "provenance_changes": provenance,
        "document_changes": documents,
        "before_sha256": before.fingerprint(),
        "after_sha256": after.fingerprint(),
    }
