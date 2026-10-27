"""Números y unidades tal como se escriben en un plano: mm, pulgadas con fracción, pies-pulgadas,
NPS, coma o punto decimal, separador de miles, psig, °F y lb.

Todo vuelve en la unidad del contrato (mm, deg, bar, C, kg). El texto leído se conserva aparte
(`text_original`) para que la cita se pueda comprobar.
"""

import re
from fractions import Fraction

MM_PER_INCH = 25.4
# Diámetro nominal: pulgadas NPS → DN (serie normalizada ASME B36.10 / ISO 6708).
NPS_TO_DN = {
    "1/2": 15,
    "3/4": 20,
    "1": 25,
    "1 1/4": 32,
    "1 1/2": 40,
    "2": 50,
    "2 1/2": 65,
    "3": 80,
    "4": 100,
    "5": 125,
    "6": 150,
    "8": 200,
    "10": 250,
    "12": 300,
    "14": 350,
    "16": 400,
    "18": 450,
    "20": 500,
    "24": 600,
}
DN_SERIES = sorted(set(NPS_TO_DN.values()))

FT_IN = re.compile(r"^(\d+)\s*'\s*-?\s*(\d+)?(?:\s+(\d+)/(\d+)|\s*-\s*(\d+)/(\d+))?\s*\"?$")
INCHES = re.compile(r"^(?:(\d+)(?:\s+|-))?(\d+)/(\d+)\s*\"$|^(\d+)\s*\"$")
PLAIN = re.compile(r"^-?\d{1,3}(?:[.,\s]\d{3})*(?:[.,]\d+)?$|^-?\d+(?:[.,]\d+)?$")


def parse_number(text: str, *, decimal: str | None = None) -> float | None:
    """«12.500» (es) → 12500; «1,234.5» → 1234.5; «2,5» → 2.5. `decimal` fuerza el separador."""
    clean = text.strip().replace("−", "-").replace(" ", "")
    if not clean or not PLAIN.match(text.strip().replace("−", "-")):
        return None
    if decimal is None:
        if "," in clean and "." in clean:
            decimal = "," if clean.rfind(",") > clean.rfind(".") else "."
        elif "," in clean:
            head, _, tail = clean.rpartition(",")
            decimal = "." if len(tail) == 3 and head.lstrip("-").isdigit() else ","
        elif "." in clean:
            head, _, tail = clean.rpartition(".")
            decimal = "," if len(tail) == 3 and clean.count(".") > 1 else "."
        else:
            decimal = "."
    thousands = "," if decimal == "." else "."
    clean = clean.replace(thousands, "").replace(decimal, ".")
    try:
        return float(clean)
    except ValueError:
        return None


def parse_length(text: str, *, decimal: str | None = None) -> float | None:
    """Longitud en mm. Admite «2000», «2.000», «78 3/4"», «6'-6 3/4"» y «1 3/16"»."""
    raw = text.strip().replace("″", '"').replace("′", "'").replace("''", '"')
    if "'" in raw:
        m = FT_IN.match(raw)
        if not m:
            return None
        inches = Fraction(int(m[1]) * 12 + int(m[2] or 0))
        if m[3]:
            inches += Fraction(int(m[3]), int(m[4]))
        elif m[5]:
            inches += Fraction(int(m[5]), int(m[6]))
        return float(inches) * MM_PER_INCH
    if raw.endswith('"'):
        m = INCHES.match(raw)
        if not m:
            value = parse_number(raw[:-1], decimal=decimal)
            return None if value is None else value * MM_PER_INCH
        if m[4]:
            return int(m[4]) * MM_PER_INCH
        inches = Fraction(int(m[1] or 0)) + Fraction(int(m[2]), int(m[3]))
        return float(inches) * MM_PER_INCH
    if raw.lower().endswith("mm"):
        raw = raw[:-2].strip()
    return parse_number(raw, decimal=decimal)


def parse_length_any_direction(text: str, *, decimal: str | None = None) -> list[float]:
    """Lecturas posibles de una cota girada: el texto tal cual y con los caracteres invertidos."""
    out = []
    for candidate in (text, text[::-1]):
        stripped = candidate.strip()
        if stripped and stripped[0] == "0" and len(stripped) > 1 and stripped[1].isdigit():
            continue  # «0078» no es una cota: es «8700» leído al revés
        value = parse_length(candidate, decimal=decimal)
        if value is not None and value > 0 and value not in out:
            out.append(value)
    return out


def parse_nominal_size(text: str) -> int | None:
    """«DN150», «150», «6"», «NPS 6» → DN en mm."""
    clean = text.strip().upper().replace("NPS", "").replace("DN", "").strip()
    if clean.endswith('"'):
        return NPS_TO_DN.get(clean[:-1].strip().replace("-", " "))
    value = parse_number(clean)
    if value is not None and float(value).is_integer() and int(value) in DN_SERIES:
        return int(value)
    return None


def parse_angle(text: str) -> float | None:
    clean = text.strip().replace("°", "").replace("º", "").strip()
    value = parse_number(clean)
    return None if value is None else value % 360


PRESSURE = re.compile(r"^(-?[\d.,\s]+?)\s*(bar\s*\(?g\)?|barg|bar|kpa|mpa|psig|psi)$", re.I)
TEMPERATURE = re.compile(r"^(-?[\d.,\s]+?)\s*°?\s*([CF])$", re.I)
WEIGHT = re.compile(r"^([\d.,\s]+?)\s*(kg|lbs?)$", re.I)


def parse_pressure(text: str, *, decimal: str | None = None) -> tuple[float, str] | None:
    """Presión manométrica → (bar, unidad original)."""
    m = PRESSURE.match(text.strip())
    if not m or (value := parse_number(m[1], decimal=decimal)) is None:
        return None
    unit = m[2].lower().replace(" ", "")
    factor = {"kpa": 0.01, "mpa": 10.0, "psig": 1 / 14.5038, "psi": 1 / 14.5038}.get(unit, 1.0)
    return value * factor, m[2]


def parse_temperature(text: str, *, decimal: str | None = None) -> tuple[float, str] | None:
    m = TEMPERATURE.match(text.strip())
    if not m or (value := parse_number(m[1], decimal=decimal)) is None:
        return None
    if m[2].upper() == "F":
        return (value - 32) / 1.8, "°F"
    return value, "°C"


def parse_weight(text: str, *, decimal: str | None = None) -> tuple[float, str] | None:
    m = WEIGHT.match(text.strip())
    if not m or (value := parse_number(m[1], decimal=decimal)) is None:
        return None
    if m[2].lower().startswith("lb"):
        return value / 2.204623, "lb"
    return value, "kg"
