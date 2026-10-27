"""Lee la misma página con proveedores distintos y verifica su caché offline.

Los errores quedan en el informe; no se cuenta un proveedor simulado como medición real.
"""

import argparse
import io
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from .base import PolicyError, VisionError
from .cache import sha256
from .prompts import TASKS, validate
from .providers import get_provider
from .reader import render_page


def compare_page(path, providers, *, page=1, dpi=100, dataset="real", crop=None):
    data = path.read_bytes()
    image = (
        render_page(data, page, dpi)
        if path.suffix.lower() == ".pdf"
        else Image.open(io.BytesIO(data)).convert("RGB")
    )
    if crop:
        x0, y0, x1, y1 = crop
        if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
            raise ValueError("Región inválida: usa x0 y0 x1 y1 en 0–1")
        image = image.crop(
            (
                round(x0 * image.width),
                round(y0 * image.height),
                round(x1 * image.width),
                round(y1 * image.height),
            )
        )
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    png = buffer.getvalue()
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "document_sha256": sha256(data),
        "image_sha256": sha256(png),
        "dataset": dataset,
        "page": page,
        "crop": crop,
        "dpi": dpi,
        "schema": TASKS["lineas"].schema,
        "results": [],
    }
    for spec in providers:
        started = time.perf_counter()
        try:
            provider = get_provider(spec, dataset=dataset)
            result = provider.read(png, "lineas", page_ref=f"{sha256(data)}#p{page}")
            assert not validate(result.data, TASKS["lineas"].schema)
            assert all(0 <= value <= 1 for item in result.data["items"] for value in item["bbox"])
            # El mismo adaptador debe reproducir la lectura sin clave ni conexión de red.
            old = os.environ.get("TRAZIA_VISION_OFFLINE")
            os.environ["TRAZIA_VISION_OFFLINE"] = "1"
            try:
                replay = provider.read(png, "lineas", page_ref=f"{sha256(data)}#p{page}")
                assert replay.cached and replay.data == result.data
            finally:
                if old is None:
                    os.environ.pop("TRAZIA_VISION_OFFLINE", None)
                else:
                    os.environ["TRAZIA_VISION_OFFLINE"] = old
            row = {
                "requested": spec,
                "success": True,
                "offline_replay": True,
                **result.to_cache(),
                "cached": result.cached,
            }
        except (VisionError, PolicyError, ValueError, AssertionError) as error:
            row = {"requested": spec, "success": False, "error": str(error)}
        row["seconds_wall"] = time.perf_counter() - started
        report["results"].append(row)
        print(
            json.dumps({k: v for k, v in row.items() if k != "data"}, ensure_ascii=False),
            flush=True,
        )
    families = {r["provider"].split(":")[0] for r in report["results"] if r["success"]}
    report["distinct_providers"] = len(families)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", type=Path)
    parser.add_argument(
        "--proveedores", nargs="+", default=["ollama:qwen3-vl:4b-instruct", "gemini"]
    )
    parser.add_argument("--dataset", choices=("synthetic", "real"), default="real")
    parser.add_argument("--pagina", type=int, default=1)
    parser.add_argument("--dpi", type=int, default=100)
    parser.add_argument("--recorte", nargs=4, type=float)
    parser.add_argument("--minimo", type=int, default=2)
    parser.add_argument(
        "--salida", type=Path, default=Path("generated/phase1/vision-comparison.json")
    )
    args = parser.parse_args(argv)
    if args.pagina < 1 or not 50 <= args.dpi <= 600 or args.minimo < 1:
        parser.error("Página/mínimo deben ser positivos y dpi estar entre 50 y 600")
    result = compare_page(
        args.document,
        args.proveedores,
        page=args.pagina,
        dpi=args.dpi,
        dataset=args.dataset,
        crop=args.recorte,
    )
    result["complete"] = result["distinct_providers"] >= args.minimo
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    return 0 if result["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
