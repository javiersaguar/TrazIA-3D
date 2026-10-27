"""Geometría de un GA escaneado con OpenCV (DEC-07): mismas estructuras que `vector`, en puntos.

Pasos:
1. Binarizar (Otsu) y enderezar: el giro del escaneo se mide con las líneas largas del marco.
2. Virola: el par de verticales largas unidas por arriba y por abajo (una cota no lo está).
3. Fondo superior: la cúpula más alta junto al eje (sin la columna del eje, que es discontinuo).
4. Suelo: la línea horizontal larga bajo la virola; el faldón va de la virola al suelo.
5. Boquillas del alzado: trazos horizontales que salen de los laterales; el cuello son dos líneas.
6. Planta: circunferencia por Hough; los muñones cruzan un anillo exterior con dos trazos cada uno.

La precisión depende de la resolución y del escaneo: es una medida, no una lectura.
"""

import math

import numpy as np

from .vector import Elevation, ElevationStub, Plan, PlanStub


def _cv():
    import cv2  # opencv-python-headless (Apache-2.0)

    return cv2


def binarize(image, *, with_angle: bool = False):
    """Imagen PIL → máscara de tinta (True = trazo), enderezada. Con `with_angle`, también el
    giro corregido (grados), para devolver puntos al marco original con `unrotate`."""
    cv2 = _cv()
    gray = np.array(image.convert("L"))
    _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    angle = _skew(ink)
    if abs(angle) > 0.05:
        h, w = ink.shape
        matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        ink = cv2.warpAffine(ink, matrix, (w, h), flags=cv2.INTER_NEAREST, borderValue=0)
    else:
        angle = 0.0
    return (ink > 0, angle) if with_angle else ink > 0


def unrotate(point, angle: float, shape) -> tuple[float, float]:
    """Punto del marco enderezado → marco original de la página (mismas unidades)."""
    if not angle:
        return point
    h, w = shape
    cx, cy = w / 2, h / 2
    a = math.radians(angle)  # warpAffine giró la imagen +angle; se deshace con −angle
    x, y = point[0] - cx, point[1] - cy
    return (cx + x * math.cos(a) - y * math.sin(a), cy + x * math.sin(a) + y * math.cos(a))


