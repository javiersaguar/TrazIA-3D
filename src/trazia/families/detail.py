"""Detalle derivado para demostraciones sintéticas; no es un dimensionado mecánico.

Patrones de brida: catálogo público HISAKA, ASME B16.5-1996 (150/300).
No se extrapolan DN ni clases. El diámetro de boquilla es el nominal del contrato;
el bore y el resto de proporciones son representaciones, no selección de schedule.
"""

import math
from dataclasses import dataclass, replace

from . import Part, Solid, nozzle_frame

SOURCE = "https://www.hisaka.co.jp/valve/english/techdoc-en/techdoc04-en/"


@dataclass(frozen=True)
class FlangePattern:
    outside: float
    thickness: float
    pitch: float
    count: int
    hole: float
    bolt: float


# DN: D, t, C, n, h, diámetro del perno (mm). Datos dimensionales, no ratings P/T.
PATTERNS = {
    150: {
        50: FlangePattern(152, 19.1, 120.6, 4, 19, 15.875),
        80: FlangePattern(190, 24, 152.4, 4, 19, 15.875),
        100: FlangePattern(229, 24, 190.5, 8, 19, 15.875),
        150: FlangePattern(279, 25.5, 241.3, 8, 22, 19.05),
        200: FlangePattern(343, 28.5, 298.4, 8, 22, 19.05),
        500: FlangePattern(700, 43, 635, 20, 32, 28.575),
    },
    300: {
        50: FlangePattern(165, 22.5, 127, 8, 19, 15.875),
        80: FlangePattern(210, 28.5, 168.1, 8, 22, 19.05),
        100: FlangePattern(254, 32, 200.2, 8, 22, 19.05),
        150: FlangePattern(318, 37, 269.7, 12, 22, 19.05),
        200: FlangePattern(381, 41.5, 330.2, 12, 26, 22.225),
        500: FlangePattern(775, 63.5, 685.8, 24, 35, 31.75),
    },
}


def flange_pattern(dn, rating):
    """Solo coincidencia exacta. Una clase no reconocida nunca se convierte a 150."""
    try:
        pressure_class = float(str(rating).strip())
    except (TypeError, ValueError):
        return None
    return PATTERNS.get(pressure_class, {}).get(dn)


def basis(direction):
    seed = (0.0, 0.0, 1.0) if abs(direction[2]) < 0.9 else (1.0, 0.0, 0.0)
    dot = sum(a * b for a, b in zip(seed, direction))
    x = tuple(a - dot * b for a, b in zip(seed, direction))
    length = math.sqrt(sum(v * v for v in x))
    x = tuple(v / length for v in x)
    y = (
        direction[1] * x[2] - direction[2] * x[1],
        direction[2] * x[0] - direction[0] * x[2],
        direction[0] * x[1] - direction[1] * x[0],
    )
    return x, y


def offset(point, direction, distance):
    return tuple(p + d * distance for p, d in zip(point, direction))


def bolt_holes(pattern):
    return tuple(
        (
            pattern.pitch / 2000 * math.cos(2 * math.pi * (i + 0.5) / pattern.count),
            pattern.pitch / 2000 * math.sin(2 * math.pi * (i + 0.5) / pattern.count),
            pattern.hole / 2000,
        )
        for i in range(pattern.count)
    )


def derived(identifier, solids, *, parent, kind, properties=None):
    return Part(
        identifier,
        f"derived/{identifier}",
        tuple(solids),
        object_type=kind,
        parent_id=parent,
        properties={
            "Origen": "derivado_de_norma",
            "LeidoDelPlano": False,
            "RequiereVerificacion": True,
            "Alcance": "Patrón normativo cuando se indica Norma; resto paramétrico ilustrativo",
            **(properties or {}),
        },
    )


