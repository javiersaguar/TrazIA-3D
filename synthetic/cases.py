"""Recipientes verticales aleatorios, válidos para el núcleo, y revisiones con cambios conocidos.

Todo es sintético: sirve para medir el pipeline con verdad conocida, no para afirmar precisión
sobre planos reales.
"""

import hashlib
import json
import math
import random
from dataclasses import asdict, dataclass, replace

from trazia.model import Revision

DN = (50, 80, 100, 150, 200, 250, 300)
MATERIALS = ("SA-516-70", "SA-516-60", "SA-240-316L", "SA-537-CL1")
ATTRIBUTE_UNITS = {
    "design_pressure": "bar",
    "design_temperature": "C",
    "material": "1",
    "operating_weight": "kg",
}


@dataclass(frozen=True)
class NozzleSpec:
    id: str
    diameter: int
    projection: int
    elevation: int
    azimuth: int


@dataclass(frozen=True)
class VesselSpec:
    tag: str
    diameter: int
    height: int
    head_depth: int
    skirt_height: int
    skirt_thickness: int
    nozzles: tuple[NozzleSpec, ...]
    design_pressure: int
    design_temperature: int
    material: str
    operating_weight: int

    @property
    def shell_bottom(self) -> int:
        return self.skirt_height

    @property
    def shell_top(self) -> int:
        return self.skirt_height + self.height

    def nozzle_fits(self, n: NozzleSpec, others: tuple[NozzleSpec, ...] = ()) -> bool:
        """Misma regla que el núcleo + separación mínima entre boquillas."""
        margin = n.diameter / 2 + 100
        if not self.shell_bottom + margin <= n.elevation <= self.shell_top - margin:
            return False
        if n.diameter >= self.diameter / 4:
            return False
        for o in others:
            if o.id == n.id:
                continue
            same_side = min(abs(o.azimuth - n.azimuth), 360 - abs(o.azimuth - n.azimuth)) < 30
            if same_side and abs(o.elevation - n.elevation) < (o.diameter + n.diameter) / 2 + 200:
                return False
        return True

    def valid(self) -> bool:
        return all(self.nozzle_fits(n, self.nozzles) for n in self.nozzles) and len(
            {n.id for n in self.nozzles}
        ) == len(self.nozzles)


def flatten(spec: VesselSpec) -> dict[str, tuple[float | str, str]]:
    """Mismas rutas que trazia.model.fields: valor y unidad canónica."""
    out: dict[str, tuple[float | str, str]] = {"tag": (spec.tag, "1")}
    for key in ("diameter", "height", "head_depth", "skirt_height", "skirt_thickness"):
        out[key] = (float(getattr(spec, key)), "mm")
    for key, unit in ATTRIBUTE_UNITS.items():
        value = getattr(spec, key)
        out[f"attributes.{key}"] = (value if isinstance(value, str) else float(value), unit)
    for n in spec.nozzles:
        out[f"nozzles.{n.id}.diameter"] = (float(n.diameter), "mm")
        out[f"nozzles.{n.id}.projection"] = (float(n.projection), "mm")
        out[f"nozzles.{n.id}.elevation"] = (float(n.elevation), "mm")
        out[f"nozzles.{n.id}.azimuth"] = (float(n.azimuth), "deg")
    return out


def _random_nozzle(rng: random.Random, spec: VesselSpec, nozzle_id: str) -> NozzleSpec | None:
    choices = [d for d in DN if d < spec.diameter / 4]
    for _ in range(200):
        dn = rng.choice(choices)
        low = math.ceil((spec.shell_bottom + dn / 2 + 100) / 50) * 50
        high = math.floor((spec.shell_top - dn / 2 - 100) / 50) * 50
        if high <= low:
            return None
        n = NozzleSpec(
            id=nozzle_id,
            diameter=dn,
            projection=rng.randrange(200, 501, 50),
            elevation=rng.randrange(low, high + 1, 50),
            azimuth=rng.randrange(0, 360, 15),
        )
        if spec.nozzle_fits(n, spec.nozzles):
            return n
    return None


def random_case(rng: random.Random, index: int) -> VesselSpec:
    """Recipiente vertical con fondos 2:1, faldón y entre 3 y 7 boquillas radiales."""
    diameter = rng.randrange(1200, 4001, 100)
    head_depth = diameter // 4
    spec = VesselSpec(
        tag=f"{rng.choice('VDC')}-{100 + index}",
        diameter=diameter,
        height=rng.randrange(4000, 16001, 100),
        head_depth=head_depth,
        skirt_height=rng.randrange(max(1200, head_depth + 300), 3201, 50),
        skirt_thickness=rng.choice((12, 16, 20, 25, 30)),
        nozzles=(),
        design_pressure=rng.randrange(3, 46),
        design_temperature=rng.randrange(60, 421, 10),
        material=rng.choice(MATERIALS),
        operating_weight=rng.randrange(8000, 90001, 100),
    )
    target = rng.randint(3, 7)
    while len(spec.nozzles) < target:
        n = _random_nozzle(rng, spec, f"N{len(spec.nozzles) + 1}")
        if n is None:
            break
        spec = replace(spec, nozzles=(*spec.nozzles, n))
    if len(spec.nozzles) < 3 or not spec.valid():
        return random_case(rng, index)
    return spec


