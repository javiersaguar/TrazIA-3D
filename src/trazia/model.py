import copy
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Identifier = Annotated[str, Field(min_length=1, pattern=r"^[A-Za-z0-9_-]+$")]
SHA256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
FieldState = Literal["candidate", "conflict", "abstained", "accepted", "corrected", "assumed"]
Channel = Literal[
    "texto",
    "tabla",
    "cota",
    "cajetin",
    "hoja_datos",
    "vesor",
    "ocr",
    "detector",
    "vision",
    "geometria",
    "rag",
    "memoria_revision",
    "humano",
]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)


class Source(Model):
    document_id: Identifier
    page: int | None = Field(default=None, ge=1)
    sheet: str | None = None
    cell: str | None = None
    locator: str = Field(min_length=1)
    bbox: tuple[float, float, float, float] | None = Field(default=None, strict=False)
    confidence: float = Field(ge=0, le=1)
    reviewed: bool = False
    confidence_raw: float | None = None
    channel: Channel | None = None
    strategy: str | None = None
    model: str | None = None
    prompt_sha256: SHA256 | None = None
    grounded: bool | None = None
    text_original: str | None = None
    unit_original: str | None = None

    @model_validator(mode="after")
    def check_location(self):
        if self.page is None and not (self.sheet and self.cell):
            raise ValueError("La evidencia necesita página o bien hoja y celda")
        if self.bbox is not None:
            x0, y0, x1, y1 = self.bbox
            if self.page is None or not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
                raise ValueError("bbox debe ser una región normalizada de una página")
        return self


class Interval(Model):
    low: float
    high: float
    level: float = Field(gt=0, lt=1)
    method: Literal["conformal"] = "conformal"

    @model_validator(mode="after")
    def check_order(self):
        if self.low > self.high:
            raise ValueError("El límite inferior del intervalo no puede superar al superior")
        return self


class Alternative(Model):
    value: float | str
    unit: str = Field(min_length=1)
    source: Source


class TracedField(Model):
    source: Source
    state: FieldState = "candidate"
    interval: Interval | None = None
    alternatives: list[Alternative] = Field(default_factory=list)
    explanation: str | None = None

    @model_validator(mode="after")
    def sync_reviewed(self):
        self.source = self.source.model_copy(
            update={"reviewed": self.state in ("accepted", "corrected")}
        )
        return self


class Dimension(TracedField):
    # Las coordenadas del origen también son Dimension: pueden ser cero o negativas.
    # La positividad se valida en los parámetros físicos y en Envelope.size.
    value: float
    unit: Literal["mm"] = "mm"


class Elevation(TracedField):
    value: float = Field(ge=0)
    unit: Literal["mm"] = "mm"


class Angle(TracedField):
    value: float = Field(ge=0, lt=360)
    unit: Literal["deg"] = "deg"


class Attribute(TracedField):
    value: float | str
    unit: str = Field(min_length=1)


class Tag(TracedField):
    value: str = Field(min_length=1)
    unit: Literal["1"] = "1"


class Vector3(Model):
    x: Dimension
    y: Dimension
    z: Dimension


class Envelope(Model):
    origin: Vector3
    size: Vector3

    @model_validator(mode="after")
    def check_size(self):
        if any(getattr(self.size, axis).value <= 0 for axis in "xyz"):
            raise ValueError("Los tamaños de la envolvente deben ser positivos")
        return self


class Document(Model):
    id: Identifier
    filename: str = Field(min_length=1)
    revision: str = Field(min_length=1)
    sha256: SHA256
    page_count: int | None = Field(default=None, ge=1)


class Nozzle(Model):
    id: Identifier
    diameter: Dimension
    projection: Dimension
    elevation: Elevation
    azimuth: Angle
    service: Attribute | None = None
    rating: Attribute | None = None
    nozzle_type: Literal["radial", "tangential", "top", "bottom", "inclined"] | None = None

    @model_validator(mode="after")
    def check_sizes(self):
        if self.diameter.value <= 0 or self.projection.value <= 0:
            raise ValueError("Diámetro y proyección de boquilla deben ser positivos")
        return self


class Equipment(Model):
    id: Identifier
    tag: Tag
    kind: Literal[
        "vertical_vessel", "horizontal_vessel", "column", "tank", "pump", "compressor", "generic"
    ] = "vertical_vessel"
    lod: Literal[1, 2, 3] = 2
    support: Literal["skirt", "legs", "saddles", "lugs", "baseplate", "none"] | None = None
    envelope: Envelope | None = None
    diameter: Dimension | None = None
    height: Dimension | None = None  # Longitud de virola entre tangentes, no altura total.
    head_depth: Dimension | None = None  # Profundidad común de los dos fondos semielipsoidales.
    skirt_height: Dimension | None = None  # Desde suelo hasta la tangente inferior de la virola.
    skirt_thickness: Dimension | None = None
    attributes: dict[Identifier, Attribute] = Field(default_factory=dict)
    nozzles: list[Nozzle]

    @property
    def shell_bottom(self) -> float:
        return self.skirt_height.value if self.skirt_height else 0

    @property
    def total_height(self) -> float:
        if self.height and self.head_depth:
            return self.shell_bottom + self.head_depth.value + self.height.value
        return self.envelope.size.z.value if self.envelope else 0

    @model_validator(mode="after")
    def check_geometry(self):
        ids = [n.id for n in self.nozzles]
        if len(ids) != len(set(ids)):
            raise ValueError("Las boquillas deben tener identificadores únicos")
        for name in GEOMETRY_FIELDS:
            value = getattr(self, name)
            if value is not None and value.value <= 0:
                raise ValueError(f"{name}: la dimensión física debe ser positiva")
        if self.lod == 1 and self.envelope is None:
            raise ValueError("El nivel de detalle 1 requiere una envolvente con evidencia")
        if self.kind != "vertical_vessel" or self.lod == 1:
            return self
        if any(getattr(self, key) is None for key in GEOMETRY_FIELDS):
            raise ValueError("El recipiente vertical de nivel 2/3 necesita sus cinco dimensiones")
        if len(self.nozzles) < 3:
            raise ValueError("El recipiente vertical de nivel 2/3 necesita al menos tres boquillas")
        if self.skirt_thickness.value >= self.diameter.value / 2:
            raise ValueError("El espesor del faldón debe ser menor que el radio")
        if self.skirt_height.value <= self.head_depth.value:
            raise ValueError("El fondo inferior debe quedar por encima del suelo")
        if self.head_depth.value > self.diameter.value / 2:
            raise ValueError("Esta familia admite fondos con profundidad hasta el radio")
        for nozzle in self.nozzles:
            radius = nozzle.diameter.value / 2
            low = self.shell_bottom + radius
            high = self.shell_bottom + self.height.value - radius
            if not low <= nozzle.elevation.value <= high:
                raise ValueError(f"Boquilla {nozzle.id}: debe quedar dentro de la virola")
            if nozzle.diameter.value >= self.diameter.value:
                raise ValueError(f"Boquilla {nozzle.id}: diámetro incompatible con la virola")
        return self


