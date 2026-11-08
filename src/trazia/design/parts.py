"""Operaciones estructurales K.8: catálogo cerrado, unidades y snapshots reversibles."""

import copy
import math
import re
from typing import Literal

from pydantic import Field

from trazia.model import Identifier, LadderParameters, Model, Nozzle, PlatformParameters
from trazia.units import normalize


class PartValue(Model):
    value: float | str
    unit: str


class PartChange(Model):
    action: Literal["add", "remove"]
    collection: Literal["nozzles", "platforms", "ladders"]
    id: Identifier
    parameters: dict[str, PartValue] = Field(default_factory=dict, max_length=16)


MODELS = {"nozzles": Nozzle, "platforms": PlatformParameters, "ladders": LadderParameters}
PARAMETERS = {
    "nozzles": ("diameter", "projection", "elevation", "azimuth"),
    "platforms": ("x", "y", "z", "size_x", "size_y", "size_z"),
    "ladders": ("x", "y", "z", "width", "height", "rail_diameter", "rung_spacing"),
}
EXPLICIT = ("x", "y", "z", "dx", "dy", "dz")


def semantic(value):
    """Compara datos de pieza; aceptar una fuente no cambia su geometría ni identidad."""
    if isinstance(value, dict):
        if "value" in value and "source" in value:
            return {"value": value["value"], "unit": value["unit"]}
        return {k: semantic(v) for k, v in value.items()}
    if isinstance(value, list):
        return [semantic(v) for v in value]
    return value


def _component(change, equipment, source):
    explicit = change.collection == "nozzles" and equipment.kind != "vertical_vessel"
    required = set(PARAMETERS[change.collection])
    if explicit:
        required = {"diameter", "projection", *EXPLICIT}
    if set(change.parameters) != required:
        raise ValueError("Parámetros requeridos: " + ", ".join(sorted(required)))
    values = {}
    for key, item in change.parameters.items():
        dimensionless = key in {"dx", "dy", "dz"}
        if dimensionless:
            if item.unit != "1":
                raise ValueError("Las componentes de dirección usan unidad 1")
            value, unit = float(item.value), "1"
        else:
            magnitude = "angle" if key == "azimuth" else "length"
            parsed = normalize(f"{item.value} {item.unit}", magnitude, default_unit=None)
            if parsed.notices:
                raise ValueError("; ".join(parsed.notices))
            value, unit = parsed.value, parsed.unit
        if not math.isfinite(value):
            raise ValueError("El parámetro debe ser finito")
        values[key] = {
            "value": value,
            "unit": unit,
            "source": source.model_copy(
                update={
                    "text_original": f"{item.value} {item.unit}",
                    "unit_original": item.unit,
                }
            ).model_dump(mode="json"),
            "state": "candidate",
        }

    def vector(prefix=""):
        return {axis: values[prefix + axis] for axis in "xyz"}

    data = {"id": change.id}
    if change.collection == "nozzles":
        data.update({k: values[k] for k in ("diameter", "projection")})
        data["stable_id"] = f"design-{source.design.proposal_id[:12]}-{change.id}"
        if explicit:
            data.update(position=vector(), direction=vector("d"), nozzle_type="inclined")
            data["elevation"] = values["z"]
            data["azimuth"] = {
                **values["dx"],
                "unit": "deg",
                "source": source.model_copy(
                    update={
                        "text_original": "atan2(dy, dx): azimut derivado de dirección explícita",
                        "unit_original": "deg",
                    }
                ).model_dump(mode="json"),
                "value": math.degrees(math.atan2(values["dy"]["value"], values["dx"]["value"]))
                % 360,
            }
        else:
            data.update(
                elevation=values["elevation"], azimuth=values["azimuth"], nozzle_type="radial"
            )
    elif change.collection == "platforms":
        data.update(origin=vector(), size=vector("size_"))
    else:
        data.update(
            origin=vector(),
            **{k: values[k] for k in ("width", "height", "rail_diameter", "rung_spacing")},
        )
    return MODELS[change.collection].model_validate(data)


