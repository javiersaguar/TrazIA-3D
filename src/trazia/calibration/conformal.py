"""Intervalos conformes partidos de Mondrian para campos numéricos (tarea 3.3).

El residuo no depende de la unidad, para poder juntar campos de escalas distintas:

- `deg`: error angular en grados que sobra de la tolerancia (0,5°).
- `mm`: error en mm que sobra de la tolerancia (1 mm), dividido entre el valor leído.
- `num` (atributos con otras unidades): igual que `mm`, con tolerancia máx(0,5; 0,5 %).

Los grupos de Mondrian son (clase de campo, franja de confianza calibrada). El cuantil es el de
muestra finita, ⌈(n+1)·nivel⌉-ésimo residuo: con datos intercambiables, la cobertura del grupo es
al menos el nivel. Si el grupo es tan pequeño que ese cuantil no existe, no se da intervalo.

Un intervalo que cubre el 90 % solo porque es enorme no informa: en las franjas de confianza baja
más del 10 % de las lecturas son otro número (residuo de cientos de veces el valor). Por encima de
`MAX_RESIDUAL` no se da intervalo y el campo se abstiene: hay que confirmarlo a mano.
"""

import math

LEVEL = 0.9
BANDS = (0.5, 0.8, 0.95)  # cortes de la confianza calibrada
# Residuo máximo de un intervalo útil: 5 % del valor (mm, num) o 5° (deg) además de la tolerancia.
MAX_RESIDUAL = {"mm": 0.05, "num": 0.05, "deg": 5.0}


def kind_of(value: float | str, unit: str) -> str | None:
    if isinstance(value, str):
        return None
    if unit == "deg":
        return "deg"
    if unit == "mm":
        return "mm"
    return "num"


def band_of(confidence: float) -> int:
    return sum(confidence >= cut for cut in BANDS)


def _tolerance(kind: str, value: float) -> float:
    if kind == "deg":
        return 0.5
    if kind == "mm":
        return 1.0
    return max(0.5, 0.005 * abs(value))


def _scale(kind: str, value: float) -> float:
    return 1.0 if kind == "deg" else max(abs(value), 1.0)


def residual(kind: str, predicted: float, expected: float) -> float:
    if kind == "deg":
        d = abs(predicted - expected) % 360
        error = min(d, 360 - d)
    else:
        error = abs(predicted - expected)
    return max(0.0, error - _tolerance(kind, predicted)) / _scale(kind, predicted)


def quantile(residuals: list[float], level: float = LEVEL) -> float | None:
    """Cuantil conforme de muestra finita; `None` si hay muy pocos residuos para el nivel."""
    n = len(residuals)
    k = math.ceil((n + 1) * level)
    if n == 0 or k > n:
        return None
    return sorted(residuals)[k - 1]


def informative(kind: str, q: float) -> bool:
    return q <= MAX_RESIDUAL[kind]


def half_width(kind: str, value: float, q: float) -> float:
    return _tolerance(kind, value) + q * _scale(kind, value)
