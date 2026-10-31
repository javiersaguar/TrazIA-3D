"""Plano de orientación de boquillas (VESOR): rótulos de planta «N3 135°» (ROADMAP 2.1).

La tabla de orientación, si la hay, la lee `DrawingExtractor` como cualquier tabla de boquillas.
Aquí se leen los rótulos de la planta, que a menudo son lo único que trae un VESOR: marca de la
boquilla y ángulo en el mismo texto. Solo se aplica a documentos VESOR: en un GA, un rótulo así
puede ser otra cosa (una nota, una vista girada).
"""

import re

from ..extraction import Candidate
from ..ingest import Bundle
from .units import parse_angle

PLAN_LABEL = re.compile(r"^([A-Z]{1,2}\d{1,3}[A-Z]?)\s*[-–:/]?\s*(\d{1,3}(?:[.,]\d+)?\s*°)$")
CONFIDENCE = 0.7  # un rótulo suelto: menos que una celda de tabla con cabecera


def is_vesor(bundle: Bundle) -> bool:
    name = bundle.document.filename.upper()
    return name.startswith("VESOR") or bundle.document.id.upper().startswith("VESOR")


def plan_labels(bundle: Bundle) -> list[Candidate]:
    out = []
    for line in bundle.lines:
        match = PLAN_LABEL.match(line.text.strip().upper())
        if not match or line.source.bbox is None:
            continue
        angle = parse_angle(match.group(2))
        if angle is None or not 0 <= angle < 360:
            continue
        mark = match.group(1)
        out.append(
            Candidate(
                path=f"nozzles.{mark}.azimuth",
                value=angle,
                unit="deg",
                source=line.source.model_copy(
                    update={
                        "confidence": CONFIDENCE,
                        "locator": f"VESOR · rótulo de planta «{line.text.strip()}»",
                    }
                ),
                text_original=line.text.strip(),
            )
        )
    return out
