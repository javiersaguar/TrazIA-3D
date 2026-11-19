"""Núcleo de mallas de las plantas de proceso: primitivas y detalles repetidos.

Coordenadas en metros en el sistema local del IFC (+X este, +Y norte de dibujo, +Z
elevación), redondeadas al milímetro. Las caras son polígonos con la normal hacia fuera; el
escritor IFC los triangula en abanico desde su primer vértice, así que cada cara es convexa o
estrellada respecto a ese vértice. Cada llamada a una primitiva queda registrada como un grupo
para que los planos dibujen su contorno por separado.
"""

from math import acos, ceil, cos, pi, sin, sqrt, tan, tau

import numpy as np

DECIMALS = 3
BOX_FACES = ((3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))
UP = (0.0, 0.0, 1.0)


def vec(point) -> np.ndarray:
    return np.asarray(point, dtype=float)


def unit(vector) -> np.ndarray:
    vector = vec(vector)
    norm = float(np.linalg.norm(vector))
    if norm < 1e-12:
        raise ValueError("Dirección nula")
    return vector / norm


def basis(direction):
    """(d, u, v) ortonormales a derechas (u × v = d). En ejes verticales u = +X; en
    horizontales v = +Z, así las fases angulares son predecibles."""
    d = unit(direction)
    if abs(d[2]) > 0.999:
        u = np.array([1.0, 0.0, 0.0])
    else:
        u = unit(np.cross(UP, d))
    return d, u, np.cross(d, u)


def mm(value: float) -> float:
    return round(float(value), DECIMALS) + 0.0


class Mesh:
    """Malla de un material: caras propias e instancias de plantillas (IfcMappedItem)."""

    __slots__ = ("vertices", "faces", "groups", "instances", "_expanded")

    def __init__(self):
        self.vertices: list[tuple[float, float, float]] = []
        self.faces: list[tuple[int, ...]] = []
        # (primer vértice, último + 1, solo contorno): un grupo por primitiva.
        self.groups: list[tuple[int, int, bool]] = []
        # (clave de plantilla, origen, rotación 3×3 con los ejes locales en columnas).
        self.instances: list[tuple[str, tuple, tuple]] = []
        self._expanded = None

    def add(self, vertices, faces, *, outline=False):
        first = len(self.vertices)
        self.vertices.extend((mm(p[0]), mm(p[1]), mm(p[2])) for p in vertices)
        self.faces.extend(tuple(first + i for i in face) for face in faces)
        self.groups.append((first, len(self.vertices), outline))
        self._expanded = None

    def place(self, key, origin, rotation):
        self.instances.append((key, origin, rotation))
        self._expanded = None

    @property
    def own_triangles(self) -> int:
        return sum(len(face) - 2 for face in self.faces)

    @property
    def triangles(self) -> int:
        """Triángulos dibujados: propios más los de cada instancia."""
        return self.own_triangles + sum(
            TEMPLATES[key].own_triangles for key, _, _ in self.instances
        )

    def expanded(self) -> "Mesh":
        """Malla con las instancias desplegadas en coordenadas del modelo (planos y cotas)."""
        if not self.instances:
            return self
        if self._expanded is None:
            result = Mesh()
            result.vertices = list(self.vertices)
            result.faces = list(self.faces)
            result.groups = list(self.groups)
            for key, origin, rotation in self.instances:
                template = TEMPLATES[key]
                first = len(result.vertices)
                points = np.asarray(template.vertices) @ np.asarray(rotation).T + np.asarray(origin)
                result.vertices.extend(tuple(round(float(c), 3) + 0.0 for c in p) for p in points)
                result.faces.extend(tuple(first + i for i in face) for face in template.faces)
                result.groups.extend((first + a, first + b, o) for a, b, o in template.groups)
            self._expanded = result
        return self._expanded


# --- Plantillas de detalle repetido ---------------------------------------------------------

# Geometría local de cada plantilla por clave y papel ("clave#n"). Se escribe en el IFC una vez
# por fichero como IfcRepresentationMap y cada uso es un IfcMappedItem con su transformación.
TEMPLATES: dict[str, Mesh] = {}
_RESULTS: dict[str, object] = {}
_DEPTH = [0]


def clear_templates():
    """Libera las plantillas que se crearon al generar un borrador."""
    TEMPLATES.clear()
    _RESULTS.clear()


def frame_axes(x_axis, z_axis):
    """Rotación con columnas (x, y, z) ortonormales a derechas a partir de x y z."""
    z = unit(z_axis)
    x = vec(x_axis) - z * float(np.dot(x_axis, z))
    x = unit(x)
    y = np.cross(z, x)
    return tuple(tuple(round(float(c), 6) + 0.0 for c in row) for row in np.column_stack((x, y, z)))


def mapped(key, meshes, origin, rotation, build):
    """Dibuja 'build' una sola vez en coordenadas locales y lo coloca en 'meshes'.

    'meshes' es una malla por papel (acero, junta…); 'build' recibe tantas mallas locales y
    devuelve un resultado (número de pernos, longitud…) que se memoriza con la plantilla.
    Dentro de otra plantilla la geometría se copia transformada en lugar de instanciarse.
    """
    if key not in _RESULTS:
        local = [Mesh() for _ in meshes]
        _DEPTH[0] += 1
        try:
            _RESULTS[key] = build(*local)
        finally:
            _DEPTH[0] -= 1
        for i, mesh in enumerate(local):
            TEMPLATES[f"{key}#{i}"] = mesh
    o = tuple(mm(c) for c in origin)
    r = np.asarray(rotation, dtype=float)
    for i, target in enumerate(meshes):
        name = f"{key}#{i}"
        template = TEMPLATES[name]
        if not template.faces:
            continue
        if _DEPTH[0]:
            target.add(np.asarray(template.vertices) @ r.T + np.asarray(o), template.faces)
        else:
            target.place(name, o, tuple(tuple(float(c) for c in row) for row in r))
    return _RESULTS[key]


