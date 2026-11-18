"""Mallas ligeras para los complejos de proceso y sus vistas de plano."""

from collections import defaultdict
from dataclasses import dataclass, field, replace
from math import cos, sin, tau

import numpy as np
from process_projects import Equipment, Line, Point, Project

PALETTE = {
    "Acero": "#9eaebc",
    "Refuerzo": "#536979",
    "Motor": "#2a5977",
    "Seguridad": "#e2a842",
    "Hormigón": "#8b9293",
    "Asfalto": "#56636c",
    "Mezcla": "#8b76b3",
    "Gas": "#e7b44c",
    "Crudo": "#4b866c",
    "Agua": "#54b0cb",
    "Condensado": "#69a896",
    "GNL": "#85c8e9",
    "Aislante": "#d0dbe0",
}


@dataclass
class Mesh:
    vertices: list[Point] = field(default_factory=list)
    faces: list[tuple[int, ...]] = field(default_factory=list)

    def add(self, vertices, faces):
        first = len(self.vertices)
        self.vertices.extend(tuple(round(float(x), 4) for x in p) for p in vertices)
        self.faces.extend(tuple(first + i for i in face) for face in faces)

    def box(self, center: Point, size: Point):
        x, y, z = center
        a, b, c = (value / 2 for value in size)
        self.add(
            [
                (x + i * a, y + j * b, z + k * c)
                for k in (-1, 1)
                for i, j in ((-1, -1), (1, -1), (1, 1), (-1, 1))
            ],
            [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)],
        )

    def revolve(self, a: Point, b: Point, profile, sides=16):
        # Producto vectorial ortonormal, también para soportes inclinados.
        start, end = np.array(a, dtype=float), np.array(b, dtype=float)
        axis = end - start
        norm = np.linalg.norm(axis)
        if norm < 1e-6:
            return
        direction = axis / norm
        reference = (0, 0, 1) if abs(direction[2]) < 0.9 else (0, 1, 0)
        u = np.cross(reference, direction)
        u /= np.linalg.norm(u)
        v = np.cross(direction, u)
        directions = [cos(i * tau / sides) * u + sin(i * tau / sides) * v for i in range(sides)]
        vertices = [start + t * axis + radius * d for t, radius in profile for d in directions]
        faces = [tuple(reversed(range(sides)))]
        for k in range(len(profile) - 1):
            for i in range(sides):
                j = (i + 1) % sides
                faces.append(
                    (k * sides + i, k * sides + j, (k + 1) * sides + j, (k + 1) * sides + i)
                )
        faces.append(tuple(range(len(vertices) - sides, len(vertices))))
        self.add(vertices, faces)

    def tube(self, a: Point, b: Point, radius, sides=12):
        self.revolve(a, b, ((0, radius), (1, radius)), sides)

    def cap(self, a, b, radius):
        self.revolve(
            a,
            b,
            (
                (0, radius * 0.20),
                (0.025, radius * 0.65),
                (0.085, radius * 0.93),
                (0.16, radius),
                (0.84, radius),
                (0.915, radius * 0.93),
                (0.975, radius * 0.65),
                (1, radius * 0.20),
            ),
            24,
        )


@dataclass
class Part:
    tag: str
    name: str
    kind: str
    meshes: dict[str, Mesh] = field(default_factory=lambda: defaultdict(Mesh))
    details: list[tuple[str, str, str]] = field(default_factory=list)

    def material(self, color) -> Mesh:
        return self.meshes[color]


def ports(project: Project, equipment: dict[str, Equipment]):
    """Cada extremo tiene posición propia dentro de la cara de conexión del equipo."""
    result = {}
    for tag, eq in equipment.items():
        incoming = [line for line in project.lines if tag in (line.start, line.end)]
        for side in (-1, 1):
            side_lines = [
                line for line in incoming if (1 if line.rack_y > eq.xy[1] else -1) == side
            ]
            for index, line in enumerate(side_lines):
                x, y = eq.xy
                spacing = eq.size[0] / (len(side_lines) + 1)
                anchor = x + spacing * (index - (len(side_lines) - 1) / 2)
                # Las conexiones visuales se apoyan en la envolvente circular o rectangular real.
                radius = eq.size[1] / 2
                if eq.family in ("vertical", "column", "tank"):
                    radius *= (1 - ((anchor - x) / (eq.size[0] / 2)) ** 2) ** 0.5
                result[tag, line.tag] = anchor, y + side * radius, project.deck + 1.7
    return result


