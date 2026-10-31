"""Baseline explícito de etiquetas; no interpreta vistas ni sustituye a un extractor de visión."""

import json
import re
from typing import Literal, Protocol, get_args

from pydantic import Field

from .ingest import Bundle
from .model import GEOMETRY_FIELDS, Channel, FieldState, Model, Revision, Source, nozzle_misfit

CHANNELS = set(get_args(Channel))


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
    # Solo la etapa `calibrate` lo fija ("abstained"); si no, el campo nace como "candidate".
    state: FieldState | None = None


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


def _traced_source(source: Source, reading: "Candidate | Alternative") -> dict:
    """Evidencia del contrato 0.3: completa la procedencia con lo que trae la lectura."""
    data = source.model_dump(mode="json")
    data["reviewed"] = False
    if data.get("confidence_raw") is None:
        data["confidence_raw"] = source.confidence
    if data.get("channel") is None and reading.channel in CHANNELS:
        data["channel"] = reading.channel
    if isinstance(reading, Candidate):
        for key in ("strategy", "model", "grounded", "text_original", "unit_original"):
            if data.get(key) is None:
                data[key] = getattr(reading, key)
    return data


def _misfit(equipment: dict, nozzle: dict) -> str | None:
    values = [
        nozzle["diameter"]["value"],
        nozzle["elevation"]["value"],
        equipment["diameter"]["value"],
        equipment["skirt_height"]["value"],
        equipment["height"]["value"],
    ]
    if not all(isinstance(v, int | float) for v in values):
        return None  # lo rechaza el contrato, con su propio mensaje
    return nozzle_misfit(*values)


def assemble(
    bundles: list[Bundle],
    candidates: list[Candidate],
    *,
    project_id: str,
    equipment_id: str,
    revision: str,
    dataset: str = "real",
    warnings: list[str] | None = None,
) -> Revision:
    chosen = {}
    for candidate in candidates:
        previous = chosen.get(candidate.path)
        if previous and (previous.value, previous.unit) != (candidate.value, candidate.unit):
            raise ValueError(f"Conflicto en {candidate.path}: seleccione la evidencia correcta")
        chosen.setdefault(candidate.path, candidate)
    envelope = any(path.startswith("envelope.") for path in chosen)
    required = (
        ("tag", *(f"envelope.{part}.{axis}" for part in ("origin", "size") for axis in "xyz"))
        if envelope
        else ("tag", *GEOMETRY_FIELDS)
    )
    missing = [key for key in required if key not in chosen]
    if missing:
        raise ValueError("Faltan datos explícitos: " + ", ".join(missing))
    equipment = {"id": equipment_id, "kind": "vertical_vessel", "attributes": {}, "nozzles": []}
    if envelope:
        kind = chosen.get("attributes.equipment_type")
        equipment.update(
            kind="pump" if kind and kind.value == "pump" else "generic",
            lod=1,
            envelope={"origin": {}, "size": {}},
        )
    nozzles = {}
    for path, candidate in chosen.items():
        value = {
            "value": candidate.value,
            "unit": candidate.unit,
            "source": _traced_source(candidate.source, candidate),
            "state": candidate.state or "candidate",
            "interval": candidate.interval.model_dump(mode="json") if candidate.interval else None,
            "alternatives": [
                {
                    "value": a.value,
                    "unit": a.unit,
                    "source": _traced_source(a.source, a),
                }
                for a in candidate.alternatives
            ],
            "explanation": candidate.explanation,
        }
        if envelope and path.startswith("envelope."):
            _, part, axis = path.split(".")
            equipment["envelope"][part][axis] = value
        elif envelope and not (path == "tag" or path.startswith("attributes.")):
            continue  # LOD 1 no convierte coordenadas de conexión en salientes supuestos.
        elif path.startswith("nozzles."):
            _, nozzle_id, key = path.split(".")
            nozzles.setdefault(nozzle_id, {"id": nozzle_id})[key] = value
        elif path.startswith("attributes."):
            equipment["attributes"][path.split(".", 1)[1]] = value
        else:
            equipment[path] = value
    # Una boquilla sin alguno de sus cuatro datos no se puede colocar en 3D: queda fuera del
    # modelo, pero sus valores siguen como candidatos para la revisión humana.
    complete = {"diameter", "projection", "elevation", "azimuth"}
    incomplete = sorted(n for n, data in nozzles.items() if not complete <= data.keys())
    if incomplete and warnings is not None:
        warnings.append(
            "Boquillas incompletas fuera del modelo (faltan datos): " + ", ".join(incomplete)
        )
    # Igual con la que no cabe en la virola leída: una lectura mal hecha no deja sin modelo a todo
    # el equipo.
    misfits = sorted(
        n
        for n, data in nozzles.items()
        if n not in incomplete and _misfit(equipment, data) is not None
    )
    if misfits and warnings is not None:
        warnings.append("Boquillas fuera del modelo (no caben en la virola): " + ", ".join(misfits))
    excluded = {*incomplete, *misfits}
    equipment["nozzles"] = [data for n, data in nozzles.items() if n not in excluded]
    content = {
        "schema_version": "0.3",
        "approval": None,
        "project_id": project_id,
        "revision": revision,
        "dataset": dataset,
        "documents": [b.document.model_dump(mode="json") for b in bundles],
        "equipment": equipment,
        "unplaced_nozzles": sorted(excluded),
    }
    return Revision.model_validate_json(json.dumps(content))
