"""Estadística del estudio: bootstrap pareado por equipo, McNemar exacto y frontera de Pareto."""

import random
from collections.abc import Callable, Sequence

from scipy.stats import binomtest


def bootstrap_ci(
    units: Sequence,
    statistic: Callable[[Sequence], float | None],
    *,
    resamples: int = 1000,
    seed: int = 2026,
    level: float = 0.95,
) -> list[float] | None:
    """Intervalo percentil remuestreando unidades (equipos) con reemplazo."""
    if not units:
        return None
    rng = random.Random(seed)
    values = []
    for _ in range(resamples):
        sample = [units[rng.randrange(len(units))] for _ in units]
        value = statistic(sample)
        if value is not None:
            values.append(value)
    if not values:
        return None
    values.sort()
    low = values[int((1 - level) / 2 * (len(values) - 1))]
    high = values[int((1 + level) / 2 * (len(values) - 1))]
    return [round(low, 4), round(high, 4)]


def paired_bootstrap_delta(
    keys: Sequence,
    statistic_a: Callable[[Sequence], float | None],
    statistic_b: Callable[[Sequence], float | None],
    *,
    resamples: int = 1000,
    seed: int = 2026,
) -> list[float] | None:
    """IC del 95 % de a − b remuestreando las mismas unidades para las dos variantes."""

    def delta(sample):
        a, b = statistic_a(sample), statistic_b(sample)
        return None if a is None or b is None else a - b

    return bootstrap_ci(keys, delta, resamples=resamples, seed=seed)


def mcnemar(a: Sequence[bool], b: Sequence[bool]) -> dict:
    """Prueba exacta de McNemar sobre aciertos pareados (mismos campos, mismos documentos)."""
    if len(a) != len(b):
        raise ValueError("McNemar necesita los mismos campos en las dos variantes")
    only_a = sum(1 for x, y in zip(a, b, strict=True) if x and not y)
    only_b = sum(1 for x, y in zip(a, b, strict=True) if y and not x)
    n = only_a + only_b
    p = 1.0 if n == 0 else binomtest(only_a, n, 0.5).pvalue
    return {"only_a": only_a, "only_b": only_b, "p": float(p)}


def pareto(points: dict[str, tuple[float, float, float]]) -> list[str]:
    """Variantes no dominadas en (coste €, segundos, −puntuación): menos es mejor en las tres."""
    front = []
    for name, p in points.items():
        dominated = any(
            all(q[i] <= p[i] for i in range(3)) and any(q[i] < p[i] for i in range(3))
            for other, q in points.items()
            if other != name
        )
        if not dominated:
            front.append(name)
    return sorted(front, key=lambda n: points[n][2])
