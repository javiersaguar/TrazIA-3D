import argparse
import json
from pathlib import Path

from .report import summarize, to_markdown
from .runner import EXTRACTORS, run_bench


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="GA2MODEL Bench sobre un conjunto con verdad conocida"
    )
    parser.add_argument("--entrada", type=Path, default=Path("generated/synthetic"))
    parser.add_argument("--salida", type=Path, default=Path("generated/bench"))
    parser.add_argument("--extractor", choices=sorted(EXTRACTORS), default="etiquetas")
    parser.add_argument(
        "--detalle", action="store_true", help="Guardar también los resultados por caso"
    )
    args = parser.parse_args(argv)
    if not (args.entrada / "manifest.json").exists():
        parser.error(f"No hay conjunto en {args.entrada}. Genéralo con: uv run python -m synthetic")
    results = run_bench(args.entrada, args.extractor)
    summary = summarize(results)
    args.salida.mkdir(parents=True, exist_ok=True)
    (args.salida / "report.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.salida / "report.md").write_text(to_markdown(summary), encoding="utf-8")
    if args.detalle:
        (args.salida / "cases.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    for style, data in summary["styles"].items():
        g, a, d = data["geometry"], data["attributes"], data["delta"]

        def pct(x):
            return "-" if x is None else f"{100 * x:.0f}%"

        print(
            f"{style:10s} geometria {pct(g['field_accuracy'])}"
            f" | atributos {pct(a['accuracy_value_unit'])}"
            f" | F1 cambios {pct(d['f1'])} | modelos {data['models_built']}/{data['revisions']}"
        )
    print(f"Informe: {args.salida / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
