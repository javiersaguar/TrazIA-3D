"""Verificación independiente de cita para el estudio (tasa de alucinación, DEC-10 y DEC-22).

Para cada valor emitido se busca el texto que hay en la región citada del documento original
(caja de la página o celda de la hoja) y se comprueba que contiene el valor, con tolerancia de
formato: decimales con punto o coma, separadores de miles, fracciones de pulgada, pies-pulgadas,
dígitos invertidos de texto girado y las conversiones habituales (pulgadas, psi, °F, lb).

- `True`: el valor está en la región citada.
- `False`: sin cita, o la región citada no lo contiene → cuenta como alucinación.
- `None`: no verificable por texto (página escaneada sin capa de texto). Se informa aparte; con OCR
  (tarea 6) estas regiones pasarán a verificarse.

Si el candidato declara `text_original` (lo que leyó antes de transformar: datum, unidades), se
comprueba ese texto y la transformación queda en su explicación.
"""

import re
from fractions import Fraction

from trazia.extraction import Candidate
from trazia.ingest import Bundle

MARGIN = 0.004
NUMBER = re.compile(r"\d[\d.,\s]*\d|\d")
FEET_INCHES = re.compile(r"(\d+)'\s*-?\s*(\d+)?(?:\s+(\d+)/(\d+))?\"?")
INCH_FRACTION = re.compile(r"(\d+)\s+(\d+)/(\d+)\"|(\d+)/(\d+)\"|(\d+)\"")


def _norm(text: str) -> str:
    return re.sub(r"\s+", "", text).upper()


def _interpretations(token: str) -> set[float]:
    """Valores posibles de un número escrito: 1.234,5 · 1,234.5 · 12.500 (miles) · 0078 (girado)."""
    clean = token.replace(" ", "")
    out: set[float] = set()
    for decimal, thousands in ((".", ","), (",", ".")):
        candidate = clean.replace(thousands, "").replace(decimal, ".")
        try:
            out.add(float(candidate))
        except ValueError:
            pass
    digits = re.sub(r"\D", "", clean)
    if digits:
        out.add(float(digits))
        out.add(float(digits[::-1]))
    return out


def numbers_in(text: str) -> set[float]:
    values: set[float] = set()
    for match in FEET_INCHES.finditer(text):
        feet, inches = int(match[1]), int(match[2] or 0)
        frac = Fraction(int(match[3]), int(match[4])) if match[3] else Fraction(0)
        values.add(float(12 * feet + inches + frac))
    for match in INCH_FRACTION.finditer(text):
        if match[1]:
            values.add(int(match[1]) + int(match[2]) / int(match[3]))
        elif match[4]:
            values.add(int(match[4]) / int(match[5]))
        else:
            values.add(float(match[6]))
    for token in NUMBER.findall(text):
        values |= _interpretations(token)
    # Cada grupo suelto también cuenta: «110 1/4"» respalda 110 (leerlo en mm es un error de
    # unidad, que mide el acierto; aquí solo se mide si el número está en la cita).
    for token in re.findall(r"\d[\d.,]*", text):
        values |= _interpretations(token)
    return values


def _views(value: float, unit: str) -> list[float]:
    """El valor en las unidades en que un plano podría escribirlo."""
    if unit == "mm":
        return [value, value / 25.4]
    if unit == "bar":
        return [value, value * 14.5038, value * 100, value / 10]
    if unit == "C":
        return [value, value * 1.8 + 32]
    if unit == "kg":
        return [value, value * 2.204623]
    return [value]


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= max(0.06, 0.005 * abs(b))


def region_text(candidate: Candidate, bundle: Bundle) -> str | None:
    """Texto de la región citada; None si la página no tiene capa de texto."""
    source = candidate.source
    if source.cell:
        return " ".join(line.text for line in bundle.lines if line.source.cell == source.cell)
    if source.page is None or source.bbox is None:
        return ""
    page_lines = [line for line in bundle.lines if line.source.page == source.page]
    if not page_lines:
        return None
    x0, y0, x1, y1 = source.bbox
    hits = []
    for line in page_lines:
        if line.source.bbox is None:
            continue
        a0, b0, a1, b1 = line.source.bbox
        if a1 >= x0 - MARGIN and a0 <= x1 + MARGIN and b1 >= y0 - MARGIN and b0 <= y1 + MARGIN:
            hits.append(line.text)
    return " ".join(hits)


def is_cited(candidate: Candidate) -> bool:
    source = candidate.source
    return bool(source.cell) or (source.page is not None and source.bbox is not None)


def is_supported(candidate: Candidate, bundle: Bundle | None) -> bool | None:
    if not is_cited(candidate):
        return False
    if candidate.channel == "geometria" and not candidate.text_original:
        return None  # medida sobre los trazos: no se puede verificar con texto
    if bundle is None:
        return False
    text = region_text(candidate, bundle)
    if text is None:
        return None
    if candidate.text_original:
        return _norm(candidate.text_original) in _norm(text)
    if isinstance(candidate.value, str):
        return _norm(candidate.value) in _norm(text)
    found = numbers_in(text)
    return any(_close(n, v) for v in _views(float(candidate.value), candidate.unit) for n in found)
