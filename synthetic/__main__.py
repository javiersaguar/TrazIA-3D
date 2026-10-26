import argparse
from pathlib import Path

from .generate import generate
from .render import STYLES
from .render_v2 import DEGRADATIONS
from .sets import SETS, generate_set


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Genera equipos sintéticos con verdad conocida")
    parser.add_argument(
        "--conjunto",
        nargs="+",
        choices=[*SETS, "todos"],
        help="Generador v2: conjuntos con semilla fija. Sin esta opción se usa el generador v1.",
    )
    parser.add_argument("--casos", type=int, default=None)
    parser.add_argument("--semilla", type=int, default=2026, help="Solo generador v1")
    parser.add_argument("--salida", type=Path, default=None)
    parser.add_argument("--estilos", nargs="+", choices=STYLES, default=list(STYLES))
    parser.add_argument("--degradaciones", nargs="+", choices=DEGRADATIONS, default=None)
    args = parser.parse_args(argv)
    if args.conjunto:
        names = list(SETS) if "todos" in args.conjunto else args.conjunto
        output = args.salida or Path("generated/synthetic_v2")
        degradations = tuple(args.degradaciones) if args.degradaciones else None
        for name in names:
            manifest = generate_set(name, output, args.casos, degradations)
            changes = sum(c["changes"] for c in manifest["cases"])
            print(
                f"{name}: {len(manifest['cases'])} equipos x {len(manifest['styles'])} "
                f"degradaciones en {output / name} ({changes} cambios esperados)"
            )
        return 0
    output = args.salida or Path("generated/synthetic")
    manifest = generate(output, args.casos or 20, args.semilla, tuple(args.estilos))
    changes = sum(c["changes"] for c in manifest["cases"])
    print(
        f"{len(manifest['cases'])} equipos x {len(args.estilos)} estilos en {output} "
        f"({changes} cambios de campo esperados entre rev1 y rev2)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
