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
    "Junta": "#343f45",
    "Cubierta": "#67808b",
    "Rojo": "#c95745",
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

    def cap(self, a, b, radius, sides=24):
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
            sides,
        )

    def ring(self, x, y, z, radius, wire, sides=16):
        vertices = []
        for i in range(sides):
            angle = tau * i / sides
            for j in range(5):
                section = tau * j / 5
                r = radius + wire * cos(section)
                vertices.append((x + r * cos(angle), y + r * sin(angle), z + wire * sin(section)))
        self.add(
            vertices,
            [
                (
                    i * 5 + j,
                    ((i + 1) % sides) * 5 + j,
                    ((i + 1) % sides) * 5 + (j + 1) % 5,
                    i * 5 + (j + 1) % 5,
                )
                for i in range(sides)
                for j in range(5)
            ],
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


def connection_height(equipment: Equipment, deck: float) -> float:
    # Mantiene la virola sobre su cuna al ampliar el diámetro del separador.
    if equipment.family == "horizontal":
        return deck + max(1.7, equipment.size[1] / 2 + 0.55)
    return deck + 1.7


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
                result[tag, line.tag] = (
                    anchor,
                    y + side * radius,
                    connection_height(eq, project.deck),
                )
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


def flange(steel, gasket, a, axis, radius, *, bolts=6):
    """Unión ilustrativa de dos caras, junta y pernos, con el eje del conducto."""
    center, direction = np.array(a), np.array(axis)
    half = max(0.072, radius * 0.33)
    rim = radius + max(0.11, radius * 0.55)
    for side in (-1, 1):
        steel.tube(center + side * half * direction, center + side * 0.014 * direction, rim, 12)
    gasket.tube(center - 0.017 * direction, center + 0.017 * direction, rim * 0.93, 12)
    reference = (0, 0, 1) if direction[2] == 0 else (0, 1, 0)
    u = np.cross(direction, reference)
    v = np.cross(direction, u)
    for i in range(bolts):
        angle = (i + 0.5) * tau / bolts
        anchor = center + (rim + radius) * 0.51 * (u * cos(angle) + v * sin(angle))
        span = (half + 0.035) * direction
        steel.tube(anchor - span, anchor + span, 0.037, 6)


def grating(mesh, x, y, z, width, depth, count):
    for i in range(count):
        py = y + depth * ((i + 0.5) / count - 0.5)
        mesh.box((x, py, z), (width, 0.075, 0.06))
    for side in (-1, 1):
        mesh.box((x + side * (width / 2 - 0.04), y, z - 0.034), (0.08, depth, 0.08))


def handwheel(mesh, x, y, z, radius):
    mesh.ring(x, y, z, radius, 0.032, 12)
    for side in (-1, 1):
        mesh.tube((x - radius, y, z), (x + radius, y + side * radius * 0.65, z), 0.018, 5)


def fan(steel, guard, x, y, z, radius):
    steel.ring(x, y, z, radius, 0.035, 16)
    steel.tube((x, y, z - 0.09), (x, y, z + 0.02), radius * 0.20, 10)
    for i in range(6):
        angle = i * tau / 6
        points = []
        for distance, offset, hz in (
            (0.18, 0, 0.01),
            (0.90, 0.33, 0.03),
            (0.90, 0.67, -0.024),
            (0.25, 0.19, -0.02),
        ):
            points.append(
                (
                    x + radius * distance * cos(angle + offset),
                    y + radius * distance * sin(angle + offset),
                    z + hz,
                )
            )
        steel.add(points, [(0, 1, 2, 3), (3, 2, 1, 0)])
    for angle in (0, tau / 6, tau / 3):
        dx, dy = radius * cos(angle), radius * sin(angle)
        guard.tube((x - dx, y - dy, z + 0.11), (x + dx, y + dy, z + 0.11), 0.018, 5)


def equipment_part(eq: Equipment, deck: float, connections) -> Part:
    part = Part(eq.tag, eq.name, "equipment")
    x, y = eq.xy
    width, depth, height = eq.size
    steel = part.material("Acero")
    dark = part.material("Refuerzo")
    safety = part.material("Seguridad")
    motor = part.material("Motor")
    gasket = part.material("Junta")
    dark.box((x, y, deck + 0.15), (width * 0.98, depth * 0.98, 0.30))
    for ax in (-0.42, 0.42):
        for ay in (-0.42, 0.42):
            px, py = x + ax * width, y + ay * depth
            steel.box((px, py, deck + 0.32), (0.21, 0.21, 0.045))
            steel.tube((px, py, deck + 0.34), (px, py, deck + 0.41), 0.055, 6)
    part.details.append(("Bancada o anillo base", "Refuerzo", "Apoyo del equipo"))
    if eq.family == "horizontal":
        r = depth / 2
        axis_z = connection_height(eq, deck)
        steel.cap((x - width / 2, y, axis_z), (x + width / 2, y, axis_z), r)
        for px in (x - width * 0.25, x + width * 0.25):
            dark.box((px, y, deck + 0.65), (0.5, depth * 0.7, 0.95))
            steel.tube((px - 0.08, y, axis_z), (px + 0.08, y, axis_z), r * 1.015, 24)
        for px in (x - width * 0.24, x + width * 0.2):
            steel.tube((px, y, axis_z + r * 0.65), (px, y, axis_z + r + 0.48), 0.23)
            flange(steel, gasket, (px, y, axis_z + r + 0.48), (0, 0, 1), 0.23)
        for side in (-1, 1):
            seam = x + side * width * 0.336
            steel.tube((seam - 0.025, y, axis_z), (seam + 0.025, y, axis_z), r * 1.005, 24)
            steel.box((x + side * width * 0.27, y + 0.05, axis_z + r + 0.10), (0.20, 0.30, 0.23))
        part.details.extend(
            (
                ("Virola y dos cabezales", "Acero", "Recipiente horizontal"),
                ("Cunas, cordones y bocas bridadas", "Refuerzo", "Apoyo y acceso superior"),
            )
        )
    elif eq.family in ("vertical", "column", "tank"):
        r = depth / 2
        cylinder = part.material("Aislante") if eq.family == "tank" else steel
        start = deck + 0.45
        top = deck + height
        roof = (
            ((0.90, r), (0.97, r * 0.92), (1, r * 0.17))
            if eq.family == "tank"
            else ((0.88, r), (0.94, r * 0.90), (0.98, r * 0.61), (1, r * 0.19))
        )
        cylinder.revolve(
            (x, y, start),
            (x, y, top),
            ((0, r * 0.85), (0.04, r), *roof),
            24,
        )
        for fraction in (0.15, 0.42, 0.70, 0.87):
            h = start + (top - start) * fraction
            dark.tube((x, y, h - 0.055), (x, y, h + 0.055), r * 1.009, 24)
        landing = y - r - 0.23
        grating(dark, x, landing, top - 0.66, width * 0.74, 1.2, 10)
        railing(safety, x, landing, top - 0.62, width * 0.74, 1.19)
        ladder(dark, x, y - r - 0.16, deck + 0.24, height - 0.86)
        for fraction in (0.27, 0.50, 0.72):
            z = deck + height * fraction
            safety.ring(x, y - r - 0.28, z, 0.36, 0.028, 10)
            dark.box((x, y - r - 0.12, z), (0.62, 0.24, 0.08))
        steel.tube((x, y, top - 0.35), (x, y, top + 0.42), 0.19)
        flange(steel, gasket, (x, y, top + 0.40), (0, 0, 1), 0.19)
        z = deck + min(height * 0.26, 2.5)
        steel.tube((x + r * 0.92, y, z), (x + r + 0.28, y, z), 0.30)
        flange(steel, gasket, (x + r + 0.28, y, z), (1, 0, 0), 0.30)
        if eq.family == "tank":
            steel.ring(x, y, deck + 0.49, r * 1.03, 0.053, 24)
            for offset in (-0.38, 0.38):
                steel.box((x + width * offset, y - r * 0.65, deck + 0.70), (0.18, 0.23, 0.44))
        part.details.extend(
            (
                (
                    "Envolvente y cubierta conformada",
                    "Aislante" if eq.family == "tank" else "Acero",
                    "Geometría exterior",
                ),
                ("Escala protegida, rejilla y boca bridada", "Seguridad", "Acceso e inspección"),
            )
        )
    elif eq.family in ("pump", "compressor"):
        for offset in (-0.24, 0.24):
            row = y + depth * offset
            z = deck + height * 0.49
            steel.cap((x - width * 0.43, row, z), (x - width * 0.03, row, z), height * 0.34, 16)
            motor.tube((x + width * 0.08, row, z), (x + width * 0.43, row, z), height * 0.27, 16)
            dark.tube((x - width * 0.04, row, z), (x + width * 0.1, row, z), height * 0.20)
            for i in range(5):
                px = x + width * (0.14 + 0.052 * i)
                dark.tube((px - 0.04, row, z), (px + 0.04, row, z), height * 0.278, 16)
            dark.box((x, row, deck + 0.49), (width * 0.83, depth * 0.31, 0.55))
            motor.box((x + width * 0.25, row, z + height * 0.32), (0.57, 0.44, 0.30))
            steel.tube(
                (x - width * 0.22, row, z), (x - width * 0.22, row, z + height * 0.45), 0.19, 8
            )
            flange(
                steel, gasket, (x - width * 0.22, row, z + height * 0.46), (0, 0, 1), 0.19, bolts=4
            )
            safety.box((x + 0.047 * width, row, z + height * 0.18), (0.47, 0.51, 0.20))
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
                fan(motor, steel, px, py, deck + height * 0.94, depth * 0.17)
            for fin in range(11):
                px = x + width * (fin / 10 - 0.5)
                dark.box((px, py, deck + height * 0.89), (0.033, depth * 0.38, 0.053))
        railing(safety, x, y, deck + height * 0.87, width, depth)
        part.details.extend(
            (
                ("Dos módulos de transferencia", "Acero", "Banco en paralelo"),
                (
                    "Cuatro ventiladores con aspas y guardas",
                    "Motor",
                    "Intercambio con aire ambiente",
                ),
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
            flange(steel, gasket, (px, y, deck + height), (0, 0, 1), 0.25, bolts=4)
            dark.tube((px, y, deck + 0.44), (px, y, deck + 0.79), 0.14, 8)
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
        for px, py, pz in (b, c):
            flange(steel, gasket, (px, py + 0.16, pz), (0, 1, 0), 0.29)
        dark.tube((x, y, deck + 0.25), (x, y, deck + 0.82), 0.54, 12)
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
        r = line.dn / 2000
        steel.tube((px, y, pz), (px, py, pz), r, 10)
        flange(steel, gasket, (px, py, pz), (0, side, 0), r, bolts=4)
    if connections:
        part.details.append(
            ("Boquillas según DN de línea", "Acero", "Caras, juntas y pernos visibles")
        )
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


def rounded_pipe(mesh, nodes, radius, sides=10):
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
        for fraction in np.linspace(0.0, 1.0, 4):
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
    body = part.material("Acero")
    body.revolve(
        (x - 0.55, y, z), (x + 0.55, y, z), ((0, r), (0.25, r * 1.5), (0.75, r * 1.5), (1, r)), 12
    )
    for offset in (-0.58, 0.58):
        flange(body, part.material("Junta"), (x + offset, y, z), (1, 0, 0), r, bolts=4)
    steel.tube((x, y, z + r), (x, y, z + r + 0.32), max(0.11, r * 0.61), 10)
    steel.tube((x, y, z + r + 0.25), (x, y, z + r + 0.52), 0.048, 8)
    handwheel(part.material("Seguridad"), x, y, z + r + 0.52, 0.26 + r * 0.23)
    part.details.extend(
        (
            ("Tramos y cambios de dirección", line.fluid, f"DN {line.dn}"),
            ("Spool de doble brida y válvula con volante", "Refuerzo", "Conjunto desmontable"),
        )
    )
    return part


def offshore_jacket(part: Part, deck: float):
    steel = part.material("Refuerzo")
    yellow = part.material("Seguridad")
    surface = part.material("Cubierta")
    coating = part.material("Rojo")
    surface.box((0, 7, deck - 0.15), (67, 32, 0.30))
    for y in (-8.35, -2.5, 5.5, 13.5, 21.8):
        steel.box((0, y, deck - 0.78), (66.5, 0.58, 1.12))
    for x in range(-30, 31, 5):
        steel.box((x, 7, deck - 0.54), (0.31, 31.9, 0.64))
    for y in (-8.75, 22.75):
        steel.box((0, y, deck - 0.41), (67, 0.32, 0.82))
        yellow.box((0, y, deck + 0.042), (65, 0.18, 0.055))

    def node(bay, side, h):
        flare = (deck - 1.2 - h) / (deck + 9)
        return bay * (26.8 + 4.1 * flare), 7 + side * (10.8 + 4.6 * flare), h

    levels = (-9.0, 1.0, 7.7, deck - 1.2)
    for bay in (-1, 0, 1):
        for side in (-1, 1):
            bottom, top = node(bay, side, levels[0]), node(bay, side, levels[-1])
            steel.revolve(bottom, top, ((0, 1.10), (0.46, 0.91), (1, 0.68)), 12)
            for h in levels[1:]:
                radius = 0.99 if h < 3 else 0.80
                steel.tube(node(bay, side, h - 0.32), node(bay, side, h + 0.32), radius, 12)
            coating.tube(node(bay, side, -1.95), node(bay, side, 2.0), 1.02, 12)
            steel.box((top[0], top[1], deck - 0.96), (2.8, 2.35, 0.20))
        for bottom, top in zip(levels, levels[1:]):
            steel.tube(node(bay, -1, top), node(bay, 1, top), 0.26, 8)
            steel.tube(node(bay, -1, bottom), node(bay, 1, top), 0.33, 8)
            steel.tube(node(bay, 1, bottom), node(bay, -1, top), 0.33, 8)
    for side in (-1, 1):
        for bay in (-1, 0):
            for bottom, top in zip(levels, levels[1:]):
                steel.tube(node(bay, side, top), node(bay + 1, side, top), 0.27, 8)
                steel.tube(node(bay, side, bottom), node(bay + 1, side, top), 0.31, 8)
                steel.tube(node(bay + 1, side, bottom), node(bay, side, top), 0.31, 8)

    # Pasarela, escala y defensas de una cota de embarque definida en el mismo IFC.
    grating(steel, -24.5, -10.4, 3.15, 7.2, 2.1, 13)
    railing(yellow, -24.5, -10.4, 3.18, 7.2, 2.07)
    ladder(yellow, -23.5, -10.1, 3.2, deck - 3.2)
    for x in (-27, -22):
        coating.tube((x, -11.6, -0.95), (x, -11.6, 3.31), 0.28, 10)
        steel.tube((x, -10.3, 3.1), (x, -4.1, 1.05), 0.20, 8)
    railing(yellow, 0, 7, deck, 66, 31)
    for x in (-33.15, 33.15):
        for y in (-8, -2, 4, 10, 16, 22):
            yellow.tube((x, y, deck), (x, y, deck + 1.10), 0.043, 6)
        for h in (0.56, 1.10):
            yellow.tube((x, -8.1, deck + h), (x, 22.1, deck + h), 0.043, 6)
    part.details.extend(
        (
            (
                "Jacket de seis patas y tres niveles de cruces",
                "Refuerzo",
                "Arriostramiento ilustrativo",
            ),
            ("Cubierta con retícula de vigas", "Cubierta", f"Cota local +{deck:g} m"),
            ("Embarcadero, defensas y escala", "Seguridad", "Acceso de servicio"),
        )
    )


def structure(project: Project) -> Part:
    part = Part("ST-00", "Infraestructura, accesos y rack", "structure")
    base = part.material("Hormigón")
    steel = part.material("Refuerzo")
    yellow = part.material("Seguridad")
    deck = project.deck
    if project.id == "plataforma-marina":
        offshore_jacket(part, deck)
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
        railing(yellow, -29, 16, deck + 3.62, 3.6, 2.7)
        cabin = part.material("Aislante")
        cabin.box((-16, 17.5, deck + 1.2), (7, 4.2, 2.45))
        steel.box((-16, 17.5, deck + 2.5), (7.25, 4.5, 0.16))
        for x in (-18, -16, -14):
            part.material("Motor").box((x, 15.37, deck + 1.69), (1.1, 0.07, 0.63))
        for x in (-18.6, -13.4):
            grating(steel, x, 14.75, deck + 0.23, 1.43, 1.6, 7)
            cabin.box((x, 15.38, deck + 1.15), (0.76, 0.065, 1.92))
        steel.tube((27, 16, deck + 0.015), (27, 16, deck + 0.09), 5.7, 36)
        yellow.ring(27, 16, deck + 0.095, 5.38, 0.053, 32)
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
            part.material("Junta").box((x, 5.9, deck - 0.36), (0.95, 0.55, 1.12))
            yellow.tube((x, 5.6, deck + 0.04), (x, 5.6, deck + 0.56), 0.17)
            yellow.tube((x, 5.39, deck + 0.43), (x, 5.80, deck + 0.43), 0.10)
        grating(steel, -28, -0.89, deck + 0.13, 13, 1.15, 9)
        railing(yellow, -28, -0.89, deck + 0.17, 13, 1.19)
        for i in (-1, 1):
            x = -35 + i * 0.4
            steel.tube((x, 3, -1.05), (x, 3, deck + 0.25), 0.06, 8)
        for x in (0, 18):
            base.tube((x, 8, deck - 0.17), (x, 8, deck + 0.02), 7.35, 24)
            steel.ring(x, 8, deck + 0.03, 7.36, 0.095, 32)
        part.details.append(("Pilotes, defensas y bolardos", "Refuerzo", "Frente de atraque"))
    else:
        base.box((0, 6, deck - 0.23), (67, 39, 0.46))
        part.material("Asfalto").box((0, -11, deck + 0.015), (65, 4, 0.05))
        for x in range(-28, 29, 7):
            yellow.box((x, -11, deck + 0.046), (3, 0.12, 0.012))
        for y in (17, 20.5):
            part.material("Aislante").box((-26, y, deck + 0.81), (5.4, 2.7, 1.63))
            steel.box((-26, y, deck + 1.72), (5.54, 2.82, 0.20))
            grating(steel, -26, y - 1.65, deck + 0.16, 5.55, 0.58, 5)
            for x in (-27.4, -25.8, -24.2):
                steel.box((x, y - 1.39, deck + 0.92), (0.52, 0.06, 1.08))
            for i in range(13):
                steel.box((-28.45 + i * 0.41, y + 1.355, deck + 0.91), (0.047, 0.06, 1.47))
        for x in (-32.5, 32.5):
            for y in (-5, 1, 7, 13, 19, 24):
                steel.box((x, y, deck + 0.67), (0.13, 0.13, 1.34))
            for h in (0.35, 1.18):
                steel.tube((x, -5, deck + h), (x, 24, deck + h), 0.034, 6)
        part.details.append(("Casetas, rejilla y cerramiento", "Refuerzo", "Área de servicio"))
    for x in (-22, -12, -2, 8, 18, 26):
        for y in (-7, -2):
            steel.box((x, y, deck + 1.8), (0.22, 0.22, 3.6))
            steel.box((x, y, deck + 0.09), (0.42, 0.42, 0.18))
            steel.box((x, y, deck + 3.51), (0.31, 0.29, 0.19))
        steel.box((x, -4.5, deck + 3.5), (0.24, 5.3, 0.24))
        steel.tube((x, -7, deck + 2.72), (x, -6.17, deck + 3.5), 0.06, 6)
        steel.tube((x, -2, deck + 2.72), (x, -2.83, deck + 3.5), 0.06, 6)
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
            [(lines[line], point) for (tag, line), point in nozzles.items() if tag == item.tag],
        )
        for item in equipment.values()
    ]
    parts.extend(line_part(line, paths[line.tag]) for line in lines.values())
    parts.append(structure(project))
    return equipment, lines, paths, parts
