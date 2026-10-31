"""Compara los modelos de Mistral como lector de la estrategia A (tareas 1.9 y 2.2).

    uv run python -m bench.mistral --casos 2

Pide a la API la lista de modelos de la clave (`MISTRAL_API_KEY` en `.env`), se queda con los que
aceptan imágenes, más Mistral OCR, y los mide con `bench.proveedores`.

Solo datos sintéticos: la política de visión bloquea enviar documentos reales a un proveedor
externo (DEC-03 y DEC-31).
"""

import argparse
import os
from pathlib import Path

from .proveedores import compare, load_env, spec_for

OCR_MODELS = ("mistral-ocr-latest",)


def vision_models() -> list[str]:
    """Modelos de la clave con visión, sin alias repetidos (se prefiere el «-latest»)."""
    from trazia.vision.providers import _get

    listed = _get("https://api.mistral.ai/v1/models", os.environ["MISTRAL_API_KEY"])
    names = [
        m["id"]
        for m in listed.get("data", [])
        if (m.get("capabilities") or {}).get("vision")
        and not m.get("deprecation")
        and "ocr" not in m["id"]
    ]
    latest = [n for n in names if n.endswith("-latest")]  # un alias por familia
    return sorted(set(latest or names))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Compara modelos de Mistral como lector de A")
    parser.add_argument("--datos", type=Path, default=Path("generated/synthetic_v2"))
    parser.add_argument("--conjuntos", nargs="+", default=["s-dev", "s-reservado", "s-adversarial"])
    parser.add_argument("--casos", type=int, default=2)
    parser.add_argument("--degradaciones", nargs="+", default=["vectorial", "escaneado_limpio"])
    parser.add_argument("--modelos", nargs="+", default=None, help="Por defecto, los de la clave")
    parser.add_argument("--remuestreos", type=int, default=1000)
    parser.add_argument("--salida", type=Path, default=Path("generated/mistral"))
    args = parser.parse_args(argv)

    load_env()
    if not os.environ.get("MISTRAL_API_KEY"):
        parser.error("Falta MISTRAL_API_KEY en .env")
    models = args.modelos or vision_models()
    specs = [spec_for(f"mistral-ocr:{m}") for m in OCR_MODELS]
    specs += [spec_for(f"mistral-chat:{m}") for m in models]
    print("Modelos:", ", ".join(s.id for s in specs))
    compare(
        specs,
        datos=args.datos,
        conjuntos=args.conjuntos,
        casos=args.casos,
        degradaciones=args.degradaciones,
        remuestreos=args.remuestreos,
        salida=args.salida,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
