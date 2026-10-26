"""Mide un proveedor de visión local: segundos por página, mosaicos, tokens y VRAM de pico.

    uv run python -m trazia.vision.medir --modelo ollama:qwen3-vl:4b-instruct --paginas 3

Usa las primeras páginas GA de S-dev (escaneado limpio) y una caché propia vacía, para medir
llamadas reales. La VRAM se muestrea con nvidia-smi cada 0,25 s (incluye lo que ya hubiera
cargado en la GPU antes de empezar, que se informa aparte).
"""

import argparse
import json
import os
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from .providers import get_provider
from .reader import read_page, render_page


def _vram() -> int | None:
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
            value = _vram()
            if value is not None:
                self.peak = max(self.peak, value)
            time.sleep(0.25)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        self._thread.join(timeout=2)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Mide VRAM y segundos por página")
    parser.add_argument("--modelo", default="ollama:qwen3-vl:4b-instruct")
    parser.add_argument("--datos", type=Path, default=Path("generated/synthetic_v2/s-dev"))
    parser.add_argument("--degradacion", default="escaneado_limpio")
    parser.add_argument("--paginas", type=int, default=3)
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--mosaico", type=int, default=1280)
    parser.add_argument(
        "--salida", type=Path, default=Path("generated/estudio/vision_medidas.jsonl")
    )
    args = parser.parse_args(argv)

    os.environ["TRAZIA_VISION_CACHE"] = tempfile.mkdtemp(prefix="trazia-medir-")
    os.environ.pop("TRAZIA_VISION_OFFLINE", None)
    provider = get_provider(args.modelo)
    manifest = json.loads((args.datos / "manifest.json").read_text(encoding="utf-8"))
    baseline = _vram()
    rows = []
    for case in manifest["cases"][: args.paginas]:
        tag = case["tag"]
        pdf = (args.datos / args.degradacion / tag / f"GAD_{tag}_rev1.pdf").read_bytes()
        truth = json.loads((args.datos / "truth" / f"{tag}.json").read_text(encoding="utf-8"))
        page = truth["documents"]["1"]["ga_pages"][0]
        image = render_page(pdf, page, dpi=args.dpi)
        started = time.perf_counter()
        with VramMonitor() as monitor:
            reading = read_page(
                provider, image, page_ref=f"medir#{tag}/p{page}", tile_size=args.mosaico
            )
        row = {
            "model": provider.name,
            "tag": tag,
            "vendor": case["vendor"],
            "degradation": args.degradacion,
            "dpi": args.dpi,
            "tile": args.mosaico,
            "tiles": reading.tiles,
            "items": len(reading.items),
            "seconds_wall": round(time.perf_counter() - started, 1),
            "seconds_model": round(reading.seconds, 1),
            "tokens_in": reading.tokens_in,
            "tokens_out": reading.tokens_out,
            "vram_peak_mib": monitor.peak,
            "vram_before_mib": baseline,
            "errors": reading.errors,
        }
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False))
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    with args.salida.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
