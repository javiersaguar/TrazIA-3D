"""Envolvente LOD 1 de una bomba con alzado, planta y cotas explícitas.

No reconstruye el motor ni inventa salientes de conexión. Solo admite la disposición
reconocida; una cota ambigua deja el modelo pendiente, nunca se lee la verdad sintética.
"""

import re

from ..extraction import Candidate
from .units import parse_length


def pump_envelope(lines, decimal="."):
    pump = next(
        (
            item
            for item in lines
            if re.search(r"CENTRIFUGAL\s+PUMP|BOMBA\s+CENTR[IÍ]FUGA", item.text, re.I)
        ),
        None,
    )
    if not pump:
        return None
    side = next(
        (
            item
            for item in lines
            if item.text.upper().strip() in ("SIDE ELEVATION", "ALZADO LATERAL")
        ),
        None,
    )
    plan = next((item for item in lines if item.text.upper().strip() in ("PLAN", "PLANTA")), None)
    datum = next(
        (
            item
            for item in lines
            if re.search(
                r"DATUM:.*BASEPLATE.*UNDERSIDE|ORIGEN:.*BANCADA.*INFERIOR", item.text, re.I
            )
        ),
        None,
    )
    if not side or not plan or not datum or not side.source.bbox or not plan.source.bbox:
        return []
    side_y, plan_y = side.source.bbox[1], plan.source.bbox[1]
    edge = datum.source.bbox[0]
    dims = []
    for line in lines:
        box = line.source.bbox
        if box is None or box[2] >= edge or not re.fullmatch(r"[\d\s'\"/\-.,]+", line.text.strip()):
            continue
        # Los números girados pueden llegar invertidos: la orientación de la caja decide.
        vertical = box[3] - box[1] > box[2] - box[0]
        text = (
            line.text[::-1] if vertical and not line.source.locator.startswith("OCR") else line.text
        )
        value = parse_length(text, decimal=decimal)
        if value is not None and value > 0:
            dims.append((line, value, vertical))
    horizontal = [d for d in dims if not d[2] and d[0].source.bbox[1] < side_y]
    left = [
        d
        for d in dims
        if d[2] and d[0].source.bbox[2] < side.source.bbox[0] and d[0].source.bbox[1] < side_y
    ]
    widths = [d for d in dims if d[2] and side_y < d[0].source.bbox[1] < plan_y]
    if not horizontal or not left or len(widths) != 1:
        return []
    length = max(horizontal, key=lambda d: d[0].source.bbox[1])
    height = min(left, key=lambda d: d[0].source.bbox[0])
    out = []
    for axis, item in zip("xyz", (length, widths[0], height), strict=True):
        line, value, _ = item
        out.append(
            Candidate(
                path=f"envelope.size.{axis}",
                value=value,
                unit="mm",
                source=line.source,
                channel="cota",
                text_original=line.text,
                explanation="Cota exterior de la envolvente LOD 1; sin detalle interno de la bomba",
            )
        )
        out.append(
            Candidate(
                path=f"envelope.origin.{axis}",
                value=0.0,
                unit="mm",
                source=datum.source,
                channel="cota",
                state="assumed",
                explanation=(
                    "Convención de representación: origen local en la esquina inferior de la "
                    "envolvente; requiere confirmar su alineación con la planta"
                ),
            )
        )
    out.append(
        Candidate(path="attributes.equipment_type", value="pump", unit="1", source=pump.source)
    )
    tags = [item for item in lines if re.fullmatch(r"P-\d+[A-Z]?", item.text.strip(), re.I)]
    if len({item.text.strip() for item in tags}) == 1:
        out.append(
            Candidate(path="tag", value=tags[0].text.strip(), unit="1", source=tags[0].source)
        )
    return out