def railing(mesh, x, y, z, width, depth):
    for strip in (-1, 1):
        edge = y + strip * depth / 2
        for offset in (-0.5, -0.25, 0, 0.25, 0.5):
            px = x + offset * width
            mesh.tube((px, edge, z), (px, edge, z + 1.05), 0.043, 6)
        for h in (0.55, 1.05):
            mesh.tube((x - width / 2, edge, z + h), (x + width / 2, edge, z + h), 0.043, 6)


def ladder(mesh, x, y, z, height):
    count = max(1, round(height / 0.35))
    for side in (-0.25, 0.25):
        mesh.tube((x + side, y, z), (x + side, y, z + height), 0.037, 6)
    for index in range(1, count):
        h = z + height * index / count
        mesh.tube((x - 0.25, y, h), (x + 0.25, y, h), 0.028, 6)


def equipment_part(eq: Equipment, deck: float, connections) -> Part:
    part = Part(eq.tag, eq.name, "equipment")
    x, y = eq.xy
    width, depth, height = eq.size
    steel = part.material("Acero")
    dark = part.material("Refuerzo")
    safety = part.material("Seguridad")
    motor = part.material("Motor")
    dark.box((x, y, deck + 0.15), (width * 0.98, depth * 0.98, 0.30))
    part.details.append(("Bancada o anillo base", "Refuerzo", "Apoyo del equipo"))
    if eq.family == "horizontal":
        r = depth / 2
        axis_z = deck + 1.7
        steel.cap((x - width / 2, y, axis_z), (x + width / 2, y, axis_z), r)
        for px in (x - width * 0.25, x + width * 0.25):
            dark.box((px, y, deck + 0.65), (0.5, depth * 0.7, 0.95))
            steel.tube((px - 0.08, y, axis_z), (px + 0.08, y, axis_z), r * 1.015, 24)
        for px in (x - width * 0.24, x + width * 0.2):
            steel.tube((px, y, axis_z + r * 0.65), (px, y, axis_z + r + 0.48), 0.23)
            dark.tube((px, y, axis_z + r + 0.42), (px, y, axis_z + r + 0.55), 0.36, 16)
        part.details.extend(
            (
                ("Virola y dos cabezales", "Acero", "Recipiente horizontal"),
                ("Dos cunas y refuerzos", "Refuerzo", "Apoyo y acceso superior"),
            )
        )
    elif eq.family in ("vertical", "column", "tank"):
        r = depth / 2
        cylinder = part.material("Aislante") if eq.family == "tank" else steel
        start = deck + 0.45
        top = deck + height
        cylinder.revolve(
            (x, y, start),
            (x, y, top),
            ((0, r * 0.85), (0.04, r), (0.87, r), (0.93, r * 0.86), (1, r * 0.27)),
            24,
        )
        for fraction in (0.15, 0.42, 0.70, 0.87):
            h = start + (top - start) * fraction
            dark.tube((x, y, h - 0.055), (x, y, h + 0.055), r * 1.009, 24)
        safety.box((x, y - r * 0.7, top - 0.68), (width * 0.74, depth * 0.59, 0.12))
        railing(safety, x, y - r * 0.7, top - 0.62, width * 0.74, depth * 0.55)
        ladder(dark, x, y - r - 0.16, deck + 0.24, height - 0.86)
        steel.tube((x, y, top - 0.35), (x, y, top + 0.42), 0.19)
        part.details.extend(
            (
                (
                    "Envolvente y cubierta conformada",
                    "Aislante" if eq.family == "tank" else "Acero",
                    "Geometría exterior",
                ),
                ("Escala, anillos y descansillo", "Seguridad", "Acceso e inspección"),
            )
        )
    elif eq.family in ("pump", "compressor"):
        for offset in (-0.24, 0.24):
            row = y + depth * offset
            z = deck + height * 0.49
            steel.cap((x - width * 0.43, row, z), (x - width * 0.03, row, z), height * 0.34)
            motor.tube((x + width * 0.08, row, z), (x + width * 0.43, row, z), height * 0.27, 16)
            dark.tube((x - width * 0.04, row, z), (x + width * 0.1, row, z), height * 0.20)
            for i in range(5):
                px = x + width * (0.14 + 0.052 * i)
                dark.tube((px - 0.04, row, z), (px + 0.04, row, z), height * 0.278, 16)
            dark.box((x, row, deck + 0.49), (width * 0.83, depth * 0.31, 0.55))
        part.details.extend(
            (
                ("Dos carcasas y acoplamientos", "Acero", "Tren de rotativos"),
                ("Motores con aletas", "Motor", "Accionamiento"),
            )
        )
    elif eq.family == "air-cooler":
        for offset in (-0.30, 0, 0.30):
            for side in (-0.39, 0.39):
                px, py = x + width * offset, y + depth * side
                dark.box((px, py, deck + height * 0.46), (0.18, 0.18, height * 0.86))
        for i in (-1, 1):
            py = y + i * depth * 0.24
            steel.box((x, py, deck + height * 0.83), (width, depth * 0.43, height * 0.13))
            for f in (-0.25, 0.25):
                px = x + width * f
                motor.tube(
                    (px, py, deck + height * 0.90), (px, py, deck + height * 0.94), depth * 0.14, 16
                )
                steel.tube(
                    (px, py, deck + height * 0.94), (px, py, deck + height * 0.99), depth * 0.054
                )
        railing(safety, x, y, deck + height * 0.87, width, depth)
        part.details.extend(
            (
                ("Dos módulos de transferencia", "Acero", "Banco en paralelo"),
                ("Cuatro conjuntos de ventilación", "Motor", "Intercambio con aire ambiente"),
            )
        )
    elif eq.family == "vaporizer":
        for row in (-0.27, 0.27):
            py = y + depth * row
            for index in range(7):
                px = x + width * (index - 3) / 8
                steel.tube((px, py, deck + 0.7), (px, py, deck + height), 0.14)
                for sx, sy in ((0.45, 0.12), (0.12, 0.45)):
                    steel.box((px, py, deck + height * 0.55), (sx, sy, height * 0.85))
            dark.tube((x - width * 0.46, py, deck + 0.7), (x + width * 0.46, py, deck + 0.7), 0.20)
            dark.tube(
                (x - width * 0.46, py, deck + height), (x + width * 0.46, py, deck + height), 0.22
            )
            dark.box((x, py, deck + 0.36), (width * 0.93, 1.12, 0.38))
        part.details.extend(
            (
                ("Dos bancos de tubos aleteados", "Acero", "Vaporización ambiental"),
                ("Colectores superior e inferior", "Refuerzo", "Distribución"),
            )
        )
    elif eq.family == "cyclone":
        for offset in (-0.28, 0, 0.28):
            px = x + width * offset
            steel.revolve(
                (px, y, deck + 0.55), (px, y, deck + height), ((0, 0.14), (0.6, 0.63), (1, 0.63))
            )
        safety.box((x, y, deck + height + 0.08), (width, depth * 0.65, 0.17))
        part.details.append(("Tres cuerpos cónicos", "Acero", "Tratamiento de agua"))
    elif eq.family == "arm":
        a, b, c = (
            (x, y, deck + 0.4),
            (x, y, deck + height * 0.65),
            (x + width * 0.4, y, deck + height),
        )
        d = (x + width * 0.8, y - depth * 0.34, deck + height * 0.56)
        for p, q in ((a, b), (b, c), (c, d)):
            steel.tube(p, q, 0.24)
            safety.tube((p[0], p[1] + 0.55, p[2]), (q[0], q[1] + 0.55, q[2]), 0.14)
        part.details.append(("Pedestal, brazo articulado y tubo", "Acero", "Conexión de descarga"))
    else:
        beam_z = deck + 1.6
        steel.tube((x - width / 2, y, beam_z), (x + width / 2, y, beam_z), 0.31)
        for offset in (-0.31, 0, 0.31):
            px = x + width * offset
            steel.tube((px, y, beam_z), (px, y + depth / 2, beam_z), 0.22)
            dark.tube(
                (px, y + depth * 0.2, beam_z), (px, y + depth * 0.2, deck + height * 0.8), 0.17
            )
            safety.tube(
                (px - 0.27, y + depth * 0.2, deck + height * 0.8),
                (px + 0.27, y + depth * 0.2, deck + height * 0.8),
                0.16,
                10,
            )
        part.details.append(("Colector con tres ramales", "Acero", "Distribución"))
    for line, (px, py, pz) in connections:
        side = 1 if py > y else -1
        steel.tube((px, y, pz), (px, py, pz), 0.20)
        dark.tube((px, py - side * 0.31, pz), (px, py + side * 0.035, pz), 0.34, 12)
        part.details.append((f"Boquilla de {line}", "Acero", "Unión atornillada a línea"))
    return part


