"""Ajuste de la fusión aprendida de D (tarea 3.4).

    uv run python -m bench.fusion --datos generated/synthetic_v2

1. Pasa D por `trazia.pipeline.process` sobre S-dev, con la misma rev1 aprobada por la persona
   simulada que usa el estudio y con la biblioteca de C sin el proveedor del caso (como
   `bench.calibrar`). Guarda todas las lecturas de cada ejecución antes de fusionarlas.
2. Vuelve a fusionar esas lecturas con canales apagados: ninguno, sin tablas ni cotas, sin
   plantilla y sin ambos. Simula proveedores cuyas tablas no se pueden leer o que no se parecen a
   ninguno conocido. Sin esto, en S-dev la medida del dibujo solo gana cuando todo lo demás falla y
   el modelo aprendería que el dibujo nunca acierta.
3. Cada opción de cada campo es una fila: sus señales y si su valor es el verdadero.
4. Elige la regularización dejando fuera un proveedor de S-dev cada vez (nada de S-reservado) y
   compara la elección aprendida con la heurística en esos proveedores no vistos.
5. Ajusta con todo S-dev y escribe `<salida>/fusion.json` (lo que lee D con `fusion="aprendida"`)
   e `<salida>/informe.json` con las cifras de la validación.
"""

import argparse
import json
import math
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean

from synthetic.cases import flatten, spec_from_dict
from trazia.pipeline import InputDocument, process
from trazia.strategies import d_hibrido
from trazia.strategies.fusion import FEATURES, FusionModel

from .calibrar import vendor_libraries
from .estudio import DATASET_NAMES, _documents, reviewed_by_oracle
from .metrics import ece
from .units import same

MASKS = {
    "ninguno": frozenset(),
    "sin_tablas": frozenset({"tabla", "cota", "cajetin"}),
    "sin_rag": frozenset({"rag"}),
    "sin_tablas_ni_rag": frozenset({"tabla", "cota", "cajetin", "rag"}),
}
GRID_C = (0.1, 0.3, 1.0, 3.0, 10.0)


def collect(root: Path, degradations: list[str] | None, libraries, log=print) -> list[dict]:
    """Una fila por opción de cada campo, en cada ejecución de D y con cada máscara."""
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    label = DATASET_NAMES.get(root.name, root.name)
    folders = [p.name for p in sorted(root.iterdir()) if p.is_dir() and p.name != "truth"]
    rows: list[dict] = []
    for degradation in degradations or folders:
        if not (root / degradation).is_dir():
            continue
        for case in manifest["cases"]:
            tag, vendor = case["tag"], case["vendor"]
            truth = json.loads((root / "truth" / f"{tag}.json").read_text(encoding="utf-8"))
            os.environ["TRAZIA_RAG_LIBRARY"] = str(libraries[vendor])
            previous = None
            for rev in ("1", "2"):
                docs = _documents(root / degradation / tag, tag, rev)
                if not docs[0][0].exists():
                    continue
                sink: list = []
                d_hibrido.POOL_SINK = sink
                try:
                    result = process(
                        [InputDocument(p.name, p.read_bytes(), i) for p, i in docs],
                        project_id="FUSION",
                        equipment_id=tag.lower(),
                        revision=rev,
                        strategy="d_hibrido",
                        previous=previous,
                        dataset="synthetic",
                    )
                finally:
                    d_hibrido.POOL_SINK = None
                expected = flatten(spec_from_dict(truth[f"rev{rev}"]))
                pool = sink[-1] if sink else []
                for mask_name, mask in MASKS.items():
                    kept = [c for c in pool if (c.channel or "") not in mask]
                    record: list[dict] = []
                    chosen, _ = d_hibrido.fuse(kept, record=record)
                    heuristic = {c.path: c for c in chosen}
                    for r in record:
                        exp = expected.get(r["path"])
                        h = heuristic.get(r["path"])
                        rows.append(
                            {
                                "set": label,
                                "degradation": degradation,
                                "tag": tag,
                                "vendor": vendor,
                                "rev": rev,
                                "mask": mask_name,
                                "path": r["path"],
                                "measure": r["measure"],
                                "expected": exp is not None,
                                "correct": exp is not None and same(r["value"], r["unit"], *exp),
                                "heuristic_correct": exp is not None
                                and h is not None
                                and same(h.value, h.unit, *exp),
                                "heuristic_conf": None if h is None else h.source.confidence,
                                "features": r["features"],
                            }
                        )
                if rev == "1" and result.revision is not None:
                    previous = reviewed_by_oracle(result.revision, truth["rev1"], docs)
        log(f"  {label} · {degradation}: {len(rows)} opciones acumuladas")
    return rows


def fit(rows: list[dict], c: float, meta: dict | None = None) -> FusionModel:
    from sklearn.linear_model import LogisticRegression

    seen = sorted(
        f.removeprefix("ch_")
        for f in FEATURES
        if f.startswith("ch_") and any(r["features"][f] > 0 for r in rows)
    )
    x = [[r["features"][f] for f in FEATURES] for r in rows]
    y = [bool(r["correct"]) for r in rows]
    lr = LogisticRegression(C=c, max_iter=5000).fit(x, y)
    return FusionModel(
        features=list(FEATURES),
        coef=[round(float(w), 6) for w in lr.coef_[0]],
        intercept=round(float(lr.intercept_[0]), 6),
        fitted_on="S-dev",
        meta={"C": c, "channels_seen": seen, **(meta or {})},
    )


