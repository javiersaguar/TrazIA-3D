"""Conversión a las unidades canónicas del contrato (mm, deg, bar, C, kg) con pint.

Un valor es correcto si coincide con la verdad después de convertirlo: «145 psig» y «10 bar» son el
mismo dato. La presión se trata como manométrica en las dos escalas.
"""

from functools import lru_cache

import pint

CANONICAL = {
    "length": "mm",
    "angle": "deg",
    "pressure": "bar",
    "temperature": "C",
    "mass": "kg",
}
ALIASES = {
    "mm": "millimeter",
    "in": "inch",
    "ft": "foot",
    "deg": "degree",
    "°": "degree",
    "bar": "bar",
    "barg": "bar",
    "bar(g)": "bar",
    "kpa": "kilopascal",
    "mpa": "megapascal",
    "psi": "psi",
    "psig": "psi",
    "c": "degC",
    "°c": "degC",
    "f": "degF",
    "°f": "degF",
    "kg": "kilogram",
    "lb": "pound",
    "lbs": "pound",
}
TO_CANONICAL = {
    "millimeter": "mm",
    "inch": "mm",
    "foot": "mm",
    "degree": "deg",
    "bar": "bar",
    "kilopascal": "bar",
    "megapascal": "bar",
    "psi": "bar",
    "degC": "C",
    "degF": "C",
    "kilogram": "kg",
    "pound": "kg",
}
PINT_NAME = {"mm": "millimeter", "deg": "degree", "bar": "bar", "C": "degC", "kg": "kilogram"}


@lru_cache(maxsize=1)
def _registry() -> pint.UnitRegistry:
    return pint.UnitRegistry(autoconvert_offset_to_baseunit=True)


def to_canonical(value: float | str, unit: str) -> tuple[float | str, str]:
    """(valor, unidad) en la unidad canónica. Textos y unidades desconocidas pasan tal cual."""
    if isinstance(value, str):
        return value, unit
    name = ALIASES.get(unit.strip().lower())
    if name is None or name not in TO_CANONICAL:
        return float(value), unit
    target = TO_CANONICAL[name]
    ureg = _registry()
    quantity = ureg.Quantity(float(value), name)
    return float(quantity.to(PINT_NAME[target]).magnitude), target


def same(predicted: float | str, predicted_unit: str, expected: float | str, unit: str) -> bool:
    """Igualdad tras convertir: ±1 mm, ±0,5° (DEC-22) y ±0,5 % (mín. 0,5) en atributos."""
    value, canonical = to_canonical(predicted, predicted_unit)
    if isinstance(expected, str) or isinstance(value, str):
        return str(value).strip().upper() == str(expected).strip().upper()
    if canonical != unit:
        return False
    if unit == "deg":
        d = abs(value - expected) % 360
        return min(d, 360 - d) <= 0.5
    if unit == "mm":
        return abs(value - expected) <= 1.0
    return abs(value - expected) <= max(0.5, 0.005 * abs(expected))
