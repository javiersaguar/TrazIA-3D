"""Adaptador de Plataforma al arnés de Lectura, ejecutado fuera del servidor web."""

import json
import sys
from pathlib import Path


def execute(config: dict, log=print) -> dict:
    # La firma vigente se conserva sin modificar el código del agente Lectura.
    from bench.estudio import VARIANTS, run_study

    unknown = set(config["variantes"]) - {v.id for v in VARIANTS}
    if unknown:
        raise ValueError("Variantes desconocidas: " + ", ".join(sorted(unknown)))

    return run_study(
        Path(config["datos"]),
        config["conjuntos"],
        config["variantes"],
        cases_limit=config["casos"],
        degradations=config["degradaciones"],
        resamples=config["remuestreos"],
        seed=config["semilla"],
        log=log,
    )


def main():
    from trazia.runtime import configure_offline

    configure_offline()
    config = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    result = execute(config, log=lambda text: print(text, flush=True))
    if not result.get("variants"):
        raise ValueError("El estudio no ha medido ninguna variante; no se publica como terminado")
    Path(sys.argv[2]).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
