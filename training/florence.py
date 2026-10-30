"""Ajuste fino de Florence-2 (MIT) como detector + lector de anotaciones de GA (DEC-05).

    uv sync --extra train
    uv run python -m training.florence entrenar --datos generated/train/florence
    uv run python -m training.florence evaluar --datos generated/train/florence_reservado
    uv run python -m training.florence leer --conjunto generated/synthetic_v2/s-reservado

- Modelo base: Florence-2-base (0,23 B parámetros, MIT) en la versión nativa de transformers
  (`florence-community/Florence-2-base`; el código remoto de microsoft/ ya no carga con
  transformers 4.5x). Cabe en 8 GB con bf16.
- Tarea <OCR_WITH_REGION>: el modelo escribe cada texto con su caja.
- Se entrena solo con S-dev (y, el día 1, páginas reales etiquetadas); se mide en S-reservado,
  que nunca ha visto: F1 de detección (IoU ≥ 0,5) y acierto exacto del texto.
- `leer` pasa el detector por las páginas escaneadas y deja las líneas en la caché que lee el
  canal `detector` de D (`trazia.ocr.detector`). El producto no necesita PyTorch.
"""

import argparse
import json
import math
import random
import re
import time
from pathlib import Path

LOC = re.compile(r"<loc_(\d+)>")
BASE_MODEL = "florence-community/Florence-2-base"
OUT_DIR = Path("generated/models/florence2-trazia")


def device_report():
    import torch

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Usando: {device}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"VRAM disponible: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    return device


def parse_regions(sequence: str) -> list[tuple[str, tuple[float, float, float, float]]]:
    """«texto<loc_a><loc_b><loc_c><loc_d>…» → [(texto, caja 0–1)]."""
    out = []
    for match in re.finditer(r"([^<]+)((?:<loc_\d+>){4})", sequence):
        locs = [int(v) / 1000 for v in LOC.findall(match[2])]
        out.append((match[1].strip(), tuple(locs)))
    return out


def load_model(path: str):
    from transformers import AutoProcessor, Florence2ForConditionalGeneration

    processor = AutoProcessor.from_pretrained(path)
    model = Florence2ForConditionalGeneration.from_pretrained(path)
    return processor, model


def _vision_tower(model):
    inner = getattr(model, "model", model)
    return getattr(inner, "vision_tower", None) or model.vision_tower


