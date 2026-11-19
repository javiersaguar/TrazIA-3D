"""Geometría descompuesta de los complejos de proceso: equipos, líneas e infraestructura.

Cada equipo, línea o estructura es una raíz (Part) formada por subelementos con nombre
(Component). Cada subelemento lleva sus mallas por material y las medidas que salen de su
propia geometría. El IFC, los planos y los libros se generan a partir de estas mallas.
"""

import re
from dataclasses import dataclass, field, replace
from math import ceil, cos, degrees, pi, sin, sqrt, tau

import numpy as np

from .process_mesh import (
    SLAT_FACES,
    UP,
    Mesh,
    actuated_ball_valve,
    anchor_bolts,
    angle_bar,
    beam,
    blind_flange,
    bolt_ring,
    box,
    butterfly_valve,
    extrude,
    fillet,
    flange_half,
    flange_joint,
    flange_size,
    frame_along,
    gasket,
    gate_valve,
    grating_deck,
    ibeam,
    ladder,
    lathe,
    motor,
    oriented_box,
    path_length,
    point_at,
    quad,
    railing,
    revolve,
    sector_deck,
    subpath,
    sweep,
    torus,
    tube,
    unit,
    vec,
)
from .process_projects import SIZE_AXIS, Equipment, Line, Point, Project

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
    "Rejilla": "#4f5d66",
    "Galvanizado": "#a9b4ba",
    "Aluminio": "#c3ccd1",
    "Lechada": "#a39d92",
    "Vidrio": "#2f4a5c",
    "Naranja": "#de6f2c",
    "Blanco": "#eef1f2",
    "Malla": "#7d8a91",
}

SHELL = 48
SMALL = 40  # cuerpos cilíndricos de menos de 1 m (hidrociclones, carcasas, pedestales)
TANK = 64
PIPE = 16
FLANGE = 24
KEY = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
HOT = {"GS-04", "DG-14", "LP-33", "LP-34"}


@dataclass
class Component:
    """Subelemento con nombre: geometría por material y medidas propias."""

    key: str
    label: str
    ifc_class: str
    predefined: str | None = None
    role: str = ""
    meshes: dict[str, Mesh] = field(default_factory=dict)
    dims: dict[str, float | int] = field(default_factory=dict)
    object_type: str | None = None

    def mesh(self, material: str) -> Mesh:
        if material not in PALETTE:
            raise KeyError(f"Material sin definir en PALETTE: {material}")
        return self.meshes.setdefault(material, Mesh())

    def measure(self, **values):
        for name, value in values.items():
            if isinstance(value, bool):
                raise TypeError(name)
            self.dims[name] = int(value) if isinstance(value, int) else round(float(value), 3)
        return self

    @property
    def vertices(self):
        """Vértices en coordenadas del modelo, con las instancias desplegadas."""
        return [p for mesh in self.meshes.values() for p in mesh.expanded().vertices]

    @property
    def triangles(self) -> int:
        return sum(mesh.triangles for mesh in self.meshes.values())

    def bounds(self):
        points = np.array(self.vertices)
        return points.min(axis=0), points.max(axis=0)

    @property
    def material(self) -> str:
        """Material con más superficie aproximada (más caras)."""
        return max(self.meshes, key=lambda name: len(self.meshes[name].faces))


@dataclass
class Part:
    """Raíz de un equipo, una línea o la infraestructura."""

    tag: str
    name: str
    kind: str
    components: list[Component] = field(default_factory=list)

    def add(self, key, label, ifc_class, predefined=None, role="") -> Component:
        if not KEY.match(key):
            raise ValueError(f"Clave de subelemento no válida: {key}")
        if any(c.key == key for c in self.components):
            raise ValueError(f"Clave repetida en {self.tag}: {key}")
        component = Component(key, label, ifc_class, predefined, role)
        self.components.append(component)
        return component

    def finish(self):
        """Quita subelementos sin geometría y añade las cotas que salen de sus mallas."""
        self.components = [c for c in self.components if c.vertices]
        for c in self.components:
            low, high = c.bounds()
            c.dims.setdefault("CotaInferiorM", round(float(low[2]), 3))
            c.dims.setdefault("CotaSuperiorM", round(float(high[2]), 3))
        return self

    def drawing(self):
        """(material, malla desplegada) de cada subelemento, para planos y envolventes."""
        return [(name, mesh.expanded()) for c in self.components for name, mesh in c.meshes.items()]

    @property
    def vertices(self):
        return [p for c in self.components for p in c.vertices]

    @property
    def triangles(self) -> int:
        return sum(c.triangles for c in self.components)

    @property
    def details(self):
        return [(c.label, c.material, summary(c.dims)) for c in self.components]


LABELS = (
    ("DN", "DN {}"),
    ("DiametroM", "Ø {} m"),
    ("LongitudM", "L {} m"),
    ("AlturaM", "H {} m"),
    ("AnchoM", "A {} m"),
    ("FondoM", "F {} m"),
    ("ProfundidadM", "prof. {} m"),
    ("EspesorM", "e {} m"),
    ("ProyeccionM", "salida {} m"),
    ("CotaM", "cota {} m"),
    ("CotaEjeM", "eje {} m"),
    ("NumeroPeldanos", "{} peldaños"),
    ("NumeroPernos", "{} pernos"),
    ("NumeroAspas", "{} aspas"),
    ("NumeroSoportes", "{} soportes"),
    ("NumeroAros", "{} aros"),
    ("NumeroTubos", "{} tubos"),
)


def number(value) -> str:
    if isinstance(value, int):
        return str(value)
    return f"{value:.2f}".replace(".", ",")


def summary(dims) -> str:
    parts = [template.format(number(dims[name])) for name, template in LABELS if name in dims]
    return " · ".join(parts[:4]) or "—"


# --- Boquillas y recorridos de las líneas -------------------------------------------------


@dataclass(frozen=True)
class Nozzle:
    line: Line
    point: Point  # plano de junta: aquí está el puerto
    direction: Point  # hacia la tubería (±Y)
    incoming: bool


def leg(dn: float) -> float:
    """Primer tramo desde la boquilla: brida, codo de radio largo y algo de recto."""
    f = flange_size(dn)
    return round(max(0.75, 1.5 * dn / 1000 + f["thickness"] + f["hub"] + 0.18), 2)


def standout(dn: float) -> float:
    return round(0.22 + 0.55 * dn / 1000, 3)


def side_of(line: Line, eq: Equipment) -> int:
    return 1 if line.rack_y > eq.xy[1] else -1


def spread(eq: Equipment, lines, width):
    n = len(lines)
    spacing = width / (n + 1)
    return {line.tag: eq.xy[0] + spacing * (i - (n - 1) / 2) for i, line in enumerate(lines)}


def vessel_axis_z(eq: Equipment, deck: float) -> float:
    return deck + max(1.7, eq.size[1] / 2 + 0.55)


def skirt_height(eq: Equipment, base: Equipment) -> float:
    if eq.family == "column":
        return 2.0
    return round(min(1.3, max(0.9, 0.16 * base.size[2])), 2)


def vertical_levels(eq: Equipment, base: Equipment, deck: float):
    """Cotas de un recipiente vertical: pie del faldón, tangentes y cumbre."""
    r = eq.size[1] / 2
    hemi = eq.tag.startswith("R-")
    head = r if hemi else r / 2
    bottom_tangent = deck + skirt_height(eq, base)
    top_tangent = deck + eq.size[2] - head
    return bottom_tangent, top_tangent, head, hemi


def nozzle_height(eq: Equipment, base: Equipment, deck: float, line: Line, incoming: bool):
    family = eq.family
    if family == "horizontal":
        return vessel_axis_z(eq, deck)
    if family in ("vertical", "column"):
        bottom, top, _, _ = vertical_levels(eq, base, deck)
        span = top - bottom
        gas = line.fluid == "Gas"
        if eq.tag.startswith("R-"):
            return top - 0.9 if incoming else bottom + 0.9
        if incoming:
            return bottom + (0.22 if family == "column" else 0.35) * span
        return top - 0.75 if gas else bottom + 0.6
    if family == "tank":
        floor = deck + 0.4
        shell = eq.size[2] - 0.4 - tank_rise(eq)
        if line.fluid in ("GNL",) or line.tag.startswith("BOG"):
            return floor + shell - 0.55
        return floor + (shell - 1.0 if incoming else 0.9)
    return deck + 1.7


def layout_nozzles(project: Project, equipment, base_equipment, lines):
    """Puerto de cada extremo de línea: en el plano de junta de la boquilla del equipo."""
    deck = project.deck
    result = {}
    for tag, eq in equipment.items():
        base = base_equipment[tag]
        own = [line for line in lines.values() if tag in (line.start, line.end)]
        x0, y0 = eq.xy
        length, width, height = eq.size
        for side in (-1, 1):
            group = [line for line in own if side_of(line, eq) == side]
            if not group:
                continue
            for line in group:
                incoming = line.end == tag
                point = special_port(project, eq, base, line, incoming, side)
                if point is None:
                    family = eq.family
                    if family == "horizontal":
                        tt = length - eq.size[1] / 2
                        anchors = spread(eq, group, tt * 0.75)
                        reach = width / 2 + standout(line.dn)
                    elif family in ("vertical", "column", "tank"):
                        anchors = spread(eq, group, width * 0.62)
                        reach = width / 2 + standout(line.dn)
                    else:
                        anchors = spread(eq, group, length)
                        reach = width / 2
                    z = nozzle_height(eq, base, deck, line, incoming)
                    point = (anchors[line.tag], y0 + side * reach, z)
                result[tag, line.tag] = Nozzle(
                    line,
                    tuple(round(float(c), 3) for c in point),
                    (0.0, float(side), 0.0),
                    incoming,
                )
    return result


def special_port(project, eq: Equipment, base: Equipment, line: Line, incoming: bool, side: int):
    """Familias con colectores propios: el puerto está donde termina su tubería."""
    deck = project.deck
    x0, y0 = eq.xy
    length, width, height = eq.size
    face = y0 + side * width / 2
    family = eq.family
    if family == "pump":
        g = pump_geometry(eq, deck)
        return (
            (g["suction_x"], face, g["axis_z"])
            if incoming
            else (g["casing_x"], face, g["header_z"])
        )
    if family == "compressor":
        g = compressor_geometry(eq, deck)
        return (g["suction_x"] if incoming else g["discharge_x"], face, g["port_z"])
    if family == "air-cooler":
        g = cooler_geometry(eq, deck)
        return (
            (g["inlet_x"], face, g["inlet_z"]) if incoming else (g["outlet_x"], face, g["outlet_z"])
        )
    if family == "vaporizer":
        g = vaporizer_geometry(eq, deck)
        return (
            (g["inlet_x"], face, g["inlet_z"]) if incoming else (g["outlet_x"], face, g["outlet_z"])
        )
    if family == "cyclone":
        g = cyclone_geometry(eq, deck)
        return (
            (g["inlet_x"], face, g["inlet_z"]) if incoming else (g["outlet_x"], face, g["outlet_z"])
        )
    if family == "arm":
        return (x0 + 0.15 * length, face, deck + 0.95)
    return None


def line_path(project: Project, line: Line, nozzles):
    a = nozzles[line.start, line.tag]
    b = nozzles[line.end, line.tag]
    ay = a.point[1] + a.direction[1] * leg(line.dn)
    by = b.point[1] + b.direction[1] * leg(line.dn)
    z = project.deck + line.rack_z
    nodes = (
        a.point,
        (a.point[0], ay, a.point[2]),
        (a.point[0], ay, z),
        (a.point[0], line.rack_y, z),
        (b.point[0], line.rack_y, z),
        (b.point[0], by, z),
        (b.point[0], by, b.point[2]),
        b.point,
    )
    return tuple(tuple(round(float(c), 3) for c in node) for node in nodes)


# --- Detalles comunes de recipientes -------------------------------------------------------


def head_profile(r, depth, rings=7):
    return [
        (depth * sin(pi / 2 * k / rings), r * cos(pi / 2 * k / rings)) for k in range(rings + 1)
    ]


def vessel_head(mesh, base, outward, r, depth, *, sides=SHELL, rings=7):
    """Fondo elipsoidal 2:1 o semiesférico desde la línea de tangencia."""
    lathe(mesh, base, outward, head_profile(r, depth, rings), sides, caps=(False, False))


def nozzle(comp, shell_point, joint, dn, shell_radius, *, pad=True, material="Acero", sides=FLANGE):
    """Boquilla del equipo: cuello, placa de refuerzo y brida hasta el plano de junta."""
    steel = comp.mesh(material)
    f = flange_size(dn)
    s, j = vec(shell_point), vec(joint)
    d = unit(j - s)
    hub_start = j - d * (f["gap"] / 2 + f["thickness"] + f["hub"])
    tube(steel, s - d * 0.08, hub_start, f["r_pipe"], sides, caps=(False, False))
    flange_half(steel, j, d, dn, sides=sides)
    if pad and shell_radius:
        a = f["r_pipe"] * 1.85 + 0.03
        sag = min(0.25, a * a / (2 * shell_radius) + 0.01)
        tube(comp.mesh("Refuerzo"), s - d * sag, s + d * 0.022, a, sides)
    return float(np.linalg.norm(j - s))


def blind_nozzle(comp, shell_point, direction, dn, length, shell_radius, *, pad=True):
    """Boquilla de servicio con brida ciega atornillada."""
    s = vec(shell_point)
    d = unit(direction)
    joint = s + d * length
    nozzle(comp, s, joint, dn, shell_radius, pad=pad)
    bolts = blind_flange(comp.mesh("Acero"), comp.mesh("Junta"), joint, d, dn)
    return joint, bolts


def lifting_lug(mesh, base, normal, along, *, height=0.26, thickness=0.04, length=0.32):
    """Orejeta de izado: chapa con cabeza redondeada y placa de refuerzo."""
    n = unit(normal)
    a = unit(along)
    side = np.cross(n, a)
    b = vec(base)
    oriented_box(mesh, b + n * height / 2, (a, side, n), (length / 2, thickness / 2, height / 2))
    tube(
        mesh,
        b + n * height - side * thickness * 0.6,
        b + n * height + side * thickness * 0.6,
        length * 0.42,
        12,
    )
    oriented_box(mesh, b + n * 0.01, (a, side, n), (length * 0.7, length * 0.4, 0.012))


def nameplate(comp, base, outward):
    """Placa de características sobre ménsula."""
    o = unit((outward[0], outward[1], 0.0))
    side = np.cross(UP, o)
    b = vec(base)
    steel = comp.mesh("Refuerzo")
    oriented_box(steel, b + o * 0.06, (o, side, vec(UP)), (0.06, 0.05, 0.12))
    oriented_box(comp.mesh("Aluminio"), b + o * 0.125, (o, side, vec(UP)), (0.004, 0.17, 0.11))
    comp.measure(AnchoM=0.34, AlturaM=0.22)


def davit(mesh, base, height, reach, heading, *, radius=0.045):
    """Pescante: mástil con brazo, codo y gancho."""
    b = vec(base)
    h = vec((cos(heading), sin(heading), 0.0))
    top = b + vec(UP) * height
    tube(mesh, b - vec(UP) * 0.25, top - vec(UP) * 0.15, radius, 10)
    samples = fillet((b + vec(UP) * (height * 0.7), top, top + h * reach), 0.25, quarter=4)
    sweep(mesh, samples, radius * 0.85, 10)
    end = top + h * reach
    tube(mesh, end, end - vec(UP) * 0.35, 0.008, 6)
    torus(mesh, end - vec(UP) * 0.42, np.cross(h, UP), 0.05, 0.012, 8, 4, start=0.0, arc=pi * 1.4)
    tube(mesh, b - vec(UP) * 0.3, b + vec(UP) * 0.12, radius * 1.6, 10)


def manway(
    comp, shell_point, direction, *, dn=600, standout_=0.32, shell_radius=None, davit_side=1
):
    """Boca de hombre con tapa ciega atornillada y pescante de maniobra."""
    joint, bolts = blind_nozzle(comp, shell_point, direction, dn, standout_, shell_radius)
    d = unit(direction)
    f = flange_size(dn)
    steel = comp.mesh("Acero")
    # Asas de la tapa.
    cover = joint + d * (f["gap"] / 2 + f["thickness"])
    _, side, up = frame_along(cover, cover + d)
    for k in (-1, 1):
        p = cover + up * k * 0.12
        beam(steel, p - side * 0.1, p + side * 0.1, 0.02, 0.02, d)
    # Pescante con bisagra lateral sujeto al cuello.
    hinge = (
        joint - d * (f["thickness"] + f["hub"] + 0.05) + side * davit_side * (f["radius"] + 0.12)
    )
    post_top = hinge + vec(UP) * 0.55
    tube(steel, hinge - vec(UP) * 0.35, post_top, 0.03, 8)
    samples = fillet(
        (
            hinge + vec(UP) * 0.3,
            post_top,
            post_top - side * davit_side * (f["radius"] + 0.12) + d * 0.25,
        ),
        0.15,
        quarter=3,
    )
    sweep(steel, samples, 0.026, 8)
    beam(steel, hinge - d * 0.0, hinge - side * davit_side * 0.12, 0.05, 0.05, d)
    comp.measure(DN=dn, ProyeccionM=standout_, NumeroPernos=bolts)
    return joint


