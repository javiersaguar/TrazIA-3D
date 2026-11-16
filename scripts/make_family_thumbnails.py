"""Renderiza las miniaturas WebP desde las mallas paramétricas del catálogo."""

import json
from pathlib import Path

import numpy as np
from design_variants import VARIANTS
from industrial_designs import FAMILIES
from make_industrial_designs import mesh
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "web/public/demo/familias"
RESOLUTION = 216
SAMPLES = 3
# Escoger un diseño con silueta reconocible por familia.
REPRESENTATIVES = (
    "BC-V103",
    "BC-H103",
    "BC-C104",
    "BC-E103",
    "BC-T103",
    "BC-P103",
    "BC-K103",
    "BC-G103",
    "BC-AC104",
    "BC-EV101",
    "BC-FI102",
    "BC-CE104",
    "BC-CY102",
    "BC-SE101",
    "BC-ME104",
    "BC-DO103",
    "BC-TR103",
    "BC-EX103",
)
PALETTE = np.array(
    [
        [148, 184, 207],
        [189, 207, 220],
        [104, 163, 198],
        [166, 192, 211],
        [111, 151, 177],
    ]
)


def unit(vector):
    return vector / np.linalg.norm(vector)


CAMERA = unit(np.array([5.0, -8.0, 5.0]))
RIGHT = unit(np.cross([0.0, 0.0, 1.0], CAMERA))
UP = np.cross(CAMERA, RIGHT)
PROJECTION = np.stack((RIGHT, -UP, CAMERA), axis=1)
LIGHT = unit(np.array([-4.0, -7.0, 11.0]))


def paint_triangle(screen, color, depth, pixels):
    """Interpola la profundidad por píxel para resolver las oclusiones de las piezas."""
    size = depth.shape[0]
    start = np.maximum(np.floor(screen[:, :2].min(axis=0)).astype(int), 0)
    end = np.minimum(np.ceil(screen[:, :2].max(axis=0)).astype(int), size - 1)
    x0, y0 = start
    x1, y1 = end
    if x1 < x0 or y1 < y0:
        return
    a, b, c = screen
    u = b - a
    v = c - a
    area = u[0] * v[1] - u[1] * v[0]
    if abs(area) < 1e-8:
        return
    yy, xx = np.ogrid[y0 : y1 + 1, x0 : x1 + 1]
    x, y = xx + 0.5 - a[0], yy + 0.5 - a[1]
    b_weight = (x * v[1] - y * v[0]) / area
    c_weight = (u[0] * y - u[1] * x) / area
    z = a[2] + b_weight * u[2] + c_weight * v[2]
    region = depth[y0 : y1 + 1, x0 : x1 + 1]
    mask = (b_weight >= -1e-8) & (c_weight >= -1e-8) & (b_weight + c_weight <= 1 + 1e-8)
    draw = mask & (z > region)
    region[draw] = z[draw]
    pixels[y0 : y1 + 1, x0 : x1 + 1][draw] = color


def render(design):
    parts = [mesh(part, design.size) for part in design.parts]
    points = [np.asarray(part["vertices"]) for part in parts]
    projected = [vertices @ PROJECTION for vertices in points]
    xy = np.concatenate(projected)[:, :2]
    low, high = xy.min(axis=0), xy.max(axis=0)
    side = RESOLUTION * SAMPLES
    scale = side * 0.80 / max(high - low)
    depth = np.full((side, side), -np.inf)
    pixels = np.zeros((side, side, 4), dtype=np.uint8)
    for i, (part, vertices, screen) in enumerate(zip(parts, points, projected)):
        screen[:, :2] = (screen[:, :2] - (high + low) / 2) * scale + side / 2
        for face in part["triangles"]:
            indices = list(face)
            a, b, c = vertices[indices]
            normal = np.cross(b - a, c - a)
            if normal @ CAMERA <= 0:
                continue
            normal = unit(normal)
            diffuse = max(normal @ LIGHT, 0)
            shade = 0.67 + 0.29 * diffuse + 0.11 * max(normal[2], 0)
            rgb = np.clip(PALETTE[i % len(PALETTE)] * shade, 0, 255).astype(np.uint8)
            paint_triangle(screen[indices], (*rgb, 255), depth, pixels)

    surface = Image.fromarray(pixels)
    contour = Image.new("RGBA", surface.size, (21, 44, 62, 255))
    contour.putalpha(surface.getchannel("A").filter(ImageFilter.MaxFilter(7)))
    image = Image.alpha_composite(contour, surface)
    return image.resize((RESOLUTION, RESOLUTION), Image.Resampling.LANCZOS)


def main():
    by_tag = {
        design.tag: (family_id, design)
        for family_id, designs in (
            [(family.id, family.designs) for family in FAMILIES] + list(VARIANTS.items())
        )
        for design in designs
    }
    metadata = {by_tag[tag][0]: tag for tag in REPRESENTATIVES}
    if len(metadata) != len(REPRESENTATIVES) or metadata.keys() != {f for f, _ in by_tag.values()}:
        raise ValueError("Cada familia debe tener exactamente un diseño representativo")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for family, tag in metadata.items():
        render(by_tag[tag][1]).save(OUTPUT / f"{family}.webp", quality=88, method=6)
    index = ROOT / "web/src/features/bocetos/family-thumbnails.json"
    index.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
