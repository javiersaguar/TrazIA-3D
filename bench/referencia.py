"""Verdad de referencia leída de un IFC externo y error de un equipo frente a ella (G.1 y G.3).

    uv run python -m bench.referencia data/private/<TAG>.ifc --revision revision.json

No supone nombres de elementos: el IFC de Técnicas Reunidas aún no se conoce. Identifica por
geometría y lo que no puede identificar queda en None y en `notes`, nunca como 0. Sin la
revisión solo imprime la lectura del IFC, para revisarla a mano antes de usarla como verdad.

Sin los IFC reales, esto solo está probado con IFC generados por nosotros y con los nombres
borrados: no es una medida sobre planos del organizador.

Convenios (ROADMAP C.4 y DEC-15): el azimut de TR no se conoce. Se publica el azimut geométrico
(desde +X, antihorario) y `compare_revision` busca el convenio que mejor encaja, marcándolo como
ajustado en el propio equipo. Para una cifra defendible se pasa el `convention` obtenido en otros
equipos (exclusión de uno, G.5).
"""

import argparse
import json
import math
import re
from pathlib import Path

import ifcopenshell
import ifcopenshell.geom
import numpy as np
from scipy.optimize import linear_sum_assignment

from trazia.model import Revision

from .metrics import angle_error, nozzle_face_center

MARK = re.compile(r"(?:^|[/\s_-])(N\d{1,3}[A-Z]?)(?:$|[/\s_-])", re.I)
AXIAL_NOZZLE_SHARE = 0.6  # sección máxima de una boquilla frente al diámetro del cuerpo
MAX_MATCH_MM = 500.0  # más lejos que esto no es la misma boquilla: cuenta como no encontrada


def _meshes(model: ifcopenshell.file) -> tuple[list[dict], list[str]]:
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    meshes, failed = [], []
    for product in model.by_type("IfcElement"):
        if not product.Representation:
            continue
        name = product.Name or product.GlobalId
        try:
            shape = ifcopenshell.geom.create_shape(settings, product)
        except RuntimeError:
            failed.append(name)
            continue
        points = np.array(shape.geometry.verts, dtype=float).reshape(-1, 3) * 1000
        if len(points):
            meshes.append({"name": name, "points": points})
    return meshes, failed


def _nozzle(group: list[dict], center: np.ndarray, axis: int, body: dict, mark) -> dict | None:
    """Boquilla de un grupo de elementos, o None si no lo parece (fondo, faldón, plataforma)."""
    points = np.vstack([m["points"] for m in group])
    across = [i for i in range(3) if i != axis]
    radial = points[:, across] - center
    middle = radial.mean(axis=0)
    span = points.max(axis=0) - points.min(axis=0)
    radius = body["diameter"] / 2
    offset = float(np.hypot(*middle))
    if offset > 0.5 * radius:  # lateral: sale del cuerpo
        direction = middle / offset
        lateral = np.array([-direction[1], direction[0]])
        width = float(np.ptp(radial @ lateral))
        return {
            "mark": mark,
            "type": "radial",
            "azimuth": math.degrees(math.atan2(direction[1], direction[0])) % 360,
            "elevation": float(points[:, axis].mean() - body["base"]),
            "projection": float(np.max(radial @ direction) - radius),
            "diameter": width,
        }
    width = float(max(span[across]))
    low, high = points[:, axis].min(), points[:, axis].max()
    outside = low >= body["top"] - 1 or high <= body["bottom"] + 1
    if width < AXIAL_NOZZLE_SHARE * body["diameter"] and outside:  # superior o inferior
        return {
            "mark": mark,
            "type": "axial",
            "azimuth": None,
            "elevation": float(points[:, axis].mean() - body["base"]),
            "projection": None,
            "diameter": width,
        }
    return None


def read_reference(model: ifcopenshell.file) -> dict:
    """Dimensiones principales y boquillas de un IFC, en mm y grados."""
    meshes, failed = _meshes(model)
    notes = [f"Sin geometría legible: {name}" for name in failed]
    out = {
        "elements": len(meshes),
        "axis": None,
        "diameter": None,
        "shell_length": None,  # `height` del contrato: el cuerpo, sin faldón ni fondos
        "overall_height": None,
    }
    out["nozzles"], out["notes"] = None, notes
    if not meshes:
        notes.append("El IFC no tiene elementos con geometría.")
        return out
    for m in meshes:
        m["span"] = m["points"].max(axis=0) - m["points"].min(axis=0)
    main = max(meshes, key=lambda m: float(np.prod(m["span"])))
    horizontal = max(main["span"][:2])
    axis = 2 if main["span"][2] >= horizontal else int(np.argmax(main["span"][:2]))
    across = [i for i in range(3) if i != axis]
    widths = main["span"][across]
    if abs(widths[0] - widths[1]) > 0.02 * widths.max():
        notes.append(
            f"El cuerpo no es circular en planta ({widths[0]:.0f} × {widths[1]:.0f} mm): "
            "revisar el diámetro a mano."
        )
    every = np.vstack([m["points"] for m in meshes])
    base = float(every[:, axis].min())
    center = (main["points"][:, across].min(axis=0) + main["points"][:, across].max(axis=0)) / 2
    body = {
        "diameter": float(widths.max()),
        "base": base,
        "bottom": float(main["points"][:, axis].min()),
        "top": float(main["points"][:, axis].max()),
    }
    out.update(
        axis="xyz"[axis],
        diameter=body["diameter"],
        shell_length=body["top"] - body["bottom"],
        overall_height=float(np.ptp(every[:, axis])),
    )
    if len(meshes) == 1:
        notes.append("Un solo elemento con geometría: las boquillas no se pueden separar.")
        return out
    groups: dict[str, list[dict]] = {}
    for index, m in enumerate(meshes):
        if m is main:
            continue
        found = MARK.search(m["name"])
        key = found[1].upper() if found else f"#{index}"
        groups.setdefault(key, []).append(m)
    nozzles = []
    for key, group in groups.items():
        nozzle = _nozzle(group, center, axis, body, None if key.startswith("#") else key)
        if nozzle is not None:
            nozzles.append(nozzle)
    out["nozzles"] = sorted(nozzles, key=lambda n: n["elevation"])
    return out