def platform_brackets(mesh, center, r_shell, r_out, z, angles, depth=0.7):
    """Ménsulas de una plataforma circular: viga radial y tornapuntas."""
    c = vec(center)
    for a in angles:
        w = vec((cos(a), sin(a), 0.0))
        inner = c + w * r_shell
        outer = c + w * (r_out - 0.05)
        beam(mesh, inner + vec((0, 0, z - 0.25)), outer + vec((0, 0, z - 0.25)), 0.1, 0.18, UP)
        angle_bar(
            mesh,
            inner + vec((0, 0, z - 0.25 - depth)),
            outer - w * 0.35 + vec((0, 0, z - 0.3)),
            0.07,
            np.cross(UP, w),
        )


def circular_platform(part, key, label, center, r_shell, z, start, end, *, width=1.2, rail=True):
    """Plataforma de rejilla en sector circular con su barandilla como subelemento propio."""
    deck = part.add(key, label, "IfcSlab", "LANDING", "Acceso e inspección")
    c = vec((center[0], center[1], z))
    r_in, r_out = r_shell + 0.08, r_shell + 0.08 + width
    sector_deck(deck.mesh("Rejilla"), deck.mesh("Refuerzo"), c, r_in, r_out, start, end)
    span = end - start
    count = max(2, ceil(span / (pi / 3)) + 1)
    platform_brackets(
        deck.mesh("Refuerzo"),
        (center[0], center[1], 0),
        r_shell,
        r_out,
        z,
        [start + span * (i + 0.5) / count for i in range(count)],
    )
    deck.measure(CotaM=z, AnchoM=width, DiametroM=2 * r_out, ArcoGrados=round(degrees(span), 1))
    if rail:
        guard = part.add(
            key.replace("plataforma", "barandilla"),
            label.replace("Plataforma", "Barandilla"),
            "IfcRailing",
            "GUARDRAIL",
            "Protección perimetral",
        )
        steps = max(4, ceil(span / (pi / 12)))
        r_rail = r_out - 0.04
        points = [c + vec((cos(start) * r_in, sin(start) * r_in, 0))]
        points += [
            c
            + vec(
                (cos(start + span * k / steps) * r_rail, sin(start + span * k / steps) * r_rail, 0)
            )
            for k in range(steps + 1)
        ]
        points.append(c + vec((cos(end) * r_in, sin(end) * r_in, 0)))
        length, posts = railing(
            guard.mesh("Seguridad"), guard.mesh("Seguridad"), points, spacing=1.6
        )
        guard.measure(LongitudM=length, AlturaM=1.1, NumeroPostes=posts)
    return deck


def column_ladder(part, key, label, center, radius, angle, z0, z1):
    comp = part.add(key, label, "IfcStairFlight", "STRAIGHT", "Escala de gato con jaula")
    w = vec((cos(angle), sin(angle), 0.0))
    base = vec((center[0], center[1], z0)) + w * radius
    rungs = ladder(comp.mesh("Seguridad"), comp.mesh("Seguridad"), base, z1, w)
    # Grapas de unión a la virola.
    for t in (0.25, 0.75):
        z = z0 + (z1 - z0) * t
        p = vec((center[0], center[1], z))
        for k in (-1, 1):
            q = p + w * radius + np.cross(UP, w) * k * 0.23
            beam(comp.mesh("Refuerzo"), q - w * (radius - (radius - 0.42)), q, 0.04, 0.04, UP)
    comp.measure(AlturaM=z1 - z0, NumeroPeldanos=rungs, AnchoM=0.46)
    return comp


# --- Familias de equipos -----------------------------------------------------------------


def free_side(eq: Equipment, nozzles) -> int:
    """Lado (±Y) con menos conexiones de línea."""
    count = {-1: 0, 1: 0}
    for item in nozzles:
        count[int(np.sign(item.direction[1]))] += 1
    return 1 if count[1] <= count[-1] else -1


def horizontal_vessel(part, eq, base, deck, nozzles):
    x0, y0 = eq.xy
    length, width, _ = eq.size
    r = width / 2
    head_depth = r / 2
    tt = length - 2 * head_depth
    zc = vessel_axis_z(eq, deck)
    xa, xb = x0 - tt / 2, x0 + tt / 2
    axis = vec((1.0, 0.0, 0.0))

    shell = part.add("virola", "Virola", "IfcPlate", "SHEET", "Cuerpo cilíndrico")
    tube(shell.mesh("Acero"), (xa, y0, zc), (xb, y0, zc), r, SHELL, caps=(False, False))
    for x in (x0 - tt * 0.17, x0 + tt * 0.17):
        tube(
            shell.mesh("Refuerzo"),
            (x - 0.006, y0, zc),
            (x + 0.006, y0, zc),
            r + 0.004,
            SHELL,
            caps=(False, False),
        )
    shell.measure(DiametroM=width, LongitudM=tt, CotaEjeM=zc)
    for key, label, x, sign in (
        ("fondo-oeste", "Fondo elipsoidal oeste", xa, -1),
        ("fondo-este", "Fondo elipsoidal este", xb, 1),
    ):
        h = part.add(key, label, "IfcPlate", "SHEET", "Cierre 2:1")
        vessel_head(h.mesh("Acero"), (x, y0, zc), axis * sign, r, head_depth)
        h.measure(DiametroM=width, ProfundidadM=head_depth)

    # Silletas con placa de desgaste, alma curva, nervios, placa base y pernos.
    z_floor = deck + 0.025
    saddle_w = 2 * r * 0.88 + 0.1
    for key, label, xs in (
        ("silleta-oeste", "Silleta oeste", xa + 0.2 * tt),
        ("silleta-este", "Silleta este", xb - 0.2 * tt),
    ):
        s = part.add(key, label, "IfcMember", "MEMBER", "Apoyo del recipiente")
        steel = s.mesh("Refuerzo")
        box(steel, (xs, y0, deck + 0.0125), (0.34, saddle_w, 0.025))
        arc = [(r * sin(a), (zc - deck) - r * cos(a)) for a in np.linspace(pi / 3, -pi / 3, 11)]
        polygon = [(-saddle_w / 2 + 0.03, 0.025), (saddle_w / 2 - 0.03, 0.025), *arc]
        extrude(steel, (xs - 0.011, y0, deck), axis, polygon, 0.022, center=(0.0, 0.025))
        revolve(
            s.mesh("Acero"),
            (xs - 0.22, y0, zc),
            axis,
            ((r, 0.0), (r + 0.014, 0.0), (r + 0.014, 0.44), (r, 0.44)),
            -pi / 2 - 1.1,
            -pi / 2 + 1.1,
            12,
        )
        for k in (-0.78, -0.4, 0.4, 0.78):
            y = k * r
            top = zc - sqrt(max(r * r - y * y, 0.01)) + 0.01
            box(steel, (xs, y0 + y, (z_floor + top) / 2), (0.3, 0.016, top - z_floor))
        bolts = anchor_bolts(
            steel, [(xs, y0 + k * (saddle_w / 2 - 0.12), deck + 0.025) for k in (-1, 1)]
        )
        s.measure(
            AnchoM=saddle_w,
            LongitudM=0.34,
            AlturaM=zc - r - deck,
            NumeroPernos=bolts,
            NumeroNervios=4,
        )

    rings = part.add(
        "anillos-rigidez", "Anillos de rigidez", "IfcMember", "MEMBER", "Rigidez de la virola"
    )
    for x in (x0 - tt * 0.36, x0 + tt * 0.36):
        lathe(
            rings.mesh("Refuerzo"),
            (x - 0.011, y0, zc),
            axis,
            ((0, r), (0, r + 0.075), (0.022, r + 0.075), (0.022, r)),
            32,
            caps=(False, False),
        )
    rings.measure(NumeroAnillos=2, AnchoM=0.075, EspesorM=0.022, DiametroM=width + 0.15)

    for item in nozzles:
        n = part.add(
            f"boquilla-{item.line.tag.lower()}",
            f"Boquilla {item.line.tag}",
            "IfcPipeFitting",
            "CONNECTOR",
            f"Conexión {item.line.tag}",
        )
        jx, jy, jz = item.point
        side = item.direction[1]
        reach = nozzle(n, (jx, y0 + side * r, jz), item.point, item.line.dn, r)
        n.measure(DN=item.line.dn, ProyeccionM=reach, CotaEjeM=jz)

    # Boca de hombre en el fondo este con pescante.
    mw = part.add(
        "boca-hombre", "Boca de hombre", "IfcDiscreteAccessory", "USERDEFINED", "Acceso al interior"
    )
    manway(mw, (xb + head_depth * 0.92, y0, zc), axis, shell_radius=None, davit_side=1)
    mw.measure(CotaEjeM=zc)

    # Válvula de seguridad sobre la virola.
    top = zc + r
    psv = part.add(
        "valvula-seguridad",
        "Válvula de seguridad",
        "IfcValve",
        "PRESSURERELIEF",
        "Alivio de presión",
    )
    x_psv = x0 + 0.22 * tt
    relief_valve(psv, (x_psv, y0, top), 150, r)

    lugs = part.add(
        "orejetas", "Orejetas de izado", "IfcDiscreteAccessory", "USERDEFINED", "Izado y montaje"
    )
    for x in (x0 - 0.4 * tt, x0 + 0.4 * tt):
        lifting_lug(lugs.mesh("Acero"), (x, y0, top - 0.01), UP, axis)
    lugs.measure(NumeroOrejetas=2, EspesorM=0.04, AlturaM=0.26)

    side_free = free_side(eq, nozzles)
    plate = part.add(
        "placa-caracteristicas",
        "Placa de características",
        "IfcDiscreteAccessory",
        "USERDEFINED",
        "Identificación",
    )
    nameplate(plate, (x0 - 0.05 * tt, y0 + side_free * r, zc - 0.35), (0, side_free))

    # Puente de nivel con indicador magnético en el lado libre.
    bridle = part.add(
        "puente-nivel", "Puente de nivel", "IfcFlowInstrument", "USERDEFINED", "Indicación de nivel"
    )
    level_bridle(bridle, (xb - 0.65, y0, zc), side_free, r, r * 1.5)

    # Plataforma superior con escala por el lado libre.
    z_top = zc + r + 0.32
    x_p0, x_p1 = x0 + 0.06 * tt, x0 + 0.36 * tt
    p = part.add(
        "plataforma",
        "Plataforma superior",
        "IfcSlab",
        "LANDING",
        "Acceso a la válvula de seguridad",
    )
    deck_y0 = y0 - 0.75
    deck_y1 = y0 + side_free * (r + 0.95) if side_free > 0 else y0 + 0.75
    if side_free < 0:
        deck_y0, deck_y1 = y0 - (r + 0.95), y0 + 0.75
    width_y = deck_y1 - deck_y0
    center_y = (deck_y0 + deck_y1) / 2
    grating_rect(p, (x0 + 0.21 * tt, center_y, z_top), (x_p1 - x_p0, width_y))
    for x in (x_p0 + 0.15, x_p1 - 0.15):
        for k in (-1, 1):
            beam(
                p.mesh("Refuerzo"),
                (x, y0 + k * r * 0.55, zc + r * 0.8),
                (x, y0 + k * r * 0.55, z_top - 0.18),
                0.1,
                0.1,
                (1, 0, 0),
            )
    p.measure(CotaM=z_top, LongitudM=x_p1 - x_p0, AnchoM=width_y)
    g = part.add(
        "barandilla", "Barandilla de plataforma", "IfcRailing", "GUARDRAIL", "Protección perimetral"
    )
    ladder_x = x_p1 - 0.45
    edge = deck_y1 if side_free > 0 else deck_y0
    points = [
        (ladder_x - 0.3, edge, z_top),
        (x_p0, edge, z_top),
        (x_p0, 2 * center_y - edge, z_top),
        (x_p1, 2 * center_y - edge, z_top),
        (x_p1, edge, z_top),
        (ladder_x + 0.3, edge, z_top),
    ]
    length_r, posts = railing(g.mesh("Seguridad"), g.mesh("Seguridad"), points)
    g.measure(LongitudM=length_r, AlturaM=1.1, NumeroPostes=posts)
    lad = part.add("escala", "Escala de gato", "IfcStairFlight", "STRAIGHT", "Acceso desde el piso")
    rungs = ladder(
        lad.mesh("Seguridad"),
        lad.mesh("Seguridad"),
        (ladder_x, edge + side_free * 0.2, deck),
        z_top,
        (0, side_free),
    )
    lad.measure(AlturaM=z_top - deck, NumeroPeldanos=rungs, AnchoM=0.46)


def grating_rect(comp, center, size):
    grating_deck(comp.mesh("Rejilla"), comp.mesh("Refuerzo"), center, size)


def relief_valve(comp, base, dn, shell_radius):
    """Válvula de seguridad bridada sobre su boquilla, con descarga lateral."""
    b = vec(base)
    joint = b + vec(UP) * 0.42
    nozzle(comp, b, joint, dn, shell_radius)
    steel = comp.mesh("Acero")
    junta = comp.mesh("Junta")
    gasket(junta, joint, UP, dn)
    flange_half(steel, joint, -vec(UP), dn)
    bolts = bolt_ring(steel, joint, UP, dn)
    body = joint + vec(UP) * 0.12
    lathe(
        steel,
        body,
        UP,
        (
            (0, 0.11),
            (0.08, 0.13),
            (0.22, 0.12),
            (0.24, 0.08),
            (0.62, 0.06),
            (0.66, 0.05),
            (0.74, 0.0),
        ),
        16,
    )
    out = body + vec(UP) * 0.12
    tube(steel, out, out + vec((0.42, 0, 0)), 0.1, 16, caps=(False, False))
    flange_joint(steel, junta, out + vec((0.42, 0, 0)), (1, 0, 0), 200)
    comp.measure(DN=dn, AlturaM=0.42 + 0.86, NumeroPernos=bolts)


def level_bridle(comp, at, side, shell_radius, span):
    """Columna de nivel DN 80 con dos tomas a la virola e indicador magnético."""
    x, y0, zc = at
    y_col = y0 + side * (shell_radius + 0.45)
    steel = comp.mesh("Acero")
    z_lo, z_hi = zc - span / 2 * 0.8, zc + span / 2 * 0.8
    for z in (z_lo, z_hi):
        dz = abs(z - zc)
        y_shell = y0 + side * sqrt(max(shell_radius**2 - dz * dz, 0.04))
        tube(steel, (x, y_shell, z), (x, y_col, z), 0.045, 12)
        flange_joint(steel, comp.mesh("Junta"), (x, (y_shell + y_col) / 2, z), (0, side, 0), 80)
    tube(steel, (x, y_col, z_lo - 0.35), (x, y_col, z_hi + 0.3), 0.05, 12)
    tube(
        comp.mesh("Aluminio"),
        (x + 0.16, y_col, z_lo - 0.1),
        (x + 0.16, y_col, z_hi + 0.1),
        0.035,
        12,
    )
    for z in (z_lo - 0.1, z_hi + 0.1):
        beam(steel, (x, y_col, z), (x + 0.16, y_col, z), 0.04, 0.04)
    box(comp.mesh("Motor"), (x - 0.18, y_col, zc + 0.2), (0.16, 0.14, 0.22))
    comp.measure(DN=80, AlturaM=z_hi - z_lo + 0.65)


