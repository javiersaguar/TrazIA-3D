"""Métricas puras, sin E/S. Unidades: mm y grados."""

import math
from statistics import fmean

LENGTH_TOLERANCE_MM = 0.5
ANGLE_TOLERANCE_DEG = 0.5


def same_value(predicted: float | str, expected: float | str, unit: str) -> bool:
    if isinstance(expected, str) or isinstance(predicted, str):
        return str(predicted).strip().upper() == str(expected).strip().upper()
    if unit == "deg":
        return angle_error(float(predicted), float(expected)) <= ANGLE_TOLERANCE_DEG
    return abs(float(predicted) - float(expected)) <= LENGTH_TOLERANCE_MM


def angle_error(a: float, b: float) -> float:
    d = abs(a - b) % 360
    return min(d, 360 - d)


def nozzle_face_center(vessel_diameter: float, elevation: float, azimuth: float, projection: float):
    """Centro de la cara de la boquilla, con el mismo convenio que trazia.ifc (azimut desde +X)."""
    radius = vessel_diameter / 2 + projection
    a = math.radians(azimuth)
    return (radius * math.cos(a), radius * math.sin(a), elevation)


def distance(p, q) -> float:
    return math.dist(p, q)


def prf(tp: int, fp: int, fn: int) -> dict:
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else None
    )
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1}


def ece(pairs: list[tuple[float, bool]], bins: int = 10) -> float | None:
    """Error de calibración esperado: |acierto − confianza| ponderado por bin."""
    if not pairs:
        return None
    total = len(pairs)
    error = 0.0
    for b in range(bins):
        low, high = b / bins, (b + 1) / bins
        group = [(c, ok) for c, ok in pairs if low <= c < high or (b == bins - 1 and c == 1.0)]
        if not group:
            continue
        confidence = fmean(c for c, _ in group)
        accuracy = fmean(1.0 if ok else 0.0 for _, ok in group)
        error += len(group) / total * abs(accuracy - confidence)
    return error


def reliability(pairs: list[tuple[float, bool]], bins: int = 10) -> list[dict]:
    """Puntos del diagrama de fiabilidad (para la pantalla Bench)."""
    out = []
    for b in range(bins):
        low, high = b / bins, (b + 1) / bins
        group = [(c, ok) for c, ok in pairs if low <= c < high or (b == bins - 1 and c == 1.0)]
        if group:
            out.append(
                {
                    "bin": [low, high],
                    "confidence": fmean(c for c, _ in group),
                    "accuracy": fmean(1.0 if ok else 0.0 for _, ok in group),
                    "n": len(group),
                }
            )
    return out


def brier(pairs: list[tuple[float, bool]]) -> float | None:
    if not pairs:
        return None
    return fmean((c - (1.0 if ok else 0.0)) ** 2 for c, ok in pairs)


def mean_or_none(values) -> float | None:
    values = list(values)
    return fmean(values) if values else None


def box_iou(a, b) -> float:
    """IoU volumétrico de dos cajas alineadas ((xmin,ymin,zmin),(xmax,ymax,zmax))."""
    inter = 1.0
    for i in range(3):
        low = max(a[0][i], b[0][i])
        high = min(a[1][i], b[1][i])
        if high <= low:
            return 0.0
        inter *= high - low

    def volume(box):
        v = 1.0
        for i in range(3):
            v *= max(0.0, box[1][i] - box[0][i])
        return v

    union = volume(a) + volume(b) - inter
    return inter / union if union > 0 else 0.0


def box_center(box):
    return tuple((box[0][i] + box[1][i]) / 2 for i in range(3))
