"""Conjuntos del generador v2 con semilla fija (DEC-21). Las semillas no se eligen por resultado.

- s-dev: los seis proveedores públicos. Única fuente para desarrollar y entrenar.
- s-reservado: los dos proveedores reservados. Solo para medir generalización; nunca se mira
  caso a caso para ajustar nada.
- s-mecanico: bombas con bancada en tres estilos públicos.
- s-adversarial: GA con instrucciones y valores falsos incrustados (DEC-32), sin hoja de datos.

Cada caso lo dibuja un proveedor (por turno, según su índice) y se entrega en cada degradación.
Uno de cada cuatro llega dentro de un paquete de proveedor; uno de cada tres llega sin hoja de
datos, para que los atributos tengan que salir del plano.

Estructura: <salida>/<conjunto>/manifest.json, truth/<TAG>.json y
<degradación>/<TAG>/GAD_<TAG>_rev{1,2}.pdf (+ HDM_<TAG>_rev{1,2}.xlsx si hay hoja de datos).
"""

import json
import random
import zlib
from dataclasses import dataclass, replace
from pathlib import Path

from .adversarial import make_overlay, plan_traps
from .cases import VesselSpec, expected_changes, flatten, mutate, random_case, spec_to_dict
from .mechanical import flatten_pump, mutate_pump, pump_to_dict, random_pump, render_pump
from .render import write_hdm
from .render_v2 import DEGRADATIONS, degrade, render_ga
from .vendors import PUBLIC, RESERVED, VENDORS, Vendor, snap_imperial


@dataclass(frozen=True)
class SetSpec:
    name: str
    seed: int
    cases: int
    vendors: tuple[str, ...]
    kind: str = "vessel"  # vessel | pump
    degradations: tuple[str, ...] = DEGRADATIONS
    tag_offset: int = 100
    package_every: int = 4
    no_hdm_every: int = 3
    adversarial: bool = False


SETS = {
    "s-dev": SetSpec("s-dev", 2026, 24, PUBLIC),
    "s-reservado": SetSpec("s-reservado", 7919, 16, RESERVED, tag_offset=600),
    "s-mecanico": SetSpec(
        "s-mecanico", 4242, 12, ("atlas", "iberica", "gulf"), kind="pump", package_every=0
    ),
    "s-adversarial": SetSpec(
        "s-adversarial",
        6666,
        12,
        ("atlas", "iberica"),
        degradations=("vectorial",),
        tag_offset=800,
        package_every=0,
        no_hdm_every=1,
        adversarial=True,
    ),
}


def snap_vessel(spec: VesselSpec, vendor: Vendor) -> VesselSpec:
    """Para proveedores en pulgadas: longitudes en la rejilla de 1/16" (verdad exacta en mm)."""
    if not vendor.imperial:
        return spec
    lengths = ("diameter", "height", "head_depth", "skirt_height", "skirt_thickness")
    nozzles = tuple(
        replace(n, projection=snap_imperial(n.projection), elevation=snap_imperial(n.elevation))
        for n in spec.nozzles
    )
    return replace(spec, **{k: snap_imperial(getattr(spec, k)) for k in lengths}, nozzles=nozzles)


def _vessel_pair(rng: random.Random, index: int, vendor: Vendor) -> tuple[VesselSpec, VesselSpec]:
    while True:
        rev1 = snap_vessel(random_case(rng, index), vendor)
        rev2 = snap_vessel(mutate(rng, rev1), vendor)
        if rev1.valid() and rev2.valid() and rev1 != rev2:
            return rev1, rev2


def _changes(old: dict, new: dict) -> list[dict]:
    out = []
    for path in sorted(old.keys() | new.keys()):
        left, right = old.get(path), new.get(path)
        if left == right:
            continue
        operation = "added" if left is None else "removed" if right is None else "modified"
        out.append(
            {
                "path": path,
                "operation": operation,
                "before": None if left is None else {"value": left[0], "unit": left[1]},
                "after": None if right is None else {"value": right[0], "unit": right[1]},
            }
        )
    return out