def vertical_vessel(part, eq, base, deck, nozzles):
    x0, y0 = eq.xy
    width = eq.size[1]
    r = width / 2
    column = eq.family == "column"
    bottom, top, head_depth, hemi = vertical_levels(eq, base, deck)
    insulated = column or eq.tag.startswith("V-4")
    skin = "Aislante" if insulated else "Acero"
    clad = 0.07 if insulated else 0.0
    rc = r + clad
    center = (x0, y0)

    # Faldón con abertura de acceso y respiraderos.
    skirt = part.add("faldon", "Faldón", "IfcPlate", "SHEET", "Apoyo cilíndrico")
    tube(
        skirt.mesh("Acero"), (x0, y0, deck + 0.04), (x0, y0, bottom), r, SHELL, caps=(False, False)
    )
    opening = vec((-1.0, 0.0, 0.0))
    o = vec((x0, y0, deck + 0.04 + 0.62)) + opening * (r - 0.04)
    lathe(
        skirt.mesh("Refuerzo"),
        o,
        opening,
        ((0, 0.34), (0.16, 0.34), (0.16, 0.3), (0.0, 0.3)),
        FLANGE,
        caps=(False, False),
    )
    tube(skirt.mesh("Junta"), o - opening * 0.01, o + opening * 0.012, 0.3, FLANGE)
    for a in (pi / 4, 3 * pi / 4, 5 * pi / 4, 7 * pi / 4):
        w = vec((cos(a), sin(a), 0.0))
        p = vec((x0, y0, bottom - 0.3)) + w * (r - 0.01)
        tube(skirt.mesh("Junta"), p, p + w * 0.02, 0.05, 8)
    skirt.measure(DiametroM=width, AlturaM=bottom - deck, NumeroAberturas=1)

    ring = part.add(
        "anillo-base",
        "Anillo base y sillas de pernos",
        "IfcPlate",
        "SHEET",
        "Anclaje a la cimentación",
    )
    lathe(
        ring.mesh("Refuerzo"),
        (x0, y0, deck),
        UP,
        ((0, r - 0.12), (0, r + 0.2), (0.04, r + 0.2), (0.04, r - 0.12)),
        SHELL,
        caps=(False, False),
    )
    chairs = 8 if width < 3.2 else 12
    for i in range(chairs):
        a = (i + 0.5) * tau / chairs
        w = vec((cos(a), sin(a), 0.0))
        side = np.cross(UP, w)
        p = vec((x0, y0, deck + 0.04)) + w * (r + 0.1)
        for k in (-1, 1):
            q = p + side * k * 0.09
            oriented_box(
                ring.mesh("Refuerzo"), q + vec((0, 0, 0.17)), (w, side, vec(UP)), (0.1, 0.008, 0.17)
            )
        oriented_box(
            ring.mesh("Refuerzo"), p + vec((0, 0, 0.35)), (w, side, vec(UP)), (0.11, 0.12, 0.015)
        )
        anchor_bolts(ring.mesh("Acero"), [p + vec((0, 0, 0.365))], radius=0.026, height=0.08)
    ring.measure(DiametroM=width + 0.4, EspesorM=0.04, NumeroPernos=chairs)

    lower = part.add("fondo-inferior", "Fondo inferior", "IfcPlate", "SHEET", "Cierre inferior")
    vessel_head(lower.mesh("Acero"), (x0, y0, bottom), (0, 0, -1), r, r / 2 if not hemi else r)
    lower.measure(DiametroM=width, ProfundidadM=r / 2 if not hemi else r)

    shell = part.add("virola", "Virola", "IfcPlate", "SHEET", "Cuerpo cilíndrico")
    tube(shell.mesh(skin), (x0, y0, bottom), (x0, y0, top), rc, SHELL, caps=(False, False))
    shell.measure(DiametroM=width, AlturaM=top - bottom, CotaInferiorM=bottom, CotaSuperiorM=top)
    if insulated:
        shell.measure(EspesorAislamientoM=clad)
        bands = part.add(
            "anillos-aislamiento",
            "Bandas del aislamiento",
            "IfcCovering",
            "CLADDING",
            "Sujeción del aislamiento",
        )
        count = max(3, int((top - bottom) / 1.6))
        for i in range(count):
            z = bottom + (top - bottom) * (i + 0.5) / count
            lathe(
                bands.mesh("Galvanizado"),
                (x0, y0, z - 0.02),
                UP,
                ((0, rc), (0, rc + 0.01), (0.04, rc + 0.01), (0.04, rc)),
                32,
                caps=(False, False),
            )
        bands.measure(NumeroAros=count, AnchoM=0.04)

    upper = part.add("fondo-superior", "Fondo superior", "IfcPlate", "SHEET", "Cierre superior")
    vessel_head(upper.mesh(skin), (x0, y0, top), UP, rc, head_depth + clad)
    upper.measure(DiametroM=width, ProfundidadM=head_depth)

    for item in nozzles:
        n = part.add(
            f"boquilla-{item.line.tag.lower()}",
            f"Boquilla {item.line.tag}",
            "IfcPipeFitting",
            "CONNECTOR",
            f"Conexión {item.line.tag}",
        )
        jx, jy, jz = item.point
        dx = jx - x0
        side = item.direction[1]
        shell_y = y0 + side * sqrt(max(r * r - dx * dx, 0.01))
        reach = nozzle(n, (jx, shell_y, jz), item.point, item.line.dn, r, pad=not insulated)
        n.measure(DN=item.line.dn, ProyeccionM=reach, CotaEjeM=jz)

    # Plataformas por el lado oeste, escalas alternas y bocas de hombre.
    levels = platform_levels(eq, base, deck, bottom, top)
    start, end = pi - 1.15, pi + 1.15
    previous = deck
    for i, z in enumerate(levels, 1):
        suffix = "" if len(levels) == 1 else f"-{i}"
        name = "Plataforma superior" if i == len(levels) else f"Plataforma intermedia {i}"
        circular_platform(part, f"plataforma{suffix}", name, center, rc, z, start, end)
        angle = pi - 0.62 if i % 2 else pi + 0.62
        column_ladder(
            part, f"escala{suffix}", f"Escala de gato {i}", center, rc + 0.62, angle, previous, z
        )
        previous = z
    manways = 2 if column else 1
    for i in range(manways):
        z = bottom + 0.9 + (top - bottom - 1.8) * (i / max(1, manways - 1) if manways > 1 else 0.35)
        for level in levels:
            if abs(level - z) < 1.2:
                z = level + 1.0
        key = "boca-hombre" if manways == 1 else f"boca-hombre-{i + 1}"
        mw = part.add(
            key,
            "Boca de hombre" if manways == 1 else f"Boca de hombre {i + 1}",
            "IfcDiscreteAccessory",
            "USERDEFINED",
            "Acceso al interior",
        )
        a = pi + (0.0 if i % 2 == 0 else 0.0)
        w = vec((cos(a), sin(a), 0.0))
        manway(mw, vec((x0, y0, z)) + w * (rc - 0.05), w, standout_=0.36 + clad, shell_radius=r)
        mw.measure(CotaEjeM=z)

    psv = part.add(
        "valvula-seguridad",
        "Válvula de seguridad",
        "IfcValve",
        "PRESSURERELIEF",
        "Alivio de presión",
    )
    top_point = (x0 + r * 0.35, y0 - r * 0.25, top + head_depth * 0.82 + clad)
    relief_valve(psv, top_point, 150 if width < 3.2 else 200, None)

    lugs = part.add(
        "orejetas", "Orejetas de izado", "IfcDiscreteAccessory", "USERDEFINED", "Izado y montaje"
    )
    for k in (-1, 1):
        y = y0 + k * rc * 0.62
        z = top + head_depth * 0.55 + clad
        lifting_lug(
            lugs.mesh("Acero"), (x0 + rc * 0.3, y, z), (0, k * 0.6, 0.8), (1, 0, 0), height=0.3
        )
    lugs.measure(NumeroOrejetas=2, EspesorM=0.04, AlturaM=0.3)

    hoist = part.add(
        "pescante", "Pescante de cabeza", "IfcDiscreteAccessory", "USERDEFINED", "Izado en cabeza"
    )
    hz = levels[-1]
    hw = vec((cos(pi + 1.0), sin(pi + 1.0), 0.0))
    hb = vec((x0, y0, hz)) + hw * (rc + 0.25)
    davit(hoist.mesh("Seguridad"), hb, 2.4 + head_depth, 1.5, pi + 1.0)
    hoist.measure(AlturaM=2.4 + head_depth, AlcanceM=1.5)

    plate = part.add(
        "placa-caracteristicas",
        "Placa de características",
        "IfcDiscreteAccessory",
        "USERDEFINED",
        "Identificación",
    )
    side_free = free_side(eq, nozzles)
    nameplate(plate, (x0 + 0.4, y0 + side_free * (r - 0.01), bottom - 0.6), (0.3, side_free))

    if eq.family == "vertical" and not eq.tag.startswith("F-"):
        bridle = part.add(
            "puente-nivel",
            "Puente de nivel",
            "IfcFlowInstrument",
            "USERDEFINED",
            "Indicación de nivel",
        )
        vertical_bridle(bridle, center, rc, bottom, top, -side_free)


def vertical_bridle(comp, center, rc, bottom, top, side):
    x0, y0 = center
    a = pi / 2 * side + 0.45 * side
    w = vec((cos(a), sin(a), 0.0))
    steel = comp.mesh("Acero")
    col = vec((x0, y0, 0.0)) + w * (rc + 0.42)
    z_lo, z_hi = bottom + 0.6, bottom + (top - bottom) * 0.7
    for z in (z_lo, z_hi):
        start = vec((x0, y0, z)) + w * (rc - 0.02)
        tube(steel, start, (col[0], col[1], z), 0.045, 12)
        flange_joint(steel, comp.mesh("Junta"), (start + vec((col[0], col[1], z))) / 2, w, 80)
    tube(steel, (col[0], col[1], z_lo - 0.4), (col[0], col[1], z_hi + 0.35), 0.05, 12)
    side_axis = np.cross(UP, w)
    g = col + side_axis * 0.16
    tube(comp.mesh("Aluminio"), (g[0], g[1], z_lo - 0.1), (g[0], g[1], z_hi + 0.1), 0.035, 12)
    for z in (z_lo - 0.1, z_hi + 0.1):
        beam(steel, (col[0], col[1], z), (g[0], g[1], z), 0.04, 0.04)
    comp.measure(DN=80, AlturaM=z_hi - z_lo + 0.75)


def platform_levels(eq, base, deck, bottom, top):
    """Cotas de plataforma: la superior junto a la tangente y las intermedias a ≤ 6 m.
    El número se fija con la revisión base para que los subelementos no cambien."""
    b_bottom, b_top, _, _ = vertical_levels(base, base, deck)
    count = max(1, ceil((b_top - 0.4 - deck) / 6.0))
    upper = top - 0.4
    return [round(deck + (upper - deck) * (i + 1) / count, 3) for i in range(count)]


def tank_rise(eq: Equipment) -> float:
    return round(0.12 * eq.size[1], 3)


def tank(part, eq, base, deck, nozzles):
    x0, y0 = eq.xy
    width = eq.size[1]
    r = width / 2
    cryogenic = any(item.line.fluid == "GNL" or item.line.tag.startswith("BOG") for item in nozzles)
    floor = deck + 0.4
    rise = tank_rise(eq)
    shell_top = deck + eq.size[2] - rise
    skin = "Aislante" if cryogenic else "Acero"

    found = part.add(
        "cimentacion", "Cimentación anular", "IfcFooting", "STRIP_FOOTING", "Apoyo del tanque"
    )
    lathe(
        found.mesh("Hormigón"),
        (x0, y0, deck - 0.2),
        UP,
        ((0, r + 0.55), (0.6, r + 0.55), (0.6, r + 0.35)),
        TANK,
        caps=(True, True),
    )
    found.measure(DiametroM=width + 1.1, AlturaM=0.6)

    bottom = part.add("fondo", "Chapa de fondo", "IfcPlate", "SHEET", "Fondo plano")
    tube(bottom.mesh("Refuerzo"), (x0, y0, floor - 0.012), (x0, y0, floor + 0.012), r + 0.08, TANK)
    bottom.measure(DiametroM=width + 0.16, EspesorM=0.024)

    shell = part.add("virola", "Envolvente", "IfcPlate", "SHEET", "Cuerpo del tanque")
    lathe(
        shell.mesh(skin),
        (x0, y0, floor),
        UP,
        ((0, r), (shell_top - floor, r)),
        TANK,
        caps=(False, False),
    )
    courses = max(3, int((shell_top - floor) / 2.2))
    for i in range(1, courses):
        z = floor + (shell_top - floor) * i / courses
        tube(
            shell.mesh("Refuerzo"),
            (x0, y0, z - 0.008),
            (x0, y0, z + 0.008),
            r + 0.006,
            TANK,
            caps=(False, False),
        )
    shell.measure(DiametroM=width, AlturaM=shell_top - floor, NumeroVirolas=courses)

    roof = part.add("techo", "Techo de domo", "IfcPlate", "SHEET", "Cubierta autoportante")
    sphere = (r * r + rise * rise) / (2 * rise)
    alpha = np.arcsin(r / sphere)
    profile = []
    for k in range(7):
        a = alpha * (1 - k / 6)
        profile.append((sphere * (cos(a) - cos(alpha)), sphere * sin(a)))
    lathe(
        roof.mesh(skin),
        (x0, y0, shell_top),
        UP,
        [(0.0, r + 0.03), *profile],
        TANK,
        caps=(True, False),
    )
    roof.measure(DiametroM=width, FlechaM=rise, RadioDomoM=sphere)

    girder = part.add(
        "anillo-viento", "Anillo de viento", "IfcMember", "MEMBER", "Rigidez de la envolvente"
    )
    zg = shell_top - 0.9
    # Con 48 lados el borde interior queda siempre dentro de la virola de 64.
    lathe(
        girder.mesh("Refuerzo"),
        (x0, y0, zg),
        UP,
        (
            (0, r),
            (0, r + 0.45),
            (0.012, r + 0.45),
            (0.012, r + 0.41),
            (0.12, r + 0.41),
            (0.12, r + 0.39),
            (0.012, r + 0.39),
            (0.012, r),
        ),
        SHELL,
        caps=(False, False),
    )
    girder.measure(AnchoM=0.45, CotaM=zg)

    # Escalera helicoidal por el sector libre (oeste) hasta el borde del techo.
    stair = part.add(
        "escalera", "Escalera helicoidal", "IfcStairFlight", "SPIRAL", "Acceso al techo"
    )
    steps, turn = helical_stair(stair, (x0, y0), r, deck, shell_top, start=pi * 0.62)
    stair.measure(
        AlturaM=shell_top - deck,
        NumeroPeldanos=steps,
        AnchoM=0.8,
        GiroGrados=round(degrees(turn), 1),
    )
    end_angle = pi * 0.62 + turn

    # Pasarela radial y barandilla de techo junto al desembarco.
    walk = part.add(
        "plataforma-techo",
        "Pasarela de techo",
        "IfcSlab",
        "LANDING",
        "Acceso a las boquillas de techo",
    )

    def roof_z(rho):
        return shell_top + max(0.0, sqrt(max(sphere**2 - rho * rho, 0.0)) - sphere * cos(alpha))

    w = vec((cos(end_angle), sin(end_angle), 0.0))
    side = np.cross(UP, w)
    c = vec((x0, y0, 0.0))
    radii = (r - 0.2, r * 0.66, r * 0.33, 0.6)
    for ra, rb in zip(radii, radii[1:]):
        pa = c + w * ra + vec((0, 0, roof_z(ra) + 0.08))
        pb = c + w * rb + vec((0, 0, roof_z(rb) + 0.08))
        beam(walk.mesh("Rejilla"), pa, pb, 0.8, 0.04, UP)
        beam(
            walk.mesh("Refuerzo"),
            pa - vec((0, 0, 0.05)) + side * 0.42,
            pb - vec((0, 0, 0.05)) + side * 0.42,
            0.06,
            0.1,
            UP,
        )
        beam(
            walk.mesh("Refuerzo"),
            pa - vec((0, 0, 0.05)) - side * 0.42,
            pb - vec((0, 0, 0.05)) - side * 0.42,
            0.06,
            0.1,
            UP,
        )
    walk.measure(LongitudM=r - 0.8, AnchoM=0.8)
    guard = part.add(
        "barandilla-techo",
        "Barandilla de techo",
        "IfcRailing",
        "GUARDRAIL",
        "Protección en el techo",
    )
    total = 0.0
    posts = 0
    for k in (-1, 1):
        pts = [c + w * rr + side * k * 0.45 + vec((0, 0, roof_z(rr) + 0.1)) for rr in radii]
        length, count = railing(guard.mesh("Seguridad"), guard.mesh("Seguridad"), pts, toe=False)
        total += length
        posts += count
    arc_pts = [
        c
        + vec((cos(end_angle + k * 0.06), sin(end_angle + k * 0.06), 0)) * (r - 0.12)
        + vec((0, 0, shell_top + 0.06))
        for k in range(-8, 9)
    ]
    length, count = railing(guard.mesh("Seguridad"), guard.mesh("Seguridad"), arc_pts)
    guard.measure(LongitudM=total + length, AlturaM=1.1, NumeroPostes=posts + count)

    for item in nozzles:
        n = part.add(
            f"boquilla-{item.line.tag.lower()}",
            f"Boquilla {item.line.tag}",
            "IfcPipeFitting",
            "CONNECTOR",
            f"Conexión {item.line.tag}",
        )
        jx, jy, jz = item.point
        dx = jx - x0
        side_y = item.direction[1]
        shell_y = y0 + side_y * sqrt(max(r * r - dx * dx, 0.01))
        reach = nozzle(n, (jx, shell_y, jz), item.point, item.line.dn, r)
        n.measure(DN=item.line.dn, ProyeccionM=reach, CotaEjeM=jz)

    if cryogenic:
        mw = part.add(
            "boca-hombre",
            "Boca de hombre de techo",
            "IfcDiscreteAccessory",
            "USERDEFINED",
            "Acceso al interior",
        )
        rho = r * 0.45
        p = c + w * rho + side * 1.0
        manway(mw, (p[0], p[1], roof_z(rho)), UP, standout_=0.45)
        spray = part.add(
            "rociadores",
            "Anillo de rociadores",
            "IfcPipeSegment",
            "RIGIDSEGMENT",
            "Protección contra incendios",
        )
        ring_z = shell_top + 0.25
        torus(spray.mesh("Rojo"), (x0, y0, ring_z), UP, r + 0.25, 0.05, 48, 8)
        riser_a = pi * 1.5 + 0.9
        rp = c + vec((cos(riser_a), sin(riser_a), 0)) * (r + 0.25)
        tube(spray.mesh("Rojo"), (rp[0], rp[1], deck), (rp[0], rp[1], ring_z), 0.05, 8)
        spray.measure(DN=100, DiametroM=width + 0.5, CotaM=ring_z)
    else:
        for i, a in enumerate((pi * 1.1, pi * 1.42), 1):
            mw = part.add(
                f"boca-hombre-{i}",
                f"Boca de hombre {i}",
                "IfcDiscreteAccessory",
                "USERDEFINED",
                "Acceso al interior",
            )
            wv = vec((cos(a), sin(a), 0.0))
            manway(mw, vec((x0, y0, floor + 0.75)) + wv * (r - 0.05), wv, shell_radius=r)
            mw.measure(CotaEjeM=floor + 0.75)
        foam = part.add(
            "camaras-espuma",
            "Cámaras de espuma",
            "IfcDiscreteAccessory",
            "USERDEFINED",
            "Protección contra incendios",
        )
        for a in (-0.35, 0.35):
            wv = vec((cos(a), sin(a), 0.0))
            top_p = vec((x0, y0, shell_top - 0.45)) + wv * (r + 0.25)
            tube(foam.mesh("Rojo"), top_p - wv * 0.25, top_p + wv * 0.05, 0.12, 12)
            lathe(
                foam.mesh("Rojo"),
                top_p + wv * 0.05 - vec((0, 0, 0.2)),
                UP,
                ((0, 0.2), (0.45, 0.2), (0.55, 0.12)),
                16,
            )
            tube(
                foam.mesh("Rojo"),
                (top_p[0] + wv[0] * 0.05, top_p[1] + wv[1] * 0.05, deck + 0.5),
                top_p + wv * 0.05 - vec((0, 0, 0.2)),
                0.05,
                8,
            )
            flange_joint(
                foam.mesh("Rojo"),
                foam.mesh("Junta"),
                (top_p[0] + wv[0] * 0.05, top_p[1] + wv[1] * 0.05, deck + 0.9),
                UP,
                80,
            )
        foam.measure(NumeroCamaras=2, DN=80)
    vents = part.add(
        "venteos", "Venteos de techo", "IfcValve", "PRESSURERELIEF", "Respiración del tanque"
    )
    for i, a in enumerate((end_angle + 0.7, end_angle - 0.9)):
        wv = vec((cos(a), sin(a), 0.0))
        rho = r * (0.3 + 0.2 * i)
        p = c + wv * rho
        z = roof_z(rho)
        tube(
            vents.mesh("Acero"),
            (p[0], p[1], z - 0.1),
            (p[0], p[1], z + 0.35),
            0.1,
            16,
            caps=(False, True),
        )
        flange_joint(vents.mesh("Acero"), vents.mesh("Junta"), (p[0], p[1], z + 0.35), UP, 200)
        lathe(
            vents.mesh("Acero"),
            (p[0], p[1], z + 0.4),
            UP,
            ((0, 0.2), (0.3, 0.2), (0.32, 0.26), (0.42, 0.14), (0.46, 0.0)),
            16,
        )
    vents.measure(NumeroVenteos=2, DN=200)


