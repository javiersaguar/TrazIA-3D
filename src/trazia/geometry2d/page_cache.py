"""Geometría sin identidad documental: se vuelve a anclar al documento actual al medir."""

import io
from dataclasses import asdict

import pdfplumber

from ..page_cache import memo_page
from .vector import Elevation, ElevationStub, Plan, PlanStub, find_elevation, find_plan


def encode(result):
    if result is None:
        return None
    elevation, plan = result
    return {"elevation": asdict(elevation), "plan": asdict(plan) if plan else None}


def decode(data):
    if data is None:
        return None
    e, p = data["elevation"], data["plan"]
    elevation = Elevation(
        tuple(e["shell"]),
        e["head_top"],
        e["head_bottom"],
        e["ground"],
        [ElevationStub(s["side"], s["z"], s["neck"], tuple(s["end"])) for s in e["stubs"]],
    )
    plan = (
        None
        if p is None
        else Plan(
            tuple(p["center"]),
            p["radius"],
            [PlanStub(s["angle"], s["length"], s["neck"], tuple(s["end"])) for s in p["stubs"]],
        )
    )
    return elevation, plan


def vector_geometry(page):
    def compute():
        elevation = find_elevation(page)
        return encode((elevation, find_plan(page, elevation.shell))) if elevation else None

    return decode(memo_page(page, "vector-geometry-v1", compute))


def raster_geometry(data, number, compute, *, dpi):
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        return decode(
            memo_page(
                pdf.pages[number - 1], "raster-geometry-v1", lambda: encode(compute()), dpi=dpi
            )
        )
