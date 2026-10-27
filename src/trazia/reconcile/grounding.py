"""Comprobación de cita (DEC-10): un valor solo entra si su región citada lo contiene.

Para cada candidato se toma el texto de la región citada (capa de texto del PDF o líneas de OCR
de esa página) y se comprueba que contiene lo que el candidato dice haber leído:
- si declara `text_original`, ese texto (sin espacios ni mayúsculas);
- si no, el valor con tolerancia de formato: decimales con coma o punto, pulgadas, pies-pulgadas,
  dígitos invertidos de texto girado y las unidades habituales del plano.

Devuelve True, False o None (no verificable: la página no tiene texto que comparar). Los modelos
de visión y el detector pasan siempre por aquí; un valor no respaldado se abstiene.
"""

import re

from ..extraction import Candidate
from ..extractors.units import parse_length_any_direction, parse_number
from ..ingest import EvidenceLine

MARGIN = 0.004
TOKEN = re.compile(r"[\d][\d.,]*(?:\s+\d+/\d+)?\"?|\d+'\s*-?\s*\d*(?:\s+\d+/\d+)?\"?")


def _norm(text: str) -> str:
    return re.sub(r"\s+", "", text).upper()


def region_text(candidate: Candidate, lines: list[EvidenceLine]) -> str | None:
    source = candidate.source
    if source.cell:
        return " ".join(line.text for line in lines if line.source.cell == source.cell)
    if source.page is None or source.bbox is None:
        return ""
    page = [line for line in lines if line.source.page == source.page and line.source.bbox]
    if not page:
        return None
    x0, y0, x1, y1 = source.bbox
    hits = [
        line.text
        for line in page
        if line.source.bbox[2] >= x0 - MARGIN
        and line.source.bbox[0] <= x1 + MARGIN
        and line.source.bbox[3] >= y0 - MARGIN
        and line.source.bbox[1] <= y1 + MARGIN
    ]
    return " ".join(hits)


def _numbers(text: str) -> set[float]:
    found: set[float] = set()
    for token in TOKEN.findall(text):
        for decimal in (".", ","):
            value = parse_number(token.strip('"'), decimal=decimal)
            if value is not None:
                found.add(value)
        found.update(v / 25.4 for v in parse_length_any_direction(token))  # en pulgadas
        found.update(parse_length_any_direction(token))
    return found


def _views(value: float, unit: str) -> list[float]:
    """El valor en las unidades en que un plano lo puede escribir."""
    return {
        "mm": [value, value / 25.4],
        "bar": [value, value * 14.5038, value * 100, value / 10],
        "C": [value, value * 1.8 + 32],
        "kg": [value, value * 2.204623],
    }.get(unit, [value])


def is_grounded(candidate: Candidate, lines: list[EvidenceLine]) -> bool | None:
    source = candidate.source
    if not source.cell and (source.page is None or source.bbox is None):
        return False  # sin cita no hay respaldo posible
    text = region_text(candidate, lines)
    if text is None:
        return None
    if candidate.text_original:
        return _norm(candidate.text_original) in _norm(text)
    if isinstance(candidate.value, str):
        return _norm(candidate.value) in _norm(text)
    numbers = _numbers(text)
    return any(
        abs(n - v) <= max(0.06, 0.005 * abs(v))
        for v in _views(float(candidate.value), candidate.unit)
        for n in numbers
    )