def helical_stair(comp, center, r, z0, z1, *, start, width=0.8):
    """Escalera helicoidal pegada a la envolvente: peldaños, zancas y barandilla exterior."""
    x0, y0 = center
    r_in, r_out = r + 0.12, r + 0.12 + width
    r_mid = (r_in + r_out) / 2
    steps = max(4, round((z1 - z0) / 0.21))
    rise = (z1 - z0) / steps
    step_angle = 0.25 / r_mid
    turn = steps * step_angle
    treads = comp.mesh("Rejilla")
    frame = comp.mesh("Refuerzo")
    rail = comp.mesh("Seguridad")
    c = vec((x0, y0, 0.0))
    for i in range(1, steps + 1):
        a = start + step_angle * (i - 0.5)
        w = vec((cos(a), sin(a), 0.0))
        t = np.cross(UP, w)
        p = c + w * r_mid + vec((0, 0, z0 + rise * i - 0.02))
        oriented_box(treads, p, (t, -w, vec(UP)), (0.13, width / 2, 0.017), faces=SLAT_FACES)
    segs = max(6, ceil(turn / 0.12))

    def helix(radius, k, dz=0.0):
        a = start + turn * k / segs
        return c + vec((cos(a), sin(a), 0.0)) * radius + vec((0, 0, z0 + (z1 - z0) * k / segs + dz))

    for k in range(segs):
        for radius in (r_in - 0.02, r_out + 0.02):
            beam(frame, helix(radius, k, -0.12), helix(radius, k + 1, -0.12), 0.012, 0.2, UP)
        for h in (1.0, 0.52):
            tube(
                rail,
                helix(r_out + 0.06, k, h),
                helix(r_out + 0.06, k + 1, h),
                0.021,
                6,
                caps=(False, False),
            )
    for k in range(0, segs + 1, 2):
        p = helix(r_out + 0.06, k)
        tube(rail, p, p + vec((0, 0, 1.0)), 0.032, 4, phase=pi / 4, caps=(False, True))
    # Ménsulas a la envolvente.
    for k in range(0, segs + 1, 3):
        beam(frame, helix(r, k, -0.2), helix(r_out, k, -0.2), 0.08, 0.08, UP)
    return steps, turn


WAFER = 0.12  # canto de la retención tipo wafer en la impulsión de las bombas


def valve_length(dn: float) -> float:
    """Distancia entre caras de una compuerta bridada (la de process_mesh.gate_valve)."""
    return max(0.32, 1.25 * dn / 1000 + 0.2)


def ball_length(dn: float) -> float:
    """Distancia entre caras de una válvula de bola (la de process_mesh.actuated_ball_valve)."""
    return max(0.36, 1.3 * dn / 1000 + 0.22)


def pump_geometry(eq: Equipment, deck: float):
    x0, y0 = eq.xy
    length, width, height = eq.size
    axis_z = deck + 0.3 + 0.18 + 0.2 * height
    return {
        "rows": (y0 - 0.25 * width, y0 + 0.25 * width),
        "axis_z": round(axis_z, 3),
        "casing_x": round(x0 - 0.26 * length, 3),
        "suction_x": round(x0 - 0.47 * length, 3),
        "header_z": round(deck + max(2.15, 0.88 * height), 3),
        "volute": 0.17 * height,
        "motor_r": 0.15 * height,
    }


def pump_skid(part, eq, base, deck, nozzles):
    x0, y0 = eq.xy
    length, width, height = eq.size
    g = pump_geometry(eq, deck)
    zc = g["axis_z"]
    inlet = next((n for n in nozzles if n.incoming), None)
    outlet = next((n for n in nozzles if not n.incoming), None)
    dn_in = inlet.line.dn if inlet else 300
    dn_out = outlet.line.dn if outlet else max(200, dn_in - 100)
    branch_in = max(150, int(round(dn_in * 0.8 / 50)) * 50)
    branch_out = max(150, int(round(dn_out * 0.7 / 50)) * 50)
    rows = g["rows"]
    xc = g["casing_x"]
    rv = g["volute"]
    rm = g["motor_r"]
    for label, y in zip(("a", "b"), rows):
        name = label.upper()
        # Bancada: macizo de hormigón, lechada y bancada de acero con pernos.
        bed = part.add(
            f"bancada-{label}",
            f"Bancada con lechada {name}",
            "IfcSlab",
            "BASESLAB",
            "Apoyo del grupo",
        )
        x_lo, x_hi = x0 - 0.37 * length, x0 + 0.42 * length
        bed_w = min(width * 0.42, 1.35)
        box(
            bed.mesh("Hormigón"),
            ((x_lo + x_hi) / 2, y, deck + 0.13),
            (x_hi - x_lo + 0.3, bed_w + 0.3, 0.26),
        )
        box(
            bed.mesh("Lechada"),
            ((x_lo + x_hi) / 2, y, deck + 0.29),
            (x_hi - x_lo + 0.1, bed_w + 0.1, 0.06),
        )
        ibeam(
            bed.mesh("Refuerzo"),
            (x_lo, y - bed_w / 2 + 0.1, deck + 0.42),
            (x_hi, y - bed_w / 2 + 0.1, deck + 0.42),
            0.2,
            0.18,
        )
        ibeam(
            bed.mesh("Refuerzo"),
            (x_lo, y + bed_w / 2 - 0.1, deck + 0.42),
            (x_hi, y + bed_w / 2 - 0.1, deck + 0.42),
            0.2,
            0.18,
        )
        box(bed.mesh("Refuerzo"), ((x_lo + x_hi) / 2, y, deck + 0.515), (x_hi - x_lo, bed_w, 0.012))
        bolts = anchor_bolts(
            bed.mesh("Acero"),
            [
                (x, y + k * (bed_w / 2 + 0.06), deck + 0.32)
                for x in (x_lo + 0.2, (x_lo + x_hi) / 2, x_hi - 0.2)
                for k in (-1, 1)
            ],
        )
        bed.measure(LongitudM=x_hi - x_lo, AnchoM=bed_w, AlturaM=0.53, NumeroPernos=bolts)

        pump = part.add(
            f"bomba-{label}", f"Bomba centrífuga {name}", "IfcPump", "USERDEFINED", "Impulsión"
        )
        casing = pump.mesh("Acero")
        volute = []
        for i in range(32):
            a = tau * i / 32
            rr = rv * (0.78 + 0.22 * i / 31)
            volute.append((rr * cos(a), rr * sin(a)))
        cw = 0.32 * rv + 0.12
        extrude(casing, (xc - cw / 2, y, zc), (1, 0, 0), volute, cw)
        lathe(
            casing,
            (xc + cw / 2, y, zc),
            (1, 0, 0),
            (
                (0, rv * 0.7),
                (0.06, rv * 0.72),
                (0.06, rv * 0.45),
                (0.5 * length * 0.2, rv * 0.42),
                (0.5 * length * 0.2 + 0.05, rv * 0.5),
                (0.5 * length * 0.2 + 0.18, rv * 0.5),
                (0.5 * length * 0.2 + 0.2, rv * 0.3),
            ),
            FLANGE,
        )
        box(
            casing,
            (xc + 0.1 * length, y, (deck + 0.52 + zc - rv * 0.4) / 2),
            (0.28, rv * 1.2, zc - rv * 0.4 - deck - 0.52),
        )
        box(
            casing,
            (xc, y, (deck + 0.52 + zc - rv) / 2 + 0.02),
            (cw * 0.8, rv * 1.4, max(0.05, zc - rv - deck - 0.5)),
        )
        # Boquillas: aspiración axial (oeste) e impulsión vertical.
        suction_face = vec((xc - cw / 2 - 0.32, y, zc))
        tube(
            casing,
            (xc - cw / 2 + 0.02, y, zc),
            suction_face + vec((0.0, 0, 0)),
            0.5 * branch_in / 1000,
            FLANGE,
            caps=(False, False),
        )
        flange_half(casing, suction_face, (-1, 0, 0), branch_in)
        dis_y = y + rv * 0.62
        discharge_face = vec((xc, dis_y, zc + rv + 0.3))
        tube(
            casing,
            (xc, dis_y, zc + rv * 0.5),
            discharge_face,
            0.5 * branch_out / 1000,
            FLANGE,
            caps=(False, False),
        )
        flange_half(casing, discharge_face, UP, branch_out)
        pump.measure(DiametroM=2 * rv, AnchoM=cw, CotaEjeM=zc, DN=branch_in)

        drive = part.add(
            f"motor-{label}",
            f"Motor eléctrico {name}",
            "IfcElectricMotor",
            "INDUCTION",
            "Accionamiento",
        )
        m0 = x0 + 0.06 * length
        m1 = x0 + 0.4 * length
        motor(
            drive.mesh("Motor"),
            drive.mesh("Motor"),
            drive.mesh("Refuerzo"),
            (m0, y, zc),
            (m1, y, zc),
            rm,
            feet_z=deck + 0.52,
        )
        drive.measure(DiametroM=2 * rm, LongitudM=m1 - m0, CotaEjeM=zc, NumeroAletas=24)

        guard = part.add(
            f"acoplamiento-{label}",
            f"Cubre-acoplamiento {name}",
            "IfcDiscreteAccessory",
            "USERDEFINED",
            "Protección del acoplamiento",
        )
        g0, g1 = x0 - 0.06 * length, m0 + 0.02
        revolve(
            guard.mesh("Seguridad"),
            ((g0 + g1) / 2 - (g1 - g0) / 2, y, zc),
            (1, 0, 0),
            ((0.0, 0.0), (rm * 0.7, 0.0), (rm * 0.7, g1 - g0), (0.0, g1 - g0)),
            -pi / 2 - 0.05,
            pi / 2 + 0.05,
            10,
        )
        box(guard.mesh("Seguridad"), ((g0 + g1) / 2, y, zc - 0.02), (g1 - g0, rm * 1.42, 0.03))
        tube(guard.mesh("Acero"), (g0 - 0.15, y, zc), (g1 + 0.02, y, zc), rm * 0.22, 12)
        guard.measure(LongitudM=g1 - g0, AnchoM=rm * 1.4)

        # Válvula de aspiración atornillada a la brida de la bomba y, encima de la impulsión,
        # retención wafer entre la brida de la bomba y la compuerta.
        v_in = part.add(
            f"valvula-aspiracion-{label}",
            f"Válvula de aspiración {name}",
            "IfcValve",
            "ISOLATING",
            "Aislamiento de la bomba",
        )
        length_valve = valve_length(branch_in)
        center_valve = suction_face - vec((length_valve / 2, 0, 0))
        bolts_in, _ = gate_valve(
            v_in.mesh("Acero"),
            v_in.mesh("Seguridad"),
            v_in.mesh("Junta"),
            center_valve,
            (1, 0, 0),
            branch_in,
            ends=("mate", "mate"),
        )
        v_in.measure(DN=branch_in, LongitudM=length_valve, NumeroPernos=bolts_in)
        v_out = part.add(
            f"valvula-impulsion-{label}",
            f"Válvulas de impulsión {name}",
            "IfcValve",
            "ISOLATING",
            "Retención y aislamiento",
        )
        f_out = flange_size(branch_out)
        tube(
            v_out.mesh("Acero"),
            discharge_face,
            discharge_face + vec((0, 0, WAFER)),
            f_out["circle"] - f_out["nut"] * 1.1,
            FLANGE,
        )
        bolt_ring(
            v_out.mesh("Acero"),
            discharge_face + vec((0, 0, WAFER / 2)),
            UP,
            branch_out,
            extra=WAFER,
        )
        length_out = valve_length(branch_out)
        gate_center = discharge_face + vec((0, 0, WAFER + length_out / 2))
        bolts_out, _ = gate_valve(
            v_out.mesh("Acero"),
            v_out.mesh("Seguridad"),
            v_out.mesh("Junta"),
            gate_center,
            UP,
            branch_out,
            stem=(-1, 0, 0),
            ends=("bare", "mate"),
        )
        v_out.measure(
            DN=branch_out, LongitudM=length_out + WAFER, NumeroPernos=bolts_out + f_out["bolts"]
        )

        gauge = part.add(
            f"manometro-{label}",
            f"Manómetro {name}",
            "IfcFlowInstrument",
            "PRESSUREGAUGE",
            "Presión de impulsión",
        )
        gauge_dial(
            gauge, gate_center + vec((0, 0, length_out / 2 + 0.05)), (0, 1 if y > y0 else -1, 0)
        )
        gauge.measure(DiametroM=0.16)

    # Colector de aspiración (norte-sur) y colector de impulsión elevado.
    sx = g["suction_x"]
    suction = part.add(
        "colector-aspiracion",
        "Colector de aspiración",
        "IfcPipeSegment",
        "RIGIDSEGMENT",
        "Alimentación a las bombas",
    )
    pipe = suction.mesh("Acero")
    r_in = dn_in / 2000
    y_lo, y_hi = y0 - width / 2, y0 + width / 2
    in_side = inlet.direction[1] if inlet else -1
    end_y = y_lo if in_side < 0 else y_hi
    far_y = rows[1] + 0.35 if in_side < 0 else rows[0] - 0.35
    tube(pipe, (sx, far_y, zc), (sx, end_y, zc), r_in, PIPE, caps=(True, False))
    lathe(
        pipe,
        (sx, far_y, zc),
        (0, -in_side, 0),
        head_profile(r_in, r_in * 0.5, 4),
        PIPE,
        caps=(False, False),
    )
    cw = 0.32 * rv + 0.12
    for y in rows:
        valve_joint = vec((xc - cw / 2 - 0.32 - valve_length(branch_in), y, zc))
        tube(pipe, (sx, y, zc), valve_joint, branch_in / 2000, PIPE, caps=(False, False))
        flange_half(pipe, valve_joint, (1, 0, 0), branch_in)
    if inlet:
        flange_half(pipe, inlet.point, inlet.direction, dn_in)
    suction.measure(DN=dn_in, LongitudM=abs(end_y - far_y), CotaEjeM=zc)
    supports = [(sx, y, zc) for y in rows]
    for p in supports:
        box(
            suction.mesh("Refuerzo"),
            (p[0], p[1], (deck + zc - r_in) / 2),
            (0.16, 0.16, zc - r_in - deck),
        )

    discharge = part.add(
        "colector-impulsion",
        "Colector de impulsión",
        "IfcPipeSegment",
        "RIGIDSEGMENT",
        "Salida de las bombas",
    )
    pipe = discharge.mesh("Acero")
    hz = g["header_z"]
    r_out = dn_out / 2000
    out_side = outlet.direction[1] if outlet else 1
    end_y = y_lo if out_side < 0 else y_hi
    far_y = rows[1] + 0.35 if out_side < 0 else rows[0] - 0.35
    tube(pipe, (xc, far_y, hz), (xc, end_y, hz), r_out, PIPE, caps=(True, False))
    lathe(
        pipe,
        (xc, far_y, hz),
        (0, -out_side, 0),
        head_profile(r_out, r_out * 0.5, 4),
        PIPE,
        caps=(False, False),
    )
    for y in rows:
        dis_y = y + rv * 0.62
        valve_top = zc + rv + 0.3 + WAFER + valve_length(branch_out)
        samples = fillet(
            (
                (xc, dis_y, valve_top),
                (xc, dis_y, hz),
                (xc, y0 if abs(dis_y - y0) > 0.3 else dis_y, hz),
            ),
            branch_out * 0.0015,
            quarter=5,
        )
        sweep(pipe, samples, branch_out / 2000, PIPE, caps=(False, False))
        flange_half(pipe, (xc, dis_y, valve_top), (0, 0, -1), branch_out)
    if outlet:
        flange_half(pipe, outlet.point, outlet.direction, dn_out)
        flange_joint(
            pipe,
            discharge.mesh("Junta"),
            outlet.point,
            outlet.direction,
            dn_out,
            near=False,
            far=False,
        )
    else:
        end = vec((xc, end_y, hz))
        flange_half(pipe, end, (0, out_side, 0), dn_out)
        blind_flange(pipe, discharge.mesh("Junta"), end, (0, out_side, 0), dn_out)
    for y in (rows[0] - 0.6, rows[1] + 0.6):
        if y_lo < y < y_hi:
            ibeam(
                discharge.mesh("Refuerzo"),
                (xc, y, deck),
                (xc, y, hz - r_out - 0.06),
                0.16,
                0.16,
                (1, 0, 0),
            )
            box(discharge.mesh("Refuerzo"), (xc, y, hz - r_out - 0.04), (0.3, 0.2, 0.03))
    discharge.measure(DN=dn_out, LongitudM=abs(end_y - far_y), CotaEjeM=hz)