def mutate(rng: random.Random, spec: VesselSpec) -> VesselSpec:
    """Revisión 2: entre 1 y 4 cambios del tipo que muestra el reto (pág. 11)."""
    operations = [
        "move_nozzle",
        "rotate_nozzle",
        "resize_nozzle",
        "lengthen_shell",
        "raise_skirt",
        "weight",
        "pressure",
        "add_nozzle",
        "remove_nozzle",
    ]
    rng.shuffle(operations)
    wanted = rng.randint(1, 4)
    done = 0
    current = spec
    for op in operations:
        if done == wanted:
            break
        candidate = _apply(rng, current, op)
        if candidate is not None and candidate.valid() and candidate != current:
            current = candidate
            done += 1
    return current if done else _apply(rng, spec, "weight") or spec


def _apply(rng: random.Random, spec: VesselSpec, op: str) -> VesselSpec | None:
    nozzles = list(spec.nozzles)
    if op in ("move_nozzle", "rotate_nozzle", "resize_nozzle", "remove_nozzle"):
        index = rng.randrange(len(nozzles))
        n = nozzles[index]
        if op == "move_nozzle":
            nozzles[index] = replace(
                n, elevation=n.elevation + rng.choice((-1, 1)) * rng.randrange(100, 601, 50)
            )
        elif op == "rotate_nozzle":
            nozzles[index] = replace(n, azimuth=(n.azimuth + rng.choice((-90, -45, 45, 90))) % 360)
        elif op == "resize_nozzle":
            bigger = [d for d in DN if d != n.diameter and d < spec.diameter / 4]
            if not bigger:
                return None
            nozzles[index] = replace(n, diameter=rng.choice(bigger))
        else:
            if len(nozzles) <= 3:
                return None
            nozzles.pop(index)
        return replace(spec, nozzles=tuple(nozzles))
    if op == "add_nozzle":
        next_id = f"N{max(int(n.id[1:]) for n in nozzles) + 1}"
        n = _random_nozzle(rng, spec, next_id)
        return replace(spec, nozzles=(*nozzles, n)) if n else None
    if op == "lengthen_shell":
        return replace(spec, height=spec.height + rng.randrange(200, 1001, 100))
    if op == "raise_skirt":
        return replace(spec, skirt_height=spec.skirt_height + rng.randrange(100, 401, 50))
    if op == "weight":
        return replace(spec, operating_weight=spec.operating_weight + rng.randrange(200, 2001, 100))
    if op == "pressure":
        return replace(spec, design_pressure=spec.design_pressure + rng.choice((-2, -1, 1, 2, 5)))
    return None


def expected_changes(before: VesselSpec, after: VesselSpec) -> list[dict]:
    """Cambios de campo esperados, con la misma forma que trazia.revisions.compare."""
    old, new = flatten(before), flatten(after)
    result = []
    for path in sorted(old.keys() | new.keys()):
        left, right = old.get(path), new.get(path)
        if left == right:
            continue
        result.append(
            {
                "path": path,
                "operation": "added"
                if left is None
                else "removed"
                if right is None
                else "modified",
                "before": None if left is None else {"value": left[0], "unit": left[1]},
                "after": None if right is None else {"value": right[0], "unit": right[1]},
            }
        )
    return result


def spec_to_revision(spec: VesselSpec, revision: str, project_id: str = "BENCH") -> Revision:
    """Revisión del contrato con los valores verdaderos (para construir el IFC de referencia)."""
    digest = hashlib.sha256(json.dumps(asdict(spec), sort_keys=True).encode()).hexdigest()
    source = {
        "document_id": "GT",
        "page": 1,
        "locator": "Verdad sintética",
        "confidence": 1.0,
        "reviewed": True,
    }

    def field(value, unit):
        return {"value": value, "unit": unit, "source": source}

    flat = flatten(spec)
    equipment = {
        "id": spec.tag.lower(),
        "kind": "vertical_vessel",
        "tag": field(spec.tag, "1"),
        **{
            k: field(flat[k][0], "mm")
            for k in ("diameter", "height", "head_depth", "skirt_height", "skirt_thickness")
        },
        "attributes": {k: field(flat[f"attributes.{k}"][0], u) for k, u in ATTRIBUTE_UNITS.items()},
        "nozzles": [
            {
                "id": n.id,
                "diameter": field(float(n.diameter), "mm"),
                "projection": field(float(n.projection), "mm"),
                "elevation": field(float(n.elevation), "mm"),
                "azimuth": field(float(n.azimuth), "deg"),
            }
            for n in spec.nozzles
        ],
    }
    content = {
        "schema_version": "0.2",
        "project_id": project_id,
        "revision": revision,
        "dataset": "synthetic",
        "documents": [
            {
                "id": "GT",
                "filename": "verdad.json",
                "revision": revision,
                "sha256": digest,
                "page_count": 1,
            }
        ],
        "equipment": equipment,
    }
    return Revision.model_validate_json(json.dumps(content))


def spec_to_dict(spec: VesselSpec) -> dict:
    return asdict(spec)


def spec_from_dict(data: dict) -> VesselSpec:
    nozzles = tuple(NozzleSpec(**n) for n in data["nozzles"])
    return VesselSpec(**{**data, "nozzles": nozzles})