# --- Primitivas -------------------------------------------------------------------------


def box(mesh, center, size):
    x, y, z = center
    a, b, c = (value / 2 for value in size)
    mesh.add(
        [
            (x + i * a, y + j * b, z + k * c)
            for k in (-1, 1)
            for i, j in ((-1, -1), (1, -1), (1, 1), (-1, 1))
        ],
        BOX_FACES,
    )


# Caras de una caja sin las dos caras ±b (peldaños y piezas entre largueros).
SLAT_FACES = (BOX_FACES[0], BOX_FACES[1], BOX_FACES[3], BOX_FACES[5])


def oriented_box(mesh, center, axes, half, *, faces=BOX_FACES):
    """Caja con ejes (a, b, n) ortonormales a derechas y semilados (ha, hb, hn)."""
    c = vec(center)
    a, b, n = (vec(axis) for axis in axes)
    ha, hb, hn = half
    mesh.add(
        [
            c + i * ha * a + j * hb * b + k * hn * n
            for k in (-1, 1)
            for i, j in ((-1, -1), (1, -1), (1, 1), (-1, 1))
        ],
        faces,
    )


def frame_along(a, b, up=UP):
    """Eje d de a a b, lado y 'arriba' ortogonales, con (d, lado, arriba) a derechas."""
    a, b = vec(a), vec(b)
    d = unit(b - a)
    up = vec(up)
    up = up - d * float(np.dot(up, d))
    if np.linalg.norm(up) < 1e-6:
        up = np.array([1.0, 0.0, 0.0]) if abs(d[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        up = up - d * float(np.dot(up, d))
    up = unit(up)
    return d, np.cross(up, d), up


def beam(mesh, a, b, width, height, up=UP):
    """Prisma rectangular de a a b: 'width' en horizontal y 'height' según 'up'."""
    a, b = vec(a), vec(b)
    d, side, up = frame_along(a, b, up)
    length = float(np.linalg.norm(b - a))
    oriented_box(mesh, (a + b) / 2, (d, side, up), (length / 2, width / 2, height / 2))


def section_prism(mesh, a, b, up, outline, caps, ends=(True, True)):
    """Prisma de a a b con sección poligonal antihoraria en el plano (lado, arriba).

    'outline' son los puntos (lado, arriba) de la sección y 'caps' los cuadriláteros que
    cierran cada extremo (índices de 'outline'), para secciones no convexas como I o L."""
    a, b = vec(a), vec(b)
    d, side, up = frame_along(a, b, up)
    ring = [side * s_ + up * u_ for s_, u_ in outline]
    n = len(ring)
    vertices = [a + w for w in ring] + [b + w for w in ring]
    faces = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    if ends[0]:
        faces.extend(tuple(reversed(cap)) for cap in caps)
    if ends[1]:
        faces.extend(tuple(n + i for i in cap) for cap in caps)
    mesh.add(vertices, faces)


def ibeam(mesh, a, b, depth, width, up=UP, *, flange=None, web=None, ends=(True, True)):
    """Perfil en H/I de a a b con el alma según 'up'. Los extremos que quedan contra otra
    pieza (nudos del rack, placas) pueden ir sin tapa."""
    tf = flange or max(0.008, depth * 0.075)
    tw = (web or max(0.006, depth * 0.05)) / 2
    w, h = width / 2, depth / 2
    outline = (
        (-w, -h),
        (w, -h),
        (w, -h + tf),
        (tw, -h + tf),
        (tw, h - tf),
        (w, h - tf),
        (w, h),
        (-w, h),
        (-w, h - tf),
        (-tw, h - tf),
        (-tw, -h + tf),
        (-w, -h + tf),
    )
    section_prism(mesh, a, b, up, outline, ((0, 1, 2, 11), (10, 3, 4, 9), (8, 5, 6, 7)), ends)


def angle_bar(mesh, a, b, leg, up=UP, *, thickness=None, ends=(True, True)):
    """Angular de lados iguales: un ala según 'up' y otra horizontal."""
    t = thickness or max(0.006, leg * 0.1)
    outline = ((0.0, 0.0), (leg, 0.0), (leg, t), (t, t), (t, leg), (0.0, leg))
    section_prism(mesh, a, b, up, outline, ((0, 1, 2, 3), (0, 3, 4, 5)), ends)


def lathe(mesh, origin, axis, profile, sides, *, phase=0.0, caps=(True, True), outline=False):
    """Sólido de revolución. 'profile' son pares (s, r): distancia por el eje y radio,
    con s no decreciente. Un radio nulo en un extremo cierra en punta."""
    d, u, v = basis(axis)
    o = vec(origin)
    directions = [
        cos(phase + i * tau / sides) * u + sin(phase + i * tau / sides) * v for i in range(sides)
    ]
    vertices = []
    rings = []
    for s, r in profile:
        center = o + s * d
        if r <= 1e-9:
            rings.append((len(vertices), True))
            vertices.append(center)
        else:
            rings.append((len(vertices), False))
            vertices.extend(center + r * w for w in directions)
    faces = []
    for (p, apex_p), (q, apex_q) in zip(rings, rings[1:]):
        if apex_p and apex_q:
            continue
        for i in range(sides):
            j = (i + 1) % sides
            if apex_p:
                faces.append((p, q + j, q + i))
            elif apex_q:
                faces.append((p + i, p + j, q))
            else:
                faces.append((p + i, p + j, q + j, q + i))
    (first, first_apex), (last, last_apex) = rings[0], rings[-1]
    if caps[0] and not first_apex:
        faces.append(tuple(first + i for i in reversed(range(sides))))
    if caps[1] and not last_apex:
        faces.append(tuple(last + i for i in range(sides)))
    mesh.add(vertices, faces, outline=outline)


def tube(mesh, a, b, radius, sides=16, *, caps=(True, True), phase=0.0, outline=False):
    a, b = vec(a), vec(b)
    length = float(np.linalg.norm(b - a))
    if length < 1e-6:
        return
    lathe(
        mesh,
        a,
        b - a,
        ((0.0, radius), (length, radius)),
        sides,
        caps=caps,
        phase=phase,
        outline=outline,
    )


def bolt(mesh, center, axis, radius, length):
    """Espárrago con tuercas: prisma de sección cuadrada centrado en 'center'."""
    d = unit(axis)
    c = vec(center)
    # Sin tapas: a esta escala el extremo abierto no se aprecia y ahorra un tercio.
    tube(mesh, c - d * length / 2, c + d * length / 2, radius, 4, phase=pi / 4, caps=(False, False))


def revolve(mesh, center, axis, section, start, end, segments, *, caps=True, outline=False):
    """Barre una sección (r, s) en sentido antihorario alrededor del eje entre dos ángulos."""
    d, u, v = basis(axis)
    c = vec(center)
    full = abs(end - start) >= tau - 1e-9
    count = segments if full else segments + 1
    m = len(section)
    vertices = []
    for k in range(count):
        t = start + (end - start) * k / segments
        radial = cos(t) * u + sin(t) * v
        vertices.extend(c + r * radial + s * d for r, s in section)
    faces = []
    for k in range(segments):
        k2 = (k + 1) % count if full else k + 1
        for i in range(m):
            j = (i + 1) % m
            faces.append((k * m + i, k2 * m + i, k2 * m + j, k * m + j))
    if caps and not full:
        faces.append(tuple(range(m)))
        faces.append(tuple(segments * m + i for i in reversed(range(m))))
    mesh.add(vertices, faces, outline=outline)


def torus(
    mesh, center, axis, radius, wire, segments, sides=4, *, start=0.0, arc=tau, outline=False
):
    """Toro o arco de toro: aros de jaula, volantes y anillos."""
    section = [
        (radius + wire * cos(tau * j / sides), wire * sin(tau * j / sides)) for j in range(sides)
    ]
    revolve(mesh, center, axis, section, start, start + arc, segments, outline=outline)


def extrude(mesh, origin, axis, polygon, length, *, u=None, center=(0.0, 0.0), outline=False):
    """Prisma de un polígono antihorario en el plano (u, v) normal al eje. Las tapas se
    cierran en abanico desde 'center', así valen polígonos estrellados (aletas, voluta)."""
    if u is None:
        d, u_, v_ = basis(axis)
    else:
        d = unit(axis)
        u_ = unit(vec(u) - d * float(np.dot(u, d)))
        v_ = np.cross(d, u_)
    o = vec(origin)
    n = len(polygon)
    bottom = [o + x * u_ + y * v_ for x, y in polygon]
    top = [p + length * d for p in bottom]
    cx, cy = center
    hub = o + cx * u_ + cy * v_
    vertices = bottom + top + [hub, hub + length * d]
    faces = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    faces.extend((2 * n, (i + 1) % n, i) for i in range(n))
    faces.extend((2 * n + 1, n + i, n + (i + 1) % n) for i in range(n))
    mesh.add(vertices, faces, outline=outline)


def loft(mesh, lower, upper, *, caps=(True, True)):
    """Une dos contornos cerrados con el mismo número de puntos (de abajo arriba)."""
    n = len(lower)
    vertices = [vec(p) for p in lower] + [vec(p) for p in upper]
    faces = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    if caps[0]:
        faces.append(tuple(reversed(range(n))))
    if caps[1]:
        faces.append(tuple(n + i for i in range(n)))
    mesh.add(vertices, faces)


def quad(mesh, points, *, double=True):
    """Lámina fina (aspas, señalización): dos caras opuestas."""
    faces = [(0, 1, 2, 3), (3, 2, 1, 0)] if double else [(0, 1, 2, 3)]
    mesh.add(points, faces)


# --- Recorridos con codos de radio largo -------------------------------------------------


def clean_nodes(nodes):
    points = []
    for node in nodes:
        p = vec(node)
        if not points or np.linalg.norm(p - points[-1]) > 1e-6:
            points.append(p)
    result = [points[0]]
    for before, corner, after in zip(points, points[1:], points[2:]):
        if np.linalg.norm(np.cross(corner - before, after - corner)) > 1e-9:
            result.append(corner)
    result.append(points[-1])
    return result


def fillet(nodes, bend, *, quarter=6, end_clear=(0.0, 0.0)):
    """Eje de un recorrido con codos circulares de radio 'bend'.

    Devuelve [(punto, tangente)] con un punto por extremo de tramo recto y varios por codo.
    Si un tramo es corto, el codo reduce su radio para no invadir el siguiente.
    """
    points = clean_nodes(nodes)
    n = len(points)
    lengths = [float(np.linalg.norm(points[i + 1] - points[i])) for i in range(n - 1)]
    fillets = {}
    for i in range(1, n - 1):
        d1, d2 = unit(points[i] - points[i - 1]), unit(points[i + 1] - points[i])
        theta = acos(max(-1.0, min(1.0, float(np.dot(d1, d2)))))
        if theta < 1e-4:
            continue
        before = lengths[i - 1] - (end_clear[0] if i - 1 == 0 else 0.0)
        after = lengths[i] - (end_clear[1] if i == n - 2 else 0.0)
        before *= 1.0 if i - 1 == 0 else 0.5
        after *= 1.0 if i == n - 2 else 0.5
        trim = min(bend * tan(theta / 2), 0.97 * before, 0.97 * after)
        fillets[i] = (max(trim, 1e-3), theta, d1, d2)
    samples = [(points[0], unit(points[1] - points[0]))]
    for i in range(1, n - 1):
        if i not in fillets:
            samples.append((points[i], unit(points[i + 1] - points[i - 1])))
            continue
        trim, theta, d1, d2 = fillets[i]
        radius = trim / tan(theta / 2)
        start = points[i] - d1 * trim
        normal = unit(d2 - d1 * float(np.dot(d1, d2)))
        center = start + normal * radius
        steps = max(2, ceil(theta / (pi / 2) * quarter))
        for k in range(steps + 1):
            phi = theta * k / steps
            point = center + radius * (-normal * cos(phi) + d1 * sin(phi))
            samples.append((point, d1 * cos(phi) + normal * sin(phi)))
    samples.append((points[-1], unit(points[-1] - points[-2])))
    return samples


def path_length(samples) -> float:
    return sum(float(np.linalg.norm(b[0] - a[0])) for a, b in zip(samples, samples[1:]))


def subpath(samples, start, end):
    """Parte del eje entre dos distancias medidas desde el origen del recorrido."""
    result = []
    walked = 0.0
    for (p, tp), (q, tq) in zip(samples, samples[1:]):
        step = float(np.linalg.norm(q - p))
        if step < 1e-9:
            continue
        lo, hi = walked, walked + step
        if hi >= start and lo <= end:
            a = max(start, lo)
            b = min(end, hi)
            pa = p + (q - p) * (a - lo) / step
            pb = p + (q - p) * (b - lo) / step
            ta = unit(tp + (tq - tp) * (a - lo) / step)
            tb = unit(tp + (tq - tp) * (b - lo) / step)
            if not result or np.linalg.norm(result[-1][0] - pa) > 1e-6:
                result.append((pa, ta))
            result.append((pb, tb))
        walked = hi
    return result


def point_at(samples, distance):
    part = subpath(samples, distance, distance + 1e-6)
    return part[0] if part else samples[-1]


def sweep(mesh, samples, radius, sides=16, *, caps=(True, True), outline=False):
    """Tubo a lo largo de un eje muestreado, con transporte paralelo del anillo."""
    if len(samples) < 2:
        return
    ring = [(cos(i * tau / sides), sin(i * tau / sides)) for i in range(sides)]
    vertices = []
    u = None
    for center, tangent in samples:
        d = unit(tangent)
        if u is None:
            _, u, _ = basis(d)
        else:
            u = u - d * float(np.dot(u, d))
            if np.linalg.norm(u) < 1e-9:
                _, u, _ = basis(d)
            u = unit(u)
        v = np.cross(d, u)
        vertices.extend(center + radius * (c * u + s * v) for c, s in ring)
    faces = []
    for k in range(len(samples) - 1):
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((k * sides + i, k * sides + j, (k + 1) * sides + j, (k + 1) * sides + i))
    if caps[0]:
        faces.append(tuple(reversed(range(sides))))
    if caps[1]:
        faces.append(tuple(len(vertices) - sides + i for i in range(sides)))
    mesh.add(vertices, faces, outline=outline)


# --- Bridas, válvulas y accesorios de tubería ---------------------------------------------

ORIGIN = (0.0, 0.0, 0.0)
X_AXIS = (1.0, 0.0, 0.0)
Z_AXIS = (0.0, 0.0, 1.0)


def flange_size(dn: float):
    """Proporciones de una brida con cuello ASME clase 150 aproximada por el DN (mm)."""
    d = dn / 1000
    r_pipe = d / 2
    radius = (0.1 + 1.32 * d) / 2
    thickness = 0.022 + 0.1 * d
    hub = 0.05 + 0.15 * d
    r_hub = r_pipe + 0.012 + 0.05 * d
    bolts = 4 if dn <= 80 else 8 if dn <= 200 else 12 if dn <= 350 else 16 if dn <= 450 else 20
    nut = min(0.012 + 0.03 * d, 0.45 * (radius - r_hub))
    circle = (radius + r_hub) / 2 + 0.002
    gap = 0.006 + 0.01 * d
    return {
        "r_pipe": r_pipe,
        "radius": radius,
        "thickness": thickness,
        "hub": hub,
        "r_hub": r_hub,
        "bolts": bolts,
        "nut": nut,
        "circle": circle,
        "gap": gap,
        "sides": 24 if dn >= 150 else 16 if dn >= 50 else 12,
    }


def axis_frame(axis):
    """Rotación local → modelo con el eje Z local según 'axis' (mismas fases que basis)."""
    d, u, v = basis(axis)
    return tuple(tuple(round(float(c), 6) + 0.0 for c in row) for row in np.column_stack((u, v, d)))


def _flange_half(steel, dn, sides, cast):
    f = flange_size(dn)
    start = -(f["gap"] / 2 + f["thickness"] + f["hub"])
    profile = (
        (0.0, f["r_pipe"]),
        (f["hub"], f["r_hub"]),
        (f["hub"], f["radius"]),
        (f["hub"] + f["thickness"], f["radius"]),
    )
    lathe(
        steel,
        (0.0, 0.0, start),
        Z_AXIS,
        # Una brida fundida con el cuerpo (válvulas) no tiene cuello: empieza en el disco.
        profile[1:] if cast else profile,
        sides,
        # La cara de junta queda siempre contra la junta, una ciega u otra brida.
        caps=(False, False),
    )
    return f


def flange_half(steel, joint, axis, dn, *, sides=None, cast=False):
    """Brida con cuello que llega por -axis y cuya cara queda junto al plano de junta."""
    sides = sides or flange_size(dn)["sides"]
    return mapped(
        f"brida:{dn}:{sides}{':f' if cast else ''}",
        [steel],
        joint,
        axis_frame(axis),
        lambda s: _flange_half(s, dn, sides, cast),
    )


def gasket_sides(sides: int) -> int:
    """La junta asoma solo como una línea oscura entre bridas: basta con menos lados."""
    return 16 if sides > 16 else 12


def gasket(junta, joint, axis, dn, *, sides=None):
    sides = gasket_sides(sides or flange_size(dn)["sides"])
    f = flange_size(dn)

    def build(j):
        tube(
            j,
            (0, 0, -f["gap"] / 2),
            (0, 0, f["gap"] / 2),
            f["radius"] - 0.006,
            sides,
            caps=(False, False),
        )

    mapped(f"junta:{dn}:{sides}", [junta], joint, axis_frame(axis), build)


def _bolt_ring(steel, dn, extra):
    f = flange_size(dn)
    length = 2 * f["thickness"] + f["gap"] + 2.4 * f["nut"] + extra
    for i in range(f["bolts"]):
        a = (i + 0.5) * tau / f["bolts"]
        bolt(steel, (f["circle"] * cos(a), f["circle"] * sin(a), 0.0), Z_AXIS, f["nut"], length)
    return f["bolts"]


def bolt_ring(steel, joint, axis, dn, *, extra=0.0):
    """Espárragos de una unión: atraviesan las dos bridas y asoman las tuercas."""
    return mapped(
        f"pernos:{dn}:{extra:.3f}",
        [steel],
        joint,
        axis_frame(axis),
        lambda s: _bolt_ring(s, dn, extra),
    )


def flange_joint(steel, junta, joint, axis, dn, *, sides=None, near=True, far=True, cast=False):
    """Unión bridada completa en el plano 'joint'. 'near' dibuja la brida que llega por
    -axis y 'far' la que sale por +axis ('cast': fundida con un cuerpo de válvula).
    Devuelve el número de espárragos."""
    sides = sides or flange_size(dn)["sides"]

    def build(s, j):
        if near:
            flange_half(s, ORIGIN, Z_AXIS, dn, sides=sides)
        if far:
            flange_half(s, ORIGIN, (0.0, 0.0, -1.0), dn, sides=sides, cast=cast)
        gasket(j, ORIGIN, Z_AXIS, dn, sides=sides)
        return bolt_ring(s, ORIGIN, Z_AXIS, dn)

    key = f"union:{dn}:{sides}:{int(near)}{int(far)}{'f' if cast else ''}"
    return mapped(key, [steel, junta], joint, axis_frame(axis), build)


def blind_flange(steel, junta, joint, axis, dn, *, sides=None):
    """Brida ciega atornillada sobre una brida con cuello que llega por -axis."""
    sides = sides or flange_size(dn)["sides"]
    f = flange_size(dn)

    def build(s, j):
        flange_half(s, ORIGIN, Z_AXIS, dn, sides=sides)
        gasket(j, ORIGIN, Z_AXIS, dn, sides=sides)
        tube(s, (0, 0, f["gap"] / 2), (0, 0, f["gap"] / 2 + f["thickness"]), f["radius"], sides)
        return bolt_ring(s, ORIGIN, Z_AXIS, dn)

    return mapped(f"ciega:{dn}:{sides}", [steel, junta], joint, axis_frame(axis), build)


def handwheel(steel, center, axis, radius, *, rim=None):
    """Volante de maniobra: aro, tres radios y cubo."""
    d, u, v = basis(axis)
    c = vec(center)
    wire = rim or max(0.011, radius * 0.07)
    torus(steel, c, d, radius, wire, 12, 3)
    for k in range(3):
        a = k * tau / 3
        w = cos(a) * u + sin(a) * v
        tube(steel, c, c + w * radius, wire * 0.8, 4, caps=(False, False))
    tube(steel, c - d * wire * 2, c + d * wire * 2, max(0.02, radius * 0.16), 6)


def body_sides(sides: int) -> int:
    """Cuerpos fundidos de válvula: 16 lados bastan junto a bridas de 24."""
    return min(sides, 16)


# Extremos de una válvula bridada: "full" (brida de tubería, junta, pernos y brida fundida),
# "mate" (se atornilla a una brida que ya dibuja otro: junta, pernos y brida fundida) y
# "bare" (solo la brida fundida: los pernos los pone una pieza intercalada, como una wafer).
VALVE_ENDS = ("full", "mate", "bare")


def valve_joints(steel, junta, length, dn, sides, ends=("full", "full")):
    """Las dos uniones de una válvula bridada de eje X local. Devuelve los espárragos."""
    bolts = 0
    for side, end in zip((-1, 1), ends):
        joint = (side * length / 2, 0.0, 0.0)
        if end == "bare":
            flange_half(steel, joint, (float(side), 0.0, 0.0), dn, sides=sides, cast=True)
            continue
        flange_joint(
            steel,
            junta,
            joint,
            (-float(side), 0.0, 0.0),
            dn,
            sides=sides,
            near=end == "full",
            cast=True,
        )
        bolts += flange_size(dn)["bolts"]
    return bolts


def _gate_valve(steel, wheel, junta, dn, sides, ends):
    f = flange_size(dn)
    d = vec(X_AXIS)
    s = vec(Z_AXIS)
    r = f["r_pipe"]
    length = max(0.32, 1.25 * dn / 1000 + 0.2)
    half = length / 2
    body_r = r * 1.18 + 0.02
    lathe(
        steel,
        -d * (half - f["thickness"]),
        d,
        (
            (0.0, f["r_hub"]),
            (0.05 * length, body_r),
            (length - 2 * f["thickness"] - 0.05 * length, body_r),
            (length - 2 * f["thickness"], f["r_hub"]),
        ),
        body_sides(sides),
        caps=(False, False),
    )
    bolts = valve_joints(steel, junta, length, dn, sides, ends)
    # Castillete con brida, columna y volante.
    neck = r * 1.05 + 0.05
    bonnet_top = s * (body_r + 0.45 * dn / 1000 + 0.18)
    tube(steel, s * body_r * 0.6, bonnet_top, neck * 0.55, 12)
    tube(steel, s * (body_r + 0.02), s * (body_r + 0.06), neck * 0.75, 12)
    yoke_top = bonnet_top + s * (0.25 + 0.4 * dn / 1000)
    side_axis = vec((0.0, 1.0, 0.0))
    for k in (-1, 1):
        beam(
            steel,
            bonnet_top + side_axis * k * neck * 0.35,
            yoke_top + side_axis * k * neck * 0.25,
            0.03,
            0.03,
            d,
        )
    beam(steel, yoke_top - side_axis * neck * 0.3, yoke_top + side_axis * neck * 0.3, 0.05, 0.05, d)
    tube(steel, bonnet_top, yoke_top + s * 0.12, 0.014, 6)
    wheel_r = min(0.42, 0.12 + 0.55 * dn / 1000)
    handwheel(wheel, yoke_top + s * 0.06, s, wheel_r)
    return bolts, length


def gate_valve(
    steel, wheel, junta, center, axis, dn, *, stem=UP, sides=None, ends=("full", "full")
):
    """Válvula de compuerta bridada: cuerpo, dos uniones, castillete, vástago y volante.
    'ends' dice qué lleva cada extremo (-axis, +axis), ver VALVE_ENDS.
    Devuelve (espárragos, distancia entre caras)."""
    sides = sides or flange_size(dn)["sides"]
    if any(end not in VALVE_ENDS for end in ends):
        raise ValueError(f"Extremo de válvula no válido: {ends}")
    suffix = "" if ends == ("full", "full") else ":" + "-".join(ends)
    return mapped(
        f"compuerta:{dn}:{sides}{suffix}",
        [steel, wheel, junta],
        center,
        frame_axes(axis, stem),
        lambda s, w, j: _gate_valve(s, w, j, dn, sides, tuple(ends)),
    )


def _butterfly_valve(steel, wheel, junta, dn, sides):
    f = flange_size(dn)
    d = vec(X_AXIS)
    s = vec(Z_AXIS)
    width = 0.06 + 0.12 * dn / 1000
    flange_half(steel, -d * width / 2, d, dn, sides=sides)
    flange_half(steel, d * width / 2, -d, dn, sides=sides)
    tube(steel, -d * width / 2, d * width / 2, f["circle"] - f["nut"] * 1.1, body_sides(sides))
    for side in (-1, 1):
        gasket(junta, side * d * width / 2, d, dn, sides=sides)
    bolts = bolt_ring(steel, ORIGIN, d, dn, extra=width)
    body_top = s * (f["circle"] - f["nut"])
    tube(steel, body_top - s * 0.02, body_top + s * 0.16, 0.05 + 0.04 * dn / 1000, 12)
    gear = body_top + s * 0.27
    oriented_box(steel, gear, (vec((0.0, 1.0, 0.0)), -d, s), (0.11 + 0.05 * dn / 1000, 0.1, 0.11))
    side_axis = vec((0.0, 1.0, 0.0))
    shaft_end = gear + side_axis * 0.32
    tube(steel, gear, shaft_end, 0.02, 6)
    handwheel(wheel, shaft_end, side_axis, min(0.35, 0.16 + 0.3 * dn / 1000))
    return bolts, width


def butterfly_valve(steel, wheel, junta, center, axis, dn, *, operator=UP, sides=None):
    """Válvula de mariposa tipo wafer entre bridas, con reductor y volante."""
    sides = sides or flange_size(dn)["sides"]
    return mapped(
        f"mariposa:{dn}:{sides}",
        [steel, wheel, junta],
        center,
        frame_axes(axis, operator),
        lambda s, w, j: _butterfly_valve(s, w, j, dn, sides),
    )


def _ball_valve(steel, actuator, junta, dn, sides):
    f = flange_size(dn)
    d = vec(X_AXIS)
    s = vec(Z_AXIS)
    length = max(0.36, 1.3 * dn / 1000 + 0.22)
    half = length / 2
    body_r = f["r_pipe"] * 1.35 + 0.03
    lathe(
        steel,
        -d * (half - f["thickness"]),
        d,
        (
            (0.0, f["r_hub"]),
            (0.18 * length, body_r * 0.92),
            (0.5 * length - f["thickness"], body_r),
            (length - 2 * f["thickness"] - 0.18 * length, body_r * 0.92),
            (length - 2 * f["thickness"], f["r_hub"]),
        ),
        body_sides(sides),
        caps=(False, False),
    )
    bolts = valve_joints(steel, junta, length, dn, sides)
    top = s * (body_r + 0.12)
    tube(steel, s * body_r * 0.8, top, 0.06 + 0.05 * dn / 1000, 12)
    housing = top + s * 0.14
    box(actuator, housing, (0.34, 0.3, 0.26))
    cyl = 0.12 + 0.12 * dn / 1000
    side_axis = vec((0.0, 1.0, 0.0))
    tube(
        actuator,
        housing - side_axis * 0.12,
        housing + side_axis * (0.55 + 0.6 * dn / 1000),
        cyl,
        12,
    )
    tube(actuator, housing - side_axis * 0.22, housing - side_axis * 0.12, cyl * 0.75, 12)
    return bolts, length


def actuated_ball_valve(steel, actuator, junta, center, axis, dn, *, stem=UP, sides=None):
    """Válvula de bola con actuador neumático de yugo escocés (corte de emergencia)."""
    sides = sides or flange_size(dn)["sides"]
    return mapped(
        f"bola:{dn}:{sides}",
        [steel, actuator, junta],
        center,
        frame_axes(axis, stem),
        lambda s, a, j: _ball_valve(s, a, j, dn, sides),
    )


# --- Accesos: escalas, barandillas, plataformas y escaleras -------------------------------


def ladder(rails, cage, bottom, top_z, outward, *, width=0.46, cage_from=2.3, extend=1.05):
    """Escala de gato vertical con largueros, peldaños y jaula de aros.

    'bottom' es el punto central al pie y 'outward' la dirección hacia el usuario (horizontal).
    Devuelve el número de peldaños.
    """
    b = vec(bottom)
    n = unit((outward[0], outward[1], 0.0))
    side = np.cross(UP, n)
    height = top_z - b[2]
    upper = height + extend
    for k in (-1, 1):
        p = b + side * k * width / 2
        beam(rails, p, p + vec(UP) * upper, 0.012, 0.065, n)
    rungs = max(1, int(height / 0.3))
    for i in range(1, rungs + 1):
        z = b[2] + height * i / (rungs + 0.25)
        p = vec((b[0], b[1], z))
        # Peldaño de redondo: los extremos quedan dentro de los largueros.
        tube(
            rails,
            p - side * width / 2,
            p + side * width / 2,
            0.014,
            4,
            phase=pi / 4,
            caps=(False, False),
        )
    if height > cage_from + 0.6:
        # Aro de jaula de 0,72 m que nace en los largueros y abraza la escala por fuera.
        hoop_r = 0.36
        half_width = width / 2 + 0.02
        offset = sqrt(hoop_r**2 - half_width**2)
        center = b + n * offset
        reach = pi - np.arctan2(half_width, offset)
        heading = float(np.arctan2(n[1], n[0]))
        hoops = max(2, int((upper - cage_from) / 0.9) + 1)
        for i in range(hoops):
            z = b[2] + cage_from + (upper - cage_from - 0.1) * i / (hoops - 1)
            # Aro de pletina 50 × 8: cinta de dos caras.
            revolve(
                cage,
                (center[0], center[1], z),
                UP,
                ((hoop_r, -0.025), (hoop_r, 0.025)),
                heading - reach,
                heading + reach,
                10,
                caps=False,
                outline=True,
            )
        for k in range(5):
            a = heading - reach * 0.8 + 1.6 * reach * k / 4
            w = vec((cos(a), sin(a), 0.0))
            p = center + w * (hoop_r + 0.004)
            t = np.cross(UP, w) * 0.025
            z0, z1 = b[2] + cage_from, b[2] + upper - 0.1
            quad(
                cage,
                (
                    vec((p[0], p[1], z0)) - t,
                    vec((p[0], p[1], z0)) + t,
                    vec((p[0], p[1], z1)) + t,
                    vec((p[0], p[1], z1)) - t,
                ),
            )
    return rungs


def railing(
    posts_mesh, rails_mesh, points, *, height=1.1, closed=False, spacing=1.8, toe=True, post=0.05
):
    """Barandilla industrial: postes, pasamanos, barra intermedia y rodapié.

    'points' es la poligonal a nivel de piso. Devuelve (longitud, postes)."""
    pts = [vec(p) for p in points]
    if closed:
        pts.append(pts[0])
    length = 0.0
    posts = []
    for a, b in zip(pts, pts[1:]):
        span = float(np.linalg.norm(b - a))
        if span < 1e-6:
            continue
        length += span
        count = max(1, ceil(span / spacing))
        posts.extend(a + (b - a) * i / count for i in range(count))
    if not closed:
        posts.append(pts[-1])
    for p in posts:
        tube(
            posts_mesh, p, p + vec((0, 0, height)), post * 0.7, 4, phase=pi / 4, caps=(False, True)
        )
    for a, b in zip(pts, pts[1:]):
        if np.linalg.norm(b - a) < 1e-6:
            continue
        # Pasamanos y barra intermedia corridos (sin tapas) y rodapié de chapa.
        for h in (height - 0.02, height * 0.52):
            tube(
                rails_mesh,
                a + vec((0, 0, h)),
                b + vec((0, 0, h)),
                0.021,
                6,
                phase=pi / 6,
                caps=(False, False),
            )
        if toe:
            quad(
                rails_mesh,
                (
                    a + vec((0, 0, 0.0)),
                    b + vec((0, 0, 0.0)),
                    b + vec((0, 0, 0.1)),
                    a + vec((0, 0, 0.1)),
                ),
            )
    return length, len(posts)


def grating_deck(grating, frame, center, size, *, plate=0.035):
    """Piso de rejilla rectangular con cerco perimetral. 'center' es la cara superior."""
    x, y, z = center
    w, d = size
    box(grating, (x, y, z - plate / 2), (w - 0.02, d - 0.02, plate))
    for k in (-1, 1):
        box(frame, (x, y + k * (d / 2 - 0.04), z - 0.09), (w, 0.08, 0.18))
        box(frame, (x + k * (w / 2 - 0.04), y, z - 0.09), (0.08, d - 0.16, 0.18))


def sector_deck(grating, frame, center, r_in, r_out, start, end, *, plate=0.035, segments=None):
    """Piso anular de una plataforma circular (rejilla y cerco exterior). 'center' en la
    cara superior, sobre el eje del recipiente."""
    span = end - start
    segments = segments or max(4, ceil(span / (pi / 12)))
    revolve(
        grating,
        center,
        UP,
        ((r_in, -plate), (r_out, -plate), (r_out, 0.0), (r_in, 0.0)),
        start,
        end,
        segments,
    )
    revolve(
        frame,
        vec(center) - vec((0, 0, plate)),
        UP,
        ((r_out - 0.012, -0.16), (r_out, -0.16), (r_out, 0.0), (r_out - 0.012, 0.0)),
        start,
        end,
        segments,
    )


def stair_flight(stringers, treads, rails_posts, rails, a, b, *, width=0.9, rails_both=True):
    """Tramo recto de escalera de a (pie) a b (desembarco), ambos en el eje y a nivel de piso.
    Devuelve (peldaños, longitud en planta)."""
    a, b = vec(a), vec(b)
    rise = b[2] - a[2]
    run_vec = vec((b[0] - a[0], b[1] - a[1], 0.0))
    run = float(np.linalg.norm(run_vec))
    n = unit(run_vec)
    side = np.cross(UP, n)
    steps = max(2, round(rise / 0.2))
    for k in (-1, 1):
        off = side * k * (width / 2 + 0.02)
        beam(stringers, a + off + vec((0, 0, -0.1)), b + off + vec((0, 0, -0.1)), 0.012, 0.22, UP)
    for i in range(1, steps):
        p = a + (b - a) * i / steps - vec((0, 0, 0.02))
        oriented_box(treads, p, (n, side, vec(UP)), (0.13, width / 2, 0.0175), faces=SLAT_FACES)
    for k in (-1, 1) if rails_both else (1,):
        off = side * k * (width / 2 + 0.05)
        pa, pb = a + off, b + off
        posts = max(2, ceil(run / 1.6) + 1)
        for i in range(posts):
            p = pa + (pb - pa) * i / (posts - 1)
            box(rails_posts, (p[0], p[1], p[2] + 0.5), (0.045, 0.045, 1.0))
        for h in (1.0, 0.52):
            tube(rails, pa + vec((0, 0, h)), pb + vec((0, 0, h)), 0.021, 6, phase=pi / 6)
    return steps, run


IDENTITY = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def anchor_bolts(steel, points, *, radius=0.022, height=0.09):
    """Tuercas y arandelas de pernos de anclaje sobre una placa (puntos de la cara superior)."""

    def build(s):
        # Tuerca hexagonal apoyada en la placa, abierta como el taladro roscado.
        tube(s, ORIGIN, (0, 0, height), radius, 6, phase=pi / 6, caps=(False, False))

    for p in points:
        mapped(f"anclaje:{radius:.3f}:{height:.3f}", [steel], p, IDENTITY, build)
    return len(points)


def motor(body, cowl, accessories, a, b, radius, *, fins=24, feet_z=None):
    """Motor eléctrico TEFC: carcasa con aletas axiales, escudos, tapa del ventilador,
    caja de bornas, patas y eje. 'a' es el lado de accionamiento. Los motores horizontales
    iguales comparten plantilla."""
    a, b = vec(a), vec(b)
    d = unit(b - a)
    if abs(d[2]) > 0.9:
        return _motor(body, cowl, accessories, a, b, radius, fins=fins, feet_z=feet_z)
    length = float(np.linalg.norm(b - a))
    drop = None if feet_z is None else round(float(a[2] - feet_z), 3)
    key = f"motor:{length:.3f}:{radius:.3f}:{fins}:{drop}"
    return mapped(
        key,
        [body, cowl, accessories],
        a,
        frame_axes(d, UP),
        lambda m, c, x: _motor(
            m,
            c,
            x,
            ORIGIN,
            (length, 0.0, 0.0),
            radius,
            fins=fins,
            feet_z=None if drop is None else -drop,
        ),
    )


def _motor(body, cowl, accessories, a, b, radius, *, fins=24, feet_z=None):
    a, b = vec(a), vec(b)
    d = unit(b - a)
    length = float(np.linalg.norm(b - a))
    _, u, v = basis(d)
    shield = 0.06 * length
    cowl_len = 0.16 * length
    core = length - shield - cowl_len
    star = []
    for i in range(fins * 2):
        ang = pi * i / fins
        r = radius if i % 2 == 0 else radius * 0.9
        star.append((r * cos(ang), r * sin(ang)))
    extrude(body, a + d * shield, d, star, core - shield)
    lathe(
        body,
        a,
        d,
        ((0.0, radius * 0.55), (shield * 0.5, radius * 0.88), (shield, radius * 0.9)),
        24,
        caps=(True, False),
    )
    lathe(
        body,
        a + d * (core),
        d,
        ((0.0, radius * 0.9), (shield, radius * 0.9), (shield, radius * 0.97)),
        24,
        caps=(False, False),
    )
    lathe(
        cowl,
        a + d * (core + shield),
        d,
        (
            (0.0, radius * 0.97),
            (cowl_len - shield - 0.02, radius * 0.97),
            (cowl_len - shield, radius * 0.82),
            (cowl_len - shield + 0.005, radius * 0.5),
        ),
        24,
        caps=(True, True),
    )
    tube(accessories, a - d * (0.12 + 0.2 * radius), a + d * 0.01, max(0.03, radius * 0.16), 12)
    top = vec(UP) if abs(d[2]) < 0.9 else u
    box_center = a + d * (core * 0.45) + top * (radius + 0.11)
    oriented_box(
        accessories,
        box_center,
        frame_along(box_center - d, box_center, top),
        (radius * 0.32, radius * 0.38, 0.11),
    )
    if feet_z is not None and abs(d[2]) < 0.9:
        side = np.cross(UP, d)
        for t in (0.2, 0.75):
            p = a + d * (length * t)
            for k in (-1, 1):
                q = p + side * k * radius * 0.7
                box(
                    body,
                    (q[0], q[1], (feet_z + p[2]) / 2),
                    (0.12, 0.1 + radius * 0.25, p[2] - feet_z),
                )
    return fins
