import argparse
from pathlib import Path

from .generate import generate
from .render import STYLES


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Genera equipos sintéticos con verdad conocida")
    parser.add_argument("--casos", type=int, default=20)
    parser.add_argument("--semilla", type=int, default=2026)
    parser.add_argument("--salida", type=Path, default=Path("generated/synthetic"))
    parser.add_argument("--estilos", nargs="+", choices=STYLES, default=list(STYLES))
    args = parser.parse_args(argv)
    manifest = generate(args.salida, args.casos, args.semilla, tuple(args.estilos))
    changes = sum(c["changes"] for c in manifest["cases"])
    print(
        f"{len(manifest['cases'])} equipos x {len(args.estilos)} estilos en {args.salida} "
        f"({changes} cambios de campo esperados entre rev1 y rev2)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
