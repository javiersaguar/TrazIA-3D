"""Números y unidades tal como se escriben en un plano: mm, pulgadas con fracción, pies-pulgadas,
NPS, coma o punto decimal, separador de miles, psig, °F y lb.

Todo vuelve en la unidad del contrato (mm, deg, bar, C, kg). El texto leído se conserva aparte
(`text_original`) para que la cita se pueda comprobar.
"""

import re

from trazia.units import UnitError, normalize

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
    try:
        raw = re.sub(r"(?<=\d)-(?=\d+/)", " ", text.strip())
        return normalize(raw, "length", decimal=decimal, default_unit="mm").value
    except UnitError:
        return None


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
    return _parsed(text, "pressure", decimal)


def parse_temperature(text: str, *, decimal: str | None = None) -> tuple[float, str] | None:
    return _parsed(text, "temperature", decimal)


def parse_weight(text: str, *, decimal: str | None = None) -> tuple[float, str] | None:
    return _parsed(text, "mass", decimal)


def _parsed(text, kind, decimal):
    try:
        result = normalize(text, kind, decimal=decimal)
        if result.unit == "bara" or result.notices:
            return None  # La interfaz legada no puede expresar base absoluta ni un supuesto.
        return result.value, result.unit_original
    except UnitError:
        return None