def gauge_dial(comp, base, facing):
    b = vec(base)
    f = unit(facing)
    tube(comp.mesh("Acero"), b, b + vec((0, 0, 0.25)), 0.012, 6)
    dial = b + vec((0, 0, 0.32))
    tube(comp.mesh("Acero"), dial - f * 0.03, dial + f * 0.03, 0.08, 16)
    tube(comp.mesh("Blanco"), dial + f * 0.03, dial + f * 0.034, 0.07, 16)


def compressor_geometry(eq: Equipment, deck: float):
    x0, y0 = eq.xy
    length, width, height = eq.size
    rc = 0.19 * height
    axis_z = deck + 0.4 + 0.36 * height
    c0, c1 = x0 - 0.46 * length, x0 - 0.13 * length
    return {
        "axis_z": round(axis_z, 3),
        "casing": (c0, c1),
        "radius": rc,
        "suction_x": round(c0 + 0.27 * (c1 - c0), 3),
        "discharge_x": round(c1 - 0.22 * (c1 - c0), 3),
        "port_z": round(axis_z + rc + 0.95, 3),
    }


def compressor(part, eq, base, deck, nozzles):
    x0, y0 = eq.xy
    length, width, height = eq.size
    g = compressor_geometry(eq, deck)
    zc, rc = g["axis_z"], g["radius"]
    c0, c1 = g["casing"]
    reciprocating = "evaporación" in eq.name
    skid_z = deck + 0.4
    frame = part.add("bastidor", "Bastidor", "IfcMember", "MEMBER", "Bancada del paquete")
    steel = frame.mesh("Refuerzo")
    half_w = width / 2 - 0.25
    for k in (-1, 1):
        ibeam(
            steel,
            (x0 - length / 2 + 0.1, y0 + k * half_w, deck + 0.2),
            (x0 + length / 2 - 0.1, y0 + k * half_w, deck + 0.2),
            0.4,
            0.22,
        )
    for t in np.linspace(-0.5, 0.5, 6):
        x = x0 + t * (length - 0.4)
        ibeam(steel, (x, y0 - half_w, deck + 0.2), (x, y0 + half_w, deck + 0.2), 0.36, 0.18)
    box(frame.mesh("Cubierta"), (x0, y0, skid_z - 0.006), (length - 0.2, 2 * half_w + 0.2, 0.012))
    bolts = anchor_bolts(
        frame.mesh("Acero"),
        [
            (x0 + t * (length - 0.4), y0 + k * (half_w + 0.17), deck)
            for t in (-0.5, 0, 0.5)
            for k in (-1, 1)
        ],
    )
    frame.measure(LongitudM=length - 0.2, AnchoM=2 * half_w + 0.22, AlturaM=0.4, NumeroPernos=bolts)

    body = part.add(
        "carcasa",
        "Carcasa del compresor" if not reciprocating else "Cárter y cilindros",
        "IfcCompressor",
        "USERDEFINED",
        "Compresión del gas",
    )
    casing = body.mesh("Acero")
    clen = c1 - c0
    if not reciprocating:
        lathe(
            casing,
            (c0, y0, zc),
            (1, 0, 0),
            (
                (0, rc * 0.55),
                (0.04, rc * 0.82),
                (0.12, rc * 0.86),
                (0.12, rc * 1.04),
                (0.2, rc * 1.04),
                (0.2, rc),
                (clen - 0.2, rc),
                (clen - 0.2, rc * 1.04),
                (clen - 0.12, rc * 1.04),
                (clen - 0.12, rc * 0.86),
                (clen - 0.04, rc * 0.8),
                (clen, rc * 0.5),
            ),
            SMALL,
        )
        for k in (-1, 1):
            box(casing, ((c0 + c1) / 2, y0 + k * (rc + 0.04), zc), (clen - 0.3, 0.09, 0.07))
        for x in (c0 + 0.3, c1 - 0.3):
            for k in (-1, 1):
                box(
                    body.mesh("Refuerzo"),
                    (x, y0 + k * rc * 0.75, (skid_z + zc) / 2 - 0.1),
                    (0.25, 0.3, zc - skid_z - 0.2),
                )
        body.measure(DiametroM=2 * rc, LongitudM=clen, CotaEjeM=zc)
    else:
        box(
            casing,
            ((c0 + c1) / 2, y0, (skid_z + zc + rc * 0.6) / 2),
            (clen, 1.1, zc + rc * 0.6 - skid_z),
        )
        lathe(
            casing,
            ((c0 + c1) / 2 - clen / 2, y0, zc + rc * 0.6),
            (1, 0, 0),
            ((0, 0.0), (0.0, 0.0)),
            4,
        )
        for k in (-1, 1):
            y_a = y0 + k * 0.55
            y_b = y0 + k * (width / 2 - 0.35)
            for x in (c0 + clen * 0.3, c1 - clen * 0.3):
                lathe(
                    casing,
                    (x, y_a, zc),
                    (0, k, 0),
                    (
                        (0, 0.24),
                        (0.55, 0.24),
                        (0.55, 0.36),
                        (0.6, 0.38),
                        (abs(y_b - y_a), 0.38),
                        (abs(y_b - y_a), 0.3),
                    ),
                    FLANGE,
                )
        body.measure(LongitudM=clen, AnchoM=width - 0.7, CotaEjeM=zc, NumeroCilindros=4)

    # Tuberías de aspiración y de impulsión hasta los puertos de la cara del paquete.
    for key, label, x, item in (
        (
            "tuberia-aspiracion",
            "Tubería de aspiración",
            g["suction_x"],
            next((n for n in nozzles if n.incoming), None),
        ),
        (
            "tuberia-impulsion",
            "Tubería de impulsión",
            g["discharge_x"],
            next((n for n in nozzles if not n.incoming), None),
        ),
    ):
        spool = part.add(key, label, "IfcPipeSegment", "RIGIDSEGMENT", "Conexión con la línea")
        pipe = spool.mesh("Acero")
        dn = item.line.dn if item else 300
        r = dn / 2000
        top_casing = zc + (rc if not reciprocating else rc * 0.6)
        joint = vec((x, y0, top_casing + 0.28))
        tube(pipe, (x, y0, zc), joint - vec((0, 0, 0.12)), r, FLANGE, caps=(False, False))
        flange_joint(pipe, spool.mesh("Junta"), joint, UP, dn)
        port = vec(item.point) if item else vec((x, y0 + width / 2, g["port_z"]))
        samples = fillet(
            (joint, (x, y0, port[2]), port), 1.5 * dn / 1000, quarter=6, end_clear=(0.25, 0.25)
        )
        sweep(pipe, samples, r, PIPE, caps=(False, False))
        if item:
            flange_half(pipe, port, item.direction, dn)
        else:
            blind_flange(pipe, spool.mesh("Junta"), port, (0, 1, 0), dn)
        post_y = (y0 + port[1]) / 2
        ibeam(
            spool.mesh("Refuerzo"),
            (x, post_y, skid_z),
            (x, post_y, port[2] - r - 0.05),
            0.16,
            0.16,
            (1, 0, 0),
        )
        spool.measure(DN=dn, LongitudM=path_length(samples) + 0.4, CotaM=port[2])

    gear = part.add(
        "caja-engranajes",
        "Caja de engranajes",
        "IfcBuildingElementProxy",
        "ELEMENT",
        "Multiplicadora",
    )
    gx0, gx1 = x0 - 0.06 * length, x0 + 0.1 * length
    box(
        gear.mesh("Motor"),
        ((gx0 + gx1) / 2, y0, (skid_z + zc + 0.3) / 2),
        (gx1 - gx0, 1.15, zc + 0.3 - skid_z),
    )
    lathe(gear.mesh("Motor"), (gx0, y0, zc + 0.3), (1, 0, 0), ((0, 0.575), (gx1 - gx0, 0.575)), 24)
    for x in (gx0 - 0.15, gx1 + 0.15):
        tube(gear.mesh("Acero"), (x - 0.15, y0, zc), (x + 0.15, y0, zc), 0.09, 12)
    gear.measure(LongitudM=gx1 - gx0, AnchoM=1.15, AlturaM=zc + 0.875 - skid_z)

    drive = part.add("motor", "Motor eléctrico", "IfcElectricMotor", "INDUCTION", "Accionamiento")
    mr = 0.17 * height
    m0, m1 = x0 + 0.16 * length, x0 + 0.47 * length
    motor(
        drive.mesh("Motor"),
        drive.mesh("Motor"),
        drive.mesh("Refuerzo"),
        (m0, y0, zc),
        (m1, y0, zc),
        mr,
        feet_z=skid_z,
    )
    box(
        drive.mesh("Motor"),
        ((m0 + m1) / 2 + 0.1, y0, zc + mr + 0.32),
        ((m1 - m0) * 0.55, mr * 1.4, 0.5),
    )
    drive.measure(DiametroM=2 * mr, LongitudM=m1 - m0, CotaEjeM=zc, NumeroAletas=24)

    for key, label, a, b in (
        ("acoplamiento-1", "Cubre-acoplamiento lado compresor", c1, gx0),
        ("acoplamiento-2", "Cubre-acoplamiento lado motor", gx1, m0),
    ):
        guard = part.add(
            key, label, "IfcDiscreteAccessory", "USERDEFINED", "Protección del acoplamiento"
        )
        revolve(
            guard.mesh("Seguridad"),
            (a, y0, zc),
            (1, 0, 0),
            ((0.0, 0.0), (0.32, 0.0), (0.32, b - a), (0.0, b - a)),
            -pi / 2 - 0.05,
            pi / 2 + 0.05,
            10,
        )
        box(guard.mesh("Seguridad"), ((a + b) / 2, y0, zc - 0.02), (b - a, 0.66, 0.03))
        guard.measure(LongitudM=b - a, AnchoM=0.64)

    side = free_side(eq, nozzles)
    oil = part.add(
        "consola-aceite",
        "Consola de aceite",
        "IfcBuildingElementProxy",
        "ELEMENT",
        "Lubricación y sellado",
    )
    ox0, ox1 = x0 + 0.12 * length, x0 + 0.44 * length
    oy = y0 + side * (half_w - 0.55)
    box(oil.mesh("Acero"), ((ox0 + ox1) / 2, oy, skid_z + 0.4), (ox1 - ox0, 0.85, 0.8))
    for i, x in enumerate((ox0 + 0.35, ox0 + 0.8)):
        tube(oil.mesh("Motor"), (x, oy, skid_z + 0.8), (x, oy, skid_z + 1.25), 0.13, 16)
        box(oil.mesh("Refuerzo"), (x, oy, skid_z + 0.82), (0.32, 0.32, 0.04))
    for x in (ox1 - 0.55, ox1 - 0.25):
        tube(oil.mesh("Acero"), (x, oy, skid_z + 0.8), (x, oy, skid_z + 1.45), 0.11, 16)
        lathe(oil.mesh("Acero"), (x, oy, skid_z + 1.45), UP, head_profile(0.11, 0.055, 3), 16)
    tube(
        oil.mesh("Acero"),
        (ox0 + 0.2, oy - side * 0.3, skid_z + 1.05),
        (ox1 - 0.2, oy - side * 0.3, skid_z + 1.05),
        0.12,
        16,
    )
    oil.measure(LongitudM=ox1 - ox0, AnchoM=0.85, AlturaM=1.5)

    panel = part.add(
        "panel-control",
        "Panel de control local",
        "IfcBuildingElementProxy",
        "ELEMENT",
        "Mando local",
    )
    px = x0 - 0.42 * length
    py = y0 + side * (half_w - 0.3)
    for k in (-1, 1):
        box(panel.mesh("Refuerzo"), (px + k * 0.3, py, skid_z + 0.6), (0.06, 0.06, 1.2))
    box(panel.mesh("Acero"), (px, py, skid_z + 1.3), (0.8, 0.3, 0.9))
    box(panel.mesh("Vidrio"), (px, py - side * 0.152, skid_z + 1.35), (0.5, 0.004, 0.4))
    panel.measure(AnchoM=0.8, AlturaM=2.2, FondoM=0.3)


def cooler_geometry(eq: Equipment, deck: float):
    x0, y0 = eq.xy
    length, width, height = eq.size
    bundle0 = deck + 0.74 * height
    bundle1 = deck + 0.87 * height
    return {
        "legs_top": deck + 0.5 * height,
        "plenum": (deck + 0.5 * height, deck + 0.72 * height),
        "bundle": (bundle0, bundle1),
        "inlet_x": round(x0 - length / 2 + 0.25, 3),
        "outlet_x": round(x0 + length / 2 - 0.25, 3),
        "inlet_z": round(bundle1 + 0.55, 3),
        "outlet_z": round(bundle0 - 0.55, 3),
    }


