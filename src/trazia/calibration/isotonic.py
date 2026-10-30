"""Calibración isotónica de la confianza (tarea 3.3).

Se ajusta con scikit-learn y se guarda como una curva de puntos (x, y). En inferencia basta con
interpolar entre esos puntos: no hace falta cargar scikit-learn para procesar un documento.
"""

from bisect import bisect_right


def fit_curve(scores: list[float], hits: list[bool]) -> dict:
    """Curva monótona creciente de confianza bruta → probabilidad de acierto."""
    from sklearn.isotonic import IsotonicRegression

    model = IsotonicRegression(y_min=0.0, y_max=1.0, increasing=True, out_of_bounds="clip")
    model.fit(scores, [1.0 if h else 0.0 for h in hits])
    xs = [float(x) for x in model.X_thresholds_]
    ys = [float(y) for y in model.y_thresholds_]
    return {"x": xs, "y": ys, "n": len(scores)}


def apply_curve(curve: dict, score: float) -> float:
    """Interpolación lineal entre los puntos de la curva; fuera del rango, el extremo."""
    xs, ys = curve["x"], curve["y"]
    if not xs:
        return score
    if score <= xs[0]:
        return ys[0]
    if score >= xs[-1]:
        return ys[-1]
    i = bisect_right(xs, score)
    x0, x1, y0, y1 = xs[i - 1], xs[i], ys[i - 1], ys[i]
    if x1 == x0:
        return y1
    return y0 + (y1 - y0) * (score - x0) / (x1 - x0)
