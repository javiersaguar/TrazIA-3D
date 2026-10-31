"""Recalibración CPU explícita desde el JSONL y revisiones sintéticas aprobadas.

No se activa un modelo por guardar un campo. Se propone un candidato solo con datos
suficientes; prueba, curva isotónica y cuantiles usan equipos disjuntos.
"""

import argparse
import json
import os
from collections import Counter
from pathlib import Path

from trazia.calibration import Calibration, calibration_path, load_calibration
from trazia.calibration.feedback import training_rows
from trazia.calibration.scope import for_strategy
from trazia.store import Store

from .calibrar import MIN_GROUP, evaluate, fit


def propose(rows: list[dict], base: Calibration | None, *, min_equipment: int = 6) -> tuple:
    tags = sorted({r["tag"] for r in rows})
    if len(tags) < min_equipment:
        return None, {"status": "insufficient", "reason": "Faltan equipos aprobados independientes"}
    held_out = set(tags[::3])
    train = [dict(r) for r in rows if r["tag"] not in held_out]
    test = [dict(r) for r in rows if r["tag"] in held_out]
    # fit divide train por equipo entre curva y conformal; no se mezcla con test.
    candidate = fit(train)
    if not candidate.curves or not test or len(test) < MIN_GROUP:
        return None, {"status": "insufficient", "reason": "Faltan campos para ajuste y validación"}
    strategies = {r["strategy"] for r in rows}
    train_strategies = {r["strategy"] for r in train}
    test_counts = Counter(r["strategy"] for r in test)
    if (
        set(test_counts) != strategies
        or any(n < MIN_GROUP for n in test_counts.values())
        or any(
            len({r["tag"] for r in rows if r["strategy"] == s}) < min_equipment for s in strategies
        )
    ):
        return None, {
            "status": "insufficient",
            "reason": "Faltan equipos o validación por estrategia",
        }
    if strategies != train_strategies or not all(f"{s}|*" in candidate.curves for s in strategies):
        return None, {
            "status": "insufficient",
            "reason": "Alguna estrategia carece de muestra suficiente",
        }
    candidate.fitted_on = "Correcciones humanas sintéticas aprobadas"
    candidate.curves = {k: v for k, v in candidate.curves.items() if not k.startswith("*|")}
    if base:
        # Las estrategias no observadas conservan su modelo mediante feedback_fallback.
        # Una curva antigua por media o canal no debe ocultar el reajuste de la estrategia.
        curves = {k: v for k, v in base.curves.items() if k.split("|")[0] not in strategies}
        candidate.curves = {**curves, **candidate.curves}
        candidate.quantiles = {**base.quantiles, **candidate.quantiles}
        candidate.thresholds = {
            **{k: v for k, v in base.thresholds.items() if k not in strategies},
            **candidate.thresholds,
        }
    before = {}
    for strategy in strategies:
        baseline = for_strategy(base, strategy) or Calibration({}, {}, {})
        before.update(evaluate([row for row in test if row["strategy"] == strategy], baseline))
    after = evaluate(test, candidate)
    improved = all(after[s]["ece_calibrated"] <= before[s]["ece_calibrated"] for s in after)
    candidate.meta.update(
        {
            "feedback_strategies": sorted(strategies),
            "feedback_fallback": base.to_dict() if base else None,
            "parent_sha256": base.sha256 if base else None,
            "fit_equipment": sorted(set(tags) - held_out),
            "test_equipment": sorted(held_out),
        }
    )
    return candidate, {
        "status": "candidate" if improved else "rejected",
        "fit_fields": len(train),
        "test_fields": len(test),
        "before": before,
        "after": after,
        "limitation": (
            "Validación sintética por equipo; no acredita planos reales "
            "ni ausencia de sesgo de selección"
        ),
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--almacen", type=Path, required=True)
    p.add_argument("--correcciones", type=Path, required=True)
    p.add_argument("--base", type=Path)
    p.add_argument("--salida", type=Path, default=Path("generated/recalibracion"))
    args = p.parse_args(argv)
    target = args.salida / "calibracion.json"
    base_path = args.base or calibration_path()
    if base_path and base_path.resolve() == target.resolve():
        p.error("La propuesta no puede sobrescribir la calibración base")
    rows, provenance = training_rows(Store(args.almacen), args.correcciones)
    base = load_calibration(args.base)
    candidate, report = propose(rows, base)
    args.salida.mkdir(parents=True, exist_ok=True)
    report.update(provenance)
    report["activated"] = False
    report["base_sha256"] = base.sha256 if base else None
    target = args.salida / "calibracion.json"
    if target.exists():
        target.unlink()  # Nunca dejar que una propuesta antigua parezca el resultado actual.
    if candidate is not None and report["status"] == "candidate":
        temporary = target.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(candidate.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(temporary, target)
        report["candidate_sha256"] = candidate.sha256
    (args.salida / "informe.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