def train(data: Path, out: Path, *, epochs: int, batch: int, lr: float, seed: int) -> dict:
    import torch
    from PIL import Image

    device = device_report()
    random.seed(seed)
    torch.manual_seed(seed)
    rows = [
        json.loads(line) for line in (data / "train.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    random.shuffle(rows)
    processor, model = load_model(BASE_MODEL)
    model.to(device)
    text_config = getattr(model.config, "text_config", model.config)
    start_token = text_config.decoder_start_token_id
    model.train()
    for p in _vision_tower(
        model
    ).parameters():  # visión congelada: menos memoria, menos sobreajuste
        p.requires_grad = False
    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=lr)
    steps = math.ceil(len(rows) / batch) * epochs
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lambda s: max(0.0, 1 - s / steps))
    started, losses = time.perf_counter(), []
    peak = 0
    for epoch in range(epochs):
        for i in range(0, len(rows), batch):
            chunk = rows[i : i + batch]
            images = [Image.open(data / r["image"]).convert("RGB") for r in chunk]
            inputs = processor(text=[r["task"] for r in chunk], images=images, return_tensors="pt")
            labels = processor.tokenizer(
                [r["target"] for r in chunk],
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=1024,
                return_token_type_ids=False,
            ).input_ids
            pad = processor.tokenizer.pad_token_id
            # Entrada del decodificador explícita y pérdida propia: la versión nativa vuelve a
            # desplazar las etiquetas al calcular la pérdida y el modelo aprendería a saltarse
            # un token.
            decoder_input_ids = torch.cat(
                [torch.full((labels.shape[0], 1), start_token), labels[:, :-1]], dim=1
            )
            labels[labels == pad] = -100
            with torch.autocast(device_type=device.type, dtype=torch.bfloat16):
                logits = model(
                    input_ids=inputs["input_ids"].to(device),
                    pixel_values=inputs["pixel_values"].to(device),
                    decoder_input_ids=decoder_input_ids.to(device),
                ).logits
            loss = torch.nn.functional.cross_entropy(
                logits.float().reshape(-1, logits.shape[-1]),
                labels.to(device).reshape(-1),
                ignore_index=-100,
            )
            loss.backward()
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
            losses.append(loss.item())
            if device.type == "cuda":
                peak = max(peak, torch.cuda.max_memory_allocated() / 1e9)
        recent = losses[-50:]
        print(f"época {epoch + 1}/{epochs} · pérdida media {sum(recent) / len(recent):.3f}")
    out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out)
    processor.save_pretrained(out)
    report = {
        "base": BASE_MODEL,
        "examples": len(rows),
        "epochs": epochs,
        "seconds": round(time.perf_counter() - started),
        "vram_peak_gb": round(peak, 2),
        "final_loss": round(sum(losses[-50:]) / len(losses[-50:]), 4),
        "synthetic_only": all(r.get("synthetic", True) for r in rows),
    }
    (out / "entrenamiento.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def predict(processor, model, images, device) -> list[list[tuple[str, tuple]]]:
    """Regiones leídas en cada imagen de un lote: [(texto, caja 0–1 del mosaico)]."""
    import torch

    inputs = processor(text=["<OCR_WITH_REGION>"] * len(images), images=images, return_tensors="pt")
    with torch.no_grad(), torch.autocast(device_type=device.type, dtype=torch.bfloat16):
        ids = model.generate(
            input_ids=inputs["input_ids"].to(device),
            pixel_values=inputs["pixel_values"].to(device),
            max_new_tokens=1024,
            num_beams=1,
        )
    out = []
    for text in processor.batch_decode(ids, skip_special_tokens=False):
        text = text.replace("</s>", "").replace("<s>", "").replace("<pad>", "")
        out.append(parse_regions(text))
    return out


def evaluate(model_dir: Path, data: Path, limit: int | None, batch: int = 8) -> dict:
    """F1 de detección (IoU ≥ 0,5) y acierto exacto del texto sobre mosaicos con verdad."""
    from PIL import Image

    device = device_report()
    processor, model = load_model(str(model_dir))
    model.to(device).eval()
    rows = [
        json.loads(line) for line in (data / "train.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    tp = fp = fn = exact = 0
    started = time.perf_counter()
    chosen = rows[:limit]
    predictions = []
    for i in range(0, len(chosen), batch):
        images = [Image.open(data / r["image"]).convert("RGB") for r in chosen[i : i + batch]]
        predictions += predict(processor, model, images, device)
    for row, found in zip(chosen, predictions):
        truth = parse_regions(row["target"])
        used = set()
        for text, box in found:
            match = next(
                (i for i, (_, b) in enumerate(truth) if i not in used and _iou(box, b) >= 0.5), None
            )
            if match is None:
                fp += 1
                continue
            used.add(match)
            tp += 1
            exact += text.replace(" ", "") == truth[match][0].replace(" ", "")
        fn += len(truth) - len(used)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "tiles": min(len(rows), limit or len(rows)),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(2 * precision * recall / (precision + recall), 4)
        if precision + recall
        else 0.0,
        "text_exact": round(exact / tp, 4) if tp else 0.0,
        "seconds_per_tile": round(
            (time.perf_counter() - started) / max(1, min(len(rows), limit or len(rows))), 2
        ),
    }


READ_SCORE = 0.8  # Florence-2 no da probabilidad por región; la calibración la ajusta por canal


def _tile_boxes(width: int, height: int, tile: int = 768, overlap: float = 0.2):
    """La misma rejilla que los mosaicos de entrenamiento (training.dataset.tiles_of)."""
    step = int(tile * (1 - overlap))
    xs = sorted(set(list(range(0, max(1, width - tile), step)) + [max(0, width - tile)]))
    ys = sorted(set(list(range(0, max(1, height - tile), step)) + [max(0, height - tile)]))
    return [(x, y, min(width, x + tile), min(height, y + tile)) for y in ys for x in xs]


def _dedupe(found):
    """Un texto visto en dos mosaicos solapados cuenta una vez; gana la lectura más larga."""
    kept = []
    for text, box in sorted(found, key=lambda f: -len(f[0])):
        area = max(1e-12, (box[2] - box[0]) * (box[3] - box[1]))
        duplicate = False
        for _, other in kept:
            ix = max(0.0, min(box[2], other[2]) - max(box[0], other[0]))
            iy = max(0.0, min(box[3], other[3]) - max(box[1], other[1]))
            if ix * iy / area > 0.5:
                duplicate = True
                break
        if not duplicate:
            kept.append((text, box))
    return sorted(kept, key=lambda f: (f[1][1], f[1][0]))


def read_pages(
    model_dir: Path, root: Path, styles: list[str], *, batch: int, limit: int | None
) -> dict:
    """Lee las páginas GA de los estilos dados y deja las líneas en la caché del detector."""
    import pdfplumber

    from trazia.ocr.detector import DPI, cache_path, page_key, store_page

    device = device_report()
    processor, model = load_model(str(model_dir))
    model.to(device).eval()
    name = model_dir.name
    paths = sorted(p for style in styles for p in (root / style).glob("*/GAD_*.pdf"))[:limit]
    started, pages, cached, regions = time.perf_counter(), 0, 0, 0
    for pdf_path in paths:
        data = pdf_path.read_bytes()
        with pdfplumber.open(pdf_path) as pdf:
            for number, page in enumerate(pdf.pages, start=1):
                key = page_key(data, number, dpi=DPI, model=name)
                if cache_path(key).exists():
                    cached += 1
                    continue
                image = page.to_image(resolution=DPI).original.convert("RGB")
                width, height = image.size
                boxes = _tile_boxes(width, height)
                found = []
                for i in range(0, len(boxes), batch):
                    chunk = boxes[i : i + batch]
                    crops = [image.crop(b) for b in chunk]
                    for (x0, y0, x1, y1), tile in zip(
                        chunk, predict(processor, model, crops, device)
                    ):
                        w, h = x1 - x0, y1 - y0
                        for text, (a, b, c, d) in tile:
                            if text and c > a and d > b:
                                found.append(
                                    (
                                        text,
                                        (
                                            (x0 + a * w) / width,
                                            (y0 + b * h) / height,
                                            (x0 + c * w) / width,
                                            (y0 + d * h) / height,
                                        ),
                                    )
                                )
                lines = [
                    {"text": t, "bbox": [round(v, 5) for v in box], "score": READ_SCORE}
                    for t, box in _dedupe(found)
                ]
                store_page(key, lines)
                pages += 1
                regions += len(lines)
        print(f"{pdf_path.parent.parent.name}/{pdf_path.name}: {pages} páginas leídas")
    seconds = time.perf_counter() - started
    return {
        "model": name,
        "documents": len(paths),
        "pages_read": pages,
        "pages_cached": cached,
        "regions": regions,
        "seconds_per_page": round(seconds / pages, 2) if pages else None,
    }


def _iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Detector propio con Florence-2")
    sub = parser.add_subparsers(dest="command", required=True)
    t = sub.add_parser("entrenar")
    t.add_argument("--datos", type=Path, default=Path("generated/train/florence"))
    t.add_argument("--salida", type=Path, default=OUT_DIR)
    t.add_argument("--epocas", type=int, default=2)
    t.add_argument("--lote", type=int, default=4)
    t.add_argument("--lr", type=float, default=1e-5)
    t.add_argument("--semilla", type=int, default=2026)
    e = sub.add_parser("evaluar")
    e.add_argument("--modelo", type=Path, default=OUT_DIR)
    e.add_argument("--datos", type=Path, default=Path("generated/train/florence_reservado"))
    e.add_argument("--mosaicos", type=int, default=200)
    e.add_argument("--lote", type=int, default=8)
    r = sub.add_parser("leer")
    r.add_argument("--modelo", type=Path, default=OUT_DIR)
    r.add_argument("--conjunto", type=Path, default=Path("generated/synthetic_v2/s-reservado"))
    r.add_argument("--estilos", nargs="+", default=["escaneado_limpio", "escaneado_pobre"])
    r.add_argument("--lote", type=int, default=6)
    r.add_argument("--documentos", type=int, default=None)
    args = parser.parse_args(argv)
    if args.command == "entrenar":
        print(
            json.dumps(
                train(
                    args.datos,
                    args.salida,
                    epochs=args.epocas,
                    batch=args.lote,
                    lr=args.lr,
                    seed=args.semilla,
                ),
                indent=2,
            )
        )
    elif args.command == "evaluar":
        print(json.dumps(evaluate(args.modelo, args.datos, args.mosaicos, args.lote), indent=2))
    else:
        report = read_pages(
            args.modelo, args.conjunto, args.estilos, batch=args.lote, limit=args.documentos
        )
        print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
