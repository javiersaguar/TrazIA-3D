"""Compara los modelos de Mistral como lector de la estrategia A (tareas 1.9 y 2.2).

    uv run python -m bench.mistral --datos generated/synthetic_v2 --casos 2

1. Pide a la API la lista de modelos de la clave (`MISTRAL_API_KEY` en `.env`) y se queda con los
   que aceptan imágenes, más Mistral OCR.
2. Mide cada uno con el estudio como lector de A (`a_vision`), sobre el mismo subconjunto que se
   use para Qwen3-VL local: Puntuación GA2MODEL, acierto por grupo, segundos y € por equipo.
3. Escribe `<salida>/estudio.json` y `estudio.md`. Las respuestas quedan en la caché de visión:
   repetir el estudio no vuelve a llamar ni a pagar.

Solo datos sintéticos: la política de visión bloquea enviar documentos reales a un proveedor
externo (DEC-03 y DEC-31).
"""

import argparse
import json
import os
from pathlib import Path

from . import estudio
from .estudio import VariantSpec, run_study, to_markdown

OCR_MODELS = ("mistral-ocr-latest",)


def _load_env(path: Path = Path(".env")) -> None:
    """Lee `MISTRAL_API_KEY` y precios de `.env` sin imprimir nada de su contenido."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        name, sep, value = line.partition("=")
        if sep and name.strip().startswith("MISTRAL_") and name.strip() not in os.environ:
            os.environ[name.strip()] = value.strip().strip('"').strip("'")


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

    _load_env()
    if not os.environ.get("MISTRAL_API_KEY"):
        parser.error("Falta MISTRAL_API_KEY en .env")
    models = args.modelos or vision_models()
    specs = [VariantSpec(f"a_vision@{m}", "a_vision", (f"mistral-ocr:{m}",)) for m in OCR_MODELS]
    specs += [
        VariantSpec(f"a_vision@{m}", "a_vision", (f"mistral-chat:{m}",), None, f"A con {m}")
        for m in models
    ]
    print("Modelos:", ", ".join(s.id for s in specs))
    estudio.VARIANTS = (*estudio.VARIANTS, *specs)
    study = run_study(
        args.datos,
        args.conjuntos,
        [s.id for s in specs],
        cases_limit=args.casos,
        degradations=args.degradaciones,
        resamples=args.remuestreos,
    )
    study["subset"] = {"cases_per_set": args.casos, "degradations": args.degradaciones}
    args.salida.mkdir(parents=True, exist_ok=True)
    (args.salida / "estudio.json").write_text(
        json.dumps(study, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (args.salida / "estudio.md").write_text(to_markdown(study), encoding="utf-8")
    for e in sorted(study["variants"], key=lambda e: e["metrics"]["score"], reverse=True):
        m = e["metrics"]
        print(
            f"{e['id']:<40} puntuación {m['score']:.3f} · {m['seconds_per_revision']:.0f} s/rev"
            f" · {m['cost_eur_per_equipment']:.4f} €/equipo"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