def flange_parts(
    identifier,
    parent,
    dn,
    rating,
    origin,
    direction,
    *,
    assumed=False,
    blind=False,
    paired=False,
    dimensions=None,
):
    pattern = flange_pattern(dn, rating)
    if pattern is None:
        return []
    outside, thickness = dimensions or (pattern.outside, pattern.thickness)
    if outside <= pattern.pitch + pattern.hole or outside <= dn or thickness <= 0:
        return []
    metadata = {
        "Norma": "ASME B16.5-1996",
        "FuenteTabla": SOURCE,
        "Clase": int(float(rating)),
        "ClaseOrigen": "supuesto_visual" if assumed else "campo_trazado",
        "DN": dn,
        "DiametroExterior_mm": pattern.outside,
        "PCD_mm": pattern.pitch,
        "NumeroTaladros": pattern.count,
        "Taladro_mm": pattern.hole,
        "DimensionesNormadas": "C,n,h; D y t leídos"
        if dimensions
        else "D,t,C,n,h; no rating presión/temperatura",
    }
    plate = Solid(
        "drilled",
        origin=origin,
        direction=direction,
        diameter=outside,
        length=thickness,
        thickness=None if blind else (outside - dn) / 2,
        holes=bolt_holes(pattern),
    )
    result = [
        derived(f"{identifier}/flange", [plate], parent=parent, kind="FLANGE", properties=metadata)
    ]
    grip = thickness * (2 if paired else 1) + (8 if paired else 0)
    x, y = basis(direction)
    for i, (hx, hy, _) in enumerate(bolt_holes(pattern)):
        point = tuple(p + hx * a + hy * b for p, a, b in zip(origin, x, y))
        shaft = Solid(
            "cylinder",
            origin=offset(point, direction, -0.006),
            direction=direction,
            diameter=pattern.bolt,
            length=grip + 18,
        )
        head = Solid(
            "cylinder",
            origin=offset(point, direction, grip / 1000),
            direction=direction,
            diameter=pattern.bolt * 1.6,
            length=pattern.bolt * 0.65,
        )
        result.append(
            derived(
                f"{identifier}/bolt-{i + 1:02}",
                [shaft, head],
                parent=parent,
                kind="BOLT",
                properties={
                    "Norma": "ASME B16.5-1996",
                    "FuenteTabla": SOURCE,
                    "DiametroNominal_mm": pattern.bolt,
                    "Cabeza": "envolvente cilíndrica ilustrativa, sin rosca",
                },
            )
        )
    return result