class Approval(Model):
    reviewer: str = Field(min_length=2)
    timestamp: datetime = Field(strict=False)
    input_sha256: SHA256

    @model_validator(mode="after")
    def check_timezone(self):
        if self.timestamp.tzinfo is None:
            raise ValueError("La fecha de revisión debe incluir zona horaria")
        return self


class RunInfo(Model):
    strategy: str
    providers: list[str]
    seconds: float = Field(ge=0)
    gpu_seconds: float | None = Field(default=None, ge=0)
    tokens_in: int | None = Field(default=None, ge=0)
    tokens_out: int | None = Field(default=None, ge=0)
    cost_eur: float | None = Field(default=None, ge=0)
    external_calls: int = Field(ge=0)


class Revision(Model):
    schema_version: Literal["0.3"] = "0.3"
    project_id: Identifier
    revision: str = Field(min_length=1)
    dataset: Literal["synthetic", "real"]
    documents: list[Document] = Field(min_length=1)
    equipment: Equipment
    approval: Approval | None = None
    run: RunInfo | None = None

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy(cls, data):
        return migrate_revision(data) if isinstance(data, dict) else data

    @model_validator(mode="after")
    def check_sources_and_approval(self):
        docs = {d.id: d for d in self.documents}
        if len(docs) != len(self.documents):
            raise ValueError("Los documentos deben tener identificadores únicos")
        for path, field in fields(self.equipment).items():
            document = docs.get(field.source.document_id)
            if document is None:
                raise ValueError(f"{path}: referencia a documento desconocido")
            for source in [field.source, *[a.source for a in field.alternatives]]:
                reference = docs.get(source.document_id)
                if reference is None:
                    raise ValueError(f"{path}: alternativa con documento desconocido")
                if reference.page_count and source.page and source.page > reference.page_count:
                    raise ValueError(f"{path}: página fuera del documento")
        if self.approval:
            if self.pending_review():
                raise ValueError("La aprobación requiere revisar todos los campos")
            if self.approval.input_sha256 != self.fingerprint():
                raise ValueError("La aprobación no corresponde a estos datos; vuelva a revisar")
        return self

    def pending_review(self) -> list[str]:
        return [
            p for p, f in fields(self.equipment).items() if f.state not in ("accepted", "corrected")
        ]

    def fingerprint(self) -> str:
        content = json.dumps(
            self.model_dump(mode="json", exclude={"approval"}),
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return hashlib.sha256(content.encode()).hexdigest()


GEOMETRY_FIELDS = ("diameter", "height", "head_depth", "skirt_height", "skirt_thickness")


def fields(equipment: Equipment) -> dict:
    result = {"tag": equipment.tag}
    result.update(
        {k: getattr(equipment, k) for k in GEOMETRY_FIELDS if getattr(equipment, k) is not None}
    )
    if equipment.envelope:
        for vector in ("origin", "size"):
            for axis in "xyz":
                result[f"envelope.{vector}.{axis}"] = getattr(
                    getattr(equipment.envelope, vector), axis
                )
    result.update({f"attributes.{k}": v for k, v in equipment.attributes.items()})
    for nozzle in equipment.nozzles:
        for key in ("diameter", "projection", "elevation", "azimuth", "service", "rating"):
            if getattr(nozzle, key) is not None:
                result[f"nozzles.{nozzle.id}.{key}"] = getattr(nozzle, key)
    return result


def load_revision(path: Path) -> Revision:
    return Revision.model_validate_json(path.read_text(encoding="utf-8"))


def migrate_revision(data: dict) -> dict:
    """0.2 → 0.3 sin mutar la entrada; una migración nunca conserva la aprobación."""
    if data.get("schema_version") != "0.2":
        return data
    result = copy.deepcopy(data)
    result["schema_version"] = "0.3"
    result["approval"] = None

    def visit(value):
        if isinstance(value, dict):
            source = value.get("source")
            if isinstance(source, dict) and "value" in value:
                value["state"] = "accepted" if source.get("reviewed") else "candidate"
                if source.get("confidence_raw") is None:
                    source["confidence_raw"] = source.get("confidence")
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(result.get("equipment", {}))
    return result