def _groups(rows: list[dict]) -> dict[tuple, list[dict]]:
    out: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        out[(r["set"], r["degradation"], r["tag"], r["rev"], r["mask"], r["path"])].append(r)
    return out


def picks(rows: list[dict], model: FusionModel) -> list[dict]:
    """Por campo con verdad: qué elige el modelo y qué eligió la heurística."""
    out = []
    for key, group in _groups(rows).items():
        if not group[0]["expected"]:
            continue
        probs = [model.prob(r["features"]) for r in group]
        best = max(range(len(group)), key=lambda i: probs[i])
        out.append(
            {
                "mask": key[4],
                "vendor": group[0]["vendor"],
                "learned_correct": bool(group[best]["correct"]),
                "learned_conf": probs[best],
                "learned_measure": bool(group[best]["measure"]),
                "heuristic_correct": bool(group[0]["heuristic_correct"]),
                "heuristic_conf": group[0]["heuristic_conf"],
            }
        )
    return out


def summarize(chosen: list[dict]) -> dict:
    by_mask: dict[str, list[dict]] = defaultdict(list)
    for p in chosen:
        by_mask[p["mask"]].append(p)
        by_mask["todas"].append(p)
    out = {}
    for mask, group in sorted(by_mask.items()):
        heur = [(p["heuristic_conf"], p["heuristic_correct"]) for p in group if p["heuristic_conf"]]
        out[mask] = {
            "fields": len(group),
            "accuracy_learned": round(fmean(p["learned_correct"] for p in group), 4),
            "accuracy_heuristic": round(fmean(p["heuristic_correct"] for p in group), 4),
            "ece_learned": _r(ece([(p["learned_conf"], p["learned_correct"]) for p in group])),
            "ece_heuristic_raw": _r(ece(heur)),
            "measure_chosen": round(fmean(p["learned_measure"] for p in group), 4),
        }
    return out


def log_loss(rows: list[dict], model: FusionModel) -> float:
    total = 0.0
    for r in rows:
        p = min(1 - 1e-6, max(1e-6, model.prob(r["features"])))
        total -= math.log(p if r["correct"] else 1 - p)
    return total / max(1, len(rows))


def leave_one_vendor_out(rows: list[dict], c: float) -> tuple[list[dict], float]:
    vendors = sorted({r["vendor"] for r in rows})
    chosen, losses = [], []
    for vendor in vendors:
        train = [r for r in rows if r["vendor"] != vendor]
        test = [r for r in rows if r["vendor"] == vendor]
        model = fit(train, c)
        chosen += picks(test, model)
        losses.append(log_loss(test, model))
    return chosen, fmean(losses)


def _r(x):
    return None if x is None else round(x, 4)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Ajusta la fusión aprendida de D (tarea 3.4)")
    parser.add_argument("--datos", type=Path, default=Path("generated/synthetic_v2"))
    parser.add_argument("--ajuste", default="s-dev")
    parser.add_argument("--degradaciones", nargs="+", default=None)
    parser.add_argument("--salida", type=Path, default=Path("generated/fusion"))
    parser.add_argument(
        "--reusar", action="store_true", help="Reajusta con las filas ya recogidas (filas.json)"
    )
    args = parser.parse_args(argv)

    os.environ["TRAZIA_CALIBRATION"] = "off"
    os.environ["TRAZIA_FUSION"] = "off"
    from trazia.rag.library import build
    from trazia.strategies.c_rag import library_path

    args.salida.mkdir(parents=True, exist_ok=True)
    stored = args.salida / "filas.json"
    if args.reusar:
        rows = json.loads(stored.read_text(encoding="utf-8"))
    else:
        full = library_path()
        if not full.exists():
            build(args.datos / args.ajuste, full)
        libraries = vendor_libraries(full, args.salida)
        print("Recogiendo lecturas de D…")
        rows = collect(args.datos / args.ajuste, args.degradaciones, libraries)
        os.environ["TRAZIA_RAG_LIBRARY"] = str(full)
        stored.write_text(json.dumps(rows), encoding="utf-8")

    grid = {}
    for c in GRID_C:
        chosen, loss = leave_one_vendor_out(rows, c)
        grid[c] = {"log_loss": round(loss, 4), "summary": summarize(chosen)}
        acc = grid[c]["summary"]["todas"]
        print(
            f"C={c:<5} pérdida {loss:.4f} · acierto aprendida {acc['accuracy_learned']:.4f}"
            f" · heurística {acc['accuracy_heuristic']:.4f}"
        )
    best_c = min(GRID_C, key=lambda c: grid[c]["log_loss"])
    model = fit(
        rows,
        best_c,
        meta={
            "options": len(rows),
            "masks": {k: sorted(v) for k, v in MASKS.items()},
            "selection": "pérdida logarítmica dejando fuera un proveedor de S-dev",
            "fitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
    )
    (args.salida / "fusion.json").write_text(
        json.dumps(model.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "synthetic": True,
        "fitted_on": args.ajuste,
        "validation": "dejando fuera un proveedor de S-dev cada vez",
        "C": best_c,
        "fusion_sha256": model.sha256,
        "grid": {str(c): v for c, v in grid.items()},
        "coefficients": dict(zip(model.features, model.coef, strict=True)),
        "intercept": model.intercept,
    }
    (args.salida / "informe.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(grid[best_c]["summary"], indent=1, ensure_ascii=False))
    print(f"Modelo en {args.salida / 'fusion.json'} (C={best_c}, sha256 {model.sha256[:12]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
