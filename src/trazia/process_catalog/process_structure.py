"""Infraestructura de las plantas (ST-00): losas, rack de tuberías, accesos y plataforma marina.

La estructura es una raíz IfcElementAssembly con subelementos con nombre. Coordenadas en
metros en el sistema local del IFC (+X este, +Y norte de dibujo, +Z elevación).
"""

from dataclasses import dataclass
from math import ceil, cos, floor, pi, sin, tau

import numpy as np

from .process_geometry import Part, insulation
from .process_mesh import (
    UP,
    anchor_bolts,
    angle_bar,
    beam,
    box,
    grating_deck,
    ibeam,
    ladder,
    lathe,
    oriented_box,
    railing,
    revolve,
    stair_flight,
    torus,
    tube,
    unit,
    vec,
)

# Franja Y del rack principal: las líneas con su tramo largo dentro de ella apoyan en él.
BAND = (-7.0, -2.0)
SHOE = 0.12
BEAM = 0.25  # canto de las vigas de nivel del rack
JACKET = 20  # lados de las patas del jacket: casi todo queda bajo el agua

# Losas por proyecto: (x mínimo, x máximo, y mínimo, y máximo).
SLABS = {
    "planta-desierto": (-33.5, 33.5, -13.5, 25.5),
    "refineria-activa": (-33.5, 33.5, -13.5, 26.5),
    "terminal-costera": (-19.0, 37.0, -21.0, 21.0),
}
DECK = (-33.5, 33.5, -9.0, 23.0)  # cubierta de la plataforma marina
JETTY = (-35.5, -19.0, -7.6, 7.0)  # plataforma de atraque de la terminal costera


def pipe_radius(line) -> float:
    return line.dn / 2000 + insulation(line)


@dataclass(frozen=True)
class Rack:
    """Rack de tuberías: pórticos según X y niveles de vigas según Z."""

    south: float
    north: float
    bents: tuple[float, ...]
    tiers: tuple[float, ...]
    tags: frozenset[str]

    def holds(self, line) -> bool:
        return line.tag in self.tags

    def tier_below(self, z: float) -> float:
        below = [t for t in self.tiers if t <= z + 1e-6]
        return max(below) if below else self.tiers[0]

    @property
    def x_range(self):
        return self.bents[0], self.bents[-1]

    @classmethod
    def build(cls, project, variants, paths):
        """'variants' son las líneas de todas las revisiones (para el ancho del rack) y
        'paths' los recorridos de la revisión A (para pórticos y niveles)."""
        deck = project.deck
        base = {line.tag: line for line in project.lines}
        held = sorted(tag for tag, line in base.items() if BAND[0] <= line.rack_y <= BAND[1])
        every = [line for lines in variants for line in lines.values() if line.tag in held]
        south = min(line.rack_y - pipe_radius(line) for line in every) - 0.45
        north = max(line.rack_y + pipe_radius(line) for line in every) + 0.45
        south, north = floor(south * 20) / 20, ceil(north * 20) / 20
        xs = [x for tag in held for x in (paths[tag][3][0], paths[tag][4][0])]
        x_lo, x_hi = min(xs) - 1.2, max(xs) + 1.2
        # Cruces: tramos según Y que atraviesan la franja del rack (subidas y líneas ajenas).
        crossings = []
        supports = []
        for tag, path in paths.items():
            line = base[tag]
            r = pipe_radius(line)
            for a, b in zip(path, path[1:]):
                if abs(a[0] - b[0]) > 1e-6 or abs(a[2] - b[2]) > 1e-6:
                    continue
                lo, hi = sorted((a[1], b[1]))
                if hi > south - 0.3 and lo < north + 0.3:
                    crossings.append((a[0], r))
                    if tag not in held and lo < south and hi > north:
                        supports.append((a[2] - r - SHOE, a[2] + r))
        count = max(2, ceil((x_hi - x_lo) / 6.0) + 1)
        bents = []
        for i in range(count):
            x = x_lo + (x_hi - x_lo) * i / (count - 1)
            for _ in range(6):
                clash = [(cx, cr) for cx, cr in crossings if abs(x - cx) < cr + 0.45]
                if not clash:
                    break
                cx, cr = clash[0]
                x = cx + (cr + 0.5) * (1 if x >= cx or i == 0 else -1)
                if i == count - 1 and x > cx:
                    x = cx - (cr + 0.5)
            bents.append(round(x, 3))
        bents = tuple(sorted(bents))
        # Niveles: grupos de apoyos separados lo bastante para meter una viga entre ellos.
        rest = sorted(
            [
                (
                    deck + base[t].rack_z - pipe_radius(base[t]) - SHOE,
                    deck + base[t].rack_z + pipe_radius(base[t]),
                )
                for t in held
            ]
            + supports
        )
        tiers = [floor(rest[0][0] * 20) / 20]
        top = rest[0][1]
        for bottom, upper in rest[1:]:
            candidate = floor(bottom * 20) / 20
            if candidate - BEAM - 0.05 > top and candidate - tiers[-1] > 1.2:
                tiers.append(candidate)
            top = max(top, upper)
        if len(tiers) == 1:
            tiers.append(round(ceil((top + BEAM + 0.45) * 20) / 20, 3))
        return cls(south, north, bents, tuple(round(t, 3) for t in tiers), frozenset(held))


# --- Rack de tuberías ----------------------------------------------------------------------


def base_plate(comp, x, y, z, size=0.5, bolts=4):
    """Placa de anclaje con lechada y pernos."""
    box(comp.mesh("Lechada"), (x, y, z + 0.025), (size + 0.08, size + 0.08, 0.05))
    box(comp.mesh("Refuerzo"), (x, y, z + 0.06), (size, size, 0.025))
    d = size / 2 - 0.07
    points = [(x + i * d, y + j * d, z + 0.0725) for i in (-1, 1) for j in (-1, 1)][:bolts]
    return anchor_bolts(comp.mesh("Acero"), points, radius=0.02, height=0.07)


