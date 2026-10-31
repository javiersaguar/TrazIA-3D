"""Compara proveedores de visión como lector de la estrategia A (tareas 1.9 y 2.2).

    uv run python -m bench.proveedores --modelos gemini:gemini-3.5-flash-lite groq:qwen/qwen3.8-27b

1. Lee las claves de `.env` (`GEMINI_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`,
   `NVIDIA_API_KEY`, `CLOUDFLARE_API_TOKEN` y `CLOUDFLARE_ACCOUNT_ID`, `MISTRAL_API_KEY`) sin
   imprimirlas.
2. Mide cada modelo con el estudio como lector de A (`a_vision`) sobre el mismo subconjunto, junto
   a Qwen3-VL local y a A sin visión como referencia: Puntuación GA2MODEL, acierto por grupo,
   segundos y € por equipo.
3. Cuenta las teselas que fallan (cuota agotada, servicio saturado, JSON roto). Una tesela fallida
   deja la página con menos texto y baja la puntuación sin avisar, así que el informe las separa:
   un modelo con fallos no está medido del todo. Repetir el estudio no vuelve a pagar lo que ya
   respondió (caché de visión) y solo pide las teselas que faltan.
4. Escribe `<salida>/estudio.json`, `estudio.md` y `teselas.json`.

Solo datos sintéticos: la política de visión bloquea enviar documentos reales a un proveedor
externo (DEC-03 y DEC-31).
"""

import argparse
import json
import os
from collections import Counter
from pathlib import Path

from . import estudio
from .estudio import VariantSpec, run_study, to_markdown

KEY_PREFIXES = ("GEMINI_", "GROQ_", "OPENROUTER_", "NVIDIA_", "CLOUDFLARE_", "MISTRAL_")
BASELINES = ("a_geometria", "a_vision")  # A sin visión y A con Qwen3-VL local (ya en caché)


def load_env(path: Path = Path(".env")) -> None:
    """Pasa a `os.environ` las claves de proveedores de `.env` sin imprimir nada de su valor."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        name, sep, value = line.partition("=")
        name = name.strip()
        if sep and name.startswith(KEY_PREFIXES) and name not in os.environ:
            os.environ[name] = value.strip().strip('"').strip("'")


def count_tile_errors() -> Counter:
    """Envuelve el lector de página para contar, por proveedor, teselas sin respuesta."""
    import trazia.vision as vision

    errors: Counter = Counter()
    original = vision.read_page

    def read_page(provider, *args, **kwargs):
        reading = original(provider, *args, **kwargs)
        errors[provider.name] += len(reading.errors)
        if reading.errors:
            errors[f"{provider.name}|{reading.errors[0][:120]}"] += 1
        return reading

    vision.read_page = read_page
    return errors


def compare(
    specs: list[VariantSpec],
    *,
    datos: Path,
    conjuntos: list[str],
    casos: int,
    degradaciones: list[str],
    remuestreos: int,
    salida: Path,
    baselines: tuple[str, ...] = BASELINES,
) -> dict:
    estudio.VARIANTS = (*estudio.VARIANTS, *specs)
    errors = count_tile_errors()
    study = run_study(
        datos,
        conjuntos,
        [*baselines, *(s.id for s in specs)],
        cases_limit=casos,
        degradations=degradaciones,
        resamples=remuestreos,
    )
    study["subset"] = {"cases_per_set": casos, "degradations": degradaciones}
    tiles = {
        s.id: {
            "tile_errors": errors.get(s.providers[0], 0),
            "examples": sorted(
                k.split("|", 1)[1] for k in errors if k.startswith(f"{s.providers[0]}|")
            )[:3],
        }
        for s in specs
    }
    study["tile_errors"] = tiles
    salida.mkdir(parents=True, exist_ok=True)
    (salida / "estudio.json").write_text(
        json.dumps(study, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (salida / "estudio.md").write_text(to_markdown(study), encoding="utf-8")
    (salida / "teselas.json").write_text(
        json.dumps(tiles, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    for e in sorted(study["variants"], key=lambda e: e["metrics"]["score"], reverse=True):
        m = e["metrics"]
        failed = tiles.get(e["id"], {}).get("tile_errors", 0)
        print(
            f"{e['id']:<55} puntuación {m['score']:.3f} · alucinación"
            f" {m['hallucination_rate']:.1%} · {m['seconds_per_revision']:.0f} s/rev"
            f" · {m['cost_eur_per_equipment']:.4f} €/equipo · teselas fallidas {failed}",
            flush=True,
        )
    return study


def spec_for(provider: str) -> VariantSpec:
    return VariantSpec(f"a_vision@{provider}", "a_vision", (provider,), None, f"A con {provider}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Compara proveedores de visión como lector de A")
    parser.add_argument("--modelos", nargs="+", required=True, help="«servicio:modelo»")
    parser.add_argument("--datos", type=Path, default=Path("generated/synthetic_v2"))
    parser.add_argument("--conjuntos", nargs="+", default=["s-dev", "s-reservado", "s-adversarial"])
    parser.add_argument("--casos", type=int, default=1)
    parser.add_argument("--degradaciones", nargs="+", default=["escaneado_limpio"])
    parser.add_argument("--remuestreos", type=int, default=1000)
    parser.add_argument("--salida", type=Path, default=Path("generated/proveedores"))
    parser.add_argument(
        "--sin-referencias", action="store_true", help="No mide A sin visión ni Qwen3-VL local"
    )
    args = parser.parse_args(argv)

    load_env()
    compare(
        [spec_for(m) for m in args.modelos],
        datos=args.datos,
        conjuntos=args.conjuntos,
        casos=args.casos,
        degradaciones=args.degradaciones,
        remuestreos=args.remuestreos,
        salida=args.salida,
        baselines=() if args.sin_referencias else BASELINES,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
