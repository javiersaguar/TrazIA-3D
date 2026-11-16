"""Prepara la evidencia PDF y los fotogramas de las revisiones IFC sintéticas."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

PITCH = Path(__file__).resolve().parents[1]
ROOT = PITCH.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from make_family_thumbnails import paint_triangle  # noqa: E402

SIZE = 832
OUTPUT = PITCH / "public" / "media"
WORK = PITCH / "generated"


def unit(vector):
    return vector / np.linalg.norm(vector)


CAMERA = unit(np.array([4.8, -8.0, 2.8]))
RIGHT = unit(np.cross([0.0, 0.0, 1.0], CAMERA))
UP = np.cross(CAMERA, RIGHT)
VIEW = np.stack((RIGHT, -UP, CAMERA), axis=1)
KEY = unit(np.array([-4.0, -6.0, 9.0]))
RIM = unit(np.array([6.0, 4.0, 2.0]))


def render(parts, center, scale):
    depth = np.full((SIZE, SIZE), -np.inf)
    target = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    for part in parts:
        vertices = np.asarray(part["positions"])
        faces = np.asarray(part["indices"]).reshape(-1, 3)
        triangles = vertices[faces]
        normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
        front = normals @ CAMERA > 1e-12
        normals = normals[front]
        normals /= np.linalg.norm(normals, axis=1)[:, None]
        reflected = np.maximum(normals @ unit(KEY + CAMERA), 0) ** 22
        shine = (
            0.30
            + 0.54 * np.maximum(normals @ KEY, 0)
            + 0.24 * reflected
            + 0.18 * np.maximum(normals @ RIM, 0)
        )
        colors = np.clip(shine[:, None] * np.array([197, 217, 231]), 0, 255).astype(np.uint8)
        screen = vertices @ VIEW
        screen[:, :2] = (screen[:, :2] - center) * scale + SIZE / 2
        for face, rgb in zip(faces[front], colors):
            paint_triangle(screen[face], (*rgb, 255), depth, target)
    image = Image.fromarray(target)
    if image.getbbox() is None:
        raise ValueError("El IFC no produjo ningún píxel visible")
    return image


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    source = ROOT / "examples" / "documents" / "GAD_V-101_revB.pdf"
    subprocess.run(
        ["pdftoppm", "-png", "-scale-to", "1800", "-singlefile", source, WORK / "ga"],
        check=True,
    )
    shutil.copyfile(source, OUTPUT / "GA-V101-B.pdf")
    plan = Image.open(WORK / "ga.png").convert("RGB")
    plan.save(OUTPUT / "ga.webp", quality=88, method=6)

    model = json.loads((ROOT / "examples" / "vessel_rev_b.json").read_text(encoding="utf8"))
    field = model["equipment"]["height"]
    x0, y0, x1, y1 = np.array(field["source"]["bbox"]) * ([plan.width, plan.height] * 2)
    left, top = round(x0 - 26), round(y0 - 64)
    crop = plan.crop((left, top, round(x1 + 220), round(y1 + 65)))
    ImageDraw.Draw(crop).rounded_rectangle(
        (x0 - left - 6, y0 - top - 5, x1 - left + 6, y1 - top + 5),
        radius=4,
        outline="#035793",
        width=3,
    )
    crop.save(OUTPUT / "evidence.webp", quality=91, method=6)
    shutil.copyfile(ROOT / "web" / "src" / "app" / "icon.svg", OUTPUT / "brand.svg")

    models = [json.loads((WORK / f"rev-{rev}.json").read_text()) for rev in ("a", "b")]
    xy = np.concatenate([part["positions"] for parts in models for part in parts]) @ VIEW[:, :2]
    low, high = xy.min(axis=0), xy.max(axis=0)
    center = (low + high) / 2
    scale = SIZE * 0.93 / max(high - low)
    for rev, parts in zip(("a", "b"), models):
        image = render(parts, center, scale)
        image.save(OUTPUT / f"ifc-{rev}.webp", quality=93, method=6)
        if rev == "b":
            alpha = image.getchannel("A")
            outer = alpha.filter(ImageFilter.MaxFilter(7))
            inner = alpha.filter(ImageFilter.MinFilter(5))
            outline = Image.new("RGBA", image.size, (92, 196, 255, 255))
            outline.putalpha(ImageChops.subtract(outer, inner))
            outline.save(OUTPUT / "ifc-contour.webp", lossless=True, method=6)
    print(f"Medios en {OUTPUT}")


if __name__ == "__main__":
    main()
