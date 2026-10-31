"""Normalización de ingeniería con Pint; conserva el original y rechaza ambigüedades."""

import math
import re
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache

import pint


class UnitError(ValueError):
    pass


class AmbiguousNumber(UnitError):
    def __init__(self, text, alternatives):
        self.alternatives = tuple(alternatives)
        super().__init__(
            f"Separador ambiguo en {text!r}: {self.alternatives}; indica decimal '.' o ','"
        )


@lru_cache(maxsize=1)
def registry():
    return pint.UnitRegistry(autoconvert_offset_to_baseunit=True)


CANONICAL = {"length": "mm", "angle": "deg", "pressure": "bar", "temperature": "C", "mass": "kg"}
PINT = {"mm": "millimeter", "deg": "degree", "bar": "bar", "C": "degC", "kg": "kilogram"}
ALIASES = {
    "mm": "millimeter",
    "cm": "centimeter",
    "m": "meter",
    "in": "inch",
    '"': "inch",
    "ft": "foot",
    "deg": "degree",
    "°": "degree",
    "bar": "bar",
    "barg": "bar",
    "bar(g)": "bar",
    "bara": "bar",
    "bar(a)": "bar",
    "kpa": "kilopascal",
    "mpa": "megapascal",
    "psi": "psi",
    "psig": "psi",
    "psia": "psi",
    "kgf/cm2": "kilogram_force / centimeter**2",
    "kg/cm2": "kilogram_force / centimeter**2",
    "c": "degC",
    "°c": "degC",
    "f": "degF",
    "°f": "degF",
    "kg": "kilogram",
    "t": "metric_ton",
    "lb": "pound",
    "lbs": "pound",
}


def number(text: str, *, decimal: str | None = None) -> float:
    raw = text.strip().replace("−", "-").replace("\u00a0", " ")
    if decimal not in (None, ".", ","):
        raise UnitError("El separador decimal debe ser '.' o ','")
    # Espacios solo como grupos de miles, no se unen dígitos arbitrariamente.
    if " " in raw:
        if not re.fullmatch(r"[+-]?\d{1,3}(?: \d{3})+(?:[.,]\d+)?", raw):
            raise UnitError("Agrupación de miles inválida")
        raw = raw.replace(" ", "")
    if not re.fullmatch(r"[+-]?\d+(?:[.,]\d+)*", raw):
        raise UnitError("Número inválido")
    if decimal is None:
        if "." in raw and "," in raw:
            decimal = "." if raw.rfind(".") > raw.rfind(",") else ","
        elif re.fullmatch(r"[+-]?[1-9]\d{0,2}[.,]\d{3}", raw):
            point = raw.replace(",", ".")
            raise AmbiguousNumber(text, (float(point), float(re.sub(r"[.,]", "", raw))))
        elif raw.count(".") > 1 or raw.count(",") > 1:
            decimal = "," if "." in raw else "."
        else:
            decimal = "," if "," in raw else "."
    group = "," if decimal == "." else "."
    if group in raw:
        pattern = rf"[+-]?\d{{1,3}}(?:{re.escape(group)}\d{{3}})+(?:{re.escape(decimal)}\d+)?"
        if not re.fullmatch(pattern, raw):
            raise UnitError("Separadores incompatibles con el contexto decimal")
    clean = raw.replace(group, "").replace(decimal, ".")
    try:
        result = float(clean)
    except ValueError as exc:
        raise UnitError("Número inválido") from exc
    if not math.isfinite(result):
        raise UnitError("El valor debe ser finito")
    return result


@dataclass(frozen=True)
class Quantity:
    value: float
    unit: str
    unit_original: str
    text_original: str
    pressure_basis: str | None = None
    notices: tuple[str, ...] = ()


def normalize(
    text: str, magnitude: str, *, decimal: str | None = None, default_unit: str | None = None
) -> Quantity:
    if magnitude not in CANONICAL:
        raise UnitError("Magnitud desconocida")
    raw = text.strip().replace("″", '"').replace("′", "'").replace("''", '"')
    feet = re.fullmatch(r"([+-]?\d+)\s*'\s*-?\s*(\d+(?:\s+\d+/\d+)?|\d+/\d+)?\s*\"?", raw)
    fraction = re.fullmatch(r"(\d+)[ -]+(\d+/\d+)\s*(\"|in)", raw)
    plain_fraction = re.fullmatch(r"(\d+/\d+)\s*(\"|in)", raw)
    try:
        if feet:
            if magnitude != "length":
                raise UnitError("Pies-pulgadas no corresponden a esta magnitud")
            whole, _, part = (feet[2] or "0").partition(" ")
            inches = Fraction(whole) + (Fraction(part) if part else 0)
            if inches >= 12:
                raise UnitError("La parte de pulgadas debe ser menor que 12")
            value = abs(int(feet[1])) * 12 + float(inches)
            value *= -1 if feet[1].startswith("-") else 1
            original, alias = "ft-in", "inch"
        elif fraction or plain_fraction:
            if fraction:
                value = float(Fraction(fraction[1]) + Fraction(fraction[2]))
                original = fraction[3]
            else:
                value, original = float(Fraction(plain_fraction[1])), plain_fraction[2]
            alias = "inch"
        else:
            match = re.fullmatch(r"([+\-−]?\d[\d.,\s\u00a0]*)\s*(.*?)", raw)
            if not match:
                raise UnitError("No se reconoce un valor y su unidad")
            value = number(match[1], decimal=decimal)
            original = match[2].strip() or default_unit or ""
            alias = ALIASES.get(
                original.lower().replace(" ", "").replace("²", "2").replace("º", "°")
            )
        if not alias:
            raise UnitError(f"Unidad no admitida: {original!r}")
        target = CANONICAL[magnitude]
        converted = registry().Quantity(value, alias).to(PINT[target]).magnitude
    except (ZeroDivisionError, pint.errors.PintError) as exc:
        raise UnitError("Unidad incompatible o fracción inválida") from exc
    basis = None
    normalized = original.lower().replace(" ", "")
    if magnitude == "pressure":
        basis = (
            "absolute"
            if normalized in ("bara", "bar(a)", "psia")
            else ("gauge" if normalized in ("barg", "bar(g)", "psig") else "unspecified")
        )
        # Nunca equiparar presión absoluta y manométrica sin presión atmosférica declarada.
        if basis == "absolute":
            target = "bara"
    notices = (
        ("kg/cm² interpretado como kgf/cm²; confirmar convención del documento",)
        if normalized.replace("²", "2") == "kg/cm2"
        else ()
    )
    return Quantity(float(converted), target, original, text, basis, notices)