def line_path(project: Project, line: Line, nozzles):
    a = nozzles[line.start, line.tag]
    b = nozzles[line.end, line.tag]
    ay = a[1] + (0.75 if line.rack_y > a[1] else -0.75)
    by = b[1] + (0.75 if line.rack_y > b[1] else -0.75)
    z = project.deck + line.rack_z
    return (
        a,
        (a[0], ay, a[2]),
        (a[0], ay, z),
        (a[0], line.rack_y, z),
        (b[0], line.rack_y, z),
        (b[0], by, z),
        (b[0], by, b[2]),
        b,
    )


def rounded_pipe(mesh, nodes, radius, sides=12):
    points = [np.array(point, dtype=float) for point in nodes]
    route = [points[0]]
    for before, corner, after in zip(points, points[1:], points[2:]):
        first, second = before - corner, after - corner
        first_length, second_length = np.linalg.norm(first), np.linalg.norm(second)
        if min(first_length, second_length) < 1e-6:
            continue
        trim = min(radius * 2.4, first_length * 0.42, second_length * 0.42)
        start = corner + trim * first / first_length
        end = corner + trim * second / second_length
        for fraction in np.linspace(0.0, 1.0, 5):
            route.append(
                (1 - fraction) ** 2 * start
                + 2 * (1 - fraction) * fraction * corner
                + fraction**2 * end
            )
    route.append(points[-1])
    ring = [(cos(i * tau / sides), sin(i * tau / sides)) for i in range(sides)]
    vertices = []
    # Transporte paralelo del anillo para evitar torsiones al cambiar de plano.
    u = None
    for n, center in enumerate(route):
        direction = route[min(n + 1, len(route) - 1)] - route[max(0, n - 1)]
        direction /= np.linalg.norm(direction)
        if u is None:
            ref = (0, 0, 1) if abs(direction[2]) < 0.9 else (0, 1, 0)
            u = np.cross(ref, direction)
        else:
            u -= direction * np.dot(u, direction)
        u /= np.linalg.norm(u)
        v = np.cross(direction, u)
        vertices.extend(center + radius * (cosine * u + sine * v) for cosine, sine in ring)
    faces = [tuple(reversed(range(sides)))]
    for n in range(len(route) - 1):
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((n * sides + i, n * sides + j, (n + 1) * sides + j, (n + 1) * sides + i))
    faces.append(tuple(range(len(vertices) - sides, len(vertices))))
    mesh.add(vertices, faces)


