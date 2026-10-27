"""Datos de entrenamiento del detector propio (DEC-05): mosaicos con texto y caja de cada anotación.

    uv run python -m training.dataset --conjunto generated/synthetic_v2/s-dev

- Fuente: las páginas GA vectoriales de S-dev. La capa de texto da el texto y la caja exacta de
  cada anotación (cotas, celdas, rótulos), sin etiquetado manual.
- Aleatorización de dominio por imagen: resolución, desenfoque, ruido, contraste, JPEG y un giro
  pequeño. Las cajas se transforman con el mismo giro.
- Mosaicos de 768 px con solape; cada uno lleva la secuencia objetivo de Florence-2 para la tarea
  <OCR_WITH_REGION>: «texto<loc_x1><loc_y1><loc_x2><loc_y2>…» con coordenadas 0–999.

Nunca usa S-reservado: ese conjunto solo mide (DEC-21).
"""

import argparse
import io
import json
import math
import random
from pathlib import Path

import pdfplumber
from PIL import Image, ImageEnhance, ImageFilter

TILE = 768
OVERLAP = 0.2
TASK = "<OCR_WITH_REGION>"


def _page_lines(page) -> list[tuple[str, tuple[float, float, float, float]]]:
    """Texto y caja (pt, origen arriba) de cada línea, separadas como en la ingesta."""
    out = []
    for row in page.extract_text_lines(return_chars=True):
        groups = [[]]
        for char in sorted(row["chars"], key=lambda c: c["x0"]):
            if groups[-1] and char["x0"] - groups[-1][-1]["x1"] > 12:
                groups.append([])
            groups[-1].append(char)
        for group in groups:
            text = "".join(
                (" " if i and c["x0"] - group[i - 1]["x1"] > 1.0 else "") + c["text"]
                for i, c in enumerate(group)
            ).strip()
            if text:
                box = (
                    min(c["x0"] for c in group),
                    min(c["top"] for c in group),
                    max(c["x1"] for c in group),
                    max(c["bottom"] for c in group),
                )
                out.append((text, box))
    out = _merge_vertical(out)
    # Textos superpuestos (etiquetas encima unas de otras): ambiguos, fuera del objetivo.
    clean = []
    for i, (text, box) in enumerate(out):
        if not any(i != j and _iou(box, other) > 0.3 for j, (_, other) in enumerate(out)):
            clean.append((text, box))
    return clean


def _iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def _merge_vertical(items):
    """Texto girado 90°: pdfplumber lo entrega en trozos apilados y al revés. Se unen y se pone
    en su orden de lectura, que es lo que el detector debe aprender a escribir."""
    vertical = [(t, b) for t, b in items if (b[3] - b[1]) > 1.5 * (b[2] - b[0])]
    rest = [(t, b) for t, b in items if (b[3] - b[1]) <= 1.5 * (b[2] - b[0])]
    vertical.sort(key=lambda it: (round(it[1][0]), it[1][1]))
    merged = []
    for text, box in vertical:
        if merged:
            last_text, last = merged[-1]
            if abs(last[0] - box[0]) < 1 and 0 <= box[1] - last[3] < 5:
                merged[-1] = (
                    f"{last_text} {text}",
                    (last[0], last[1], max(last[2], box[2]), box[3]),
                )
                continue
        merged.append((text, box))
    return rest + [(text[::-1], box) for text, box in merged]


def augment(image: Image.Image, rng: random.Random) -> tuple[Image.Image, float]:
    """Aleatorización de dominio. Devuelve la imagen y el giro aplicado (grados)."""
    image = image.convert("L")
    angle = rng.uniform(-1.5, 1.5) if rng.random() < 0.7 else 0.0
    if angle:
        image = image.rotate(angle, resample=Image.Resampling.BICUBIC, expand=False, fillcolor=255)
    if rng.random() < 0.8:
        image = image.filter(ImageFilter.GaussianBlur(rng.uniform(0.0, 1.0)))
    if rng.random() < 0.8:
        noise = Image.effect_noise(image.size, rng.uniform(10, 50)).convert("L")
        image = Image.blend(image, noise, rng.uniform(0.0, 0.15))
    if rng.random() < 0.5:
        image = ImageEnhance.Contrast(image).enhance(rng.uniform(0.6, 1.2))
    if rng.random() < 0.5:
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", quality=rng.randint(25, 85))
        image = Image.open(io.BytesIO(buffer.getvalue())).convert("L")
    return image.convert("RGB"), angle


