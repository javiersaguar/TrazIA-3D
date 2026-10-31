"""Diagnósticos de revisión: reglas geométricas simples, no comprobación normativa."""

import math
import re

from trazia.model import Revision, fields


def issues_for(error, edited_path=None):
    issues = []
    for item in error.errors():
        path = ".".join(str(p) for p in item["loc"] if p not in ("body", "equipment"))
        message = item["msg"].removeprefix("Value error, ")
        context = item.get("ctx", {})
        translations = {
            "missing": "Falta este dato obligatorio.",
            "float_type": "Escribe un número finito.",
            "float_parsing": "Escribe un número con punto decimal en el contrato JSON.",
            "int_type": "Escribe un número entero.",
            "string_type": "Escribe un texto.",
            "extra_forbidden": "Este campo no pertenece al contrato.",
            "literal_error": f"Valor no admitido: {context.get('expected', 'otro valor')}.",
            "greater_than": f"El valor debe ser mayor que {context.get('gt')}.",
            "greater_than_equal": f"El valor debe ser al menos {context.get('ge')}.",
            "less_than": f"El valor debe ser menor que {context.get('lt')}.",
            "less_than_equal": f"El valor debe ser como máximo {context.get('le')}.",
            "finite_number": "El número debe ser finito.",
        }
        message = translations.get(item["type"], message)
        nozzle = re.search(r"Boquilla ([^:]+):", message)
        if nozzle:
            path = f"nozzles.{nozzle[1]}.elevation"
        path = path or edited_path or "$revision"
        if "unit" in path or "unidad" in message:
            action = "Convierte la unidad del plano: mm para longitudes y deg para ángulos."
        elif "virola" in message or "suelo" in message or "fondo" in message:
            action = (
                "Contrasta elevación, diámetro, longitud y fondos con sus evidencias del plano."
            )
        elif any(
            token in message + path
            for token in ("documento", "página", "bbox", "document_id", "page")
        ):
            action = "Selecciona un documento de esta revisión, una página válida y su región."
        else:
            action = "Revisa el valor y su evidencia; corrige el campo indicado y vuelve a guardar."
        issues.append({"path": path, "message": message, "action": action})
    return issues


def diagnostics(revision: Revision):
    issues = []
    for path, traced in fields(revision.equipment).items():
        if traced.state in ("conflict", "abstained"):
            issues.append(
                {
                    "path": path,
                    "severity": "review",
                    "code": traced.state,
                    "message": "La lectura requiere confirmación humana.",
                    "action": "Contrasta las evidencias y acepta, corrige o rechaza la lectura.",
                }
            )
        if traced.alternatives:
            from trazia.families.change_detection import equal_value

            agreement = all(equal_value(traced, alt, path) for alt in traced.alternatives)
            issues.append(
                {
                    "path": path,
                    "severity": "info" if agreement else "review",
                    "code": "equivalent_alternatives" if agreement else "document_disagreement",
                    "message": "Las alternativas son equivalentes."
                    if agreement
                    else "Las evidencias discrepan en el valor o la unidad.",
                    "action": "Compara valor, unidad y documento de cada alternativa.",
                }
            )
    equipment = revision.equipment
    if equipment.kind == "vertical_vessel" and equipment.diameter is not None:
        radius = equipment.diameter.value / 2
        radial = [n for n in equipment.nozzles if n.position is None]
        for i, a in enumerate(radial):
            for b in radial[i + 1 :]:
                angle = math.radians((a.azimuth.value - b.azimuth.value + 180) % 360 - 180)
                arc = radius * angle
                separation = math.hypot(arc, a.elevation.value - b.elevation.value)
                if separation < (a.diameter.value + b.diameter.value) / 2:
                    issues.append(
                        {
                            "path": f"nozzles.{a.id}.elevation",
                            "related_path": f"nozzles.{b.id}.elevation",
                            "severity": "warning",
                            "code": "possible_overlap",
                            "message": f"Posible solape de las aberturas {a.id} y {b.id}.",
                            "action": (
                                "Comprueba posiciones y diámetros en el plano. Cribado sobre la "
                                "virola desplegada; no certifica bridas ni soldaduras."
                            ),
                        }
                    )
    return {"issues": issues, "normative_check": False}


REFERENCE_SYSTEM = {
    "schema_version": "1",
    "handedness": "right",
    "origin": "Centro del equipo en planta y cota de suelo local; sin georreferenciación",
    "vertical_axis": "+Z",
    "contract_length_unit": "mm",
    "ifc_length_unit": "m",
    "azimuth_zero_axis": "+X",
    "azimuth_90_axis": "+Y",
    "azimuth_rotation": "counterclockwise_viewed_from_positive_Z",
    "web_ifc_mapping": "(X,Y,Z) IFC → (X,Z,-Y) Three.js; conversión aplicada por web-ifc",
    "plant_north": None,
    "tr_reference_verified": False,
    "detail": (
        "Convenio interno comprobable con los IFC sintéticos; Norte de planta y convenio TR "
        "pendientes de contraste con una referencia autorizada."
    ),
}