def _faces(nozzles: list[dict], diameter: float, sign: int, offset: float) -> np.ndarray:
    return np.array(
        [
            nozzle_face_center(
                diameter, n["elevation"], sign * n["azimuth"] + offset, n["projection"]
            )
            for n in nozzles
        ]
    )


def _match(ours: list[dict], reference: list[dict], diameter: float, sign: int, offset: float):
    a, b = _faces(ours, diameter, sign, offset), _faces(reference, diameter, 1, 0.0)
    cost = np.linalg.norm(a[:, None, :] - b[None, :, :], axis=2)
    rows, cols = linear_sum_assignment(cost)
    return [(int(r), int(c), float(cost[r, c])) for r, c in zip(rows, cols, strict=True)]


def compare_revision(revision: Revision, reference: dict, *, convention: dict | None = None):
    """Error de una revisión frente a la referencia: dimensiones en mm y boquillas en mm y grados.

    `convention` ({"sign": ±1, "offset": grados}) fija el convenio de azimut. Si falta, se busca el
    que mejor encaja aquí y la salida lo marca con `fitted`: esa cifra es optimista.
    """
    equipment = revision.equipment
    dimensions = {}
    for key, value, ref_key in (
        ("diameter", equipment.diameter, "diameter"),
        ("height", equipment.height, "shell_length"),
    ):
        known = reference.get(ref_key)
        dimensions[key] = {
            "ours": value.value,
            "reference": known,
            "error_mm": None if known is None else abs(value.value - known),
        }
    out = {"dimensions": dimensions, "nozzles": None, "convention": convention}
    listed = reference.get("nozzles")
    if listed is None:
        out["nozzle_note"] = "La referencia no permite separar boquillas: sin medir."
        return out
    ours = [
        {
            "id": n.id,
            "elevation": n.elevation.value,
            "azimuth": n.azimuth.value,
            "projection": n.projection.value,
            "diameter": n.diameter.value,
        }
        for n in equipment.nozzles
    ]
    radial = [n for n in listed if n["type"] == "radial"]
    diameter = reference["diameter"]
    if not ours or not radial:
        out["nozzles"] = {"matched": [], "missing": len(radial), "extra": len(ours)}
        return out
    options = (
        [(convention["sign"], convention["offset"])]
        if convention
        else [(s, o) for s in (1, -1) for o in (0.0, 90.0, 180.0, 270.0)]
    )

    def quality(option):
        pairs = _match(ours, radial, diameter, *option)
        kept = [p for p in pairs if p[2] <= MAX_MATCH_MM]
        return (-len(kept), sum(p[2] for p in kept)), option, kept

    _, (sign, offset), kept = min((quality(o) for o in options), key=lambda q: q[0])
    out["convention"] = {"sign": sign, "offset": offset, "fitted": convention is None}
    matched = []
    for r, c, error in kept:
        mine, ref = ours[r], radial[c]
        matched.append(
            {
                "ours": mine["id"],
                "reference": ref["mark"],
                "position_error_mm": error,
                "azimuth_error_deg": angle_error(
                    (sign * mine["azimuth"] + offset) % 360, ref["azimuth"]
                ),
                "elevation_error_mm": mine["elevation"] - ref["elevation"],
                "diameter_error_mm": abs(mine["diameter"] - ref["diameter"]),
            }
        )
    errors = [m["position_error_mm"] for m in matched]
    bias = [m["elevation_error_mm"] for m in matched]
    out["nozzles"] = {
        "matched": matched,
        "missing": len(radial) - len(matched),
        "extra": len(ours) - len(matched),
        "position_error_mean_mm": float(np.mean(errors)) if errors else None,
        "position_error_max_mm": max(errors) if errors else None,
        # Una mediana lejos de 0 con poca dispersión indica otro origen de cotas, no mala lectura.
        "elevation_bias_mm": float(np.median(bias)) if bias else None,
    }
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Lee la verdad de referencia de un IFC (G.1)")
    parser.add_argument("ifc", type=Path)
    parser.add_argument("--revision", type=Path, default=None, help="JSON del contrato a comparar")
    parser.add_argument("--signo", type=int, choices=(1, -1), default=None)
    parser.add_argument("--desfase", type=float, default=None, help="Grados del convenio de azimut")
    args = parser.parse_args(argv)
    reference = read_reference(ifcopenshell.open(str(args.ifc)))
    out = {"reference": reference}
    if args.revision:
        revision = Revision.model_validate_json(args.revision.read_text(encoding="utf-8"))
        convention = None
        if args.signo is not None and args.desfase is not None:
            convention = {"sign": args.signo, "offset": args.desfase}
        out["comparison"] = compare_revision(revision, reference, convention=convention)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