def line_part(line: Line, path) -> Part:
    part = Part(line.tag, f"{line.fluid} · {line.start} → {line.end}", "pipe")
    fluid = part.material(line.fluid)
    steel = part.material("Refuerzo")
    r = line.dn / 2000
    rounded_pipe(fluid, path, r)
    x = (path[3][0] + path[4][0]) / 2
    y, z = path[3][1:]
    axis = 1 if path[4][0] > path[3][0] else -1
    steel.tube((x - axis * 0.55, y, z), (x + axis * 0.55, y, z), r * 1.30)
    for offset in (-0.58, 0.58):
        steel.tube((x + offset - 0.07, y, z), (x + offset + 0.07, y, z), r * 1.65, 16)
    steel.tube((x, y, z), (x, y, z + r + 0.45), r * 0.48, 10)
    part.material("Seguridad").tube(
        (x - 0.29, y, z + r + 0.45), (x + 0.29, y, z + r + 0.45), 0.15, 12
    )
    part.details.extend(
        (
            ("Tramos y cambios de dirección", line.fluid, f"DN {line.dn}"),
            ("Spool bridado y válvula", "Refuerzo", "Conjunto desmontable"),
        )
    )
    return part


def structure(project: Project) -> Part:
    part = Part("ST-00", "Infraestructura, accesos y rack", "structure")
    base = part.material("Hormigón")
    steel = part.material("Refuerzo")
    yellow = part.material("Seguridad")
    deck = project.deck
    if project.id == "plataforma-marina":
        steel.box((0, 7, deck - 0.56), (67, 32, 1.12))
        for x in (-27, 0, 27):
            for y in (-5, 19):
                steel.tube((x, y, -1.1), (x, y, deck - 0.55), 0.69)
                steel.tube((x - 4, y, 0), (x + 4, y, deck - 1), 0.25)
            steel.tube((x, -5, 1), (x, 19, deck - 1), 0.29)
            steel.tube((x, -5, deck - 1), (x, 19, 1), 0.29)
        railing(yellow, 0, 7, deck, 66, 31)
        steel.box((-29, 16, deck + 2.1), (1.4, 1.4, 4.2))
        steel.box((-29, 16, deck + 4.8), (2.3, 1.6, 1.45))
        for side in (-0.43, 0.43):
            yellow.tube((-29, 16 + side, deck + 5.3), (-20, 16 + side, deck + 10.9), 0.10, 8)
            yellow.tube((-29, 16 + side, deck + 6.1), (-20, 16 + side, deck + 10.9), 0.10, 8)
        for step in range(4):
            x = -29 + step * 2.25
            h = deck + 5.6 + step * 1.32
            yellow.tube((x, 15.57, h), (x + 2.25, 16.43, h + 1.32), 0.065, 8)
        steel.tube((-20, 16, deck + 10.9), (-20, 16, deck + 5.9), 0.035, 8)
        steel.box((-20, 16, deck + 5.85), (0.33, 0.34, 0.26))
        cabin = part.material("Aislante")
        cabin.box((-16, 17.5, deck + 1.2), (7, 4.2, 2.45))
        steel.box((-16, 17.5, deck + 2.5), (7.25, 4.5, 0.16))
        for x in (-18, -16, -14):
            part.material("Motor").box((x, 15.37, deck + 1.69), (1.1, 0.07, 0.63))
        steel.tube((27, 16, deck + 0.015), (27, 16, deck + 0.09), 5.7, 36)
        for side in (-1.4, 1.4):
            cabin.box((27 + side, 16, deck + 0.097), (0.18, 4.9, 0.017))
        cabin.box((27, 16, deck + 0.097), (2.9, 0.18, 0.017))
        part.details.extend(
            (
                ("Grúa de celosía y caseta", "Refuerzo", "Servicios de cubierta"),
                ("Plataforma de toma", "Aislante", "Implantación conceptual"),
            )
        )
    elif project.id == "terminal-costera":
        base.box((4, 0, deck - 0.40), (66, 38, 0.8))
        base.box((-27, 2, deck - 0.36), (16, 8, 0.72))
        for x in (-31, -25, -20):
            steel.tube((x, 2, -1), (x, 2, deck - 0.3), 0.48)
            steel.box((x, 5.9, deck - 0.36), (0.9, 0.55, 0.95))
            yellow.tube((x, 5.6, deck + 0.04), (x, 5.6, deck + 0.56), 0.17)
        for x in (0, 18):
            base.tube((x, 8, deck - 0.17), (x, 8, deck + 0.02), 7.35, 24)
    else:
        base.box((0, 6, deck - 0.23), (67, 39, 0.46))
        part.material("Asfalto").box((0, -11, deck + 0.015), (65, 4, 0.05))
        for x in range(-28, 29, 7):
            yellow.box((x, -11, deck + 0.046), (3, 0.12, 0.012))
        for y in (17, 20.5):
            part.material("Aislante").box((-26, y, deck + 0.81), (5.4, 2.7, 1.63))
            steel.box((-26, y, deck + 1.72), (5.54, 2.82, 0.20))
            for x in (-27.4, -25.8, -24.2):
                steel.box((x, y - 1.39, deck + 0.92), (0.52, 0.06, 1.08))
    for x in (-22, -12, -2, 8, 18, 26):
        for y in (-7, -2):
            steel.box((x, y, deck + 1.8), (0.22, 0.22, 3.6))
        steel.box((x, -4.5, deck + 3.5), (0.24, 5.3, 0.24))
    part.details.append(("Bases, accesos y pórticos", "Refuerzo", "Implantación de referencia"))
    return part


def scene(project: Project, active: set[str]):
    equipment = {item.tag: item for item in project.equipment}
    lines = {item.tag: item for item in project.lines}
    for change in project.changes:
        if change.tag not in active:
            continue
        if (item := equipment.get(change.tag)) is not None:
            w, d, h = item.size
            size = (w, change.after, h) if change.property == "width" else (w, d, change.after)
            equipment[change.tag] = replace(item, size=size)
        else:
            line = lines[change.tag]
            value = int(change.after) if change.property == "dn" else change.after
            lines[change.tag] = replace(line, **{change.property: value})
    nozzles = ports(project, equipment)
    paths = {line.tag: line_path(project, line, nozzles) for line in lines.values()}
    parts = [
        equipment_part(
            item,
            project.deck,
            [(line, point) for (tag, line), point in nozzles.items() if tag == item.tag],
        )
        for item in equipment.values()
    ]
    parts.extend(line_part(line, paths[line.tag]) for line in lines.values())
    parts.append(structure(project))
    return equipment, lines, paths, parts
