"""Familias en mm; únicamente los sólidos de salida se expresan en metros."""

import math
from dataclasses import dataclass, field

from ..model import Equipment, Vector3
from .geometry import head_mesh


@dataclass(frozen=True)
class Solid:
    kind: str
    origin: tuple = (0.0, 0.0, 0.0)
    direction: tuple = (0.0, 0.0, 1.0)
    diameter: float = 0.0
    length: float = 0.0
    thickness: float | None = None
    size: tuple = ()
    points: tuple = ()
    vertices: list = field(default_factory=list)
    triangles: list = field(default_factory=list)


@dataclass(frozen=True)
class Part:
    id: str
    guid_key: str
    solids: tuple[Solid, ...]
    ifc_class: str = "IfcBuildingElementProxy"
    object_type: str = "COMPONENT"


def vector(value: Vector3):
    return tuple(getattr(value, axis).value / 1000 for axis in "xyz")


def frustum(bottom: float, top: float, height: float, z: float, segments=64):
    """Malla cerrada y orientada; radios y alturas en metros, sin caras degeneradas."""
    vertices = [
        (
            bottom * math.cos(2 * math.pi * i / segments),
            bottom * math.sin(2 * math.pi * i / segments),
            z,
        )
        for i in range(segments)
    ]
    triangles = []
    if top > 0:
        vertices += [
            (
                top * math.cos(2 * math.pi * i / segments),
                top * math.sin(2 * math.pi * i / segments),
                z + height,
            )
            for i in range(segments)
        ]
        for i in range(segments):
            j = (i + 1) % segments
            triangles.extend(
                [(i + 1, j + 1, j + segments + 1), (i + 1, j + segments + 1, i + segments + 1)]
            )
        cap = len(vertices) + 1
        vertices.append((0.0, 0.0, z + height))
        triangles += [
            (cap, i + segments + 1, (i + 1) % segments + segments + 1) for i in range(segments)
        ]
    else:
        cap = len(vertices) + 1
        vertices.append((0.0, 0.0, z + height))
        triangles += [(i + 1, (i + 1) % segments + 1, cap) for i in range(segments)]
    cap = len(vertices) + 1
    vertices.append((0.0, 0.0, z))
    triangles += [(cap, (i + 1) % segments + 1, i + 1) for i in range(segments)]
    return Solid("mesh", vertices=vertices, triangles=triangles)


def nozzle_frame(equipment, nozzle):
    if nozzle.position is not None:
        origin = vector(nozzle.position)
        direction = tuple(getattr(nozzle.direction, a).value for a in "xyz")
        norm = math.sqrt(sum(d * d for d in direction))
        return origin, tuple(d / norm for d in direction)
    angle = math.radians(nozzle.azimuth.value)
    direction = (math.cos(angle), math.sin(angle), 0.0)
    radius = equipment.diameter.value / 2000
    return (radius * direction[0], radius * direction[1], nozzle.elevation.value / 1000), direction


