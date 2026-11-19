"""Regenera las miniaturas de los proyectos de proceso desde el visor real.

Compila la web, abre cada proyecto en su entorno con Playwright
(web/tests/e2e/miniaturas.spec.ts), con la animación quieta, y guarda el lienzo 3D.
Después reduce cada captura a 720 × 380 y la guarda en WebP como
web/public/demo/proceso/<id>/preview.webp:

    uv run python scripts/miniaturas_proceso.py

Usa los IFC sintéticos de web/public/demo/proceso, sin API. Las capturas intermedias
quedan en generated/miniaturas-proceso/, que Git ignora.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "web"
CATALOGO = WEB / "src/features/process-projects/catalog.json"
CAPTURAS = RAIZ / "generated" / "miniaturas-proceso"
DESTINO = WEB / "public/demo/proceso"
TAMANO = (720, 380)
PNPM = ["pnpm@10.18.0"]


def corepack() -> str:
    ruta = shutil.which("corepack")
    if not ruta:
        sys.exit("No se encuentra corepack. Instala Node.js 22.12 o posterior.")
    return ruta


def capturar(puerto: int, compilar: bool, salida: Path, cpu: bool) -> None:
    if compilar:
        subprocess.run([corepack(), *PNPM, "build"], cwd=WEB, check=True)
    entorno = {**os.environ, "PW_USE_BUILD": "1", "PW_PORT": str(puerto)}
    entorno["MINIATURAS_DIR"] = str(salida)
    if cpu:
        entorno["PW_CPU_ONLY"] = "1"
    orden = [corepack(), *PNPM, "exec", "playwright", "test", "--project=miniaturas"]
    subprocess.run(orden, cwd=WEB, env=entorno, check=True)


def reducir(captura: Path, destino: Path) -> None:
    """Recorta al aspecto de la tarjeta y reduce con Lanczos."""
    imagen = Image.open(captura).convert("RGB")
    ancho, alto = imagen.size
    objetivo = TAMANO[0] / TAMANO[1]
    if ancho / alto > objetivo:
        nuevo = round(alto * objetivo)
        imagen = imagen.crop(((ancho - nuevo) // 2, 0, (ancho + nuevo) // 2, alto))
    else:
        nuevo = round(ancho / objetivo)
        imagen = imagen.crop((0, (alto - nuevo) // 2, ancho, (alto + nuevo) // 2))
    imagen = imagen.resize(TAMANO, Image.Resampling.LANCZOS)
    imagen.save(destino, "WEBP", quality=86, method=6)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--puerto", type=int, default=3291)
    parser.add_argument("--sin-compilar", action="store_true", help="reutilizar web/.next")
    parser.add_argument("--cpu", action="store_true", help="capturar con el WebGL por software")
    parser.add_argument(
        "--destino", type=Path, default=DESTINO, help="carpeta con una subcarpeta por proyecto"
    )
    args = parser.parse_args(argv)
    carpeta_capturas = CAPTURAS.resolve()
    if not carpeta_capturas.is_relative_to(RAIZ):
        sys.exit("La carpeta de capturas debe estar dentro del repositorio.")
    carpeta_capturas.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="captura-", dir=carpeta_capturas) as temporal:
        salida = Path(temporal)
        capturar(args.puerto, not args.sin_compilar, salida, args.cpu)
        for proyecto in json.loads(CATALOGO.read_text(encoding="utf8")):
            captura = salida / f"{proyecto['id']}.png"
            if not captura.is_file():
                sys.exit(f"Falta la captura de {proyecto['id']}.")
            carpeta = args.destino / proyecto["id"]
            carpeta.mkdir(parents=True, exist_ok=True)
            destino = carpeta / "preview.webp"
            reducir(captura, destino)
            print(
                f"{destino.relative_to(RAIZ) if destino.is_relative_to(RAIZ) else destino}"
                f" · {destino.stat().st_size / 1024:.0f} KB"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