def enrich_parts(equipment, source):
    """El llamador habilita explícitamente estos supuestos visuales (API sintética o demo).

    IDs derivados del identificador estable del elemento, sin revisión, índice global ni cotas.
    """
    if equipment.kind != "vertical_vessel" or equipment.lod < 2:
        return source
    result = []
    radius = equipment.diameter.value / 2000
    skirt = equipment.skirt_height.value / 1000
    # Aberturas opuestas en el faldón, conservando su producto/GUID original.
    width, height = min(0.48, radius * 0.55), min(0.65, skirt * 0.65)
    for part in source:
        if part.id == "skirt" and height > 0.05:
            cuts = (
                ((-width / 2, -radius - 0.05, 0.08), (width, 2 * radius + 0.1, height)),
                ((-radius - 0.05, -width / 2, 0.08), (2 * radius + 0.1, width, height)),
            )
            part = replace(
                part,
                solids=(replace(part.solids[0], cutouts=cuts),),
                properties={
                    "Origen": "derivado_de_norma",
                    "LeidoDelPlano": False,
                    "RequiereVerificacion": True,
                    "Alcance": "Aberturas de proporción ilustrativa; no dimensionado de soporte",
                },
            )
        result.append(part)
    for nozzle in equipment.nozzles:
        origin, direction = nozzle_frame(equipment, nozzle)
        rating = nozzle.rating.value if nozzle.rating else 150
        pattern = flange_pattern(nozzle.diameter.value, rating)
        if pattern:
            dimensions = (
                (nozzle.flange.outer_diameter.value, nozzle.flange.thickness.value)
                if nozzle.flange
                else None
            )
            depth = dimensions[1] if dimensions else pattern.thickness
            end = offset(origin, direction, (nozzle.projection.value - depth) / 1000)
            items = flange_parts(
                f"nozzle-{nozzle.stable_id or nozzle.id}",
                nozzle.id,
                nozzle.diameter.value,
                rating,
                end,
                direction,
                assumed=nozzle.rating is None,
                dimensions=dimensions,
            )
            if nozzle.flange and items:
                # El OD, el espesor y el GUID explícitos se conservan; solo se deriva el taladrado.
                old_id = f"{nozzle.id}/flange"
                result = [
                    replace(
                        part,
                        solids=items[0].solids,
                        parent_id=nozzle.id,
                        properties=items[0].properties,
                    )
                    if part.id == old_id
                    else part
                    for part in result
                ]
                result.extend(items[1:])
            elif not nozzle.flange:
                result.extend(items)
    # Boca de hombre y pescante: ubicación/proporciones de demostración, no evidencia nueva.
    dn = 500 if radius >= 0.6 else 100
    mw_z = min(equipment.shell_bottom / 1000 + 0.85, equipment.total_height / 1000 - 0.5)
    origin, direction = (0.0, -radius, mw_z), (0.0, -1.0, 0.0)
    neck = Solid(
        "cylinder", origin=origin, direction=direction, diameter=dn, length=260, thickness=12
    )
    result.append(
        derived(
            "manway/neck",
            [neck],
            parent="shell",
            kind="MANWAY",
            properties={"Regla": "DN y proyección ilustrativos, no leídos del plano"},
        )
    )
    face = offset(origin, direction, 0.26)
    result.extend(
        flange_parts("manway", "shell", dn, 150, face, direction, assumed=True, paired=True)
    )
    pattern = flange_pattern(dn, 150)
    cover = Solid(
        "drilled",
        origin=offset(face, direction, pattern.thickness / 1000 + 0.008),
        direction=direction,
        diameter=pattern.outside,
        length=pattern.thickness,
        holes=bolt_holes(pattern),
    )
    result.append(derived("manway/cover", [cover], parent="shell", kind="MANWAY_COVER"))
    result.append(
        derived(
            "manway/davit",
            [
                Solid(
                    "cylinder", origin=(0.42, -radius - 0.25, mw_z - 0.25), diameter=35, length=800
                ),
                Solid(
                    "cylinder",
                    origin=(0.42, -radius - 0.25, mw_z + 0.55),
                    direction=(-1.0, 0.0, 0.0),
                    diameter=35,
                    length=420,
                ),
            ],
            parent="shell",
            kind="DAVIT",
        )
    )
    # Orejetas taladradas; se mantienen por debajo de la cota superior original.
    z = (
        equipment.shell_bottom / 1000
        + equipment.height.value / 1000
        + equipment.head_depth.value * 0.6 / 1000
    )
    for i, sign in enumerate((-1, 1), 1):
        point = (sign * radius * 0.9, -0.045, z)
        eye = Solid(
            "drilled",
            origin=point,
            direction=(0.0, -1.0, 0.0),
            diameter=240,
            thickness=75,
            length=70,
        )
        pad = Solid("box", origin=(point[0] - 0.12, -0.115, z - 0.22), size=(0.24, 0.07, 0.22))
        result.append(
            derived(
                f"lug-{i}",
                [eye, pad],
                parent="top_head",
                kind="LIFTING_LUG",
                properties={"Regla": "Proporción ilustrativa, sin cálculo de izado"},
            )
        )
    count = 12
    pitch = radius + 0.065
    holes = tuple(
        (
            pitch * math.cos(2 * math.pi * i / count),
            pitch * math.sin(2 * math.pi * i / count),
            0.015,
        )
        for i in range(count)
    )
    ring = Solid(
        "drilled", diameter=(radius + 0.14) * 2000, thickness=0.22 * 1000, length=35, holes=holes
    )
    result.append(
        derived(
            "base/ring",
            [ring],
            parent="skirt",
            kind="BASE_RING",
            properties={"Regla": "Proporción ilustrativa, no verificación civil"},
        )
    )
    for i, (x, y, _) in enumerate(holes, 1):
        result.append(
            derived(
                f"base/anchor-{i:02}",
                [
                    Solid("cylinder", origin=(x, y, 0.0), diameter=24, length=110),
                    Solid("cylinder", origin=(x, y, 0.035), diameter=40, length=18),
                ],
                parent="skirt",
                kind="ANCHOR_BOLT",
                properties={"Regla": "Anclaje ilustrativo, sin rosca"},
            )
        )
    return result
