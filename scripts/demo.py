"""La demo del guion con un comando: API offline, web compilada y pestañas en orden.

    uv run python scripts/demo.py                # API (TRAZIA_OFFLINE=1) + web en :3000
    uv run python scripts/demo.py --sin-api      # plan B: web con los datos de public/demo
    uv run python scripts/demo.py --pitch        # además, el pitch compilado en :4173
    uv run python scripts/demo.py --construir    # recompilar la web aunque ya esté compilada

Comprueba lo que falta antes de que falte delante del jurado: dependencias de la web, la
compilación con la URL de la API correcta (Next la fija al compilar), la carpeta de datos con
sus cachés y que los puertos estén libres. Luego espera a que respondan y abre las pestañas en
el orden de docs/GUION_DEMO.md. Ctrl+C lo para todo.
"""

import argparse
import os
import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "web"
PITCH = RAIZ / "pitch" / "web"
PNPM = [shutil.which("corepack") or "corepack", "pnpm@10.18.0"]  # en Windows, corepack.cmd
PESTANAS = (  # orden de docs/GUION_DEMO.md
    "/documentos",
    "/pipeline",
    "/modelo?vista=revision",
    "/bench?vista=estudio",
    "/",
    "/modelo?vista=cambios",
    "/impacto",
)


def ocupado(puerto: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", puerto)) == 0


def esperar(puerto: int, nombre: str, segundos: float = 90) -> None:
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        if ocupado(puerto):
            print(f"✓ {nombre} en http://127.0.0.1:{puerto}")
            return
        time.sleep(0.5)
    raise SystemExit(f"{nombre} no responde en el puerto {puerto} tras {segundos:.0f} s.")


def ejecutar(orden: list[str], carpeta: Path, entorno: dict | None = None) -> None:
    print(f"$ {' '.join(orden)}  ({carpeta.relative_to(RAIZ)})")
    if subprocess.run(orden, cwd=carpeta, env=entorno).returncode != 0:
        raise SystemExit(f"Falló: {' '.join(orden)}")


def compilar_web(api_url: str, forzar: bool) -> None:
    marca = WEB / ".next" / "trazia-api-url.txt"
    compilada = (WEB / ".next" / "BUILD_ID").is_file()
    misma_api = marca.is_file() and marca.read_text(encoding="utf-8") == api_url
    if compilada and misma_api and not forzar:
        print("✓ Web ya compilada para esta API")
        return
    entorno = dict(os.environ, NEXT_PUBLIC_API_URL=api_url)
    ejecutar([*PNPM, "build"], WEB, entorno)
    marca.write_text(api_url, encoding="utf-8")


def comprobar_datos() -> dict:
    datos = Path(os.getenv("TRAZIA_DATA", RAIZ / "data"))
    if not datos.is_absolute():
        datos = RAIZ / datos
    cache = datos / "cache"
    if not cache.is_dir() or not any(cache.iterdir()):
        print(
            f"! {cache} está vacía: en modo offline no se crean cachés. El copiloto responderá "
            "503 y la visión no leerá nada nuevo. Prepáralas con red antes (docs/DEMO.md)."
        )
    else:
        print(f"✓ Cachés en {cache}: {', '.join(sorted(p.name for p in cache.iterdir()))}")
    return {"TRAZIA_DATA": str(datos)}


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Arrancar la demo del guion")
    parser.add_argument("--sin-api", action="store_true", help="Plan B: solo la web")
    parser.add_argument("--pitch", action="store_true", help="Servir también el pitch")
    parser.add_argument("--construir", action="store_true", help="Recompilar web y pitch")
    parser.add_argument("--no-abrir", action="store_true", help="No abrir el navegador")
    parser.add_argument("--puerto-api", type=int, default=8000)
    parser.add_argument("--puerto-web", type=int, default=3000)
    parser.add_argument("--puerto-pitch", type=int, default=4173)
    args = parser.parse_args(argv)

    for programa in ("uv", "corepack"):
        if shutil.which(programa) is None:
            raise SystemExit(f"Falta «{programa}» en el PATH.")
    puertos = [args.puerto_web] + ([] if args.sin_api else [args.puerto_api])
    puertos += [args.puerto_pitch] if args.pitch else []
    for puerto in puertos:
        if ocupado(puerto):
            raise SystemExit(f"El puerto {puerto} ya está en uso: para lo que lo ocupa.")
    if not (WEB / "node_modules").is_dir():
        ejecutar([*PNPM, "install", "--frozen-lockfile"], WEB)
    api_url = "" if args.sin_api else f"http://127.0.0.1:{args.puerto_api}"
    compilar_web(api_url, args.construir)
    if args.pitch:
        if not (PITCH / "node_modules").is_dir():
            ejecutar([*PNPM, "install", "--frozen-lockfile"], PITCH)
        if args.construir or not (PITCH / "dist" / "index.html").is_file():
            ejecutar([*PNPM, "build"], PITCH)

    procesos = []
    try:
        if not args.sin_api:
            entorno = dict(
                os.environ,
                **comprobar_datos(),
                TRAZIA_OFFLINE="1",
                TRAZIA_PORT=str(args.puerto_api),
            )
            orden = [
                shutil.which("uv") or "uv",
                "run",
                "--extra",
                "api",
                "python",
                "-m",
                "trazia.api",
            ]
            procesos.append(subprocess.Popen(orden, cwd=RAIZ, env=entorno))
        web = [*PNPM, "exec", "next", "start", "--port", str(args.puerto_web)]
        procesos.append(subprocess.Popen(web, cwd=WEB))
        if args.pitch:
            pitch = [*PNPM, "exec", "vite", "preview", "--host", "127.0.0.1", "--strictPort"]
            pitch += ["--port", str(args.puerto_pitch)]
            procesos.append(subprocess.Popen(pitch, cwd=PITCH))
        if not args.sin_api:
            esperar(args.puerto_api, "API offline")
        esperar(args.puerto_web, "Web")
        if args.pitch:
            esperar(args.puerto_pitch, "Pitch")
        base = f"http://localhost:{args.puerto_web}"
        if not args.no_abrir:
            for ruta in PESTANAS:
                webbrowser.open_new_tab(base + ruta)
            if args.pitch:
                webbrowser.open_new_tab(f"http://127.0.0.1:{args.puerto_pitch}")
        print("\nPestañas del guion:", *(base + r for r in PESTANAS), sep="\n  ")
        print(
            "\nRecórrelas una vez para dejar el IFC y los PDF en caché. "
            "Navegador a 1920×1080 y tema oscuro. Ctrl+C para parar."
        )
        while all(p.poll() is None for p in procesos):
            time.sleep(1)
        print("Un proceso se ha parado: cierro el resto.")
        return 1
    except KeyboardInterrupt:
        print("\nParando la demo.")
        return 0
    finally:
        for proceso in procesos:
            if proceso.poll() is None and sys.platform == "win32":  # .cmd: matar el árbol
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proceso.pid)], check=False)
            elif proceso.poll() is None:
                proceso.terminate()
        for proceso in procesos:
            try:
                proceso.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proceso.kill()


if __name__ == "__main__":
    raise SystemExit(main())