def _skew(ink: np.ndarray) -> float:
    """Giro en grados medido con las líneas casi horizontales más largas (marco y cajetín)."""
    cv2 = _cv()
    h, w = ink.shape
    lines = cv2.HoughLinesP(ink, 1, np.pi / 1800, threshold=200, minLineLength=w // 3, maxLineGap=8)
    if lines is None:
        return 0.0
    angles = []
    for x0, y0, x1, y1 in lines[:, 0]:
        a = math.degrees(math.atan2(y1 - y0, x1 - x0))
        if abs(a) < 3:
            angles.append(a)
    return float(np.median(angles)) if angles else 0.0


def _runs(values: np.ndarray, min_len: int = 1) -> list[tuple[int, int]]:
    """Tramos consecutivos de True: [(inicio, fin_inclusivo)]."""
    out, start = [], None
    for i, v in enumerate(values):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start >= min_len:
                out.append((start, i - 1))
            start = None
    if start is not None and len(values) - start >= min_len:
        out.append((start, len(values) - 1))
    return out


def _vertical_segments(ink: np.ndarray, min_len: int) -> list[tuple[int, int, int]]:
    """Segmentos verticales largos (x, y0, y1) tras abrir con un núcleo vertical."""
    cv2 = _cv()
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, min_len))
    opened = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_OPEN, kernel)
    count, _, stats, _ = cv2.connectedComponentsWithStats(opened, connectivity=8)
    segments = []
    for i in range(1, count):
        x, y, w, h, _ = stats[i]
        if h >= min_len and w <= 6:
            segments.append((x + w // 2, y, y + h - 1))
    return segments


def find_elevation(ink: np.ndarray, px_per_pt: float) -> Elevation | None:
    h, w = ink.shape
    min_len = int(60 * px_per_pt)
    segments = _vertical_segments(ink, min_len)
    best = None
    for a in segments:
        for b in segments:
            if b[0] - a[0] < 15 * px_per_pt or b[0] - a[0] > 260 * px_per_pt:
                continue
            # Arriba coinciden; abajo un lateral puede seguir en la pata del faldón.
            if abs(a[1] - b[1]) > 6 or abs(a[2] - b[2]) > 20 * px_per_pt:
                continue
            span = slice(a[0] + 2, b[0] - 1)
            y0, y1 = max(a[1], b[1]), min(a[2], b[2])
            # Bordes superior e inferior: filas llenas entre los laterales. El lateral puede
            # seguir en la curva del fondo o en la pata, así que se buscan cerca de cada extremo.
            full = [
                y
                for y in range(y0, y1 + 1)
                if ink[y, span].mean() > 0.8
                or ink[max(0, y - 1) : y + 2, span].any(axis=0).mean() > 0.9
            ]
            if not full:
                continue
            reach = (y1 - y0) * 0.35
            tops = [y for y in full if y <= y0 + reach]
            bottoms = [y for y in full if y >= y1 - reach]
            if not tops or not bottoms:
                continue
            top, bottom = max(tops), min(bottoms)
            if bottom - top < min_len:
                continue
            # Una tabla también es un rectángulo cerrado, pero la cruzan filas; la virola no,
            # y lleva un fondo encima.
            interior = [y for y in full if top + 4 < y < bottom - 4]
            if interior or _dome(ink, a[0], b[0], top, up=True) is None:
                continue
            if best is None or (bottom - top) * (b[0] - a[0]) > best[0]:
                best = ((bottom - top) * (b[0] - a[0]), a[0], top, b[0], bottom)
    if best is None:
        return None
    _, x0, top, x1, bottom = best
    head = _dome(ink, x0, x1, top, up=True)
    ground = _ground(ink, x0, x1, bottom)
    if head is None or ground is None:
        return None
    to_pt = 1 / px_per_pt
    geom = Elevation(
        shell=(x0 * to_pt, top * to_pt, x1 * to_pt, bottom * to_pt),
        head_top=head * to_pt,
        head_bottom=(_dome(ink, x0, x1, bottom, up=False) or head) * to_pt,
        ground=ground * to_pt,
    )
    geom.stubs = _elevation_stubs(ink, x0, x1, top, bottom, px_per_pt)
    return geom


def _dome(ink, x0, x1, edge, *, up: bool) -> float | None:
    """Flecha del fondo: la tinta más lejana del borde cerca del eje, sin la columna del eje."""
    center = (x0 + x1) // 2
    half = max(4, (x1 - x0) // 8)
    limit = int((x1 - x0) * 0.6)
    best = None
    for x in list(range(center - half, center - 3)) + list(range(center + 4, center + half)):
        column = ink[edge - limit : edge - 2, x][::-1] if up else ink[edge + 3 : edge + limit, x]
        hits = np.flatnonzero(column)
        if len(hits):
            depth = hits[0] + (2 if up else 3)
            # la cúpula es el primer trazo; más allá están las cotas o el rótulo del diámetro
            best = depth if best is None else max(best, depth)
    return float(best) if best else None


def _ground(ink, x0, x1, bottom) -> float | None:
    width = x1 - x0
    for y in range(bottom + 6, min(ink.shape[0], bottom + int(width * 6) + 400)):
        row = ink[y - 1 : y + 2, max(0, x0 - width // 2) : x1 + width // 2].any(axis=0)
        runs = _runs(row, min_len=int(width * 1.1))
        if runs:
            return float(y)
    return None


def _elevation_stubs(ink, x0, x1, top, bottom, px_per_pt) -> list[ElevationStub]:
    to_pt = 1 / px_per_pt
    out: list[ElevationStub] = []
    for side, edge in ((1, x1), (-1, x0)):
        probe = edge + side * int(3 * px_per_pt)
        column = ink[top + 6 : bottom - 6, probe]
        runs = [(a + top + 6, b + top + 6) for a, b in _runs(column)]  # filas absolutas
        i = 0
        while i < len(runs):
            a = runs[i]
            pair = None
            if i + 1 < len(runs) and runs[i + 1][0] - a[1] <= 40 * px_per_pt:
                b = runs[i + 1]
                if _stub_reach(ink, a, edge, side) and _stub_reach(ink, b, edge, side):
                    pair = (a, b)
            if pair is None and _stub_reach(ink, a, edge, side) and a[1] - a[0] >= 2:
                pair = (a, a)  # cuello fino: las dos líneas se funden en un solo trazo
            if pair:
                (a0, _), (_, b1) = pair
                z = (a0 + b1) / 2
                neck = max(0.5, ((b1 - a0) / 2 - px_per_pt * 0.35))
                reach = _stub_reach(ink, pair[0], edge, side)
                end_x = edge + side * reach
                out.append(ElevationStub(side, z * to_pt, neck * to_pt, (end_x * to_pt, z * to_pt)))
                i += 1 if pair[0] is pair[1] else 2
            else:
                i += 1
    return out


def _stub_reach(ink, run, edge, side) -> int:
    """Largo del trazo horizontal que sale del lateral (0 si no sale)."""
    y = (run[0] + run[1]) // 2
    reach = 0
    for d in range(1, 400):
        x = edge + side * d
        if x < 0 or x >= ink.shape[1]:
            break
        if ink[max(0, y - 1) : y + 2, x].any():
            reach = d
        elif d - reach > 3:
            break
    return reach if reach > 4 else 0


def find_plan(
    ink: np.ndarray, px_per_pt: float, exclude_x: tuple[float, float] | None
) -> Plan | None:
    cv2 = _cv()
    blurred = cv2.GaussianBlur(ink.astype(np.uint8) * 255, (5, 5), 1.5)
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1.5,
        minDist=200 * px_per_pt,
        param1=120,
        param2=60,
        minRadius=int(25 * px_per_pt),
        maxRadius=int(115 * px_per_pt),
    )
    if circles is None:
        return None
    candidates = []
    for cx, cy, r in circles[0]:
        if exclude_x and exclude_x[0] - 5 <= cx / px_per_pt <= exclude_x[1] + 5:
            continue
        refined = _refine_radius(ink, cx, cy, r)
        candidates.append((_completeness(ink, cx, cy, refined), refined, cx, cy))
    if not candidates:
        return None
    score, r, cx, cy = max(candidates)
    if score < 0.8:
        return None  # ninguna circunferencia dibujada entera: no hay planta
    stubs = _plan_stubs(ink, cx, cy, r, px_per_pt)
    to_pt = 1 / px_per_pt
    return Plan(
        (cx * to_pt, cy * to_pt),
        r * to_pt,
        [
            PlanStub(
                s.angle, s.length * to_pt, s.neck * to_pt, (s.end[0] * to_pt, s.end[1] * to_pt)
            )
            for s in stubs
        ],
    )


def _completeness(ink, cx, cy, r) -> float:
    """Fracción del perímetro con tinta: un círculo dibujado está casi completo."""
    hits = 0
    for k in range(360):
        a = math.radians(k)
        x, y = int(round(cx + r * math.cos(a))), int(round(cy + r * math.sin(a)))
        if 0 <= y < ink.shape[0] and 0 <= x < ink.shape[1]:
            hits += bool(ink[max(0, y - 1) : y + 2, max(0, x - 1) : x + 2].any())
    return hits / 360


def _refine_radius(ink, cx, cy, r) -> float:
    """Radio por la tinta a lo largo de 72 radios (Hough da un radio aproximado)."""
    found = []
    for k in range(72):
        a = 2 * math.pi * k / 72
        for d in np.arange(r - 6, r + 7, 0.5):
            x, y = int(round(cx + d * math.cos(a))), int(round(cy + d * math.sin(a)))
            if 0 <= y < ink.shape[0] and 0 <= x < ink.shape[1] and ink[y, x]:
                found.append(d)
                break
    return float(np.median(found)) if found else float(r)


def _plan_stubs(ink, cx, cy, r, px_per_pt) -> list[PlanStub]:
    ring = r + 4 * px_per_pt
    samples = 3600
    hits = np.zeros(samples, dtype=bool)
    for k in range(samples):
        a = 2 * math.pi * k / samples
        x, y = int(round(cx + ring * math.cos(a))), int(round(cy + ring * math.sin(a)))
        if 0 <= y < ink.shape[0] and 0 <= x < ink.shape[1]:
            hits[k] = ink[y, x]
    runs = _runs(np.concatenate([hits, hits[:200]]))
    runs = [(s, e) for s, e in runs if s < samples]
    out: list[PlanStub] = []
    used: set[int] = set()
    max_gap = int(samples * (40 * px_per_pt) / (2 * math.pi * ring))
    for i, a in enumerate(runs):
        if i in used:
            continue
        for j in range(i + 1, len(runs)):
            b = runs[j]
            if b[0] - a[1] > max_gap:
                break
            ka, kb = (a[0] + a[1]) / 2, (b[0] + b[1]) / 2
            la = _radial_length(ink, cx, cy, r, 2 * math.pi * ka / samples)
            lb = _radial_length(ink, cx, cy, r, 2 * math.pi * kb / samples)
            if la > 3 and lb > 3 and abs(la - lb) <= 3:
                used |= {i, j}
                mid = 2 * math.pi * ((ka + kb) / 2) / samples
                neck = ring * math.sin((kb - ka) / samples * math.pi)
                length = (la + lb) / 2
                end = (cx + (r + length) * math.cos(mid), cy + (r + length) * math.sin(mid))
                angle = math.degrees(-mid) % 360  # y de la imagen hacia abajo
                out.append(PlanStub(angle, length, max(0.5, neck - 0.35 * px_per_pt), end))
                break
    return out


def _radial_length(ink, cx, cy, r, a) -> float:
    reach = 0.0
    for d in np.arange(1, 300, 0.5):
        x = int(round(cx + (r + d) * math.cos(a)))
        y = int(round(cy + (r + d) * math.sin(a)))
        if not (0 <= y < ink.shape[0] and 0 <= x < ink.shape[1]):
            break
        if ink[max(0, y - 2) : y + 3, max(0, x - 2) : x + 3].any():
            reach = d
        elif d - reach > 3:
            break
    return reach