def air_cooler(part, eq, base, deck, nozzles):
    x0, y0 = eq.xy
    length, width, height = eq.size
    g = cooler_geometry(eq, deck)
    z_top = g["legs_top"]
    p0, p1 = g["plenum"]
    b0, b1 = g["bundle"]
    structure = part.add(
        "estructura", "Estructura soporte", "IfcMember", "MEMBER", "Pórticos y arriostramiento"
    )
    steel = structure.mesh("Refuerzo")
    xs = (x0 - length / 2 + 0.3, x0, x0 + length / 2 - 0.3)
    ys = (y0 - width / 2 + 0.2, y0 + width / 2 - 0.2)
    for x in xs:
        for y in ys:
            ibeam(steel, (x, y, deck), (x, y, b0 - 0.02), 0.25, 0.25, (1, 0, 0))
            box(steel, (x, y, deck + 0.015), (0.45, 0.45, 0.03))
    anchor_bolts(
        structure.mesh("Acero"),
        [
            (x + i * 0.15, y + j * 0.15, deck + 0.03)
            for x in xs
            for y in ys
            for i in (-1, 1)
            for j in (-1, 1)
        ][::2],
        radius=0.02,
    )
    for y in ys:
        ibeam(steel, (xs[0], y, z_top), (xs[-1], y, z_top), 0.3, 0.18)
    for x in xs:
        ibeam(steel, (x, ys[0], z_top), (x, ys[1], z_top), 0.3, 0.18)
    for x in (xs[0], xs[-1]):
        angle_bar(steel, (x, ys[0], deck + 0.3), (x, ys[1], z_top - 0.2), 0.08, (1, 0, 0))
        angle_bar(steel, (x, ys[1], deck + 0.3), (x, ys[0], z_top - 0.2), 0.08, (1, 0, 0))
    for y in ys:
        angle_bar(steel, (xs[0], y, deck + 0.3), (xs[1], y, z_top - 0.2), 0.08, (0, 1, 0))
        angle_bar(steel, (xs[1], y, deck + 0.3), (xs[0], y, z_top - 0.2), 0.08, (0, 1, 0))
    structure.measure(
        LongitudM=xs[-1] - xs[0], AnchoM=ys[1] - ys[0], AlturaM=b0 - deck, NumeroPilares=6
    )

    bays = (y0 - width / 4, y0 + width / 4)
    bay_w = width / 2 - 0.15
    fans = 0
    for i, y in enumerate(bays, 1):
        plenum = part.add(
            f"plenum-{i}",
            f"Cámara de aire {i}",
            "IfcBuildingElementProxy",
            "ELEMENT",
            "Conducción del aire",
        )
        box(plenum.mesh("Acero"), (x0, y, (p0 + p1) / 2), (length - 0.9, bay_w, p1 - p0))
        plenum.measure(LongitudM=length - 0.9, AnchoM=bay_w, AlturaM=p1 - p0)

        bundle = part.add(
            f"haz-{i}",
            f"Haz de tubos aleteados {i}",
            "IfcBuildingElementProxy",
            "ELEMENT",
            "Intercambio de calor",
        )
        x_lo, x_hi = x0 - length / 2 + 0.55, x0 + length / 2 - 0.55
        box(
            bundle.mesh("Aluminio"),
            (x0, y, (b0 + b1) / 2),
            (x_hi - x_lo, bay_w - 0.12, b1 - b0 - 0.04),
        )
        for k in (-1, 1):
            box(
                bundle.mesh("Refuerzo"),
                (x0, y + k * (bay_w / 2 - 0.03), (b0 + b1) / 2),
                (x_hi - x_lo, 0.06, b1 - b0 + 0.04),
            )
        for k in range(1, 6):
            xk = x_lo + (x_hi - x_lo) * k / 6
            box(bundle.mesh("Refuerzo"), (xk, y, b1 - 0.005), (0.05, bay_w - 0.1, 0.03))
        plugs = 0
        for x_h, sign in ((x_lo - 0.18, -1), (x_hi + 0.18, 1)):
            box(bundle.mesh("Acero"), (x_h, y, (b0 + b1) / 2), (0.34, bay_w, b1 - b0 + 0.12))
            for row in (0.33, 0.67):
                for j in range(8):
                    yy = y - bay_w / 2 + bay_w * (j + 0.5) / 8
                    zz = b0 + (b1 - b0) * row
                    box(bundle.mesh("Refuerzo"), (x_h + sign * 0.19, yy, zz), (0.04, 0.045, 0.045))
                    plugs += 1
        bundle.measure(LongitudM=x_hi - x_lo, AnchoM=bay_w, AlturaM=b1 - b0, NumeroTapones=plugs)

        for j, xf in enumerate((x0 - length / 4, x0 + length / 4)):
            fans += 1
            radius = min(bay_w, length / 2 - 0.4) * 0.43
            fan = part.add(
                f"ventilador-{fans}",
                f"Ventilador {fans}",
                "IfcFan",
                "PROPELLORAXIAL",
                "Tiro forzado",
            )
            ring_bottom = p0 - 0.42
            lathe(
                fan.mesh("Acero"),
                (xf, y, ring_bottom),
                UP,
                (
                    (0, radius + 0.09),
                    (0.06, radius + 0.02),
                    (0.36, radius + 0.02),
                    (0.42, radius + 0.06),
                ),
                32,
                caps=(False, False),
            )
            box(fan.mesh("Acero"), (xf, y, p0 - 0.01), (radius * 2 + 0.3, radius * 2 + 0.3, 0.02))
            hub_z = ring_bottom + 0.18
            lathe(
                fan.mesh("Refuerzo"),
                (xf, y, hub_z - 0.1),
                UP,
                ((0, 0.12), (0.18, 0.14), (0.24, 0.06)),
                12,
            )
            blades = 6
            for k in range(blades):
                a = k * tau / blades + j * 0.3
                pts = []
                for dist, off, hz in (
                    (0.14, -0.1, 0.04),
                    (0.97, -0.05, 0.015),
                    (0.97, 0.13, -0.015),
                    (0.14, 0.22, -0.04),
                ):
                    pts.append(
                        (
                            xf + radius * dist * cos(a + off),
                            y + radius * dist * sin(a + off),
                            hub_z + hz,
                        )
                    )
                quad(fan.mesh("Galvanizado"), pts)
            for k in range(3):
                a = k * pi / 3 + 0.2
                d = vec((cos(a), sin(a), 0.0)) * (radius + 0.02)
                beam(
                    fan.mesh("Refuerzo"),
                    (xf - d[0], y - d[1], ring_bottom - 0.05),
                    (xf + d[0], y + d[1], ring_bottom - 0.05),
                    0.03,
                    0.03,
                )
            fan.measure(DiametroM=2 * radius, NumeroAspas=blades, CotaM=ring_bottom)

            drive = part.add(
                f"accionamiento-{fans}",
                f"Motor y transmisión {fans}",
                "IfcElectricMotor",
                "INDUCTION",
                "Accionamiento por correa",
            )
            shaft_x = xf
            tube(
                drive.mesh("Acero"),
                (shaft_x, y, hub_z - 0.1),
                (shaft_x, y, ring_bottom - 0.55),
                0.035,
                8,
            )
            tube(
                drive.mesh("Acero"),
                (shaft_x, y, ring_bottom - 0.65),
                (shaft_x, y, ring_bottom - 0.53),
                0.28,
                20,
            )
            mx = shaft_x + 0.62
            motor_top = ring_bottom - 0.5
            lathe(
                drive.mesh("Motor"),
                (mx, y, motor_top - 0.75),
                UP,
                ((0, 0.12), (0.06, 0.2), (0.6, 0.2), (0.62, 0.18), (0.75, 0.16)),
                16,
            )
            tube(
                drive.mesh("Acero"), (mx, y, motor_top - 0.15), (mx, y, motor_top + 0.02), 0.09, 12
            )
            box(
                drive.mesh("Seguridad"),
                ((shaft_x + mx) / 2, y, ring_bottom - 0.59),
                (0.62 + 0.75, 0.66, 0.2),
            )
            for k in (-1, 1):
                beam(
                    drive.mesh("Refuerzo"),
                    (mx - 0.3, y + k * 0.3, motor_top - 0.2),
                    (mx - 0.3, y + k * 0.3, p0 - 0.05),
                    0.08,
                    0.08,
                    (1, 0, 0),
                )
            drive.measure(DiametroPoleaM=0.56, AlturaM=0.75, DistanciaEjesM=0.62)

    inlet = next((n for n in nozzles if n.incoming), None)
    outlet = next((n for n in nozzles if not n.incoming), None)
    for key, label, item, x, z_port, z_nozzle, toward in (
        (
            "colector-entrada",
            "Colector de entrada",
            inlet,
            g["inlet_x"],
            g["inlet_z"],
            b1 + 0.06,
            1,
        ),
        (
            "colector-salida",
            "Colector de salida",
            outlet,
            g["outlet_x"],
            g["outlet_z"],
            b0 - 0.06,
            -1,
        ),
    ):
        manifold = part.add(key, label, "IfcPipeSegment", "RIGIDSEGMENT", "Reparto a los haces")
        pipe = manifold.mesh("Acero")
        dn = item.line.dn if item else (inlet.line.dn if inlet else 300)
        branch = max(150, int(round(dn * 0.7 / 50)) * 50)
        side = int(item.direction[1]) if item else 1
        y_face = y0 + side * width / 2
        far = bays[0] if side > 0 else bays[1]
        header = ((x, far, z_port), (x, y_face, z_port))
        tube(pipe, header[0], header[1], dn / 2000, PIPE, caps=(True, False))
        for y in bays:
            tube(pipe, (x, y, z_port), (x, y, z_nozzle), branch / 2000, PIPE, caps=(False, False))
            flange_joint(
                pipe,
                manifold.mesh("Junta"),
                (x, y, (z_port + z_nozzle) / 2),
                (0, 0, -toward),
                branch,
            )
        if item:
            flange_half(pipe, item.point, item.direction, dn)
        else:
            blind_flange(pipe, manifold.mesh("Junta"), (x, y_face, z_port), (0, side, 0), dn)
        manifold.measure(DN=dn, LongitudM=abs(y_face - far), CotaEjeM=z_port)

    walk_z = b0 - 0.25
    x_w = x0 - length / 2 - 0.55
    walk = part.add(
        "pasillo", "Pasillo de mantenimiento", "IfcSlab", "LANDING", "Acceso a los cabezales"
    )
    grating_rect(walk, (x_w, y0, walk_z), (0.9, width - 0.2))
    for y in (ys[0], ys[1]):
        beam(
            walk.mesh("Refuerzo"),
            (x_w - 0.45, y, walk_z - 0.12),
            (xs[0], y, walk_z - 0.12),
            0.12,
            0.2,
        )
    walk.measure(CotaM=walk_z, LongitudM=width - 0.2, AnchoM=0.9)
    guard = part.add(
        "barandilla-pasillo",
        "Barandilla del pasillo",
        "IfcRailing",
        "GUARDRAIL",
        "Protección perimetral",
    )
    pts = [
        (x_w + 0.4, y0 - width / 2 + 0.15, walk_z),
        (x_w - 0.42, y0 - width / 2 + 0.15, walk_z),
        (x_w - 0.42, y0 + width / 2 - 0.15, walk_z),
        (x_w + 0.4, y0 + width / 2 - 0.15, walk_z),
    ]
    length_r, posts = railing(guard.mesh("Seguridad"), guard.mesh("Seguridad"), pts)
    guard.measure(LongitudM=length_r, AlturaM=1.1, NumeroPostes=posts)
    lad = part.add("escala", "Escala de gato", "IfcStairFlight", "STRAIGHT", "Acceso al pasillo")
    rungs = ladder(
        lad.mesh("Seguridad"),
        lad.mesh("Seguridad"),
        (x_w - 0.65, y0 + width * 0.1, deck),
        walk_z,
        (-1, 0),
    )
    lad.measure(AlturaM=walk_z - deck, NumeroPeldanos=rungs, AnchoM=0.46)


def vaporizer_geometry(eq: Equipment, deck: float):
    x0, y0 = eq.xy
    length, width, height = eq.size
    return {
        "inlet_x": round(x0 - length / 2 + 0.35, 3),
        "outlet_x": round(x0 + length / 2 - 0.35, 3),
        "inlet_z": round(deck + 0.75, 3),
        "outlet_z": round(deck + height - 0.25, 3),
    }


def vaporizer(part, eq, base, deck, nozzles):
    x0, y0 = eq.xy
    length, width, height = eq.size
    g = vaporizer_geometry(eq, deck)
    found = part.add(
        "bancada", "Bancada de hormigón", "IfcFooting", "PAD_FOOTING", "Apoyo del banco"
    )
    box(found.mesh("Hormigón"), (x0, y0, deck + 0.15), (length - 0.2, width - 0.4, 0.3))
    found.measure(LongitudM=length - 0.2, AnchoM=width - 0.4, AlturaM=0.3)
    frame = part.add("bastidor", "Bastidor", "IfcMember", "MEMBER", "Estructura de los módulos")
    steel = frame.mesh("Refuerzo")
    z_bot, z_top = deck + 0.95, deck + height - 0.55
    rows = (y0 - width * 0.24, y0 + width * 0.24)
    x_lo, x_hi = x0 - length / 2 + 0.7, x0 + length / 2 - 0.7
    for y in rows:
        for z in (deck + 0.45, z_top + 0.1):
            ibeam(steel, (x_lo - 0.3, y, z), (x_hi + 0.3, y, z), 0.2, 0.14)
        for x in (x_lo - 0.3, x0, x_hi + 0.3):
            ibeam(steel, (x, y, deck + 0.3), (x, y, z_top + 0.2), 0.18, 0.18, (1, 0, 0))
    for x in (x_lo - 0.3, x_hi + 0.3):
        ibeam(steel, (x, rows[0], z_top + 0.1), (x, rows[1], z_top + 0.1), 0.2, 0.14)
        angle_bar(steel, (x, rows[0], deck + 0.5), (x, rows[1], z_top), 0.07, (1, 0, 0))
    frame.measure(LongitudM=x_hi - x_lo + 0.6, AnchoM=rows[1] - rows[0], AlturaM=z_top + 0.2 - deck)

    fins, r_core, r_fin = 8, 0.05, 0.23
    tubes_total = 0
    for i, y in enumerate(rows):
        module = part.add(
            f"modulo-{'ab'[i]}",
            f"Módulo de tubos aleteados {'AB'[i]}",
            "IfcBuildingElementProxy",
            "ELEMENT",
            "Vaporización con aire ambiente",
        )
        count = 6
        xs = [x_lo + (x_hi - x_lo) * k / (count - 1) for k in range(count)]
        for row_off in (-0.3, 0.3):
            for x in xs:
                # Tubo de aluminio con ocho aletas radiales de chapa (láminas de dos caras).
                tube(
                    module.mesh("Aluminio"),
                    (x, y + row_off, z_bot),
                    (x, y + row_off, z_top),
                    r_core,
                    8,
                    caps=(False, True),
                )
                for k in range(fins):
                    a = tau * k / fins
                    w = vec((cos(a), sin(a), 0.0))
                    c = vec((x, y + row_off, 0.0))
                    quad(
                        module.mesh("Aluminio"),
                        (
                            c + w * r_core + vec((0, 0, z_bot)),
                            c + w * r_fin + vec((0, 0, z_bot)),
                            c + w * r_fin + vec((0, 0, z_top)),
                            c + w * r_core + vec((0, 0, z_top)),
                        ),
                    )
                tubes_total += 1
        # Codos de retorno entre las dos filas, arriba.
        for x in xs:
            samples = fillet(
                (
                    (x, y - 0.3, z_top),
                    (x, y - 0.3, z_top + 0.18),
                    (x, y + 0.3, z_top + 0.18),
                    (x, y + 0.3, z_top),
                ),
                0.15,
                quarter=2,
            )
            sweep(module.mesh("Acero"), samples, 0.035, 8, caps=(False, False))
        module.measure(
            NumeroTubos=2 * count,
            AlturaM=z_top - z_bot,
            LongitudM=x_hi - x_lo + 0.46,
            NumeroAletas=fins,
        )

    inlet = next((n for n in nozzles if n.incoming), None)
    outlet = next((n for n in nozzles if not n.incoming), None)
    for key, label, item, x, z in (
        ("colector-entrada", "Colector inferior de entrada", inlet, g["inlet_x"], g["inlet_z"]),
        ("colector-salida", "Colector superior de salida", outlet, g["outlet_x"], g["outlet_z"]),
    ):
        manifold = part.add(key, label, "IfcPipeSegment", "RIGIDSEGMENT", "Reparto entre módulos")
        pipe = manifold.mesh("Acero")
        dn = item.line.dn if item else (inlet.line.dn if inlet else 400)
        side = int(item.direction[1]) if item else 1
        y_face = y0 + side * width / 2
        far = rows[0] - 0.4 if side > 0 else rows[1] + 0.4
        tube(pipe, (x, far, z), (x, y_face, z), dn / 2000, PIPE, caps=(True, False))
        for y in rows:
            tube(pipe, (x, y, z), (x_lo if x < x0 else x_hi, y, z), 0.09, PIPE, caps=(False, True))
        if item:
            flange_half(pipe, item.point, item.direction, dn)
        else:
            blind_flange(pipe, manifold.mesh("Junta"), (x, y_face, z), (0, side, 0), dn)
        manifold.measure(DN=dn, LongitudM=abs(y_face - far), CotaEjeM=z)
    valve = part.add(
        "valvula-entrada",
        "Válvula de corte de entrada",
        "IfcValve",
        "SAFETYCUTOFF",
        "Corte de emergencia",
    )
    if inlet:
        dn = inlet.line.dn
        side = int(inlet.direction[1])
        center = vec(inlet.point) - vec(
            (0, side * (flange_size(dn)["thickness"] + flange_size(dn)["hub"] + 0.5), 0)
        )
        bolts, length_v = actuated_ball_valve(
            valve.mesh("Acero"),
            valve.mesh("Seguridad"),
            valve.mesh("Junta"),
            center + vec((0, -side * 0.1, 0)),
            (0, side, 0),
            dn,
        )
        valve.measure(DN=dn, LongitudM=length_v, NumeroPernos=bolts)


def cyclone_geometry(eq: Equipment, deck: float):
    x0, y0 = eq.xy
    length, width, height = eq.size
    return {
        "inlet_x": round(x0 - length / 2 + 0.3, 3),
        "outlet_x": round(x0 + length / 2 - 0.3, 3),
        "inlet_z": round(deck + 0.45 * height, 3),
        "outlet_z": round(deck + 0.85 * height, 3),
    }


