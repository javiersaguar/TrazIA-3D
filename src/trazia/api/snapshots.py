from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import Field

from trazia.bcf_snapshot import snapshot_bcf
from trazia.model import Model

router = APIRouter()


class Snapshot(Model):
    png_base64: str = Field(max_length=7_000_000)
    eye: list[float] = Field(min_length=3, max_length=3)
    target: list[float] = Field(min_length=3, max_length=3)
    up: list[float] = Field(min_length=3, max_length=3)
    zoom: float = Field(ge=5, le=650)
    viewport_height: float = Field(gt=0, le=10000)
    guid: str = Field(pattern=r"^[A-Za-z0-9_$]{22}$")
    actor: str = Field(default="Revisor sin identificar", min_length=2, max_length=100)


@router.post("/viewer/bcf")
def bcf(data: Snapshot):
    try:
        content = snapshot_bcf(data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return Response(
        content,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="vista_DRAFT.bcfzip"'},
    )