def parts(equipment: Equipment) -> list[Part]:
    result = []

    def add(identifier, solid, key=None, ifc_class="IfcBuildingElementProxy", kind="COMPONENT"):
        result.append(Part(identifier, key or identifier, (solid,), ifc_class, kind))

    if equipment.lod == 1:
        add(
            "shell",
            Solid(
                "box",
                origin=vector(equipment.envelope.origin),
                size=vector(equipment.envelope.size),
            ),
        )
    elif equipment.kind == "vertical_vessel":
        add(
            "shell",
            Solid(
                "cylinder",
                diameter=equipment.diameter.value,
                length=equipment.height.value,
                origin=(0.0, 0.0, equipment.shell_bottom / 1000),
            ),
        )
        for name, up, z in (
            ("bottom_head", -1, equipment.shell_bottom),
            ("top_head", 1, equipment.shell_bottom + equipment.height.value),
        ):
            vertices, triangles = head_mesh(
                equipment.diameter.value / 2000, equipment.head_depth.value / 1000, z / 1000, up
            )
            add(
                name, Solid("mesh", vertices=vertices, triangles=triangles), kind="ELLIPSOIDAL_HEAD"
            )
        add(
            "skirt",
            Solid(
                "cylinder",
                diameter=equipment.diameter.value,
                length=equipment.skirt_height.value,
                thickness=equipment.skirt_thickness.value,
            ),
            kind="SKIRT_SUPPORT",
        )
    elif equipment.kind == "horizontal_vessel":
        p = equipment.horizontal
        radius = p.diameter.value / 2000
        center = p.support_height.value / 1000 + radius
        add(
            "shell",
            Solid(
                "cylinder",
                origin=(0.0, 0.0, center),
                direction=(1.0, 0.0, 0.0),
                diameter=p.diameter.value,
                length=p.length.value,
            ),
        )
        for name, up, x in (("bottom_head", -1, 0.0), ("top_head", 1, p.length.value / 1000)):
            verts, triangles = head_mesh(radius, p.head_depth.value / 1000, 0.0, up)
            # Rotación propia Z→X (det=+1), misma superficie semielipsoidal.
            vertices = [(x + z, y, center - vx) for vx, y, z in verts]
            add(
                name, Solid("mesh", vertices=vertices, triangles=triangles), kind="ELLIPSOIDAL_HEAD"
            )
        for i, position in enumerate(p.saddle_positions):
            # Sección con asiento cóncavo en el plano YZ, extruida en X.
            half = p.saddle_span.value / 2000
            points = [(-half, 0.0), (half, 0.0)]
            for j in range(25):
                y = half - 2 * half * j / 24
                points.append((y, center - math.sqrt(radius * radius - y * y)))
            add(
                f"saddle-{i + 1}",
                Solid(
                    "profile",
                    origin=(position.value / 1000 - p.saddle_width.value / 2000, 0.0, 0.0),
                    direction=(1.0, 0.0, 0.0),
                    points=tuple(points),
                    length=p.saddle_width.value,
                ),
                kind="SADDLE_SUPPORT",
            )
    elif equipment.kind == "column":
        z = 0.0
        for index, section in enumerate(equipment.column.sections):
            top = (section.top_diameter or section.diameter).value
            solid = Solid(
                "cylinder",
                diameter=section.diameter.value,
                length=section.height.value,
                origin=(0.0, 0.0, z),
            )
            if top != section.diameter.value:
                solid = frustum(
                    section.diameter.value / 2000, top / 2000, section.height.value / 1000, z
                )
            add(
                "shell" if index == 0 else f"section-{section.id}",
                solid,
                key=f"section/{section.id}",
                kind="COLUMN_SECTION",
            )
            z += section.height.value / 1000
    elif equipment.kind == "tank":
        p = equipment.tank
        add("shell", Solid("cylinder", diameter=p.diameter.value, length=p.height.value))
        if p.roof == "conical":
            add(
                "roof",
                frustum(
                    p.diameter.value / 2000, 0, p.roof_height.value / 1000, p.height.value / 1000
                ),
                kind="ROOF",
            )
        elif p.roof == "domed":
            verts, triangles = head_mesh(
                p.diameter.value / 2000, p.roof_height.value / 1000, p.height.value / 1000, 1
            )
            add("roof", Solid("mesh", vertices=verts, triangles=triangles), kind="ROOF")
    for nozzle in equipment.nozzles:
        origin, direction = nozzle_frame(equipment, nozzle)
        add(
            nozzle.id,
            Solid(
                "cylinder",
                diameter=nozzle.diameter.value,
                length=nozzle.projection.value,
                origin=origin,
                direction=direction,
            ),
            key=f"nozzle/{nozzle.stable_id or nozzle.id}",
            ifc_class="IfcPipeSegment",
            kind="NOZZLE",
        )
        if equipment.lod == 3 and nozzle.flange:
            flange = nozzle.flange
            distance = (nozzle.projection.value - flange.thickness.value) / 1000
            add(
                f"{nozzle.id}/flange",
                Solid(
                    "cylinder",
                    diameter=flange.outer_diameter.value,
                    length=flange.thickness.value,
                    thickness=(flange.outer_diameter.value - nozzle.diameter.value) / 2,
                    origin=tuple(a + distance * b for a, b in zip(origin, direction)),
                    direction=direction,
                ),
                key=f"nozzle/{nozzle.stable_id or nozzle.id}/flange",
                ifc_class="IfcPipeFitting",
                kind="FLANGE",
            )
    if equipment.lod == 3:
        for platform in equipment.platforms:
            add(
                f"platform-{platform.id}",
                Solid("box", origin=vector(platform.origin), size=vector(platform.size)),
                key=f"platform/{platform.id}",
                kind="PLATFORM",
            )
        for ladder in equipment.ladders:
            x, y, z = vector(ladder.origin)
            width = ladder.width.value / 1000
            solids = [
                Solid(
                    "cylinder",
                    origin=(x + offset, y, z),
                    diameter=ladder.rail_diameter.value,
                    length=ladder.height.value,
                )
                for offset in (0, width)
            ]
            for i in range(1, int(ladder.height.value / ladder.rung_spacing.value) + 1):
                solids.append(
                    Solid(
                        "cylinder",
                        origin=(x, y, z + i * ladder.rung_spacing.value / 1000),
                        direction=(1.0, 0.0, 0.0),
                        diameter=ladder.rail_diameter.value,
                        length=ladder.width.value,
                    )
                )
            result.append(
                Part(
                    f"ladder-{ladder.id}",
                    f"ladder/{ladder.id}",
                    tuple(solids),
                    object_type="LADDER",
                )
            )
    return result
