"""Exporta el pitch web a PowerPoint y PDF para entregarlo al jurado.

Las bases de IndesIAhack piden un .pptx. La presentación sigue siendo la web en React;
este script la compila, captura cada escena a 1920×1080 y monta:

- pitch/TrazIA-3D.pptx: una diapositiva por escena con su guion en las notas del orador.
- pitch/TrazIA-3D.pdf: las mismas escenas, para enviar o imprimir.

Desde la raíz del repositorio, con las dependencias de pitch/web y de web/ instaladas:

    uv run --with python-pptx python pitch/web/scripts/exportar_pptx.py

Si cambian las cifras del evento (bench.cifras aplicar), basta con volver a ejecutarlo.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.util import Emu

WEB = Path(__file__).resolve().parents[1]
PITCH = WEB.parent
PNPM = ["pnpm@10.18.0"]


def corepack() -> str:
    ruta = shutil.which("corepack")
    if not ruta:
        sys.exit("No se encuentra corepack. Instala Node.js 22.12 o posterior.")
    return ruta


def esperar(url: str, segundos: float = 60) -> None:
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return
        except OSError:
            time.sleep(0.5)
    sys.exit(f"El servidor de vista previa no respondió en {url}.")


def capturar(puerto: int, carpeta: Path) -> dict:
    subprocess.run([corepack(), *PNPM, "build"], cwd=WEB, check=True)
    orden = [corepack(), *PNPM, "preview", "--port", str(puerto), "--strictPort"]
    servidor = subprocess.Popen(orden, cwd=WEB)
    try:
        url = f"http://127.0.0.1:{puerto}/"
        esperar(url)
        nodo = shutil.which("node") or "node"
        captura = [nodo, "scripts/capturar-escenas.mjs", url, str(carpeta)]
        subprocess.run(captura, cwd=WEB, check=True)
    finally:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(servidor.pid)], capture_output=True)
        else:
            servidor.terminate()
        servidor.wait(timeout=30)
    return json.loads((carpeta / "escenas.json").read_text(encoding="utf-8"))


def montar(datos: dict, carpeta: Path, pptx: Path, pdf: Path) -> None:
    presentacion = Presentation()
    presentacion.slide_width, presentacion.slide_height = Emu(12192000), Emu(6858000)  # 16:9
    presentacion.core_properties.title = datos["titulo"]
    presentacion.core_properties.author = "Equipo TrazIA-3D"
    blanco = presentacion.slide_layouts[6]
    paginas = []
    for escena in datos["escenas"]:
        imagen = carpeta / escena["archivo"]
        jpg = imagen.with_suffix(".jpg")
        with Image.open(imagen) as original:
            rgb = original.convert("RGB")
        rgb.save(jpg, quality=90, optimize=True)
        paginas.append(rgb)
        diapositiva = presentacion.slides.add_slide(blanco)
        ancho, alto = presentacion.slide_width, presentacion.slide_height
        foto = diapositiva.shapes.add_picture(str(jpg), 0, 0, ancho, alto)
        foto.name = escena["titulo"]
        foto._element.nvPicPr.cNvPr.set("descr", escena["titulo"])  # texto alternativo
        notas = diapositiva.notes_slide.notes_text_frame
        notas.text = f"{escena['titulo']} · {escena['segundos']} s\n\n{escena['notas']}"
    presentacion.save(pptx)
    paginas[0].save(pdf, save_all=True, append_images=paginas[1:], resolution=144)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--puerto", type=int, default=4179)
    parser.add_argument("--salida", type=Path, default=PITCH / "TrazIA-3D")
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix="trazia-pitch-") as temporal:
        carpeta = Path(temporal)
        datos = capturar(args.puerto, carpeta)
        pptx, pdf = args.salida.with_suffix(".pptx"), args.salida.with_suffix(".pdf")
        montar(datos, carpeta, pptx, pdf)
    total = sum(escena["segundos"] for escena in datos["escenas"])
    print(f"{len(datos['escenas'])} diapositivas, {total // 60}:{total % 60:02d} de guion")
    print(f"{pptx}\n{pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