def apply_changes(base, candidate, changes, detail_level, source_factory, evaluation):
    if detail_level is not None:
        if detail_level < base.lod:
            evaluation.issues.append(
                {
                    "severity": "error",
                    "code": "lod",
                    "message": "No se reduce el nivel de detalle al editar piezas.",
                    "path": "lod",
                    "operation_id": None,
                }
            )
        candidate.lod = detail_level
    records, seen = [], set()
    supported = candidate.lod >= 2 and candidate.kind in {
        "vertical_vessel",
        "horizontal_vessel",
        "column",
        "tank",
    }
    for index, change in enumerate(changes, 1):
        op_id = f"part-{index}"
        path = f"{change.collection}.{change.id}"
        try:
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", change.id) or change.id in {
                "shell",
                "top_head",
                "bottom_head",
                "skirt",
                "roof",
            }:
                raise ValueError(
                    "ID reservado o no válido: usa letra seguida de letras, "
                    "números, guion o subrayado (máximo 64)."
                )
            if not supported:
                raise ValueError("Esta familia/LOD no admite piezas detalladas")
            if path in seen:
                raise ValueError("No se puede añadir y eliminar la misma pieza en el lote")
            seen.add(path)
            collection = getattr(candidate, change.collection)
            existing = next((p for p in collection if p.id == change.id), None)
            before = existing.model_dump(mode="json") if existing else None
            if change.action == "add":
                if existing:
                    raise ValueError("Ya existe una pieza con ese ID")
                if change.collection != "nozzles" and candidate.lod != 3:
                    raise ValueError("Esta pieza requiere seleccionar explícitamente LOD 3")
                item = _component(change, candidate, source_factory(op_id))
                collection.append(item)
                after = item.model_dump(mode="json")
            else:
                if existing is None:
                    raise ValueError("La pieza que se quiere eliminar no existe")
                if change.parameters:
                    raise ValueError("Una baja no recibe parámetros nuevos")
                collection.remove(existing)
                after = None
            record = {
                "id": op_id,
                "target": path,
                "path": path,
                "action": change.action,
                "collection": change.collection,
                "part_id": change.id,
                "label": ("Añadir " if change.action == "add" else "Eliminar ") + path,
                "input": {
                    "text": change.action,
                    "unit_original": None,
                    "datum": None,
                    "parameters": change.model_dump(mode="json")["parameters"],
                },
                "before": {"value": path if before else "No existe", "unit": "1"},
                "after": {"value": path if after else "Eliminada", "unit": "1"},
                "before_part": before,
                "after_part": after,
            }
            evaluation.operations.append(record)
            records.append(record)
        except (ValueError, TypeError, OverflowError) as error:
            evaluation.issues.append(
                {
                    "severity": "error",
                    "code": "part",
                    "message": str(error),
                    "path": path,
                    "operation_id": op_id,
                }
            )
    if candidate.kind == "vertical_vessel" and candidate.lod >= 2 and len(candidate.nozzles) < 3:
        evaluation.issues.append(
            {
                "severity": "error",
                "code": "minimum_nozzles",
                "message": "Esta familia requiere al menos tres boquillas.",
                "path": "nozzles",
                "operation_id": None,
            }
        )
    return records


def restore_change(candidate, record, evaluation):
    collection = getattr(candidate.equipment, record["collection"])
    current = next((p for p in collection if p.id == record["part_id"]), None)
    data = current.model_dump(mode="json") if current else None
    if semantic(data) != semantic(record["after_part"]):
        evaluation.issues.append(
            {
                "severity": "error",
                "code": "changed_after_apply",
                "message": "La pieza cambió después de aplicar la orden.",
                "path": record["path"],
                "operation_id": record["id"],
            }
        )
        return None
    if current:
        collection.remove(current)
    restored = record["before_part"]
    if restored:
        collection.append(MODELS[record["collection"]].model_validate(restored))
    inverse = copy.deepcopy(record)
    inverse.update(
        action="remove" if record["action"] == "add" else "add",
        before_part=data,
        after_part=restored,
        before=record["after"],
        after=record["before"],
        label="Deshacer " + record["label"],
    )
    evaluation.operations.append(inverse)
    return inverse


def attachment_issues(equipment):
    """La boquilla explícita debe arrancar en la virola soportada, dirigida hacia fuera."""
    for nozzle in equipment.nozzles:
        if nozzle.position is None:
            if equipment.kind != "vertical_vessel":
                yield (
                    nozzle.id,
                    "Fuera del recipiente vertical se requiere posición y dirección explícitas.",
                )
            continue
        x, y, z = (getattr(nozzle.position, a).value for a in "xyz")
        dx, dy, dz = (getattr(nozzle.direction, a).value for a in "xyz")
        radius = nozzle.diameter.value / 2
        if equipment.kind == "vertical_vessel":
            valid = (
                equipment.shell_bottom + radius
                <= z
                <= equipment.shell_bottom + equipment.height.value - radius
                and radius < equipment.diameter.value / 2
                and abs(math.hypot(x, y) - equipment.diameter.value / 2) <= 0.5
                and x * dx + y * dy > 0
            )
        elif equipment.kind == "horizontal_vessel":
            p = equipment.horizontal
            center = p.support_height.value + p.diameter.value / 2
            distance = math.hypot(y, z - center)
            valid = (
                radius < p.diameter.value / 2
                and radius <= x <= p.length.value - radius
                and abs(distance - p.diameter.value / 2) <= 0.5
                and abs(dx) < 1e-6
                and y * dy + (z - center) * dz > 0
            )
        elif equipment.kind == "tank":
            p = equipment.tank
            valid = (
                radius < p.diameter.value / 2
                and radius <= z <= p.height.value - radius
                and abs(math.hypot(x, y) - p.diameter.value / 2) <= 0.5
                and abs(dz) < 1e-6
                and x * dx + y * dy > 0
            )
        elif equipment.kind == "column":
            bottom, valid = 0, False
            for section in equipment.column.sections:
                top = bottom + section.height.value
                if bottom + radius <= z <= top - radius:
                    r0 = section.diameter.value / 2
                    r1 = (section.top_diameter or section.diameter).value / 2
                    surface = r0 + (r1 - r0) * (z - bottom) / section.height.value
                    valid = (
                        radius < surface
                        and abs(math.hypot(x, y) - surface) <= 0.5
                        and x * dx + y * dy > 0
                    )
                    break
                bottom = top
        else:
            continue
        if not valid:
            yield (
                nozzle.id,
                "Posición/dirección incompatible con la superficie de la "
                "virola; revise el lote completo.",
            )
