"""Ajuste fino de Florence-2 (MIT) como detector + lector de anotaciones de GA (DEC-05).

    uv sync --extra train
    uv run python -m training.florence entrenar --datos generated/train/florence
    uv run python -m training.florence evaluar --conjunto generated/synthetic_v2/s-reservado

- Modelo base: microsoft/Florence-2-base (0,23 B parámetros, MIT): cabe en 8 GB con bf16.
- Tarea <OCR_WITH_REGION>: el modelo escribe cada texto con su caja.
- Se entrena solo con S-dev (y, el día 1, páginas reales etiquetadas); se mide en S-reservado,
  que nunca ha visto: F1 de detección (IoU ≥ 0,5) y acierto exacto del texto.
"""

import argparse
import json
import math
import random
import re
import time
from pathlib import Path

LOC = re.compile(r"<loc_(\d+)>")
BASE_MODEL = "microsoft/Florence-2-base"
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
    from transformers import AutoModelForCausalLM, AutoProcessor

    processor = AutoProcessor.from_pretrained(path, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(path, trust_remote_code=True)
    return processor, model


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
    model.train()
    for p in model.vision_tower.parameters():  # visión congelada: menos memoria, menos sobreajuste
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
            labels[labels == processor.tokenizer.pad_token_id] = -100
            with torch.autocast(device_type=device.type, dtype=torch.bfloat16):
                loss = model(
                    input_ids=inputs["input_ids"].to(device),
                    pixel_values=inputs["pixel_values"].to(device),
                    labels=labels.to(device),
                ).loss
            loss.backward()
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
            losses.append(float(loss))
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


def predict(processor, model, image, device) -> list[tuple[str, tuple[float, float, float, float]]]:
    import torch

    inputs = processor(text="<OCR_WITH_REGION>", images=image, return_tensors="pt")
    with torch.no_grad(), torch.autocast(device_type=device.type, dtype=torch.bfloat16):
        ids = model.generate(
            input_ids=inputs["input_ids"].to(device),
            pixel_values=inputs["pixel_values"].to(device),
            max_new_tokens=1024,
            num_beams=1,
        )
    text = processor.batch_decode(ids, skip_special_tokens=False)[0]
    text = text.replace("</s>", "").replace("<s>", "").replace("<pad>", "")
    return parse_regions(text)


def evaluate(model_dir: Path, data: Path, limit: int | None) -> dict:
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
    for row in rows[:limit]:
        truth = parse_regions(row["target"])
        found = predict(processor, model, Image.open(data / row["image"]).convert("RGB"), device)
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
    else:
        print(json.dumps(evaluate(args.modelo, args.datos, args.mosaicos), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
