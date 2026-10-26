"""Baseline explícito de etiquetas; no interpreta vistas ni sustituye a un extractor de visión."""

import json
import re
from typing import Literal, Protocol

from pydantic import Field

from .ingest import Bundle
from .model import GEOMETRY_FIELDS, Model, Revision, Source


class Interval(Model):
    """Intervalo conforme de un valor numérico (contrato 0.3, DEC-12)."""

    low: float
    high: float
    level: float = Field(gt=0, lt=1)
    method: Literal["conformal"] = "conformal"


class Alternative(Model):
    """Otro valor candidato para el mismo campo, con su evidencia."""

    value: float | str
    unit: str
    source: Source
    channel: str | None = None


class Candidate(Model):
    path: str
    value: float | str
    unit: str
    source: Source
    # Procedencia ampliada (contrato 0.3). Todo opcional: los extractores antiguos no lo rellenan.
    channel: str | None = None
    strategy: str | None = None
    model: str | None = None
    prompt_sha256: str | None = None
    grounded: bool | None = None
    confidence_raw: float | None = None
    text_original: str | None = None
    unit_original: str | None = None
    alternatives: list[Alternative] = Field(default_factory=list)
    interval: Interval | None = None
    explanation: str | None = None


class Extractor(Protocol):
    def extract(self, bundles: list[Bundle]) -> list[Candidate]: ...


NUMBER = r"-?\d+(?:\.\d+)?"
LENGTH = {"mm": 1, "cm": 10, "m": 1000, "in": 25.4}
LABELS = {
    "diameter": ("DIAMETER", "OUTSIDE DIAMETER", "DIAMETRO EXTERIOR"),
    "height": ("HEIGHT", "TANGENT LENGTH", "LONGITUD DE VIROLA"),
    "head_depth": ("HEAD_DEPTH", "HEAD DEPTH", "PROFUNDIDAD DE FONDO"),
    "skirt_height": ("SKIRT_HEIGHT", "SKIRT HEIGHT", "ALTURA DE FALDON"),
    "skirt_thickness": ("SKIRT_THICKNESS", "SKIRT THICKNESS", "ESPESOR DE FALDON"),
}


class LabelExtractor:
    def extract(self, bundles: list[Bundle]) -> list[Candidate]:
        result = []
        for bundle in bundles:
            for line in bundle.lines:
                text = line.text.strip()
                tag = re.fullmatch(r"TAG\s*[:=]\s*([A-Za-z0-9_-]+)", text, re.I)
                if tag:
                    result.append(Candidate(path="tag", value=tag[1], unit="1", source=line.source))
                for path, aliases in LABELS.items():
                    labels = "|".join(re.escape(a) for a in aliases)
                    match = re.fullmatch(
                        rf"(?:{labels})\s*[:=]\s*({NUMBER})\s*(mm|cm|m|in)", text, re.I
                    )
                    if match:
                        result.append(
                            Candidate(
                                path=path,
                                value=float(match[1]) * LENGTH[match[2].lower()],
                                unit="mm",
                                source=line.source,
                            )
                        )
                nozzle = re.fullmatch(r"NOZZLE\s+([A-Za-z0-9_-]+)\s*:\s*(.+)", text, re.I)
                if nozzle:
                    for pair in nozzle[2].split(";"):
                        match = re.fullmatch(
                            rf"\s*(DIAMETER|PROJECTION|ELEVATION|AZIMUTH)\s*=\s*({NUMBER})\s*(mm|cm|m|in|deg)\s*",
                            pair,
                            re.I,
                        )
                        if not match:
                            continue
                        key, value, unit = match[1].lower(), float(match[2]), match[3].lower()
                        if (key == "azimuth") != (unit == "deg"):
                            continue
                        result.append(
                            Candidate(
                                path=f"nozzles.{nozzle[1]}.{key}",
                                value=value if unit == "deg" else value * LENGTH[unit],
                                unit="deg" if unit == "deg" else "mm",
                                source=line.source,
                            )
                        )
                attribute = re.fullmatch(
                    rf"(DESIGN_PRESSURE|DESIGN_TEMPERATURE|OPERATING_WEIGHT)\s*[:=]\s*({NUMBER})\s*(bar|kPa|MPa|C|kg)",
                    text,
                    re.I,
                )
                if attribute:
                    expected = {
                        "design_pressure": {"bar", "kpa", "mpa"},
                        "design_temperature": {"c"},
                        "operating_weight": {"kg"},
                    }
                    key = attribute[1].lower()
                    unit = attribute[3]
                    if unit.lower() in expected[key]:
                        result.append(
                            Candidate(
                                path=f"attributes.{key}",
                                value=float(attribute[2]),
                                unit=unit,
                                source=line.source,
                            )
                        )
                material = re.fullmatch(r"MATERIAL\s*[:=]\s*(.+)", text, re.I)
                if material:
                    result.append(
                        Candidate(
                            path="attributes.material",
                            value=material[1],
                            unit="1",
                            source=line.source,
                        )
                    )
        return result


def assemble(
    bundles: list[Bundle],
    candidates: list[Candidate],
    *,
    project_id: str,
    equipment_id: str,
    revision: str,
    dataset: str = "real",
) -> Revision:
    chosen = {}
    for candidate in candidates:
        previous = chosen.get(candidate.path)
        if previous and (previous.value, previous.unit) != (candidate.value, candidate.unit):
            raise ValueError(f"Conflicto en {candidate.path}: seleccione la evidencia correcta")
        chosen.setdefault(candidate.path, candidate)
    missing = [key for key in ("tag", *GEOMETRY_FIELDS) if key not in chosen]
    if missing:
        raise ValueError("Faltan datos explícitos: " + ", ".join(missing))
    equipment = {"id": equipment_id, "kind": "vertical_vessel", "attributes": {}, "nozzles": []}
    nozzles = {}
    for path, candidate in chosen.items():
        value = {
            "value": candidate.value,
            "unit": candidate.unit,
            "source": candidate.source.model_dump(mode="json"),
        }
        value["source"]["reviewed"] = False
        if path.startswith("nozzles."):
            _, nozzle_id, key = path.split(".")
            nozzles.setdefault(nozzle_id, {"id": nozzle_id})[key] = value
        elif path.startswith("attributes."):
            equipment["attributes"][path.split(".", 1)[1]] = value
        else:
            equipment[path] = value
    equipment["nozzles"] = list(nozzles.values())
    content = {
        "schema_version": "0.2",
        "project_id": project_id,
        "revision": revision,
        "dataset": dataset,
        "documents": [b.document.model_dump(mode="json") for b in bundles],
        "equipment": equipment,
    }
    return Revision.model_validate_json(json.dumps(content))