def generate_set(
    name: str,
    output: Path,
    cases: int | None = None,
    degradations: tuple[str, ...] | None = None,
) -> dict:
    spec = SETS[name]
    cases = spec.cases if cases is None else cases
    degradations = degradations or spec.degradations
    rng = random.Random(spec.seed)
    root = output / name
    (root / "truth").mkdir(parents=True, exist_ok=True)
    manifest = {
        "version": 2,
        "set": name,
        "seed": spec.seed,
        "synthetic": True,
        "kind": spec.kind,
        "styles": list(degradations),  # compatibilidad con el bench: una carpeta por degradación
        "vendors": {
            k: {
                "reserved": VENDORS[k].reserved,
                "lang": VENDORS[k].lang,
                "units": VENDORS[k].length_unit,
            }
            for k in spec.vendors
        },
        "cases": [],
    }
    used: set[str] = set()
    for index in range(cases):
        vendor = VENDORS[spec.vendors[index % len(spec.vendors)]]
        if spec.kind == "pump":
            rev1 = random_pump(rng, spec.tag_offset + index, vendor)
            rev2 = mutate_pump(rng, rev1, vendor)
        else:
            rev1, rev2 = _vessel_pair(rng, spec.tag_offset + index, vendor)
        if rev1.tag in used:
            rev1 = replace(rev1, tag=f"{rev1.tag}-{index}")
            rev2 = replace(rev2, tag=rev1.tag)
        used.add(rev1.tag)
        if spec.kind == "pump":
            old = flatten_pump(rev1)
            changes = _changes(old, flatten_pump(rev2))
            truth_specs = {"rev1": pump_to_dict(rev1), "rev2": pump_to_dict(rev2)}
        else:
            old = flatten(rev1)
            changes = expected_changes(rev1, rev2)
            truth_specs = {"rev1": spec_to_dict(rev1), "rev2": spec_to_dict(rev2)}
        package = bool(spec.package_every) and index % spec.package_every == spec.package_every - 1
        hdm = spec.kind == "vessel" and not (
            spec.no_hdm_every and index % spec.no_hdm_every == spec.no_hdm_every - 1
        )
        traps = plan_traps(rng, rev1) if spec.adversarial else []
        documents: dict[str, dict] = {}
        for degradation in degradations:
            folder = root / degradation / rev1.tag
            folder.mkdir(parents=True, exist_ok=True)
            for rev, current in (("1", rev1), ("2", rev2)):
                changed = {c["path"] for c in changes} if rev == "2" else set()
                if spec.kind == "pump":
                    pdf, meta = render_pump(current, rev, vendor, changed=changed)
                else:
                    sheets = 2 if vendor.table_position == "page2" else 1
                    table_page = (2 if package else 0) + sheets
                    overlay = make_overlay(traps, current, vendor, table_page) if traps else None
                    pdf, meta = render_ga(
                        current, rev, vendor, changed=changed, package=package, overlay=overlay
                    )
                seed = zlib.crc32(f"{name}/{rev1.tag}/{rev}/{degradation}".encode())
                (folder / f"GAD_{rev1.tag}_rev{rev}.pdf").write_bytes(
                    degrade(pdf, degradation, seed)
                )
                documents[rev] = meta
                if hdm:
                    write_hdm(folder / f"HDM_{rev1.tag}_rev{rev}.xlsx", current)
        truth = {
            "tag": rev1.tag,
            "kind": spec.kind,
            "vendor": vendor.key,
            "reserved": vendor.reserved,
            "package": package,
            "hdm": hdm,
            "documents": documents,
            **truth_specs,
            "changes": changes,
            "fields": len(old),
            "traps": [t.to_dict() for t in traps],
        }
        (root / "truth" / f"{rev1.tag}.json").write_text(
            json.dumps(truth, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        row = {
            "tag": rev1.tag,
            "vendor": vendor.key,
            "package": package,
            "hdm": hdm,
            "changes": len(changes),
            "traps": len(traps),
        }
        if spec.kind == "vessel":
            row["nozzles"] = len(rev1.nozzles)
        manifest["cases"].append(row)
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest
