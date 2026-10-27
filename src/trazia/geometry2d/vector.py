"""Geometría de un GA vectorial desde sus trazos (DEC-07): sin leer ningún texto.

Coordenadas en puntos de PDF con el origen arriba a la izquierda (como pdfplumber).

- Virola: el rectángulo con dos curvas (los fondos) apoyadas en sus bordes superior e inferior.
- Fondos: flecha = 0,75 · (inicio − control) de la Bézier cúbica simétrica que los dibuja.
- Faldón: patas bajo la virola; su parte inferior es el suelo (Z = 0).
- Boquillas del alzado: pares de líneas paralelas que salen del borde de la virola (el cuello),
  o círculos dentro de la virola (boquillas de frente). Su eje da la cota.
- Planta: la circunferencia mayor; cada muñón es un par de líneas radiales: su ángulo da la
  orientación, su largo el saliente y su separación el diámetro nominal.
"""

import math
from dataclasses import dataclass, field

TOL = 0.6  # pt


@dataclass
class ElevationStub:
    side: int  # +1 derecha, −1 izquierda, 0 de frente (círculo)
    z: float  # eje de la boquilla (pt, hacia abajo)
    neck: float  # radio del cuello (pt)
    end: tuple[float, float]  # extremo exterior, donde va la etiqueta


@dataclass
class Elevation:
    shell: tuple[float, float, float, float]  # x0, top, x1, bottom
    head_top: float  # flecha del fondo superior (pt)
    head_bottom: float
    ground: float  # y del suelo
    stubs: list[ElevationStub] = field(default_factory=list)

    @property
    def width(self) -> float:
        return self.shell[2] - self.shell[0]

    @property
    def shell_height(self) -> float:
        return self.shell[3] - self.shell[1]

    @property
    def skirt(self) -> float:
        return self.ground - self.shell[3]

    @property
    def overall(self) -> float:
        return self.ground - (self.shell[1] - self.head_top)


@dataclass
class PlanStub:
    angle: float  # grados, antihorario desde +X
    length: float  # saliente (pt)
    neck: float  # radio del cuello (pt)
    end: tuple[float, float]


@dataclass
class Plan:
    center: tuple[float, float]
    radius: float
    stubs: list[PlanStub] = field(default_factory=list)


def _horizontal(line) -> bool:
    return abs(line["top"] - line["bottom"]) < 0.01 and line["x1"] - line["x0"] > 0.5


def _cubic_depth(curve) -> float | None:
    for op in curve.get("path") or []:
        if op[0] == "c":
            start_y = curve["pts"][0][1]
            control_y = op[1][1]
            return 0.75 * abs(start_y - control_y)
    return None


def find_elevation(page) -> Elevation | None:
    rects = [r for r in page.rects if r["width"] > 5 and r["height"] > 5]
    curves = page.curves
    best = None
    for r in rects:
        attached = [
            c
            for c in curves
            if abs(c["x0"] - r["x0"]) < TOL
            and abs(c["x1"] - r["x1"]) < TOL
            and (abs(c["top"] - r["top"]) < TOL or abs(c["bottom"] - r["bottom"]) < TOL)
        ]
        if len(attached) >= 2 and (best is None or r["height"] * r["width"] > best[0]):
            best = (r["height"] * r["width"], r, attached)
    if best is None:
        return None
    _, shell, heads = best
    top = next((c for c in heads if abs(c["top"] - shell["top"]) < TOL), None)
    bottom = next((c for c in heads if abs(c["bottom"] - shell["bottom"]) < TOL), None)
    head_top = _cubic_depth(top) if top else None
    head_bottom = _cubic_depth(bottom) if bottom else None
    legs = [
        r
        for r in page.rects
        if r is not shell
        and abs(r["top"] - shell["bottom"]) < TOL
        and r["x0"] >= shell["x0"] - TOL
        and r["x1"] <= shell["x1"] + TOL
    ]
    if not legs or head_top is None:
        return None
    ground = max(r["bottom"] for r in legs)
    geom = Elevation(
        shell=(shell["x0"], shell["top"], shell["x1"], shell["bottom"]),
        head_top=head_top,
        head_bottom=head_bottom or head_top,
        ground=ground,
    )
    geom.stubs = _elevation_stubs(page, geom) + _front_nozzles(page, geom)
    return geom


def _elevation_stubs(page, geom: Elevation) -> list[ElevationStub]:
    x0, top, x1, bottom = geom.shell
    lines = [ln for ln in page.lines if _horizontal(ln) and top - 1 < ln["top"] < bottom + 1]
    out: list[ElevationStub] = []
    for side, edge in ((1, x1), (-1, x0)):
        own = [
            ln
            for ln in lines
            if (side == 1 and abs(ln["x0"] - edge) < TOL and ln["x1"] - edge < 80)
            or (side == -1 and abs(ln["x1"] - edge) < TOL and edge - ln["x0"] < 80)
        ]
        own.sort(key=lambda ln: ln["top"])
        used: set[int] = set()
        for i, a in enumerate(own):
            if i in used:
                continue
            for j in range(i + 1, len(own)):
                b = own[j]
                same_reach = abs((a["x1"] - a["x0"]) - (b["x1"] - b["x0"])) < TOL
                if j not in used and same_reach and 0 < b["top"] - a["top"] < 20:
                    used |= {i, j}
                    end_x = a["x1"] if side == 1 else a["x0"]
                    z = (a["top"] + b["top"]) / 2
                    out.append(ElevationStub(side, z, (b["top"] - a["top"]) / 2, (end_x, z)))
                    break
    return out


def _front_nozzles(page, geom: Elevation) -> list[ElevationStub]:
    x0, top, x1, bottom = geom.shell
    out = []
    for c in page.curves:
        w, h = c["x1"] - c["x0"], c["bottom"] - c["top"]
        cx, cy = (c["x0"] + c["x1"]) / 2, (c["top"] + c["bottom"]) / 2
        if 0 < w < geom.width / 2 and abs(w - h) < TOL and x0 < cx < x1 and top < cy < bottom:
            out.append(ElevationStub(0, cy, w / 2, (c["x1"], cy)))
    return out


def find_plan(page, exclude: tuple[float, float, float, float] | None = None) -> Plan | None:
    circles = [
        c
        for c in page.curves
        if c["x1"] - c["x0"] > 40 and abs((c["x1"] - c["x0"]) - (c["bottom"] - c["top"])) < TOL
    ]
    if exclude:
        circles = [c for c in circles if not (exclude[0] <= c["x0"] <= exclude[2])]
    if not circles:
        return None
    circle = max(circles, key=lambda c: c["x1"] - c["x0"])
    cx, cy = (circle["x0"] + circle["x1"]) / 2, (circle["top"] + circle["bottom"]) / 2
    r = (circle["x1"] - circle["x0"]) / 2
    radial = []
    for ln in page.lines:
        (ax, ay), (bx, by) = (ln["x0"], ln["top"]), (ln["x1"], ln["bottom"])
        # pdfplumber ordena x0 < x1: hay que recuperar los extremos reales del segmento.
        pts = ln.get("pts") or [(ax, ay), (bx, by)]
        (ax, ay), (bx, by) = pts[0], pts[-1]
        da, db = math.hypot(ax - cx, ay - cy), math.hypot(bx - cx, by - cy)
        near, far = ((ax, ay), (bx, by)) if da < db else ((bx, by), (ax, ay))
        d_near, d_far = min(da, db), max(da, db)
        if abs(d_near - r) > 3 or d_far - d_near < 2 or d_far > r + 200:
            continue
        direction = math.atan2(far[1] - near[1], far[0] - near[0])
        radial_angle = math.atan2(near[1] - cy, near[0] - cx)
        if abs(math.sin(direction - radial_angle)) > 0.2:
            continue  # no es radial
        radial.append((near, far, d_far))
    stubs: list[PlanStub] = []
    used: set[int] = set()
    for i, (n1, f1, d1) in enumerate(radial):
        if i in used:
            continue
        for j in range(i + 1, len(radial)):
            n2, f2, d2 = radial[j]
            if j in used or abs(d1 - d2) > TOL:
                continue
            gap = math.hypot(n1[0] - n2[0], n1[1] - n2[1])
            if gap > 30:
                continue
            used |= {i, j}
            mx, my = (f1[0] + f2[0]) / 2, (f1[1] + f2[1]) / 2
            angle = math.degrees(math.atan2(-(my - cy), mx - cx)) % 360  # y del PDF hacia abajo
            length = math.hypot(mx - cx, my - cy) - r
            stubs.append(PlanStub(angle, length, gap / 2, (mx, my)))
            break
    return Plan((cx, cy), r, stubs)
