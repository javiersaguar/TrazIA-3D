"""Medición de PaddleOCR-VL en la GPU local (tareas 2.2 y 0.10).

    uv sync --extra train
    uv run python -m training.paddle_vl --paginas 10

Mismas condiciones que la tabla 0.10 de docs/PLATAFORMA.md: primeras páginas GA de S-dev
(escaneado limpio), 150 ppp y mosaicos de 1.280 px con solape del 15 %. Se carga en bf16 con la
clase nativa de transformers 5 (PaddlePaddle/PaddleOCR-VL, Apache-2.0). El código remoto del
repositorio no funciona con transformers 4.55 ni 4.57: en 4.57, con un parche de nombres, cada
token tarda 1,5 s y la VRAM desborda. La VRAM de pico es la que reserva PyTorch y la que ve
nvidia-smi (incluye lo que ya hubiera en la GPU).

Solo mide: tiempo por página, VRAM y textos leídos. Integrarlo como motor de `trazia.ocr` queda
condicionado a estas cifras.
"""

import argparse
import json
import subprocess
import threading
import time
from pathlib import Path

MODEL = "PaddlePaddle/PaddleOCR-VL"


def _vram_mib() -> int | None:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout
        return int(out.strip().splitlines()[0])
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
        return None


class VramMonitor:
    def __init__(self):
        self.peak = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        while not self._stop.is_set():
            self.peak = max(self.peak, _vram_mib() or 0)
            time.sleep(0.25)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        self._thread.join(timeout=2)


def tile_boxes(width: int, height: int, size: int = 1280, overlap: float = 0.15):
    step = max(1, int(size * (1 - overlap)))

    def starts(total):
        if total <= size:
            return [0]
        return sorted(set(list(range(0, total - size, step)) + [total - size]))

    return [
        (x, y, min(width, x + size), min(height, y + size))
        for y in starts(height)
        for x in starts(width)
    ]


def main(argv=None) -> int:
    import pdfplumber
    import torch
    from transformers import AutoProcessor, PaddleOCRVLForConditionalGeneration

    parser = argparse.ArgumentParser(description="Mide PaddleOCR-VL en la GPU local")
    parser.add_argument("--datos", type=Path, default=Path("generated/synthetic_v2/s-dev"))
    parser.add_argument("--degradacion", default="escaneado_limpio")
    parser.add_argument("--paginas", type=int, default=10)
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--mosaico", type=int, default=1280)
    parser.add_argument("--tokens", type=int, default=512, help="Tope de tokens por mosaico")
    parser.add_argument("--salida", type=Path, default=Path("generated/estudio/paddle_vl.jsonl"))
    args = parser.parse_args(argv)

    before = _vram_mib()
    started = time.perf_counter()
    processor = AutoProcessor.from_pretrained(MODEL)
    model = (
        PaddleOCRVLForConditionalGeneration.from_pretrained(MODEL, dtype=torch.bfloat16)
        .to("cuda")
        .eval()
    )
    load_seconds = round(time.perf_counter() - started, 1)
    manifest = json.loads((args.datos / "manifest.json").read_text(encoding="utf-8"))
    rows = []
    for case in manifest["cases"][: args.paginas]:
        tag = case["tag"]
        truth = json.loads((args.datos / "truth" / f"{tag}.json").read_text(encoding="utf-8"))
        number = truth["documents"]["1"]["ga_pages"][0]
        path = args.datos / args.degradacion / tag / f"GAD_{tag}_rev1.pdf"
        with pdfplumber.open(path) as pdf:
            image = pdf.pages[number - 1].to_image(resolution=args.dpi).original.convert("RGB")
        boxes = tile_boxes(*image.size, size=args.mosaico)
        torch.cuda.reset_peak_memory_stats()
        texts, failed, tokens, tile_seconds = [], 0, [], []
        page_started = time.perf_counter()
        with VramMonitor() as monitor:
            for box in boxes:
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image", "image": image.crop(box)},
                            {"type": "text", "text": "OCR:"},
                        ],
                    }
                ]
                tile_started = time.perf_counter()
                try:
                    inputs = processor.apply_chat_template(
                        messages,
                        tokenize=True,
                        add_generation_prompt=True,
                        return_dict=True,
                        return_tensors="pt",
                    ).to("cuda")
                    with torch.no_grad():
                        ids = model.generate(**inputs, max_new_tokens=args.tokens, do_sample=False)
                    answer = processor.batch_decode(
                        ids[:, inputs["input_ids"].shape[1] :], skip_special_tokens=True
                    )[0]
                    texts += [line.strip() for line in answer.splitlines() if line.strip()]
                    tokens.append(int(ids.shape[1] - inputs["input_ids"].shape[1]))
                except Exception as exc:  # noqa: BLE001 - se anota el mosaico y se sigue
                    failed += 1
                    print(f"  mosaico fallido: {type(exc).__name__}: {str(exc)[:160]}")
                tile_seconds.append(round(time.perf_counter() - tile_started, 1))
        row = {
            "model": MODEL,
            "tag": tag,
            "vendor": case.get("vendor"),
            "degradation": args.degradacion,
            "dpi": args.dpi,
            "tile": args.mosaico,
            "tiles": len(boxes),
            "failed_tiles": failed,
            "texts": len(texts),
            "tokens_per_tile": tokens,
            "tiles_at_token_cap": sum(t >= args.tokens for t in tokens),
            "seconds_per_tile": tile_seconds,
            "seconds": round(time.perf_counter() - page_started, 1),
            "torch_peak_mib": round(torch.cuda.max_memory_reserved() / 2**20),
            "vram_peak_mib": monitor.peak,
            "vram_before_mib": before,
            "load_seconds": load_seconds,
            "sample": texts[:8],
        }
        rows.append(row)
        print(json.dumps({k: v for k, v in row.items() if k != "sample"}, ensure_ascii=False))
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    with args.salida.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
