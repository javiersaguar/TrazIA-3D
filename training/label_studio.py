"""Páginas reales etiquetadas el día 1 en Label Studio → mismo formato que `training.dataset`.

    uv run python -m training.label_studio export.json --imagenes data/private/paginas \\
        --salida data/private/train_real

Configuración de etiquetado esperada en Label Studio (una región por texto del plano):

    <View>
      <Image name="image" value="$image"/>
      <RectangleLabels name="label" toName="image">
        <Label value="cota"/><Label value="celda"/><Label value="rotulo"/><Label value="marca"/>
      </RectangleLabels>
      <TextArea name="transcription" toName="image" perRegion="true"/>
    </View>

Label Studio exporta las cajas en porcentaje (0–100) de la imagen. Los datos reales se quedan en
`data/private/` (fuera de Git) y nunca se envían a un tercero (DEC-31).
"""

import argparse
import json
from pathlib import Path

from PIL import Image

from .dataset import TASK, tiles_of


def regions(task: dict) -> list[tuple[str, tuple[float, float, float, float]]]:
    """(texto, caja en % de la imagen) de cada región transcrita de una tarea exportada."""
    annotations = task.get("annotations") or []
    if not annotations:
        return []
    result = annotations[0].get("result", [])
    boxes, texts = {}, {}
    for item in result:
        value = item.get("value", {})
        if item.get("type") == "rectanglelabels":
            boxes[item["id"]] = (
                value["x"],
                value["y"],
                value["x"] + value["width"],
                value["y"] + value["height"],
            )
        elif item.get("type") == "textarea":
            texts[item["id"]] = " ".join(value.get("text", [])).strip()
    return [(texts[i], boxes[i]) for i in boxes if texts.get(i)]


def convert(export: Path, images: Path, out: Path) -> list[dict]:
    tasks = json.loads(export.read_text(encoding="utf-8"))
    (out / "images").mkdir(parents=True, exist_ok=True)
    rows = []
    for task in tasks:
        name = Path(str(task["data"]["image"]).split("?")[0]).name.split("-", 1)[-1]
        path = images / name
        if not path.exists():
            continue
        image = Image.open(path).convert("RGB")
        w, h = image.size
        items = [
            (text, (x0 / 100 * w, y0 / 100 * h, x1 / 100 * w, y1 / 100 * h))
            for text, (x0, y0, x1, y1) in regions(task)
        ]
        for k, (tile, target) in enumerate(tiles_of(image, items, None)):
            tile_name = f"{path.stem}_t{k}.png"
            tile.save(out / "images" / tile_name)
            rows.append(
                {"image": f"images/{tile_name}", "task": TASK, "target": target, "synthetic": False}
            )
    (out / "train.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8"
    )
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Label Studio → datos del detector")
    parser.add_argument("export", type=Path)
    parser.add_argument("--imagenes", type=Path, required=True)
    parser.add_argument("--salida", type=Path, default=Path("data/private/train_real"))
    args = parser.parse_args(argv)
    rows = convert(args.export, args.imagenes, args.salida)
    print(f"{len(rows)} mosaicos reales en {args.salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
