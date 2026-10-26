from .model import GEOMETRY_FIELDS, Revision, fields


def compare(before: Revision, after: Revision) -> dict:
    if (before.project_id, before.equipment.id) != (after.project_id, after.equipment.id):
        raise ValueError("Solo se pueden comparar revisiones del mismo proyecto y equipo")
    old, new = fields(before.equipment), fields(after.equipment)
    changes, provenance = [], []
    for path in sorted(old.keys() | new.keys()):
        left, right = old.get(path), new.get(path)
        evidence = {
            "before_source": left.source.model_dump(mode="json") if left else None,
            "after_source": right.source.model_dump(mode="json") if right else None,
        }
        previous = {"value": left.value, "unit": left.unit} if left else None
        current = {"value": right.value, "unit": right.unit} if right else None
        if previous != current:
            geometry = path in GEOMETRY_FIELDS or path.startswith("nozzles.")
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
        elif left.source != right.source:
            provenance.append({"path": path, **evidence})
    old_docs = {d.id: d.model_dump(mode="json") for d in before.documents}
    new_docs = {d.id: d.model_dump(mode="json") for d in after.documents}
    documents = [
        {"id": key, "before": old_docs.get(key), "after": new_docs.get(key)}
        for key in sorted(old_docs.keys() | new_docs.keys())
        if old_docs.get(key) != new_docs.get(key)
    ]
    return {
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
