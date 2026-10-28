import html

from .families.change_detection import (
    crosscheck,
    equal_value,
    geometry_delta,
    match_nozzles,
    visual_delta,
)
from .model import GEOMETRY_FIELDS, Revision, fields


def markdown_report(before: Revision, after: Revision, report: dict) -> str:
    """Salida legible del mismo delta JSON, con fuentes y huellas de ambas revisiones."""

    def text(value):
        return (
            html.escape(str(value))
            .replace("\\", "\\\\")
            .replace("|", "\\|")
            .replace("`", "\\`")
            .replace("\r", " ")
            .replace("\n", " ")
        )

    def value(item):
        return "—" if item is None else text(f"{item['value']} {item['unit']}")

    def evidence(source, revision):
        if source is None:
            return "Sin campo en esta revisión"
        document = next(d for d in revision.documents if d.id == source["document_id"])
        location = (
            f"página {source['page']}"
            if source.get("page")
            else f"hoja {source.get('sheet')}, celda {source.get('cell')}"
        )
        return text(f"{document.filename} · {location} · {source['locator']}") + (
            f" · SHA-256 `{document.sha256}`"
        )

    lines = [
        "# Informe de cambios",
        "",
        f"Proyecto {text(after.project_id)} · equipo {text(after.equipment.id)}.",
        "",
        "**Datos sintéticos.**"
        if before.dataset == after.dataset == "synthetic"
        else "Datos reales.",
        "",
        f"Revisión {text(before.revision)} → {text(after.revision)}.",
        f"Huella anterior: `{report['before_sha256']}`.",
        f"Huella nueva: `{report['after_sha256']}`.",
        "",
        "Estado anterior: " + ("APPROVED" if before.approval else "DRAFT") + ".",
        "Estado nuevo: " + ("APPROVED" if after.approval else "DRAFT") + ".",
        "La comparación no concede aprobación de diseño.",
        "",
        f"Cambios de diseño: {report['summary']['changes']}; "
        f"cambios de evidencia: {report['summary']['provenance_changes']}.",
        "",
        "| Campo | Operación | Antes | Después | Categoría | Disciplinas | Severidad | Acción |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for change in report["changes"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    text(change["path"]),
                    change["operation"],
                    value(change["before"]),
                    value(change["after"]),
                    change["category"],
                    text(", ".join(change["disciplines"])),
                    change["severity"],
                    text(change["suggested_action"]),
                ]
            )
            + " |"
        )
    lines += ["", "## Evidencias de los campos", ""]
    for change in [*report["changes"], *report["provenance_changes"]]:
        lines += [
            f"- **{text(change['path'])}**",
            f"  - Antes: {evidence(change.get('before_source'), before)}.",
            f"  - Después: {evidence(change.get('after_source'), after)}.",
        ]
    lines += ["", "## Documentos cambiados", ""]
    for document in report["document_changes"]:
        old, new = document["before"], document["after"]
        lines.append(
            f"- {text(document['id'])}: "
            + (text(old["filename"]) + f" (`{old['sha256']}`)" if old else "Ausente")
            + " → "
            + (text(new["filename"]) + f" (`{new['sha256']}`)" if new else "Ausente")
            + "."
        )
    if not report["document_changes"]:
        lines.append("Sin cambios en los documentos del contrato.")
    return "\n".join(lines) + "\n"


def change_impact(change: dict, before: Revision, after: Revision) -> dict:
    """Reglas de coordinación; no calculan esfuerzos ni conceden aprobación de diseño."""
    path = change["path"]
    category = (
        "identity"
        if path == "tag" or path.endswith(".id")
        else "geometry"
        if change["affects_geometry"]
        else "attribute"
    )
    if path.startswith("nozzles."):
        disciplines = ["Piping"]
        reasons = ["Cambia una conexión o su identificación."]
        marks = {path.split(".")[1]}
        if change["operation"] == "renamed":
            marks.add(change["before"]["value"])
        instrument = any(
            nozzle.service
            and any(
                token in str(nozzle.service.value).casefold()
                for token in ("instrument", "termopozo", "thermowell", "transmitter", "transmisor")
            )
            for revision in (before, after)
            for nozzle in revision.equipment.nozzles
            if nozzle.id in marks
        )
        if instrument:
            disciplines.append("I&C")
            reasons.append("El servicio de la boquilla identifica instrumentación.")
        if path.endswith(".rating"):
            disciplines.append("Mecánica")
            reasons.append("El rating afecta a la especificación de presión de la conexión.")
        severity = "high" if change["affects_geometry"] or path.endswith(".rating") else "medium"
        action = "Revisar conexión, isométricos y soportes de las líneas afectadas."
        if instrument:
            action += " Verificar también la conexión y documentación de instrumentación."
    elif path.startswith("skirt_") or (
        path.startswith("attributes.") and "weight" in path.rsplit(".", 1)[-1]
    ):
        disciplines = ["Civil", "Estructuras"]
        reasons = ["El soporte o el peso puede modificar cargas y anclajes."]
        severity = "high"
        action = "Comprobar cargas, cimentación, anclajes y estructura de soporte."
    elif path.startswith("attributes.") and any(
        token in path for token in ("pressure", "temperature")
    ):
        disciplines = ["Mecánica", "Procesos"]
        reasons = ["Cambia una condición de presión o temperatura del equipo."]
        severity = "high"
        action = "Revisar hoja de datos, condiciones de proceso y diseño mecánico."
    elif change["affects_geometry"]:
        disciplines = ["Mecánica", "Piping"]
        reasons = ["Cambia la envolvente, la familia o un componente geométrico."]
        severity = "high"
        action = "Comprobar implantación, interferencias e interfaces del equipo."
    else:
        disciplines = ["Mecánica"]
        reasons = ["Cambia una propiedad o la identificación del equipo."]
        severity = "medium"
        action = "Revisar la hoja de datos y actualizar las referencias del equipo."
    return {
        "category": category,
        "disciplines": disciplines,
        "severity": severity,
        "impact_reasons": reasons,
        "suggested_action": action,
        "impact": action,
    }


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
        {
            "id": key,
            "before": old_docs.get(key),
            "after": new_docs.get(key),
            "category": "documentary",
        }
        for key in sorted(old_docs.keys() | new_docs.keys())
        if old_docs.get(key) != new_docs.get(key)
    ]
    for change in changes:
        change.update(change_impact(change, before, after))
    for entry in provenance:
        entry.update(
            category="documentary",
            disciplines=[],
            severity="low",
            suggested_action="Verificar la nueva evidencia; el valor de diseño es equivalente.",
        )
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
