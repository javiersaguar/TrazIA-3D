"""Graba el vídeo de respaldo de la demo (ROADMAP 4.6) sin intervención.

Compila la web, recorre la app en el orden de docs/GUION_DEMO.md con Playwright
(web/tests/e2e/video-respaldo.spec.ts) y monta un MP4 H.264 a 1920×1080 y 30 fps:

    uv run --with imageio-ffmpeg python scripts/video_respaldo.py

Usa los datos sintéticos de web/public/demo (sin API, como el plan B). El vídeo va sin voz:
cada pantalla lleva un rótulo. Sale en generated/video-respaldo/, que Git ignora.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "web"
SALIDA = RAIZ / "generated" / "video-respaldo"
PNPM = ["pnpm@10.18.0"]


def corepack() -> str:
    ruta = shutil.which("corepack")
    if not ruta:
        sys.exit("No se encuentra corepack. Instala Node.js 22.12 o posterior.")
    return ruta


def grabar(fotogramas: Path, puerto: int, compilar: bool) -> None:
    if compilar:
        subprocess.run([corepack(), *PNPM, "build"], cwd=WEB, check=True)
    entorno = {**os.environ, "PW_USE_BUILD": "1", "PW_PORT": str(puerto)}
    entorno["VIDEO_FRAMES"] = str(fotogramas)
    orden = [corepack(), *PNPM, "exec", "playwright", "test", "--project=video"]
    subprocess.run(orden, cwd=WEB, env=entorno, check=True)


def montar(fotogramas: Path, destino: Path) -> None:
    lista = fotogramas / "fotogramas.txt"
    if not lista.is_file():
        sys.exit("La grabación no dejó fotogramas.")
    entrada = ["-f", "concat", "-safe", "0", "-i", str(lista)]
    filtro = ["-vf", "fps=30,scale=1920:1080:flags=lanczos,format=yuv420p"]
    codec = "-c:v libx264 -preset slow -crf 18 -movflags +faststart".split()
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    orden = [ffmpeg, "-y", "-loglevel", "error", *entrada, *filtro, *codec, str(destino)]
    subprocess.run(orden, check=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--puerto", type=int, default=3290)
    parser.add_argument("--sin-compilar", action="store_true", help="reutilizar web/.next")
    parser.add_argument("--destino", type=Path, default=SALIDA / "TrazIA-3D-demo-respaldo.mp4")
    args = parser.parse_args(argv)
    fotogramas = SALIDA / "fotogramas"
    args.destino.parent.mkdir(parents=True, exist_ok=True)
    grabar(fotogramas, args.puerto, not args.sin_compilar)
    montar(fotogramas, args.destino)
    shutil.rmtree(fotogramas, ignore_errors=True)
    megas = args.destino.stat().st_size / 1e6
    print(f"{args.destino} · {megas:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