def pipe_rack(part, project, rack):
    deck = project.deck
    south, north = rack.south, rack.north
    top = rack.tiers[-1]
    columns = part.add("rack-pilares", "Pilares del rack", "IfcColumn", "COLUMN", "Pórticos")
    bolts = 0
    for x in rack.bents:
        for y in (south, north):
            ibeam(
                columns.mesh("Refuerzo"),
                (x, y, deck + 0.085),
                (x, y, top),
                0.3,
                0.3,
                (1, 0, 0),
                ends=(False, True),
            )
            bolts += base_plate(columns, x, y, deck)
    columns.measure(
        NumeroPilares=2 * len(rack.bents),
        NumeroPorticos=len(rack.bents),
        AlturaM=top - deck,
        NumeroPernos=bolts,
    )

    beams = part.add("rack-vigas", "Vigas de nivel y longitudinales", "IfcBeam", "BEAM", "Apoyo")
    steel = beams.mesh("Refuerzo")
    for z in rack.tiers:
        for x in rack.bents:
            ibeam(steel, (x, south - 0.2, z - BEAM / 2), (x, north + 0.2, z - BEAM / 2), BEAM, 0.16)
        for y in (south, north):
            for a, b in zip(rack.bents, rack.bents[1:]):
                ibeam(
                    steel,
                    (a + 0.15, y, z - 0.11),
                    (b - 0.15, y, z - 0.11),
                    0.22,
                    0.12,
                    ends=(False, False),
                )
    span = max(b - a for a, b in zip(rack.bents, rack.bents[1:]))
    beams.measure(
        LongitudM=rack.bents[-1] - rack.bents[0],
        AnchoM=north - south,
        VanoM=span,
        **{f"CotaNivel{i}M": z for i, z in enumerate(rack.tiers, 1)},
    )

    braces = part.add("rack-arriostramiento", "Arriostramiento", "IfcMember", "BRACE", "Rigidez")
    steel = braces.mesh("Refuerzo")
    low = rack.tiers[0] - BEAM
    count = 0
    for x in rack.bents:
        for y, sign in ((south, 1), (north, -1)):
            angle_bar(
                steel,
                (x, y, low - 1.0),
                (x, y + sign * 1.0, low),
                0.08,
                (1, 0, 0),
                ends=(False, False),
            )
            count += 1
    bays = list(zip(rack.bents, rack.bents[1:]))
    for a, b in bays[:: max(1, len(bays) // 3)][:3]:
        for y in (south, north):
            angle_bar(
                steel,
                (a + 0.15, y, deck + 0.3),
                (b - 0.15, y, low - 0.1),
                0.09,
                (0, 1, 0),
                ends=(False, False),
            )
            angle_bar(
                steel,
                (b - 0.15, y, deck + 0.3),
                (a + 0.15, y, low - 0.1),
                0.09,
                (0, 1, 0),
                ends=(False, False),
            )
            count += 2
    braces.measure(NumeroDiagonales=count)

    trays = part.add(
        "bandejas-cables",
        "Bandejas de cables",
        "IfcCableCarrierSegment",
        "CABLETRAYSEGMENT",
        "Cables de fuerza e instrumentos",
    )
    x0, x1 = rack.bents[0] - 0.2, rack.bents[-1] + 0.2
    lanes = (north - 0.45, north - 1.2)
    for i, y in enumerate(lanes):
        z = top + 0.02 + 0.32 * i
        if i:
            for x in rack.bents:
                beam(
                    trays.mesh("Refuerzo"),
                    (x, y - 0.4, z - 0.05),
                    (x, y + 0.4, z - 0.05),
                    0.06,
                    0.06,
                )
                for k in (-1, 1):
                    beam(
                        trays.mesh("Refuerzo"),
                        (x, y + k * 0.38, top),
                        (x, y + k * 0.38, z - 0.08),
                        0.05,
                        0.05,
                    )
        box(trays.mesh("Galvanizado"), ((x0 + x1) / 2, y, z + 0.005), (x1 - x0, 0.6, 0.01))
        for k in (-1, 1):
            box(
                trays.mesh("Galvanizado"),
                ((x0 + x1) / 2, y + k * 0.3, z + 0.05),
                (x1 - x0, 0.012, 0.1),
            )
        box(trays.mesh("Junta"), ((x0 + x1) / 2, y - 0.08, z + 0.045), (x1 - x0, 0.36, 0.07))
    trays.measure(NumeroBandejas=len(lanes), AnchoM=0.6, LongitudM=x1 - x0, CotaM=top + 0.02)

    access = part.add(
        "rack-escala", "Escala de acceso al rack", "IfcStairFlight", "STRAIGHT", "Mantenimiento"
    )
    xe = rack.bents[-1] + 0.65
    rungs = ladder(
        access.mesh("Seguridad"),
        access.mesh("Seguridad"),
        (xe, (south + north) / 2, deck),
        top,
        (1, 0, 0),
    )
    access.measure(AlturaM=top - deck, NumeroPeldanos=rungs, AnchoM=0.46)


# --- Elementos comunes en tierra -----------------------------------------------------------


def slab(part, project, extent, *, label="Losa de la planta"):
    deck = project.deck
    x0, x1, y0, y1 = extent
    s = part.add("losa", label, "IfcSlab", "BASESLAB", "Pavimento de hormigón")
    box(s.mesh("Hormigón"), ((x0 + x1) / 2, (y0 + y1) / 2, deck - 0.2), (x1 - x0, y1 - y0, 0.4))
    s.measure(LongitudM=x1 - x0, AnchoM=y1 - y0, EspesorM=0.4, CotaM=deck)
    k = part.add(
        "bordillos", "Bordillos", "IfcBuildingElementProxy", "ELEMENT", "Contención y drenaje"
    )
    for (ax, ay), (bx, by) in (
        ((x0, y0), (x1, y0)),
        ((x1, y0), (x1, y1)),
        ((x1, y1), (x0, y1)),
        ((x0, y1), (x0, y0)),
    ):
        beam(k.mesh("Hormigón"), (ax, ay, deck + 0.075), (bx, by, deck + 0.075), 0.2, 0.15)
    k.measure(LongitudM=2 * (x1 - x0 + y1 - y0), AlturaM=0.15, AnchoM=0.2)


def road(part, project, x0, x1, y, *, width=5.0):
    deck = project.deck
    r = part.add("vial", "Vial de servicio", "IfcSlab", "USERDEFINED", "Circulación de vehículos")
    r.object_type = "Vial"
    box(r.mesh("Asfalto"), ((x0 + x1) / 2, y, deck + 0.02), (x1 - x0, width, 0.04))
    for k in (-1, 1):
        box(
            r.mesh("Blanco"),
            ((x0 + x1) / 2, y + k * (width / 2 - 0.2), deck + 0.042),
            (x1 - x0, 0.12, 0.004),
        )
    dashes = int((x1 - x0) / 6)
    for i in range(dashes):
        x = x0 + (i + 0.5) * (x1 - x0) / dashes
        box(r.mesh("Blanco"), (x, y, deck + 0.042), (3.0, 0.12, 0.004))
    r.measure(LongitudM=x1 - x0, AnchoM=width)


def fence(part, project, extent, gate):
    """Cerramiento de malla: postes, alambres tensores y brazo con espino."""
    deck = project.deck
    x0, x1, y0, y1 = extent
    f = part.add(
        "cerramiento", "Cerramiento perimetral", "IfcRailing", "USERDEFINED", "Seguridad física"
    )
    f.object_type = "Cerramiento"
    g0, g1 = gate
    runs = [
        ((x0, y0), (g0, y0)),
        ((g1, y0), (x1, y0)),
        ((x1, y0), (x1, y1)),
        ((x1, y1), (x0, y1)),
        ((x0, y1), (x0, y0)),
    ]
    posts = 0
    total = 0.0
    for (ax, ay), (bx, by) in runs:
        a, b = vec((ax, ay, deck)), vec((bx, by, deck))
        length = float(np.linalg.norm(b - a))
        if length < 0.5:
            continue
        total += length
        n = max(1, ceil(length / 3.0))
        d = unit(b - a)
        out = np.cross(d, UP)
        for i in range(n + 1):
            p = a + (b - a) * i / n
            tube(f.mesh("Galvanizado"), p, p + vec((0, 0, 2.4)), 0.035, 6, caps=(False, True))
            tube(
                f.mesh("Galvanizado"),
                p + vec((0, 0, 2.35)),
                p + vec((0, 0, 2.35)) + out * 0.3 + vec((0, 0, 0.25)),
                0.015,
                4,
                caps=(False, False),
            )
            posts += 1
        for h in (0.1, 1.2, 2.3):
            tube(f.mesh("Galvanizado"), a + vec((0, 0, h)), b + vec((0, 0, h)), 0.008, 4)
        for h in (0.1, 0.22):
            p, q = a + out * 0.3 + vec((0, 0, 2.6 - h)), b + out * 0.3 + vec((0, 0, 2.6 - h))
            tube(f.mesh("Galvanizado"), p, q, 0.006, 4)
        # Malla: lámina fina en el plano del cerramiento.
        beam(f.mesh("Malla"), a + vec((0, 0, 1.2)), b + vec((0, 0, 1.2)), 0.01, 2.2)
    for x in (g0, g1):
        tube(f.mesh("Refuerzo"), (x, y0, deck), (x, y0, deck + 2.6), 0.08, 8)
    f.measure(LongitudM=total, AlturaM=2.6, NumeroPostes=posts)


def lighting(part, project, points, *, height=9.0, label="Alumbrado exterior"):
    """Báculos de alumbrado con brazo y proyector."""
    deck = project.deck
    lamp = part.add(
        "alumbrado", label, "IfcLightFixture", "DIRECTIONSOURCE", "Iluminación nocturna"
    )
    for x, y, heading in points:
        b = vec((x, y, deck))
        box(lamp.mesh("Hormigón"), (x, y, deck + 0.15), (0.5, 0.5, 0.3))
        lathe(
            lamp.mesh("Galvanizado"),
            b + vec((0, 0, 0.3)),
            UP,
            ((0.0, 0.09), (height - 0.3, 0.045)),
            8,
            caps=(True, True),
        )
        h = vec((cos(heading), sin(heading), 0.0))
        top = b + vec((0, 0, height))
        tube(
            lamp.mesh("Galvanizado"),
            top - vec((0, 0, 0.1)),
            top + h * 1.2 + vec((0, 0, 0.15)),
            0.035,
            6,
        )
        head = top + h * 1.35 + vec((0, 0, 0.1))
        oriented_box(lamp.mesh("Refuerzo"), head, (h, np.cross(UP, h), vec(UP)), (0.32, 0.18, 0.07))
        oriented_box(
            lamp.mesh("Blanco"),
            head - vec((0, 0, 0.075)),
            (h, np.cross(UP, h), vec(UP)),
            (0.28, 0.15, 0.006),
        )
    lamp.measure(NumeroBaculos=len(points), AlturaM=height)


def building(part, project, key, label, center, size, *, storeys=1, heading=1):
    """Edificio de control o subestación: muros, ventanas, puertas, cubierta y climatizadores."""
    deck = project.deck
    x, y = center
    length, width = size
    height = 3.4 * storeys
    b = part.add(key, label, "IfcBuildingElementProxy", "ELEMENT", "Edificio auxiliar")
    box(b.mesh("Hormigón"), (x, y, deck + 0.1), (length + 0.4, width + 0.4, 0.2))
    box(b.mesh("Blanco"), (x, y, deck + 0.2 + height / 2), (length, width, height))
    box(b.mesh("Cubierta"), (x, y, deck + 0.2 + height + 0.1), (length + 0.3, width + 0.3, 0.2))
    for k in (-1, 1):
        box(
            b.mesh("Cubierta"),
            (x, y + k * (width / 2 + 0.1), deck + 0.2 + height + 0.35),
            (length + 0.3, 0.1, 0.3),
        )
        box(
            b.mesh("Cubierta"),
            (x + k * (length / 2 + 0.1), y, deck + 0.2 + height + 0.35),
            (0.1, width + 0.3, 0.3),
        )
    face = y + heading * (width / 2 + 0.005)
    windows = max(2, int(length / 2.2))
    for s in range(storeys):
        z = deck + 0.2 + 3.4 * s + 1.75
        for i in range(windows):
            wx = x - length / 2 + (i + 0.5) * length / windows
            if s == 0 and i == windows // 2:
                box(b.mesh("Refuerzo"), (wx, face, deck + 0.2 + 1.05), (1.0, 0.02, 2.1))
                box(
                    b.mesh("Cubierta"),
                    (wx, face + heading * 0.6, deck + 0.2 + 2.45),
                    (1.6, 1.2, 0.08),
                )
                continue
            box(b.mesh("Vidrio"), (wx, face, z), (1.2, 0.02, 0.9))
            box(b.mesh("Aluminio"), (wx, face + heading * 0.04, z - 0.48), (1.3, 0.08, 0.05))
    units = max(1, int(length / 4))
    for i in range(units):
        ux = x - length / 2 + (i + 0.5) * length / units
        box(b.mesh("Acero"), (ux, y, deck + 0.2 + height + 0.55), (1.6, 1.0, 0.7))
        tube(
            b.mesh("Junta"),
            (ux, y, deck + 0.2 + height + 0.9),
            (ux, y, deck + 0.2 + height + 0.92),
            0.38,
            16,
        )
    b.measure(LongitudM=length, AnchoM=width, AlturaM=height + 0.4, NumeroPlantas=storeys)


def bund(part, project, center, half, *, height=1.2, key="cubeto", label="Cubeto del tanque"):
    """Muro de contención perimetral alrededor de un tanque."""
    deck = project.deck
    x, y = center
    w = part.add(key, label, "IfcWall", "PARAPET", "Retención de derrames")
    corners = [
        (x - half, y - half),
        (x + half, y - half),
        (x + half, y + half),
        (x - half, y + half),
    ]
    for (ax, ay), (bx, by) in zip(corners, corners[1:] + corners[:1]):
        beam(
            w.mesh("Hormigón"),
            (ax, ay, deck + height / 2),
            (bx, by, deck + height / 2),
            0.3,
            height,
        )
    # Pasos de escalera sobre el muro (dos tramos simétricos).
    steps = int(height / 0.2) + 1
    for s in range(steps):
        z = deck + 0.2 * (s + 1) - 0.02
        for k in (-1, 1):
            box(
                w.mesh("Rejilla"),
                (x - half + k * (0.3 + 0.26 * (steps - s)), y + 0.0, z),
                (0.24, 0.8, 0.04),
            )
    w.measure(LongitudM=8 * half, AlturaM=height, EspesorM=0.3)


def onshore(part, project, equipment, rack):
    extent = SLABS[project.id]
    x0, x1, y0, y1 = extent
    slab(part, project, extent)
    if project.id == "terminal-costera":
        road(part, project, x0 + 0.5, x1 - 0.5, y1 - 3.2)
        gate = (x1 - 9.0, x1 - 3.0)
    else:
        road(part, project, x0 + 0.5, x1 - 0.5, y0 + 3.2)
        gate = (x0 + 3.0, x0 + 9.0)
    fence(part, project, (x0 + 0.2, x1 - 0.2, y0 + 0.2, y1 - 0.2), gate)
    poles = [(x, y0 + 0.55, pi / 2) for x in np.linspace(x0 + 6, x1 - 6, 4)]
    poles += [(x0 + 0.9, y1 - 6, 0.0), (x1 - 0.9, y1 - 6, pi)]
    if project.id == "terminal-costera":
        poles = [(x, y1 - 0.55, -pi / 2) for x in np.linspace(x0 + 6, x1 - 6, 4)]
        poles += [(x1 - 0.9, y0 + 4, pi), (JETTY[0] + 0.6, 0.0, 0.0)]
    lighting(part, project, poles)
    if project.id == "terminal-costera":
        building(
            part,
            project,
            "edificio-control",
            "Edificio de control",
            (-11.0, 15.0),
            (9.0, 5.0),
            heading=-1,
        )
    else:
        building(
            part,
            project,
            "edificio-control",
            "Edificio de control",
            (-26.5, 20.0),
            (9.0, 5.0),
            heading=-1,
        )
    for item in equipment.values():
        if item.family == "tank" and project.id != "terminal-costera":
            half = item.size[1] / 2 + 2.0
            bund(part, project, item.xy, half)


# --- Terminal costera: plataforma de atraque -----------------------------------------------


def jetty(part, project):
    deck = project.deck
    x0, x1, y0, y1 = JETTY
    top = part.add("muelle", "Plataforma de atraque", "IfcSlab", "FLOOR", "Losa sobre pilotes")
    box(top.mesh("Hormigón"), ((x0 + x1) / 2, (y0 + y1) / 2, deck - 0.4), (x1 - x0, y1 - y0, 0.8))
    for x in np.linspace(x0 + 1.0, x1 - 1.0, 5):
        box(top.mesh("Hormigón"), (x, (y0 + y1) / 2, deck - 1.05), (0.8, y1 - y0 - 0.6, 0.5))
    top.measure(LongitudM=x1 - x0, AnchoM=y1 - y0, EspesorM=0.8, CotaM=deck)

    piles = part.add("pilotes", "Pilotes", "IfcPile", "DRIVEN", "Cimentación del muelle")
    count = 0
    for x in np.linspace(x0 + 1.0, x1 - 1.0, 5):
        for y in np.linspace(y0 + 1.0, y1 - 1.0, 4):
            tube(
                piles.mesh("Hormigón"),
                (x, y, -1.8),
                (x, y, deck - 1.3),
                0.38,
                12,
                caps=(False, False),
            )
            count += 1
    piles.measure(NumeroPilotes=count, DiametroM=0.76, CotaInferiorM=-1.8)

    fenders = part.add(
        "defensas",
        "Defensas de atraque",
        "IfcDiscreteAccessory",
        "USERDEFINED",
        "Amortiguación del buque",
    )
    fenders.object_type = "Defensa"
    bollards = part.add(
        "bolardos", "Bolardos", "IfcDiscreteAccessory", "USERDEFINED", "Amarre del buque"
    )
    bollards.object_type = "Bolardo"
    xf = x0 - 0.05
    for y in np.linspace(y0 + 2.0, y1 - 2.0, 4):
        box(fenders.mesh("Junta"), (xf - 0.45, y, deck - 0.9), (0.5, 2.0, 2.2))
        box(fenders.mesh("Refuerzo"), (xf - 0.75, y, deck - 0.9), (0.12, 2.4, 2.6))
        for k in (-1, 1):
            lathe(
                fenders.mesh("Junta"),
                (xf, y + k * 0.6, deck - 0.9),
                (-1, 0, 0),
                ((0, 0.42), (0.35, 0.36)),
                12,
            )
    for y in np.linspace(y0 + 1.2, y1 - 1.2, 3):
        p = vec((x0 + 0.7, y, deck))
        box(bollards.mesh("Refuerzo"), p + vec((0, 0, 0.03)), (0.7, 0.7, 0.06))
        lathe(
            bollards.mesh("Seguridad"),
            p + vec((0, 0, 0.06)),
            UP,
            ((0, 0.22), (0.4, 0.18), (0.45, 0.28), (0.55, 0.28)),
            16,
        )
        anchor_bolts(
            bollards.mesh("Acero"),
            [p + vec((i * 0.27, j * 0.27, 0.06)) for i in (-1, 1) for j in (-1, 1)],
        )
    fenders.measure(NumeroDefensas=4, AlturaM=2.6)
    bollards.measure(NumeroBolardos=3, AlturaM=0.55)

    guard = part.add(
        "barandilla-muelle",
        "Barandilla del muelle",
        "IfcRailing",
        "GUARDRAIL",
        "Protección de borde",
    )
    pts = [(x0 + 0.15, y0 + 0.15, deck), (x1, y0 + 0.15, deck)]
    length, posts = railing(guard.mesh("Seguridad"), guard.mesh("Seguridad"), pts)
    pts = [(x1, y1 - 0.15, deck), (x0 + 0.15, y1 - 0.15, deck)]
    length2, posts2 = railing(guard.mesh("Seguridad"), guard.mesh("Seguridad"), pts)
    guard.measure(LongitudM=length + length2, AlturaM=1.1, NumeroPostes=posts + posts2)


# --- Plataforma marina ---------------------------------------------------------------------


LEVELS = (-9.0, 1.0, 7.7, 14.8)


def node(bay, side, h, deck):
    flare = (deck - 1.2 - h) / (deck + 9)
    return vec((bay * (26.8 + 4.1 * flare), 7 + side * (10.8 + 4.6 * flare), h))


def offshore(part, project):
    deck = project.deck
    x0, x1, y0, y1 = DECK

    plate = part.add(
        "cubierta", "Cubierta de proceso", "IfcSlab", "FLOOR", "Piso de chapa estriada"
    )
    box(
        plate.mesh("Cubierta"),
        ((x0 + x1) / 2, (y0 + y1) / 2, deck - 0.015),
        (x1 - x0, y1 - y0, 0.03),
    )
    for (ax, ay), (bx, by) in (
        ((x0, y0), (x1, y0)),
        ((x1, y0), (x1, y1)),
        ((x1, y1), (x0, y1)),
        ((x0, y1), (x0, y0)),
    ):
        beam(plate.mesh("Seguridad"), (ax, ay, deck + 0.075), (bx, by, deck + 0.075), 0.012, 0.15)
    # Bandas de pasillo pintadas.
    for y in (-7.6, 8.6, 21.6):
        box(plate.mesh("Seguridad"), ((x0 + x1) / 2, y, deck + 0.001), (x1 - x0 - 2, 0.1, 0.002))
    plate.measure(LongitudM=x1 - x0, AnchoM=y1 - y0, CotaM=deck, EspesorM=0.03)

    girders = part.add("vigas-cubierta", "Vigas de la cubierta", "IfcBeam", "BEAM", "Emparrillado")
    steel = girders.mesh("Refuerzo")
    for y in (-8.35, -2.5, 5.5, 13.5, 21.8):
        ibeam(
            steel,
            (x0 + 0.3, y, deck - 0.6),
            (x1 - 0.3, y, deck - 0.6),
            1.14,
            0.5,
            ends=(False, False),
        )
    for x in range(-30, 31, 5):
        ibeam(
            steel,
            (x, y0 + 0.3, deck - 0.36),
            (x, y1 - 0.3, deck - 0.36),
            0.66,
            0.3,
            ends=(False, False),
        )
    for y in (y0 + 0.2, y1 - 0.2):
        ibeam(steel, (x0, y, deck - 0.43), (x1, y, deck - 0.43), 0.8, 0.3)
    for x in (x0 + 0.2, x1 - 0.2):
        ibeam(steel, (x, y0, deck - 0.43), (x, y1, deck - 0.43), 0.8, 0.3)
    girders.measure(NumeroVigas=5 + 13 + 4, CantoPrincipalM=1.14, CantoSecundarioM=0.66)

    legs = part.add("jacket-patas", "Patas del jacket", "IfcColumn", "COLUMN", "Estructura soporte")
    cans = 0
    for bay in (-1, 0, 1):
        for side in (-1, 1):
            bottom, top = node(bay, side, LEVELS[0], deck), node(bay, side, LEVELS[-1], deck)
            axis = top - bottom
            length = float(np.linalg.norm(axis))
            lathe(
                legs.mesh("Refuerzo"),
                bottom,
                axis,
                ((0, 1.1), (0.46 * length, 0.91), (length, 0.72)),
                JACKET,
                caps=(False, False),
            )
            for h in LEVELS[1:]:
                t = (h - LEVELS[0]) / (LEVELS[-1] - LEVELS[0])
                radius = (
                    0.91 + (0.72 - 0.91) * (t - 0.46) / 0.54
                    if t > 0.46
                    else 1.1 + (0.91 - 1.1) * t / 0.46
                ) + 0.06
                c = bottom + axis * t
                d = unit(axis)
                lathe(
                    legs.mesh("Refuerzo"),
                    c - d * 0.75,
                    d,
                    ((0, radius), (1.5, radius)),
                    JACKET,
                    caps=(False, False),
                )
                cans += 1
            # Revestimiento de la zona de salpicadura.
            ta = (-2.0 - LEVELS[0]) / (LEVELS[-1] - LEVELS[0])
            tb = (2.2 - LEVELS[0]) / (LEVELS[-1] - LEVELS[0])
            ra = 1.1 + (0.91 - 1.1) * ta / 0.46 + 0.035
            rb = 1.1 + (0.91 - 1.1) * tb / 0.46 + 0.035
            lathe(
                legs.mesh("Rojo"),
                bottom + axis * ta,
                axis,
                ((0, ra), (length * (tb - ta), rb)),
                JACKET,
                caps=(False, False),
            )
            # Cabeza de pata y transición a la cubierta.
            box(legs.mesh("Refuerzo"), (top[0], top[1], deck - 1.05), (2.6, 2.6, 0.3))
            lathe(
                legs.mesh("Refuerzo"),
                top,
                UP,
                ((0, 0.72), (deck - 1.2 - top[2], 0.72)),
                JACKET,
                caps=(False, False),
            )
    legs.measure(
        NumeroPatas=6,
        DiametroBaseM=2.2,
        DiametroCabezaM=1.44,
        NumeroNudos=cans,
        CotaInferiorM=LEVELS[0],
    )

    braces = part.add(
        "jacket-arriostramiento",
        "Arriostramiento del jacket",
        "IfcMember",
        "BRACE",
        "Celosía del jacket",
    )
    steel = braces.mesh("Refuerzo")
    count = 0

    def member(a, b, r):
        nonlocal count
        d = unit(b - a)
        # Los extremos quedan dentro de las patas: sin tapas.
        tube(steel, a + d * 0.6, b - d * 0.6, r, 12, caps=(False, False))
        count += 1

    for bay in (-1, 0, 1):
        for bottom, top in zip(LEVELS, LEVELS[1:]):
            member(node(bay, -1, top, deck), node(bay, 1, top, deck), 0.3)
            member(node(bay, -1, bottom, deck), node(bay, 1, top, deck), 0.34)
            member(node(bay, 1, bottom, deck), node(bay, -1, top, deck), 0.34)
    for side in (-1, 1):
        for bay in (-1, 0):
            for bottom, top in zip(LEVELS, LEVELS[1:]):
                member(node(bay, side, top, deck), node(bay + 1, side, top, deck), 0.3)
                member(node(bay, side, bottom, deck), node(bay + 1, side, top, deck), 0.32)
                member(node(bay + 1, side, bottom, deck), node(bay, side, top, deck), 0.32)
    # Diagonales en planta de los niveles intermedios.
    for h in LEVELS[1:3]:
        for bay in (-1, 0):
            member(node(bay, -1, h, deck), node(bay + 1, 1, h, deck), 0.26)
    braces.measure(NumeroBarras=count, DiametroM=0.68)

    # Embarcadero, defensas y escalera hasta la cubierta.
    landing_z = 3.15
    lx0, lx1, ly = -29.0, -20.0, -10.6
    land = part.add("embarcadero", "Embarcadero", "IfcSlab", "LANDING", "Acceso desde embarcación")
    grating_deck(
        land.mesh("Rejilla"),
        land.mesh("Refuerzo"),
        ((lx0 + lx1) / 2, ly, landing_z),
        (lx1 - lx0, 2.2),
    )
    for x in (lx0 + 0.6, lx1 - 0.6):
        leg = node(-1, -1, landing_z, deck)
        tube(
            land.mesh("Refuerzo"),
            (x, ly + 0.9, landing_z - 0.25),
            (leg[0] + (x - lx0) * 0.2, leg[1] - 0.8, landing_z - 1.6),
            0.16,
            10,
        )
    land.measure(LongitudM=lx1 - lx0, AnchoM=2.2, CotaM=landing_z)
    guard = part.add(
        "barandilla-embarcadero",
        "Barandilla del embarcadero",
        "IfcRailing",
        "GUARDRAIL",
        "Protección perimetral",
    )
    length, posts = railing(
        guard.mesh("Seguridad"),
        guard.mesh("Seguridad"),
        [
            (lx0 + 2.0, ly - 1.05, landing_z),
            (lx0, ly - 1.05, landing_z),
            (lx0, ly + 1.05, landing_z),
        ],
    )
    length2, posts2 = railing(
        guard.mesh("Seguridad"),
        guard.mesh("Seguridad"),
        [
            (lx1 - 2.0, ly - 1.05, landing_z),
            (lx1, ly - 1.05, landing_z),
            (lx1, ly + 1.05, landing_z),
        ],
    )
    guard.measure(LongitudM=length + length2, AlturaM=1.1, NumeroPostes=posts + posts2)

    bumpers = part.add(
        "defensas",
        "Defensas del embarcadero",
        "IfcDiscreteAccessory",
        "USERDEFINED",
        "Protección frente a impactos",
    )
    bumpers.object_type = "Defensa"
    for x in (lx0 + 2.6, lx1 - 2.6):
        tube(bumpers.mesh("Rojo"), (x, ly - 1.35, -2.5), (x, ly - 1.35, landing_z + 0.4), 0.3, 16)
        for z in (-1.2, 0.2, 1.6):
            tube(
                bumpers.mesh("Junta"), (x, ly - 1.35, z - 0.25), (x, ly - 1.35, z + 0.25), 0.36, 16
            )
        for z in (-1.8, landing_z - 0.3):
            tube(bumpers.mesh("Refuerzo"), (x, ly - 1.0, z), (x, ly + 1.4, z + 0.4), 0.14, 10)
    bumpers.measure(NumeroDefensas=2, DiametroM=0.6, CotaInferiorM=-2.5)

    stair = part.add(
        "escalera-embarcadero",
        "Escalera del embarcadero",
        "IfcStair",
        "HALF_TURN_STAIR",
        "Acceso a la cubierta",
    )
    flights = 4
    rise = (deck - landing_z) / flights
    run = rise / 0.78
    sx0 = lx1 - 0.9 - run
    total_steps = 0
    for i in range(flights):
        z0 = landing_z + rise * i
        y = ly + (0.55 if i % 2 == 0 else -0.55)
        a = (sx0, y, z0) if i % 2 == 0 else (sx0 + run, y, z0)
        b = (sx0 + run, y, z0 + rise) if i % 2 == 0 else (sx0, y, z0 + rise)
        steps, _ = stair_flight(
            stair.mesh("Refuerzo"),
            stair.mesh("Rejilla"),
            stair.mesh("Seguridad"),
            stair.mesh("Seguridad"),
            a,
            b,
            width=0.9,
            rails_both=False,
        )
        total_steps += steps
        if i < flights - 1:
            lx = b[0] + (0.6 if i % 2 == 0 else -0.6)
            grating_deck(
                stair.mesh("Rejilla"), stair.mesh("Refuerzo"), (lx, ly, z0 + rise), (1.2, 2.3)
            )
            tube(
                stair.mesh("Refuerzo"),
                (lx, ly - 1.0, z0 + rise - 0.2),
                (lx, ly - 1.0, landing_z),
                0.08,
                8,
            )
    stair.measure(
        AlturaM=deck - landing_z, NumeroTramos=flights, NumeroPeldanos=total_steps, AnchoM=0.9
    )

    # Grúa de celosía en el extremo noroeste.
    cx, cy = -29.5, 19.0
    pedestal = part.add(
        "grua-pedestal", "Pedestal de la grúa", "IfcColumn", "COLUMN", "Apoyo de la grúa"
    )
    lathe(
        pedestal.mesh("Seguridad"),
        (cx, cy, deck),
        UP,
        ((0, 1.3), (0.1, 1.3), (0.1, 0.95), (0.9, 0.85), (4.0, 0.85), (4.2, 1.15), (4.45, 1.15)),
        32,
    )
    torus(pedestal.mesh("Refuerzo"), (cx, cy, deck + 4.47), UP, 1.05, 0.06, 32, 4)
    anchor_bolts(
        pedestal.mesh("Acero"),
        [
            (cx + 1.15 * cos(a), cy + 1.15 * sin(a), deck + 0.1)
            for a in np.linspace(0, tau, 16, endpoint=False)
        ],
    )
    pedestal.measure(DiametroM=1.7, AlturaM=4.45)
    house = part.add(
        "grua-cabina",
        "Sala de máquinas y cabina",
        "IfcBuildingElementProxy",
        "ELEMENT",
        "Mando de la grúa",
    )
    hz = deck + 4.55
    box(house.mesh("Seguridad"), (cx + 0.6, cy, hz + 1.2), (4.2, 2.6, 2.4))
    box(house.mesh("Refuerzo"), (cx + 0.6, cy, hz + 0.08), (4.6, 3.0, 0.16))
    box(house.mesh("Seguridad"), (cx - 0.3, cy - 2.05, hz + 1.4), (1.6, 1.3, 2.0))
    box(house.mesh("Vidrio"), (cx - 0.3, cy - 2.71, hz + 1.7), (1.4, 0.02, 1.0))
    box(house.mesh("Vidrio"), (cx - 1.11, cy - 2.05, hz + 1.7), (0.02, 1.1, 1.0))
    for k in (-1, 1):
        tube(
            house.mesh("Refuerzo"),
            (cx + 2.2, cy + k * 1.0, hz + 2.4),
            (cx + 0.6, cy + k * 0.3, hz + 5.2),
            0.09,
            8,
        )
        tube(
            house.mesh("Refuerzo"),
            (cx - 0.9, cy + k * 1.0, hz + 2.4),
            (cx + 0.6, cy + k * 0.3, hz + 5.2),
            0.09,
            8,
        )
    box(house.mesh("Rojo"), (cx + 0.6, cy, hz + 5.3), (0.3, 0.9, 0.25))
    house.measure(LongitudM=4.6, AnchoM=3.0, AlturaM=5.45)

    boom = part.add(
        "grua-pluma", "Pluma de celosía", "IfcMember", "USERDEFINED", "Elevación de cargas"
    )
    boom.object_type = "Pluma de celosía"
    heel = vec((cx - 0.6, cy - 0.9, hz + 0.9))
    tip = vec((cx - 0.6, cy - 15.0, hz + 7.3))
    d = unit(tip - heel)
    side = unit(np.cross(d, UP))
    upv = np.cross(side, d)
    length = float(np.linalg.norm(tip - heel))
    panels = 10
    chords = []
    for i in range(panels + 1):
        t = i / panels
        half = 0.55 * (1 - 0.55 * abs(2 * t - 1) ** 2) if 0 < t < 1 else 0.18
        c = heel + (tip - heel) * t
        chords.append(
            [
                c + side * sx * half + upv * sz * half
                for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))
            ]
        )
    for k in range(4):
        for a, b in zip(chords, chords[1:]):
            tube(boom.mesh("Seguridad"), a[k], b[k], 0.07, 6, caps=(False, False))
    for i, (a, b) in enumerate(zip(chords, chords[1:])):
        for k in range(4):
            j = (k + 1) % 4
            p, q = (a[k], b[j]) if i % 2 == 0 else (a[j], b[k])
            tube(boom.mesh("Seguridad"), p, q, 0.035, 4, caps=(False, False))
    top_house = vec((cx + 0.6, cy, hz + 5.3))
    for k in (-1, 1):
        tube(
            boom.mesh("Acero"),
            top_house + side * k * 0.25,
            tip + upv * 0.2 + side * k * 0.15,
            0.025,
            4,
        )
    tube(boom.mesh("Acero"), tip, tip - vec((0, 0, 4.5)), 0.015, 4)
    hook = tip - vec((0, 0, 4.7))
    box(boom.mesh("Seguridad"), hook + vec((0, 0, 0.15)), (0.35, 0.25, 0.45))
    torus(
        boom.mesh("Acero"),
        hook - vec((0, 0, 0.15)),
        (1, 0, 0),
        0.12,
        0.03,
        10,
        4,
        start=pi,
        arc=pi * 1.3,
    )
    boom.measure(LongitudM=length, AlturaPuntaM=float(tip[2] - deck), NumeroPaneles=panels)

    # Módulo de alojamiento con escalera exterior y botes salvavidas.
    building(
        part,
        project,
        "modulo-alojamiento",
        "Módulo de alojamiento",
        (-15.5, 18.6),
        (8.6, 4.6),
        storeys=2,
        heading=-1,
    )
    mx, my = -15.5, 18.6
    ext = part.add(
        "escalera-modulo",
        "Escalera exterior del módulo",
        "IfcStairFlight",
        "STRAIGHT",
        "Acceso a la cubierta del módulo",
    )
    steps, run = stair_flight(
        ext.mesh("Refuerzo"),
        ext.mesh("Rejilla"),
        ext.mesh("Seguridad"),
        ext.mesh("Seguridad"),
        (mx + 4.3 + 0.75 + 5.4, my - 1.2, deck),
        (mx + 4.3 + 0.75, my - 1.2, deck + 4.2),
        width=0.9,
    )
    grating_deck(
        ext.mesh("Rejilla"),
        ext.mesh("Refuerzo"),
        (mx + 4.3 + 0.75, my - 0.3, deck + 4.2),
        (1.3, 2.6),
    )
    ext.measure(AlturaM=4.2, NumeroPeldanos=steps, LongitudM=run)
    roof = part.add(
        "barandilla-modulo",
        "Barandilla de cubierta del módulo",
        "IfcRailing",
        "GUARDRAIL",
        "Protección",
    )
    rz = deck + 0.2 + 6.8 + 0.2
    pts = [
        (mx - 4.3, my - 2.3, rz),
        (mx + 4.3, my - 2.3, rz),
        (mx + 4.3, my + 2.3, rz),
        (mx - 4.3, my + 2.3, rz),
    ]
    length, posts = railing(
        roof.mesh("Seguridad"), roof.mesh("Seguridad"), pts, closed=True, toe=False
    )
    roof.measure(LongitudM=length, AlturaM=1.1, NumeroPostes=posts)

    boats = part.add(
        "botes-salvavidas", "Botes salvavidas", "IfcBuildingElementProxy", "ELEMENT", "Evacuación"
    )
    for bx in (mx - 2.2, mx + 2.2):
        by, bz = my + 3.6, deck + 3.2
        profile = [
            (0.0, 0.0),
            (0.25, 0.55),
            (0.8, 1.0),
            (2.6, 1.15),
            (4.4, 1.0),
            (5.0, 0.6),
            (5.3, 0.0),
        ]
        hull = []
        for s, r in profile:
            hull.append((s, r))
        lathe(boats.mesh("Naranja"), (bx - 2.65, by, bz), (1, 0, 0), hull, 16)
        box(boats.mesh("Blanco"), (bx, by, bz + 0.95), (2.6, 1.5, 0.5))
        for k in (-1, 1):
            p = vec((bx + k * 2.3, my + 2.4, deck))
            tube(boats.mesh("Refuerzo"), p, p + vec((0, 0, bz - deck + 1.4)), 0.11, 8)
            tube(
                boats.mesh("Refuerzo"),
                p + vec((0, 0, bz - deck + 1.4)),
                p + vec((-k * 0.2, 1.2, bz - deck + 1.9)),
                0.09,
                8,
            )
            tube(
                boats.mesh("Acero"),
                p + vec((-k * 0.2, 1.2, bz - deck + 1.9)),
                (bx + k * 1.8, by, bz + 1.2),
                0.012,
                4,
            )
    boats.measure(NumeroBotes=2, LongitudM=5.3, DiametroM=2.3)

    # Helipuerto elevado con red perimetral.
    hx, hy, hzz = 27.6, 15.6, deck + 3.6
    hr = 6.4
    heli = part.add("helipuerto", "Helipuerto", "IfcSlab", "LANDING", "Toma de helicópteros")
    lathe(
        heli.mesh("Cubierta"),
        (hx, hy, hzz - 0.12),
        UP,
        ((0, hr), (0.12, hr)),
        32,
        caps=(True, True),
    )
    lathe(
        heli.mesh("Seguridad"),
        (hx, hy, hzz),
        UP,
        ((0, hr), (0.15, hr), (0.15, hr - 0.06), (0.0, hr - 0.06)),
        32,
        caps=(False, False),
    )
    torus(heli.mesh("Seguridad"), (hx, hy, hzz + 0.004), UP, 3.1, 0.3, 40, 4)
    for dx, dy, sx, sy in ((-1.0, 0.0, 0.35, 3.0), (1.0, 0.0, 0.35, 3.0), (0.0, 0.0, 2.0, 0.35)):
        box(heli.mesh("Blanco"), (hx + dx, hy + dy, hzz + 0.004), (sx, sy, 0.008))
    heli.measure(DiametroM=2 * hr, CotaM=hzz)
    frame = part.add(
        "helipuerto-estructura",
        "Estructura del helipuerto",
        "IfcMember",
        "MEMBER",
        "Soporte del helipuerto",
    )
    for a in np.linspace(0, tau, 6, endpoint=False):
        p = vec((hx + 4.0 * cos(a + 0.3), hy + 4.0 * sin(a + 0.3), deck))
        ibeam(
            frame.mesh("Refuerzo"),
            p,
            p + vec((0, 0, hzz - deck - 0.6)),
            0.3,
            0.3,
            (cos(a), sin(a), 0),
            ends=(False, True),
        )
        ibeam(
            frame.mesh("Refuerzo"),
            p + vec((0, 0, hzz - deck - 0.37)),
            vec((hx, hy, hzz - 0.37)),
            0.5,
            0.25,
            ends=(False, False),
        )
        box(frame.mesh("Refuerzo"), p + vec((0, 0, 0.02)), (0.6, 0.6, 0.04))
    for a in np.linspace(0, tau, 12, endpoint=False):
        w = vec((cos(a), sin(a), 0))
        ibeam(
            frame.mesh("Refuerzo"),
            vec((hx, hy, hzz - 0.37)) + w * 1.0,
            vec((hx, hy, hzz - 0.37)) + w * (hr - 0.2),
            0.5,
            0.2,
            ends=(False, False),
        )
    frame.measure(NumeroPilares=6, AlturaM=hzz - deck)
    net = part.add(
        "helipuerto-red",
        "Red perimetral del helipuerto",
        "IfcRailing",
        "USERDEFINED",
        "Protección contra caídas",
    )
    net.object_type = "Red perimetral"
    brackets = 32
    for i in range(brackets):
        a = i * tau / brackets
        w = vec((cos(a), sin(a), 0))
        p = vec((hx, hy, hzz)) + w * hr
        tube(
            net.mesh("Refuerzo"),
            p - vec((0, 0, 0.1)),
            p + w * 1.5 + vec((0, 0, 0.2)),
            0.03,
            4,
            caps=(False, False),
        )
    # Red de una sola lámina (cinta de dos caras) inclinada hacia fuera.
    revolve(
        net.mesh("Malla"),
        (hx, hy, hzz),
        UP,
        ((hr + 0.05, -0.03), (hr + 1.5, 0.22)),
        0.0,
        tau,
        48,
        caps=False,
    )
    net.measure(NumeroMensulas=brackets, AnchoM=1.5)
    hs = part.add(
        "helipuerto-escalera",
        "Escalera del helipuerto",
        "IfcStairFlight",
        "STRAIGHT",
        "Acceso al helipuerto",
    )
    sa = (hx - hr - 4.6, hy - 2.0, deck)
    sb = (hx - hr - 0.3, hy - 2.0, hzz)
    steps, run = stair_flight(
        hs.mesh("Refuerzo"),
        hs.mesh("Rejilla"),
        hs.mesh("Seguridad"),
        hs.mesh("Seguridad"),
        sa,
        sb,
        width=1.0,
    )
    hs.measure(AlturaM=hzz - deck, NumeroPeldanos=steps, LongitudM=run)

    # Barandilla perimetral con rodapié y huecos en los accesos.
    rail = part.add(
        "barandilla-perimetral",
        "Barandilla perimetral",
        "IfcRailing",
        "GUARDRAIL",
        "Protección de borde",
    )
    e = 0.12
    gap = (lx1 - 0.9 - run * 0 - 1.2, lx1 - 0.2)
    runs = [
        [
            (gap[1], y0 + e, deck),
            (x1 - e, y0 + e, deck),
            (x1 - e, y1 - e, deck),
            (x0 + e, y1 - e, deck),
            (x0 + e, y0 + e, deck),
            (gap[0], y0 + e, deck),
        ],
    ]
    total, posts = 0.0, 0
    for pts in runs:
        length, count = railing(rail.mesh("Seguridad"), rail.mesh("Seguridad"), pts, spacing=2.0)
        total += length
        posts += count
    rail.measure(LongitudM=total, AlturaM=1.1, NumeroPostes=posts)

    lighting(
        part,
        project,
        [
            (x0 + 0.6, y0 + 0.6, pi / 4),
            (x1 - 0.6, y0 + 0.6, 3 * pi / 4),
            (x0 + 0.6, 9.0, 0.0),
            (8.0, y1 - 0.6, -pi / 2),
        ],
        height=7.0,
        label="Proyectores de cubierta",
    )


def structure(project, rack, equipment, lines, paths) -> Part:
    part = Part("ST-00", "Infraestructura, accesos y rack", "structure")
    if project.id == "plataforma-marina":
        offshore(part, project)
    else:
        onshore(part, project, equipment, rack)
    if project.id == "terminal-costera":
        jetty(part, project)
    pipe_rack(part, project, rack)
    return part.finish()
