"""Borradores IFC efímeros de los proyectos sintéticos del catálogo."""

import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
from typing import Literal

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat

router = APIRouter()
generator_lock = Lock()


class Adjustment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tag: str = Field(max_length=20)
    field: Literal["length", "width", "height", "dn", "rack_z"]
    value: FiniteFloat


class PreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    applied: list[str] = Field(default_factory=list, max_length=4)
    adjustments: list[Adjustment] = Field(min_length=1, max_length=8)


@router.post("/proyectos-proceso/{project_id}/borrador", response_class=Response)
def preview_process(project_id: str, body: PreviewRequest) -> Response:
    from trazia.process_catalog.process_geometry import apply_changes, scene
    from trazia.process_catalog.process_ifc import MAX_IFC_BYTES, create_ifc
    from trazia.process_catalog.process_mesh import clear_templates
    from trazia.process_catalog.process_projects import PROJECTS, SIZE_AXIS, Change, edit_fields

    project = next((item for item in PROJECTS if item.id == project_id), None)
    if project is None:
        raise HTTPException(404, "Proyecto sintético desconocido.")
    applied = set(body.applied)
    if not applied <= {change.tag for change in project.changes}:
        raise HTTPException(422, "Uno de los cambios de revisión no pertenece a este proyecto.")
    equipment, lines = apply_changes(project, applied)
    seen = set()
    adjustments = []
    for edit in body.adjustments:
        bounds = edit_fields(project, edit.tag).get(edit.field)
        if not bounds or not bounds["min"] <= edit.value <= bounds["max"]:
            raise HTTPException(422, f"{edit.tag}: el valor está fuera del intervalo de ensayo.")
        if (edit.tag, edit.field) in seen:
            raise HTTPException(422, f"{edit.tag}: hay dos valores para el mismo parámetro.")
        seen.add((edit.tag, edit.field))
        if edit.field == "dn" and not edit.value.is_integer():
            raise HTTPException(422, "El diámetro nominal debe expresarse en milímetros enteros.")
        before = (
            equipment[edit.tag].size[SIZE_AXIS[edit.field]]
            if edit.tag in equipment
            else getattr(lines[edit.tag], edit.field)
        )
        value = round(edit.value, 0 if edit.field == "dn" else 2)
        if value != before:
            adjustments.append(
                Change(
                    edit.tag,
                    "Ensayo de diseño",
                    edit.field,
                    before,
                    value,
                    "mm" if edit.field == "dn" else "m",
                )
            )
    if not adjustments:
        raise HTTPException(422, "Introduce al menos un valor diferente de la revisión base.")
    if not generator_lock.acquire(blocking=False):
        raise HTTPException(
            429, "Ya se está generando un IFC. Vuelve a intentarlo en unos segundos."
        )
    filename = f"{project.code}-ENSAYO-DRAFT.ifc"
    try:
        with TemporaryDirectory(prefix="trazia-planta-") as directory:
            path = Path(directory) / filename
            create_ifc(path, project, "Ensayo", *scene(project, applied, adjustments))
            if path.stat().st_size > MAX_IFC_BYTES:
                raise ValueError("El borrador supera el tamaño permitido")
            content = path.read_bytes()
    except ValueError:
        logging.getLogger(__name__).warning("Borrador de planta rechazado", exc_info=True)
        raise HTTPException(
            422, "La combinación introduce una geometría o un IFC inválidos."
        ) from None
    finally:
        clear_templates()
        generator_lock.release()
    return Response(
        content,
        media_type="application/x-step",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
