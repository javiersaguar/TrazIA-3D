import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Identifier = Annotated[str, Field(min_length=1, pattern=r"^[A-Za-z0-9_-]+$")]
SHA256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)


class Source(Model):
    document_id: Identifier
    page: int | None = Field(default=None, ge=1)
    sheet: str | None = None
    cell: str | None = None
    locator: str = Field(min_length=1)
    bbox: tuple[float, float, float, float] | None = None
    confidence: float = Field(ge=0, le=1)
    reviewed: bool = False

    @model_validator(mode="after")
    def check_location(self):
        if self.page is None and not (self.sheet and self.cell):
            raise ValueError("La evidencia necesita página o bien hoja y celda")
        if self.bbox is not None:
            x0, y0, x1, y1 = self.bbox
            if self.page is None or not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
                raise ValueError("bbox debe ser una región normalizada de una página")
        return self


class Dimension(Model):
    value: float = Field(gt=0)
    unit: Literal["mm"] = "mm"
    source: Source


class Elevation(Model):
    value: float = Field(ge=0)
    unit: Literal["mm"] = "mm"
    source: Source


class Angle(Model):
    value: float = Field(ge=0, lt=360)
    unit: Literal["deg"] = "deg"
    source: Source


class Attribute(Model):
    value: float | str
    unit: str = Field(min_length=1)
    source: Source


class Tag(Model):
    value: str = Field(min_length=1)
    unit: Literal["1"] = "1"
    source: Source


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


class Equipment(Model):
    id: Identifier
    tag: Tag
    kind: Literal["vertical_vessel"] = "vertical_vessel"
    diameter: Dimension
    height: Dimension  # Longitud de virola entre tangentes, no altura total.
    head_depth: Dimension  # Profundidad común de los dos fondos semielipsoidales.
    skirt_height: Dimension  # Desde suelo hasta la tangente inferior de la virola.
    skirt_thickness: Dimension
    attributes: dict[Identifier, Attribute] = Field(default_factory=dict)
    nozzles: list[Nozzle] = Field(min_length=3)

    @property
    def shell_bottom(self) -> float:
        return self.skirt_height.value

    @property
    def total_height(self) -> float:
        return self.skirt_height.value + self.head_depth.value + self.height.value

    @model_validator(mode="after")
    def check_geometry(self):
        ids = [n.id for n in self.nozzles]
        if len(ids) != len(set(ids)):
            raise ValueError("Las boquillas deben tener identificadores únicos")
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
    timestamp: datetime
    input_sha256: SHA256

    @model_validator(mode="after")
    def check_timezone(self):
        if self.timestamp.tzinfo is None:
            raise ValueError("La fecha de revisión debe incluir zona horaria")
        return self


class Revision(Model):
    schema_version: Literal["0.2"] = "0.2"
    project_id: Identifier
    revision: str = Field(min_length=1)
    dataset: Literal["synthetic", "real"]
    documents: list[Document] = Field(min_length=1)
    equipment: Equipment
    approval: Approval | None = None

    @model_validator(mode="after")
    def check_sources_and_approval(self):
        docs = {d.id: d for d in self.documents}
        if len(docs) != len(self.documents):
            raise ValueError("Los documentos deben tener identificadores únicos")
        for path, field in fields(self.equipment).items():
            document = docs.get(field.source.document_id)
            if document is None:
                raise ValueError(f"{path}: referencia a documento desconocido")
            if document.page_count and field.source.page:
                if field.source.page > document.page_count:
                    raise ValueError(f"{path}: página fuera del documento")
        if self.approval:
            if self.pending_review():
                raise ValueError("La aprobación requiere revisar todos los campos")
            if self.approval.input_sha256 != self.fingerprint():
                raise ValueError("La aprobación no corresponde a estos datos; vuelva a revisar")
        return self

    def pending_review(self) -> list[str]:
        return [p for p, f in fields(self.equipment).items() if not f.source.reviewed]

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
    result.update({k: getattr(equipment, k) for k in GEOMETRY_FIELDS})
    result.update({f"attributes.{k}": v for k, v in equipment.attributes.items()})
    for nozzle in equipment.nozzles:
        for key in ("diameter", "projection", "elevation", "azimuth"):
            result[f"nozzles.{nozzle.id}.{key}"] = getattr(nozzle, key)
    return result


def load_revision(path: Path) -> Revision:
    return Revision.model_validate_json(path.read_text(encoding="utf-8"))
