"""Todas las comprobaciones antes de integrar en `main`, con un comando.

    uv run python scripts/comprobar.py             # guardián, ruff, pruebas y lote sintético
    uv run python scripts/comprobar.py --completo  # además, web y pitch (typecheck, lint, test)

En GitLab no corren los workflows de GitHub Actions: esto es lo que se pasa en local antes de
`merge --no-ff` y push (docs/FLUJO_IA.md). Termina con «Listo para integrar» o con el primer
paso que falla y su salida.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def pasos(completo: bool, salida_lote: Path) -> list[tuple[str, list[str], Path]]:
    uv = ["uv", "run", "--frozen", "--extra", "dev", "--extra", "api", "--extra", "ocr"]
    lista = [
        ("Guardián de datos", [sys.executable, "scripts/guardian_datos.py", "--todo"], RAIZ),
        ("Ruff check", [*uv, "ruff", "check", "."], RAIZ),
        ("Ruff format", [*uv, "ruff", "format", "--check", "."], RAIZ),
        ("Pruebas", [*uv, "pytest", "-q", "-x", "-p", "no:cacheprovider"], RAIZ),
        (
            "Lote sintético",
            [
                *uv,
                "trazia",
                "lote",
                "examples/documents",
                "-o",
                str(salida_lote),
                "--dataset",
                "synthetic",
            ],
            RAIZ,
        ),
    ]
    if completo:
        pnpm = ["corepack", "pnpm@10.18.0"]
        lista += [
            ("Web: typecheck", [*pnpm, "typecheck"], RAIZ / "web"),
            ("Web: lint", [*pnpm, "lint"], RAIZ / "web"),
            ("Web: pruebas", [*pnpm, "test:unit"], RAIZ / "web"),
            ("Pitch: pruebas", [*pnpm, "test"], RAIZ / "pitch" / "web"),
            ("Pitch: build", [*pnpm, "build"], RAIZ / "pitch" / "web"),
        ]
    return lista


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Comprobaciones antes de integrar")
    parser.add_argument("--completo", action="store_true", help="Incluir web y pitch")
    args = parser.parse_args(argv)
    temporal = Path(tempfile.mkdtemp(prefix="trazia-comprobar-"))
    resultados = []
    try:
        for nombre, orden, carpeta in pasos(args.completo, temporal / "salida"):
            programa = shutil.which(orden[0])  # en Windows corepack es corepack.cmd
            if programa is None:
                resultados.append((nombre, "falta", 0.0))
                print(f"✗ {nombre}: no encuentro «{orden[0]}» en el PATH")
                break
            orden = [programa, *orden[1:]]
            inicio = time.perf_counter()
            proceso = subprocess.run(
                orden,
                cwd=carpeta,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
            )
            segundos = time.perf_counter() - inicio
            ok = proceso.returncode == 0
            resultados.append((nombre, "ok" if ok else "fallo", segundos))
            print(f"{'✓' if ok else '✗'} {nombre} ({segundos:.0f} s)")
            if not ok:
                print((proceso.stdout + proceso.stderr)[-4000:])
                break
    finally:
        shutil.rmtree(temporal, ignore_errors=True)
    if all(estado == "ok" for _, estado, _ in resultados) and resultados:
        print("Listo para integrar.")
        return 0
    print("No integrar todavía: arregla el paso que falla y vuelve a ejecutar.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