def cyclone_skid(part, eq, base, deck, nozzles):
    x0, y0 = eq.xy
    length, width, height = eq.size
    g = cyclone_geometry(eq, deck)
    frame = part.add("bastidor", "Bastidor", "IfcMember", "MEMBER", "Patín del paquete")
    steel = frame.mesh("Refuerzo")
    for k in (-1, 1):
        ibeam(
            steel,
            (x0 - length / 2 + 0.15, y0 + k * (width / 2 - 0.2), deck + 0.15),
            (x0 + length / 2 - 0.15, y0 + k * (width / 2 - 0.2), deck + 0.15),
            0.3,
            0.18,
        )
    for t in (-0.5, -0.17, 0.17, 0.5):
        x = x0 + t * (length - 0.3)
        ibeam(
            steel,
            (x, y0 - width / 2 + 0.2, deck + 0.15),
            (x, y0 + width / 2 - 0.2, deck + 0.15),
            0.26,
            0.16,
        )
    box(frame.mesh("Cubierta"), (x0, y0, deck + 0.305), (length - 0.3, width - 0.4, 0.01))
    frame.measure(LongitudM=length - 0.3, AnchoM=width - 0.4, AlturaM=0.31)
    r = min(0.42, width * 0.12)
    z0 = deck + 0.55
    z1 = deck + height * 0.82
    vessels = []
    for i, t in enumerate((-0.27, 0.0, 0.27)):
        x = x0 + t * length
        y = y0 - width * 0.1
        vessels.append((x, y))
        v = part.add(
            f"ciclon-{'abc'[i]}",
            f"Recipiente de hidrociclones {'ABC'[i]}",
            "IfcFilter",
            "USERDEFINED",
            "Separación de aceite",
        )
        lathe(
            v.mesh("Acero"),
            (x, y, z0),
            UP,
            ((0, 0.06), (0.35, r * 0.75), (0.55, r), (z1 - z0, r)),
            SMALL,
        )
        flange_joint(v.mesh("Acero"), v.mesh("Junta"), (x, y, z1 + 0.04), UP, 2 * r * 1000 * 0.8)
        lathe(v.mesh("Acero"), (x, y, z1 + 0.1), UP, head_profile(r * 0.95, r * 0.35, 4), SMALL)
        for k in range(3):
            a = k * tau / 3 + 0.4
            p = vec((x, y, 0)) + vec((cos(a), sin(a), 0)) * (r * 0.85)
            tube(v.mesh("Refuerzo"), (p[0], p[1], deck + 0.31), (p[0], p[1], z0 + 0.7), 0.04, 8)
        v.measure(DiametroM=2 * r, AlturaM=z1 + 0.1 + r * 0.35 - z0, CotaInferiorM=z0)

    for key, label, z, dn_branch, kind in (
        ("colector-entrada", "Colector de entrada", g["inlet_z"], 150, "in"),
        ("colector-rebose", "Colector de rebose", g["outlet_z"], 100, "over"),
        ("colector-fondo", "Colector de fondo", z0 - 0.15, 80, "under"),
    ):
        m = part.add(key, label, "IfcPipeSegment", "RIGIDSEGMENT", "Reparto entre recipientes")
        pipe = m.mesh("Acero")
        item = next((n for n in nozzles if n.incoming), None) if kind == "in" else None
        dn = item.line.dn if item else (200 if kind == "over" else 150)
        y_h = y0 + width * 0.22
        x_a, x_b = vessels[0][0] - 0.3, vessels[-1][0] + 0.3
        tube(pipe, (x_a, y_h, z), (x_b, y_h, z), dn / 2000, PIPE)
        for x, y in vessels:
            target_z = z if kind != "over" else z1 + 0.25
            if kind == "under":
                samples = fillet(((x, y, z0 + 0.02), (x, y, z), (x, y_h, z)), 0.15, quarter=4)
            elif kind == "over":
                samples = fillet(
                    (
                        (x, y, z1 + 0.1 + r * 0.35),
                        (x, y, target_z + 0.2),
                        (x, y_h, target_z + 0.2),
                        (x, y_h, z),
                    ),
                    0.15,
                    quarter=4,
                )
            else:
                samples = fillet(((x, y + r, z), (x, y_h, z)), 0.1, quarter=3)
            sweep(pipe, samples, dn_branch / 2000, PIPE, caps=(False, False))
        if item:
            x_p = item.point[0]
            samples = (
                fillet(((x_a, y_h, z), (x_p, y_h, z), item.point), 0.3, quarter=5)
                if abs(x_p - x_a) > 0.05
                else fillet(((x_p, y_h, z), item.point), 0.3)
            )
            sweep(pipe, samples, dn / 2000, PIPE, caps=(False, False))
            flange_half(pipe, item.point, item.direction, dn)
        else:
            end = vec((x_b + 0.25, y_h, z))
            tube(pipe, (x_b, y_h, z), end, dn / 2000, PIPE, caps=(False, False))
            blind_flange(pipe, m.mesh("Junta"), end, (1, 0, 0), dn)
        m.measure(DN=dn, LongitudM=x_b - x_a, CotaEjeM=z)

    z_p = z1 - 0.35
    p = part.add(
        "plataforma", "Plataforma de operación", "IfcSlab", "LANDING", "Acceso a las tapas"
    )
    py = y0 - width * 0.1 - r - 0.6
    grating_rect(p, (x0, py, z_p), (length - 0.6, 1.0))
    for t in (-0.45, 0.0, 0.45):
        x = x0 + t * (length - 0.6)
        ibeam(
            p.mesh("Refuerzo"),
            (x, py - 0.4, deck + 0.3),
            (x, py - 0.4, z_p - 0.2),
            0.14,
            0.14,
            (1, 0, 0),
        )
    p.measure(CotaM=z_p, LongitudM=length - 0.6, AnchoM=1.0)
    guard = part.add(
        "barandilla", "Barandilla de plataforma", "IfcRailing", "GUARDRAIL", "Protección perimetral"
    )
    xl, xr = x0 - (length - 0.6) / 2, x0 + (length - 0.6) / 2
    pts = [(xl, py + 0.48, z_p), (xl, py - 0.48, z_p), (xr - 0.7, py - 0.48, z_p)]
    length_a, posts_a = railing(guard.mesh("Seguridad"), guard.mesh("Seguridad"), pts)
    length_b, posts_b = railing(
        guard.mesh("Seguridad"),
        guard.mesh("Seguridad"),
        [(xr - 0.1, py - 0.48, z_p), (xr, py - 0.48, z_p), (xr, py + 0.48, z_p)],
    )
    guard.measure(LongitudM=length_a + length_b, AlturaM=1.1, NumeroPostes=posts_a + posts_b)
    lad = part.add(
        "escala", "Escala de gato", "IfcStairFlight", "STRAIGHT", "Acceso a la plataforma"
    )
    rungs = ladder(
        lad.mesh("Seguridad"),
        lad.mesh("Seguridad"),
        (xr - 0.4, py - 0.65, deck + 0.31),
        z_p,
        (0, -1),
    )
    lad.measure(AlturaM=z_p - deck - 0.31, NumeroPeldanos=rungs, AnchoM=0.46)


def loading_arm(part, eq, base, deck, nozzles):
    x0, y0 = eq.xy
    length, width, height = eq.size
    outlet = next((n for n in nozzles if not n.incoming), None)
    dn = outlet.line.dn if outlet else 400
    r = dn / 2000
    riser_top = deck + 0.62 * height
    sea = vec((-1.0, 0.0, 0.0))
    ped = part.add("pedestal", "Pedestal y columna", "IfcColumn", "COLUMN", "Soporte del brazo")
    lathe(
        ped.mesh("Refuerzo"),
        (x0, y0, deck),
        UP,
        ((0, 0.75), (0.04, 0.75), (0.04, 0.48), (0.5, 0.42), (riser_top - deck - 0.4, 0.42)),
        SMALL,
        caps=(True, True),
    )
    bolts = anchor_bolts(
        ped.mesh("Acero"),
        [
            (x0 + 0.62 * cos(a), y0 + 0.62 * sin(a), deck + 0.04)
            for a in np.linspace(0, tau, 12, endpoint=False)
        ],
    )
    ped.measure(DiametroM=0.84, AlturaM=riser_top - deck - 0.4, NumeroPernos=bolts)

    base_pipe = part.add(
        "tuberia-base",
        "Tubería de base",
        "IfcPipeSegment",
        "RIGIDSEGMENT",
        "Producto hacia el colector",
    )
    port = vec(outlet.point) if outlet else vec((x0 + 0.15 * length, y0 - width / 2, deck + 0.95))
    side = outlet.direction[1] if outlet else -1
    samples = fillet(
        ((x0 + 0.55, y0, riser_top - 0.6), (x0 + 0.55, y0, port[2]), (port[0], y0, port[2]), port),
        1.5 * dn / 1000,
        quarter=6,
        end_clear=(0.0, 0.3),
    )
    sweep(base_pipe.mesh("Acero"), samples, r, PIPE, caps=(False, False))
    if outlet:
        flange_half(base_pipe.mesh("Acero"), port, (0, side, 0), dn)
    base_pipe.measure(DN=dn, LongitudM=path_length(samples))

    head = part.add(
        "cabezal-giratorio", "Cabezal giratorio", "IfcPipeFitting", "JUNCTION", "Giro del brazo"
    )
    apex = vec((x0, y0, riser_top))
    lathe(
        head.mesh("Acero"),
        apex - vec((0, 0, 0.45)),
        UP,
        ((0, 0.5), (0.25, 0.5), (0.25, 0.36), (0.6, 0.36), (0.6, 0.0)),
        SMALL,
    )
    samples = fillet(
        (
            (x0 + 0.55, y0, riser_top - 0.6),
            (x0 + 0.55, y0, riser_top + 0.25),
            (x0, y0, riser_top + 0.25),
        ),
        0.35,
        quarter=5,
    )
    sweep(head.mesh("Acero"), samples, r, PIPE, caps=(False, False))
    head.measure(DiametroM=1.0, CotaM=riser_top)

    inner = part.add(
        "brazo-interior", "Brazo interior", "IfcPipeSegment", "RIGIDSEGMENT", "Tramo con contrapeso"
    )
    elbow = apex + vec((0, 0, 0.35))
    tip = elbow + sea * (0.28 * length) + vec((0, 0, height * 0.32))
    tube(inner.mesh("Acero"), elbow, tip, r, PIPE)
    back = elbow - (tip - elbow) * 0.45
    tube(inner.mesh("Refuerzo"), elbow, back, r * 0.7, 12)
    inner.measure(DN=dn, LongitudM=float(np.linalg.norm(tip - elbow)))

    weight = part.add(
        "contrapeso", "Contrapeso", "IfcDiscreteAccessory", "USERDEFINED", "Equilibrado del brazo"
    )
    oriented_box(
        weight.mesh("Refuerzo"), back, frame_along(elbow, back, (0, 1, 0)), (0.45, 0.4, 0.35)
    )
    weight.measure(LongitudM=0.9, AnchoM=0.8, AlturaM=0.7)

    outer = part.add(
        "brazo-exterior", "Brazo exterior", "IfcPipeSegment", "RIGIDSEGMENT", "Tramo hacia el buque"
    )
    drop = tip + sea * (0.22 * length) - vec((0, 0, height * 0.42))
    samples = fillet((tip - (tip - elbow) * 0.02, tip + sea * 0.05, drop), 0.45, quarter=6)
    sweep(outer.mesh("Acero"), samples, r, PIPE, caps=(False, False))
    outer.measure(DN=dn, LongitudM=path_length(samples))

    swivels = part.add(
        "rotulas", "Rótulas giratorias", "IfcPipeFitting", "BEND", "Articulaciones del brazo"
    )
    for p, axis in ((elbow, (0, 1, 0)), (tip, (0, 1, 0)), (drop, UP)):
        lathe(
            swivels.mesh("Acero"),
            vec(p) - unit(axis) * 0.22,
            axis,
            ((0, r * 1.25), (0.44, r * 1.25)),
            FLANGE,
        )
        bolt_ring(swivels.mesh("Acero"), p, axis, dn)
    swivels.measure(NumeroRotulas=3, DN=dn)

    coupler = part.add(
        "acoplador",
        "Acoplador rápido y desconexión de emergencia",
        "IfcPipeFitting",
        "CONNECTOR",
        "Conexión con el buque",
    )
    end = drop - vec((0, 0, 0.9))
    tube(coupler.mesh("Acero"), drop, drop - vec((0, 0, 0.35)), r, PIPE, caps=(False, False))
    lathe(
        coupler.mesh("Seguridad"),
        drop - vec((0, 0, 0.35)),
        (0, 0, -1),
        (
            (0, r * 1.5),
            (0.18, r * 1.5),
            (0.22, r * 1.25),
            (0.4, r * 1.25),
            (0.45, r * 1.6),
            (0.55, r * 1.6),
        ),
        FLANGE,
    )
    for k in range(3):
        a = k * tau / 3
        w = vec((cos(a), sin(a), 0))
        tube(
            coupler.mesh("Refuerzo"),
            end + w * r * 1.6 + vec((0, 0, 0.05)),
            end + w * r * 1.6 + vec((0, 0, 0.42)),
            0.04,
            8,
        )
    coupler.measure(DN=dn, LongitudM=0.9)

    hyd = part.add(
        "cilindros-hidraulicos",
        "Cilindros hidráulicos",
        "IfcActuator",
        "HYDRAULICACTUATOR",
        "Maniobra del brazo",
    )
    for k in (-1, 1):
        a = apex + vec((0, k * 0.45, -0.6))
        b = elbow + (tip - elbow) * 0.35 + vec((0, k * 0.3, 0))
        tube(hyd.mesh("Acero"), a, a + (b - a) * 0.6, 0.07, 10)
        tube(hyd.mesh("Galvanizado"), a + (b - a) * 0.55, b, 0.035, 8)
    hyd.measure(NumeroCilindros=2)

    service = part.add(
        "plataforma-servicio",
        "Plataforma de servicio",
        "IfcSlab",
        "LANDING",
        "Mantenimiento del cabezal",
    )
    z_s = riser_top - 1.1
    sector_deck(
        service.mesh("Rejilla"), service.mesh("Refuerzo"), (x0, y0, z_s), 0.5, 1.6, 0.4, tau - 0.4
    )
    platform_brackets(service.mesh("Refuerzo"), (x0, y0, 0), 0.45, 1.6, z_s, [1.2, pi, tau - 1.2])
    service.measure(CotaM=z_s, DiametroM=3.2)
    guard = part.add(
        "barandilla", "Barandilla de servicio", "IfcRailing", "GUARDRAIL", "Protección perimetral"
    )
    pts = [
        (
            x0 + 1.55 * cos(0.4 + (tau - 0.8) * k / 16),
            y0 + 1.55 * sin(0.4 + (tau - 0.8) * k / 16),
            z_s,
        )
        for k in range(17)
    ]
    length_r, posts = railing(guard.mesh("Seguridad"), guard.mesh("Seguridad"), pts)
    guard.measure(LongitudM=length_r, AlturaM=1.1, NumeroPostes=posts)
    lad = part.add(
        "escala", "Escala de gato", "IfcStairFlight", "STRAIGHT", "Acceso a la plataforma"
    )
    rungs = ladder(
        lad.mesh("Seguridad"), lad.mesh("Seguridad"), (x0 + 1.15, y0 + 0.75, deck), z_s, (0.8, 0.6)
    )
    lad.measure(AlturaM=z_s - deck, NumeroPeldanos=rungs, AnchoM=0.46)