def _rotate_box(box, angle, size, scale):
    """Caja en pt → caja en px de la imagen girada `angle` grados alrededor de su centro."""
    w, h = size
    cx, cy = w / 2, h / 2
    a = math.radians(-angle)  # PIL gira en sentido antihorario con y hacia abajo
    corners = [(box[0], box[1]), (box[2], box[1]), (box[0], box[3]), (box[2], box[3])]
    pts = []
    for x, y in corners:
        x, y = x * scale - cx, y * scale - cy
        pts.append((cx + x * math.cos(a) - y * math.sin(a), cy + x * math.sin(a) + y * math.cos(a)))
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def target_sequence(items, tile_box) -> str:
    """Secuencia de Florence-2: texto y cuatro <loc_k> (0–999) relativos al mosaico."""
    x0, y0, x1, y1 = tile_box
    w, h = x1 - x0, y1 - y0
    parts = []
    for text, (a, b, c, d) in sorted(items, key=lambda it: (it[1][1], it[1][0])):
        locs = [
            min(999, max(0, int((a - x0) / w * 1000))),
            min(999, max(0, int((b - y0) / h * 1000))),
            min(999, max(0, int((c - x0) / w * 1000))),
            min(999, max(0, int((d - y0) / h * 1000))),
        ]
        parts.append(text + "".join(f"<loc_{v}>" for v in locs))
    return "".join(parts)


def tiles_of(image: Image.Image, items, rng: random.Random):
    w, h = image.size
    step = int(TILE * (1 - OVERLAP))
    xs = list(range(0, max(1, w - TILE), step)) + [max(0, w - TILE)]
    ys = list(range(0, max(1, h - TILE), step)) + [max(0, h - TILE)]
    for top in sorted(set(ys)):
        for left in sorted(set(xs)):
            box = (left, top, min(w, left + TILE), min(h, top + TILE))
            inside = [
                (text, b)
                for text, b in items
                if b[0] >= box[0] and b[1] >= box[1] and b[2] <= box[2] and b[3] <= box[3]
            ]
            if inside:
                yield image.crop(box), target_sequence(inside, box)


def build(
    dataset: Path,
    out: Path,
    *,
    copies: int = 2,
    seed: int = 2026,
    limit: int | None = None,
    evaluation: bool = False,
):
    rng = random.Random(seed)
    manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("set") == "s-reservado" and not evaluation:
        raise ValueError("S-reservado nunca se usa para entrenar (DEC-21); usa --evaluacion")
    (out / "images").mkdir(parents=True, exist_ok=True)
    rows = []
    for case in manifest["cases"][:limit]:
        tag = case["tag"]
        truth = json.loads((dataset / "truth" / f"{tag}.json").read_text(encoding="utf-8"))
        for rev in ("1", "2"):
            pdf_path = dataset / "vectorial" / tag / f"GAD_{tag}_rev{rev}.pdf"
            with pdfplumber.open(pdf_path) as pdf:
                for number in truth["documents"][rev]["ga_pages"]:
                    page = pdf.pages[number - 1]
                    lines = _page_lines(page)
                    for copy in range(copies):
                        dpi = rng.choice((120, 150, 200))
                        scale = dpi / 72
                        image = page.to_image(resolution=dpi).original
                        image, angle = augment(image, rng)
                        items = [
                            (text, _rotate_box(box, angle, image.size, scale))
                            for text, box in lines
                        ]
                        for k, (tile, target) in enumerate(tiles_of(image, items, rng)):
                            name = f"{tag}_r{rev}_p{number}_c{copy}_t{k}.png"
                            tile.save(out / "images" / name)
                            rows.append(
                                {
                                    "image": f"images/{name}",
                                    "task": TASK,
                                    "target": target,
                                    "vendor": truth.get("vendor"),
                                    "synthetic": True,
                                }
                            )
    (out / "train.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8"
    )
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Datos del detector propio (Florence-2)")
    parser.add_argument("--conjunto", type=Path, default=Path("generated/synthetic_v2/s-dev"))
    parser.add_argument("--salida", type=Path, default=Path("generated/train/florence"))
    parser.add_argument("--copias", type=int, default=2)
    parser.add_argument("--casos", type=int, default=None)
    parser.add_argument(
        "--evaluacion", action="store_true", help="Mosaicos para medir (permite S-reservado)"
    )
    args = parser.parse_args(argv)
    rows = build(
        args.conjunto, args.salida, copies=args.copias, limit=args.casos, evaluation=args.evaluacion
    )
    print(f"{len(rows)} mosaicos en {args.salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