def manifold(part, eq, base, deck, nozzles):
    x0, y0 = eq.xy
    length, width, height = eq.size
    zh = deck + 1.7
    dn_header = max([n.line.dn for n in nozzles] + [400]) + 50
    rh = dn_header / 2000
    xa, xb = x0 - length / 2 + 0.35, x0 + length / 2 - 0.35
    skid = part.add("patin", "Patín", "IfcMember", "MEMBER", "Bastidor del colector")
    for k in (-1, 1):
        ibeam(
            skid.mesh("Refuerzo"),
            (xa - 0.2, y0 + k * (width / 2 - 0.25), deck + 0.12),
            (xb + 0.2, y0 + k * (width / 2 - 0.25), deck + 0.12),
            0.24,
            0.16,
        )
    for x in np.linspace(xa - 0.1, xb + 0.1, 4):
        ibeam(
            skid.mesh("Refuerzo"),
            (x, y0 - width / 2 + 0.25, deck + 0.12),
            (x, y0 + width / 2 - 0.25, deck + 0.12),
            0.2,
            0.14,
        )
    box(skid.mesh("Cubierta"), (x0, y0, deck + 0.245), (xb - xa + 0.4, width - 0.4, 0.01))
    skid.measure(LongitudM=xb - xa + 0.4, AnchoM=width - 0.3, AlturaM=0.25)

    header = part.add(
        "colector", "Colector", "IfcPipeSegment", "RIGIDSEGMENT", "Cabecera de distribución"
    )
    tube(header.mesh("Acero"), (xa, y0, zh), (xb, y0, zh), rh, FLANGE, caps=(False, False))
    for x, sign in ((xa, -1), (xb, 1)):
        vessel_head(
            header.mesh("Acero"), (x, y0, zh), (sign, 0, 0), rh, rh * 0.5, sides=FLANGE, rings=4
        )
    header.measure(DN=dn_header, LongitudM=xb - xa + rh, CotaEjeM=zh)

    supports = part.add(
        "soportes", "Soportes del colector", "IfcMember", "MEMBER", "Apoyo con abrazaderas"
    )
    for x in (xa + 0.4, x0, xb - 0.4):
        ibeam(
            supports.mesh("Refuerzo"),
            (x, y0, deck + 0.25),
            (x, y0, zh - rh - 0.1),
            0.2,
            0.2,
            (1, 0, 0),
        )
        revolve(
            supports.mesh("Refuerzo"),
            (x - 0.08, y0, zh),
            (1, 0, 0),
            ((rh, 0.0), (rh + 0.02, 0.0), (rh + 0.02, 0.16), (rh, 0.16)),
            -pi / 2 - 1.2,
            -pi / 2 + 1.2,
            10,
        )
        box(supports.mesh("Refuerzo"), (x, y0, zh - rh - 0.06), (0.3, 2 * rh * 0.9, 0.08))
        torus(
            supports.mesh("Galvanizado"),
            (x, y0, zh),
            (1, 0, 0),
            rh + 0.02,
            0.012,
            16,
            4,
            start=0.0,
            arc=pi,
        )
    supports.measure(NumeroSoportes=3)

    count = 0
    used = set()
    for item in nozzles:
        tag = item.line.tag.lower()
        branch = part.add(
            f"ramal-{tag}",
            f"Ramal {item.line.tag}",
            "IfcPipeSegment",
            "RIGIDSEGMENT",
            f"Conexión {item.line.tag}",
        )
        jx, jy, jz = item.point
        side = item.direction[1]
        valve_dn = item.line.dn
        tube(
            branch.mesh("Acero"),
            (jx, y0, zh),
            (jx, y0 + side * (rh + 0.15), zh),
            valve_dn / 2000,
            FLANGE,
            caps=(False, False),
        )
        length_v = ball_length(valve_dn) if item.line.fluid == "GNL" else valve_length(valve_dn)
        v_start = y0 + side * (rh + 0.2)
        v_center = v_start + side * length_v / 2
        v_end = v_start + side * length_v
        tube(
            branch.mesh("Acero"),
            (jx, v_end, zh),
            item.point,
            valve_dn / 2000,
            FLANGE,
            caps=(False, False),
        )
        flange_half(branch.mesh("Acero"), item.point, item.direction, valve_dn)
        branch.measure(DN=valve_dn, LongitudM=abs(jy - y0), CotaEjeM=jz)
        valve = part.add(
            f"valvula-{tag}",
            f"Válvula {item.line.tag}",
            "IfcValve",
            "ISOLATING",
            "Aislamiento del ramal",
        )
        if item.line.fluid == "GNL":
            bolts, length_v = actuated_ball_valve(
                valve.mesh("Acero"),
                valve.mesh("Seguridad"),
                valve.mesh("Junta"),
                (jx, v_center, zh),
                (0, side, 0),
                valve_dn,
            )
        else:
            bolts, length_v = gate_valve(
                valve.mesh("Acero"),
                valve.mesh("Seguridad"),
                valve.mesh("Junta"),
                (jx, v_center, zh),
                (0, side, 0),
                valve_dn,
            )
        valve.measure(DN=valve_dn, LongitudM=length_v, NumeroPernos=bolts)
        used.add(round(jx, 1))
        count += 1

    if len(nozzles) < 3:
        sides = [n.direction[1] for n in nozzles]
        side = -sides[0] if sides else 1
        for i, t in enumerate((-0.3, 0.0, 0.3), 1):
            x = x0 + t * (xb - xa)
            dn = 200
            branch = part.add(
                f"ramal-{i}",
                f"Ramal de entrada {i}",
                "IfcPipeSegment",
                "RIGIDSEGMENT",
                "Conexión de pozo o de unidad",
            )
            y_end = y0 + side * (width / 2 - 0.2)
            down = deck - 1.2 if deck > 5 else deck + 0.25
            samples = fillet(
                ((x, y0, zh), (x, y_end, zh), (x, y_end, down)),
                0.3,
                quarter=5,
                end_clear=(rh + 0.2 + 0.7, 0.0),
            )
            sweep(branch.mesh("Acero"), samples, dn / 2000, PIPE, caps=(False, deck > 5))
            if deck <= 5:
                blind_flange(
                    branch.mesh("Acero"),
                    branch.mesh("Junta"),
                    (x, y_end, down + 0.1),
                    (0, 0, -1),
                    dn,
                )
            # Tramo corto del colector a la válvula (la brida con cuello la pone la válvula).
            stub = rh + 0.55 - valve_length(dn) / 2 - 0.1
            tube(
                branch.mesh("Acero"),
                (x, y0, zh),
                (x, y0 + side * stub, zh),
                dn / 2000,
                PIPE,
                caps=(False, False),
            )
            branch.measure(DN=dn, LongitudM=path_length(samples) + stub)
            valve = part.add(
                f"valvula-{i}",
                f"Válvula de entrada {i}",
                "IfcValve",
                "ISOLATING",
                "Aislamiento del ramal",
            )
            bolts, length_v = gate_valve(
                valve.mesh("Acero"),
                valve.mesh("Seguridad"),
                valve.mesh("Junta"),
                (x, y0 + side * (rh + 0.55), zh),
                (0, side, 0),
                dn,
            )
            valve.measure(DN=dn, LongitudM=length_v, NumeroPernos=bolts)

    gauges = part.add(
        "manometros", "Manómetros", "IfcFlowInstrument", "PRESSUREGAUGE", "Presión del colector"
    )
    for x in (xa + 0.25, xb - 0.25):
        gauge_dial(gauges, (x, y0, zh + rh), (1, 0, 0) if x > x0 else (-1, 0, 0))
    gauges.measure(NumeroManometros=2, DiametroM=0.16)


FAMILIES = {
    "horizontal": horizontal_vessel,
    "vertical": vertical_vessel,
    "column": vertical_vessel,
    "tank": tank,
    "pump": pump_skid,
    "compressor": compressor,
    "air-cooler": air_cooler,
    "vaporizer": vaporizer,
    "cyclone": cyclone_skid,
    "arm": loading_arm,
    "manifold": manifold,
}


def equipment_part(eq: Equipment, base: Equipment, deck: float, nozzles) -> Part:
    part = Part(eq.tag, eq.name, "equipment")
    FAMILIES[eq.family](part, eq, base, deck, nozzles)
    return part.finish()


# --- Líneas ------------------------------------------------------------------------------


def insulation(line: Line) -> float:
    if line.fluid == "GNL" or line.tag.startswith("BOG"):
        return 0.11
    if line.tag in HOT:
        return 0.07
    return 0.0


def straight_runs(samples):
    """Tramos rectos del eje: (distancia inicial, distancia final, punto a, punto b)."""
    runs = []
    walked = 0.0
    for (p, tp), (q, tq) in zip(samples, samples[1:]):
        step = float(np.linalg.norm(q - p))
        if step > 0.05 and float(np.dot(unit(tp), unit(tq))) > 0.9999:
            runs.append((walked, walked + step, p, q))
        walked += step
    return runs


def line_part(project: Project, line: Line, path, rack, obstacles=()) -> Part:
    part = Part(line.tag, f"{line.fluid} · {line.start} → {line.end}", "pipe")
    dn = line.dn
    d = dn / 1000
    r = d / 2
    f = flange_size(dn)
    flange_len = f["gap"] / 2 + f["thickness"] + f["hub"]
    samples = fillet(path, 1.5 * d, quarter=5, end_clear=(flange_len + 0.05, flange_len + 0.05))
    total = path_length(samples)
    clad = insulation(line)
    runs = straight_runs(samples)
    horizontal = [run for run in runs if abs(float(unit(run[3] - run[2])[2])) < 0.01]
    main = max(horizontal or runs, key=lambda run: run[1] - run[0])
    valve_len = (
        ball_length(dn)
        if line.fluid == "GNL"
        else (0.06 + 0.12 * d if dn >= 400 else valve_length(dn))
    )
    valve_at = (main[0] + main[1]) / 2
    if main[1] - main[0] > 6:
        valve_at = main[0] + min(3.0, (main[1] - main[0]) / 3)
    valve_point, valve_dir = point_at(samples, valve_at)
    reserve = valve_len / 2 + 2 * f["thickness"] + f["hub"] + 0.12

    pipe = part.add(
        "tramo", "Tramo de tubería", "IfcPipeSegment", "RIGIDSEGMENT", "Conducción del fluido"
    )
    if clad:
        ends = flange_len + 0.25
        gaps = [(0.0, ends), (valve_at - reserve, valve_at + reserve), (total - ends, total)]
        for a, b in gaps:
            sweep(pipe.mesh(line.fluid), subpath(samples, a, b), r, PIPE, caps=(False, False))
        for a, b in ((ends, valve_at - reserve), (valve_at + reserve, total - ends)):
            if b - a > 0.2:
                sweep(pipe.mesh("Aislante"), subpath(samples, a, b), r + clad, PIPE)
                for s in (a + 0.6, b - 0.6):
                    if b - a > 1.6:
                        sweep(
                            pipe.mesh(line.fluid),
                            subpath(samples, s - 0.08, s + 0.08),
                            r + clad + 0.006,
                            PIPE,
                            caps=(False, False),
                        )
        pipe.measure(EspesorAislamientoM=clad)
    else:
        sweep(pipe.mesh(line.fluid), samples, r, PIPE, caps=(False, False))
    bends = sum(
        1
        for a, b, c in zip(path, path[1:], path[2:])
        if np.linalg.norm(np.cross(vec(b) - vec(a), vec(c) - vec(b))) > 1e-9
    )
    pipe.measure(
        DN=dn,
        DiametroM=d,
        LongitudM=total,
        NumeroCodos=bends,
        RadioCodoM=1.5 * d,
        CotaRackM=project.deck + line.rack_z,
    )

    for key, label, point, direction in (
        ("brida-origen", f"Brida en {line.start}", path[0], vec(path[1]) - vec(path[0])),
        ("brida-destino", f"Brida en {line.end}", path[-1], vec(path[-2]) - vec(path[-1])),
    ):
        joint = part.add(key, label, "IfcPipeFitting", "CONNECTOR", "Unión con la boquilla")
        dirn = unit(direction)
        flange_half(joint.mesh("Acero"), point, -dirn, dn)
        gasket(joint.mesh("Junta"), point, dirn, dn)
        bolts = bolt_ring(joint.mesh("Acero"), point, dirn, dn)
        joint.measure(DN=dn, DiametroM=2 * f["radius"], NumeroPernos=bolts)

    valve = part.add(
        "valvula",
        "Válvula de línea",
        "IfcValve",
        "SAFETYCUTOFF" if line.fluid == "GNL" else "ISOLATING",
        "Aislamiento de la línea",
    )
    if line.fluid == "GNL":
        bolts, length_v = actuated_ball_valve(
            valve.mesh("Acero"),
            valve.mesh("Seguridad"),
            valve.mesh("Junta"),
            valve_point,
            valve_dir,
            dn,
        )
        kind = "Bola con actuador"
    elif dn >= 400:
        bolts, length_v = butterfly_valve(
            valve.mesh("Acero"),
            valve.mesh("Seguridad"),
            valve.mesh("Junta"),
            valve_point,
            valve_dir,
            dn,
        )
        kind = "Mariposa con reductor"
    else:
        bolts, length_v = gate_valve(
            valve.mesh("Acero"),
            valve.mesh("Seguridad"),
            valve.mesh("Junta"),
            valve_point,
            valve_dir,
            dn,
        )
        kind = "Compuerta con volante"
    valve.role = kind
    valve.measure(DN=dn, LongitudM=length_v, NumeroPernos=bolts, CotaEjeM=float(valve_point[2]))

    # Soportes: zapatas con guías sobre el rack o postes en T fuera de él.
    supports = part.add(
        "soportes", "Soportes de tubería", "IfcDiscreteAccessory", "SHOE", "Zapatas, guías y postes"
    )
    a, b = main[2], main[3]
    axis = unit(b - a)
    run_len = main[1] - main[0]
    z = float(a[2])
    bottom = z - r - clad
    positions = []
    on_rack = rack is not None and rack.holds(line)
    if on_rack and abs(axis[0]) > 0.99:
        lo, hi = sorted((float(a[0]), float(b[0])))
        positions = [x for x in rack.bents if lo + 0.5 < x < hi - 0.5]
    if not positions:
        count = max(2, ceil(run_len / 5.5))
        positions = [
            float((a + (b - a) * (i + 0.5) / count)[0 if abs(axis[0]) > 0.5 else 1])
            for i in range(count)
        ]
    placed = 0
    for value in positions:
        p = vec(a)
        if abs(axis[0]) > 0.5:
            p[0] = value
        else:
            p[1] = value
        if abs(float(np.dot(p - valve_point, axis))) < reserve + 0.25:
            continue
        if not on_rack and any(
            x0 - 0.3 < p[0] < x1 + 0.3 and y0 - 0.3 < p[1] < y1 + 0.3
            for x0, x1, y0, y1 in obstacles
        ):
            continue
        shoe_h = 0.12
        base_z = bottom - shoe_h
        steel = supports.mesh("Refuerzo")
        side = np.cross(UP, axis)
        oriented_box(
            steel, (p[0], p[1], base_z + 0.008), (axis, side, vec(UP)), (0.16, 0.11, 0.008)
        )
        oriented_box(
            steel,
            (p[0], p[1], (base_z + bottom) / 2),
            (axis, side, vec(UP)),
            (0.15, 0.008, shoe_h / 2),
        )
        revolve(
            steel,
            vec((p[0], p[1], z)) - axis * 0.16,
            axis,
            ((r + clad, 0.0), (r + clad + 0.012, 0.0), (r + clad + 0.012, 0.32), (r + clad, 0.32)),
            -pi / 2 - 0.8,
            -pi / 2 + 0.8,
            4,
        )
        if on_rack and rack.holds(line):
            tier = rack.tier_below(base_z)
            if base_z - tier > 0.03:
                oriented_box(
                    steel,
                    (p[0], p[1], (tier + base_z) / 2),
                    (axis, side, vec(UP)),
                    (0.07, 0.07, (base_z - tier) / 2),
                )
            for k in (-1, 1):
                g = vec((p[0], p[1], tier)) + side * k * 0.14
                oriented_box(
                    supports.mesh("Galvanizado"),
                    g + vec((0, 0, 0.03)),
                    (axis, side, vec(UP)),
                    (0.06, 0.01, 0.03),
                )
        else:
            post_top = base_z
            ibeam(steel, (p[0], p[1], project.deck), (p[0], p[1], post_top - 0.02), 0.2, 0.2, axis)
            oriented_box(
                steel, (p[0], p[1], post_top - 0.01), (axis, side, vec(UP)), (0.18, 0.18, 0.01)
            )
            oriented_box(
                steel, (p[0], p[1], project.deck + 0.012), (axis, side, vec(UP)), (0.2, 0.2, 0.012)
            )
        placed += 1
    supports.measure(NumeroSoportes=placed, AlturaZapataM=0.12)

    # Venteo en el punto alto y purga en el bajo, con válvula de bola DN 25.
    for key, label, at, sign in (
        ("venteo", "Venteo", main[0] + 0.7, 1),
        ("purga", "Purga", main[1] - 0.7, -1),
    ):
        comp = part.add(
            key,
            label,
            "IfcValve",
            "AIRRELEASE" if sign > 0 else "DRAWOFFCOCK",
            "Venteo" if sign > 0 else "Vaciado",
        )
        p, _ = point_at(samples, at)
        start = p + vec((0, 0, sign * (r * 0.9)))
        end = start + vec((0, 0, sign * (clad + 0.22)))
        tube(comp.mesh("Acero"), start, end, 0.017, 8)
        mid = end + vec((0, 0, sign * 0.06))
        box(comp.mesh("Acero"), (mid[0], mid[1], mid[2]), (0.06, 0.06, 0.09))
        tube(comp.mesh("Seguridad"), mid, mid + vec((0.16, 0, 0)), 0.01, 6)
        tube(
            comp.mesh("Acero"),
            mid + vec((0, 0, sign * 0.045)),
            mid + vec((0, 0, sign * 0.12)),
            0.02,
            8,
        )
        comp.measure(DN=25, LongitudM=clad + 0.4)
    return part.finish()


# --- Escena --------------------------------------------------------------------------------


def apply_changes(project: Project, active: set[str], adjustments=()):
    equipment = {item.tag: item for item in project.equipment}
    lines = {item.tag: item for item in project.lines}
    for change in (*(change for change in project.changes if change.tag in active), *adjustments):
        if (item := equipment.get(change.tag)) is not None:
            size = list(item.size)
            size[SIZE_AXIS[change.property]] = change.after
            if change.property == "width" and item.family in ("vertical", "column", "tank"):
                size[0] = change.after
            equipment[change.tag] = replace(item, size=tuple(size))
        else:
            line = lines[change.tag]
            value = int(change.after) if change.property == "dn" else change.after
            lines[change.tag] = replace(line, **{change.property: value})
    return equipment, lines


def routes(project: Project, active: set[str], adjustments=()):
    base = {item.tag: item for item in project.equipment}
    equipment, lines = apply_changes(project, active, adjustments)
    nozzles = layout_nozzles(project, equipment, base, lines)
    paths = {line.tag: line_path(project, line, nozzles) for line in lines.values()}
    return base, equipment, lines, nozzles, paths


def footprints(equipment):
    """Huella en planta de cada equipo (x0, x1, y0, y1) para no apoyar soportes encima."""
    return [
        (
            eq.xy[0] - eq.size[0] / 2,
            eq.xy[0] + eq.size[0] / 2,
            eq.xy[1] - eq.size[1] / 2,
            eq.xy[1] + eq.size[1] / 2,
        )
        for eq in equipment.values()
    ]


def scene(project: Project, active: set[str], adjustments=()):
    from .process_structure import Rack, structure

    every = {change.tag for change in project.changes}
    _, _, _, _, base_paths = routes(project, set())
    variants = [apply_changes(project, set())[1], apply_changes(project, every)[1]]
    base, equipment, lines, nozzles, paths = routes(project, active, adjustments)
    if adjustments:
        variants.append(lines)
    rack = Rack.build(project, variants, base_paths)
    obstacles = footprints(equipment)
    parts = [
        equipment_part(
            item,
            base[item.tag],
            project.deck,
            [nozzle for (tag, _), nozzle in nozzles.items() if tag == item.tag],
        )
        for item in equipment.values()
    ]
    parts.extend(
        line_part(project, line, paths[line.tag], rack, obstacles) for line in lines.values()
    )
    parts.append(structure(project, rack, equipment, lines, paths))
    return equipment, lines, paths, parts
