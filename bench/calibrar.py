"""Ajuste y medición de la calibración (tarea 3.3).

    uv run python -m bench.calibrar --datos generated/synthetic_v2

1. Pasa cada estrategia por `trazia.pipeline.process` sin calibrar, sobre S-dev y S-reservado,
   con la misma rev1 aprobada por la persona simulada que usa el estudio.
   En S-dev, C usa una biblioteca sin el proveedor del caso: S-reservado trae dos proveedores
   que S-dev no tiene, y sin esto la calibración aprende la ventaja de tener plantilla propia.
2. Parte S-dev por equipo en dos mitades: la primera ajusta las curvas isotónicas; la segunda,
   los cuantiles conformes y los umbrales de abstención. Así el cuantil no ve los datos con los
   que se ajustó la curva.
3. Mide en S-reservado, que no se ha usado para nada: ECE antes y después, cobertura empírica del
   intervalo al 90 % y la curva riesgo-cobertura.

Escribe `<salida>/calibracion.json` (los parámetros que lee la etapa `calibrate`) e
`<salida>/informe.json` con las cifras. Las cifras salen medidas: si no se alcanza el objetivo
(ECE < 0,05 y cobertura ≥ nominal), el informe lo dice.
"""

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean

from synthetic.cases import flatten, spec_from_dict
from trazia.calibration import Calibration, conformal
from trazia.calibration.isotonic import fit_curve
from trazia.pipeline import InputDocument, process

from .estudio import DATASET_NAMES, _documents, reviewed_by_oracle
from .metrics import ece
from .units import same, to_canonical

STRATEGIES = ("b_reglas", "c_rag", "d_hibrido")
# Su confianza ya es una probabilidad ajustada en S-dev (fusión aprendida, tarea 3.4): sin curva.
PASSTHROUGH = ("d_hibrido+fusion",)
TARGET_RISK = 0.05  # error máximo entre los campos que no se abstienen
MIN_GROUP = 30  # menos datos no bastan para una curva o un cuantil propios
TARGET_ECE = 0.05


def collect(
    root: Path,
    strategy: str,
    degradations: list[str] | None,
    *,
    libraries: dict[str, Path] | None = None,
    log=print,
) -> list[dict]:
    """Una fila por campo emitido: confianza sin calibrar, acierto y residuo frente a la verdad.

    `libraries` da, por proveedor, la biblioteca de C sin ese proveedor: así cada caso se lee como
    si su proveedor fuera nuevo, que es lo que pasa en S-reservado y con los planos reales.
    """
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    label = DATASET_NAMES.get(root.name, root.name)
    folders = [p.name for p in sorted(root.iterdir()) if p.is_dir() and p.name != "truth"]
    rows = []
    for degradation in degradations or folders:
        if not (root / degradation).is_dir():
            continue
        for case in manifest["cases"]:
            tag = case["tag"]
            truth = json.loads((root / "truth" / f"{tag}.json").read_text(encoding="utf-8"))
            if libraries is not None:
                os.environ["TRAZIA_RAG_LIBRARY"] = str(libraries[case["vendor"]])
            previous = None
            for rev in ("1", "2"):
                docs = _documents(root / degradation / tag, tag, rev)
                if not docs[0][0].exists():
                    continue
                result = process(
                    [InputDocument(p.name, p.read_bytes(), i) for p, i in docs],
                    project_id="CALIBRACION",
                    equipment_id=tag.lower(),
                    revision=rev,
                    strategy=strategy,
                    previous=previous,
                    dataset="synthetic",
                )
                expected = flatten(spec_from_dict(truth[f"rev{rev}"]))
                for c in result.candidates:
                    row = {
                        "set": label,
                        "degradation": degradation,
                        "tag": tag,
                        "strategy": strategy,
                        "channel": c.channel or c.source.channel or "*",
                        # Igual que la etapa `calibrate`: PDF sin capa de texto → «scan».
                        "media": "scan"
                        if degradation.startswith("escaneado")
                        and c.source.document_id.startswith("GA-")
                        else "vector",
                        "path": c.path,
                        "raw": c.source.confidence,
                        "correct": False,
                        "kind": None,
                        "residual": None,
                        # Clase del valor emitido, haya verdad o no: la usa la etapa.
                        "value_kind": conformal.kind_of(*to_canonical(c.value, c.unit))
                        if not isinstance(c.value, str)
                        else None,
                    }
                    if c.path in expected:
                        value, unit = expected[c.path]
                        row["correct"] = same(c.value, c.unit, value, unit)
                        predicted, canonical = to_canonical(c.value, c.unit)
                        kind = conformal.kind_of(predicted, canonical)
                        if kind is not None and not isinstance(value, str) and canonical == unit:
                            row["kind"] = kind
                            row["residual"] = conformal.residual(kind, predicted, value)
                    rows.append(row)
                if rev == "1" and result.revision is not None:
                    previous = reviewed_by_oracle(result.revision, truth["rev1"], docs)
        log(f"  {label} · {strategy} · {degradation}: {len(rows)} campos acumulados")
    return rows


def vendor_libraries(library: Path, out: Path) -> dict[str, Path]:
    """Una copia de la biblioteca de C por proveedor, sin las plantillas de ese proveedor."""
    data = json.loads(library.read_text(encoding="utf-8"))
    vendors = sorted({e.get("vendor") for e in data["entries"]})
    paths = {}
    for vendor in vendors:
        path = out / f"biblioteca_sin_{vendor}.json"
        entries = [e for e in data["entries"] if e.get("vendor") != vendor]
        path.write_text(json.dumps({**data, "entries": entries}), encoding="utf-8")
        paths[vendor] = path
    return paths


def _value_kind(row: dict) -> str | None:
    """Clase del valor emitido; las filas antiguas no la guardan y se deduce del campo."""
    if "value_kind" in row:
        return row["value_kind"]
    path = row["path"]
    if path == "tag" or path.endswith(".material") or path.endswith(".service"):
        return None
    if path.endswith(".azimuth"):
        return "deg"
    if path.startswith("attributes."):
        return "num"
    return "mm"


def _halves(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    tags = sorted({r["tag"] for r in rows})
    first = set(tags[::2])
    return [r for r in rows if r["tag"] in first], [r for r in rows if r["tag"] not in first]


def _fit_curves(rows: list[dict], skip: set[str]) -> dict[str, dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r["strategy"] in skip:
            continue
        keys = (
            f"{r['strategy']}|{r['channel']}|{r['media']}",
            f"{r['strategy']}|{r['channel']}",
            f"{r['strategy']}|*",
            "*|*",
        )
        for key in keys:
            groups[key].append(r)
    return {
        key: fit_curve([r["raw"] for r in group], [r["correct"] for r in group])
        for key, group in sorted(groups.items())
        if len(group) >= MIN_GROUP
    }


def choose_calibrator(rows: list[dict], vendors: dict[str, str]) -> dict[str, dict]:
    """Curva isotónica o confianza tal cual, por estrategia, dejando fuera un proveedor de S-dev.

    Gana lo que da menor ECE en los proveedores no vistos. Si la curva no mejora la confianza de
    la estrategia, esa estrategia pasa sin curva (S-reservado trae proveedores nuevos: es lo que se
    quiere prever sin mirarlo).
    """
    out = {}
    for strategy in sorted({r["strategy"] for r in rows} - set(PASSTHROUGH)):
        own = [r for r in rows if r["strategy"] == strategy]
        raw, iso = [], []
        for vendor in sorted({vendors[r["tag"]] for r in own}):
            train = [r for r in own if vendors[r["tag"]] != vendor]
            fold = Calibration(curves=_fit_curves(train, set()), quantiles={}, thresholds={})
            for r in own:
                if vendors[r["tag"]] == vendor:
                    raw.append((r["raw"], r["correct"]))
                    calibrated = fold.calibrated(strategy, r["channel"], r["raw"], r["media"])
                    iso.append((calibrated, r["correct"]))
        e_raw, e_iso = ece(raw), ece(iso)
        out[strategy] = {
            "ece_raw_lovo": _round(e_raw),
            "ece_isotonic_lovo": _round(e_iso),
            "choice": "sin_curva" if e_raw is not None and e_raw <= (e_iso or 1) else "isotonica",
        }
    return out


def fit(rows: list[dict], vendors: dict[str, str] | None = None) -> Calibration:
    """Curvas con la primera mitad de S-dev; cuantiles y umbrales con la segunda.

    Con `vendors` (equipo → proveedor) se elige antes, por estrategia, si lleva curva o no.
    """
    choice = choose_calibrator(rows, vendors) if vendors else {}
    passthrough = sorted(
        {r["strategy"] for r in rows if r["strategy"] in PASSTHROUGH}
        | {s for s, c in choice.items() if c["choice"] == "sin_curva"}
    )
    curve_rows, conformal_rows = _halves(rows)
    curves = _fit_curves(curve_rows, set(passthrough))
    partial = Calibration(curves=curves, quantiles={}, thresholds={}, passthrough=passthrough)
    for r in conformal_rows:
        r["calibrated"] = partial.calibrated(r["strategy"], r["channel"], r["raw"], r["media"])

    # Mondrian por estrategia, clase y franja; con respaldo por clase y franja (todas juntas).
    residuals: dict[str, list[float]] = defaultdict(list)
    for r in conformal_rows:
        if r["residual"] is None:
            continue
        band = conformal.band_of(r["calibrated"])
        for prefix in ("", f"{r['strategy']}|"):
            residuals[f"{prefix}{r['kind']}|*"].append(r["residual"])
            residuals[f"{prefix}{r['kind']}|{band}"].append(r["residual"])
    quantiles = {}
    for key, values in sorted(residuals.items()):
        q = conformal.quantile(values) if len(values) >= MIN_GROUP else None
        if q is not None:
            quantiles[key] = q

    thresholds = {}
    by_strategy: dict[str, list[dict]] = defaultdict(list)
    for r in conformal_rows:
        by_strategy[r["strategy"]].append(r)
    for strategy, group in sorted(by_strategy.items()):
        t = abstention_threshold([(r["calibrated"], r["correct"]) for r in group])
        if t is not None:
            thresholds[strategy] = t
    return Calibration(
        curves=curves,
        quantiles=quantiles,
        thresholds=thresholds,
        fitted_on="S-dev",
        passthrough=passthrough,
        meta={
            "target_risk": TARGET_RISK,
            "min_group": MIN_GROUP,
            "fields_curves": len(curve_rows),
            "fields_conformal": len(conformal_rows),
            "calibrator_choice": choice,
            "fitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
    )


def abstention_threshold(pairs: list[tuple[float, bool]]) -> float | None:
    """Umbral más bajo cuyo riesgo entre los campos que se quedan no supera el objetivo.

    Con un umbral de 0 no hay abstención. Si ni el umbral más alto lo consigue, `None`: no se
    abstiene nada y el informe lo dice, en lugar de abstener casi todo.
    """
    if not pairs:
        return None
    for t in sorted({c for c, _ in pairs}):
        kept = [ok for c, ok in pairs if c >= t]
        if kept and 1 - fmean(kept) <= TARGET_RISK:
            return round(t, 4)
    return None


def risk_coverage(pairs: list[tuple[float, bool]], steps: int = 20) -> list[dict]:
    out = []
    for i in range(steps + 1):
        t = i / steps
        kept = [ok for c, ok in pairs if c >= t]
        out.append(
            {
                "threshold": round(t, 3),
                "coverage": round(len(kept) / len(pairs), 4) if pairs else None,
                "risk": round(1 - fmean(kept), 4) if kept else None,
            }
        )
    return out


def evaluate(rows: list[dict], calibration: Calibration) -> dict:
    """Cifras en un conjunto no visto, por estrategia."""
    out = {}
    by_strategy: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_strategy[r["strategy"]].append(r)
    for strategy, group in sorted(by_strategy.items()):
        raw = [(r["raw"], r["correct"]) for r in group]
        cal = [
            (calibration.calibrated(strategy, r["channel"], r["raw"], r["media"]), r["correct"])
            for r in group
        ]
        channels: dict[str, list] = defaultdict(list)
        for (confidence, ok), r in zip(cal, group):
            channels[f"{r['channel']}|{r['media']}"].append((r["raw"], confidence, ok))
        hits: dict[str, list[bool]] = defaultdict(list)
        missing = vague_count = 0
        vague = []  # como la etapa `calibrate`: sin intervalo útil, el campo se abstiene
        for (confidence, _), r in zip(cal, group):
            kind = _value_kind(r)
            q = None if kind is None else calibration.quantile_for(kind, confidence, strategy)
            vague.append(q is not None and not conformal.informative(kind, q))
            if r["residual"] is None:
                continue
            q = calibration.quantile_for(r["kind"], confidence, strategy)
            if q is None:
                missing += 1
                continue
            if not conformal.informative(r["kind"], q):
                vague_count += 1
                continue
            hits[r["kind"]].append(r["residual"] <= q + 1e-12)
        all_hits = [h for values in hits.values() for h in values]
        threshold = calibration.threshold_for(strategy)
        kept = [
            ok for (c, ok), v in zip(cal, vague) if (threshold is None or c >= threshold) and not v
        ]
        out[strategy] = {
            "fields": len(group),
            "accuracy": round(fmean(ok for _, ok in raw), 4),
            "ece_raw": _round(ece(raw)),
            "ece_calibrated": _round(ece(cal)),
            "interval_coverage": round(fmean(all_hits), 4) if all_hits else None,
            "interval_coverage_by_kind": {k: round(fmean(v), 4) for k, v in sorted(hits.items())},
            "numeric_fields_without_interval": missing,
            "numeric_fields_vague_interval": vague_count,
            "abstention": {
                "threshold": threshold,
                "coverage": round(len(kept) / len(cal), 4) if cal else None,
                "risk_kept": round(1 - fmean(kept), 4) if kept else None,
                "risk_without_abstention": round(1 - fmean(ok for _, ok in cal), 4),
            },
            "risk_coverage": risk_coverage(cal),
            "by_channel": {
                k: {
                    "fields": len(v),
                    "accuracy": round(fmean(ok for _, _, ok in v), 4),
                    "confidence_raw": round(fmean(r for r, _, _ in v), 4),
                    "confidence": round(fmean(c for _, c, _ in v), 4),
                }
                for k, v in sorted(channels.items())
            },
        }
    return out


def _round(x):
    return None if x is None else round(x, 4)


def to_markdown(report: dict) -> str:
    lines = [
        "| Estrategia | Campos | Acierto | ECE bruta | ECE calibrada | Cobertura 90 % | "
        "Umbral | Se quedan | Riesgo con abstención |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for strategy, m in report["evaluation"].items():
        a = m["abstention"]
        lines.append(
            f"| {strategy} | {m['fields']} | {_pct(m['accuracy'])} | {m['ece_raw']} | "
            f"{m['ece_calibrated']} | {_pct(m['interval_coverage'])} | {a['threshold']} | "
            f"{_pct(a['coverage'])} | {_pct(a['risk_kept'])} |"
        )
    return "\n".join(lines)


def _pct(x):
    return "—" if x is None else f"{100 * x:.1f} %"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Ajusta y mide la calibración (tarea 3.3)")
    parser.add_argument("--datos", type=Path, default=Path("generated/synthetic_v2"))
    parser.add_argument("--ajuste", default="s-dev")
    parser.add_argument("--prueba", default="s-reservado")
    parser.add_argument("--estrategias", nargs="+", default=list(STRATEGIES))
    parser.add_argument("--degradaciones", nargs="+", default=None)
    parser.add_argument("--salida", type=Path, default=Path("generated/calibration"))
    parser.add_argument(
        "--reusar", action="store_true", help="Reajusta con las filas ya recogidas (filas.json)"
    )
    parser.add_argument(
        "--anadir",
        action="store_true",
        help="Recoge solo --estrategias y las suma a filas.json, sustituyendo sus filas",
    )
    args = parser.parse_args(argv)

    os.environ["TRAZIA_CALIBRATION"] = "off"  # se mide la confianza que da cada estrategia
    from trazia.rag.library import build
    from trazia.strategies.c_rag import library_path

    args.salida.mkdir(parents=True, exist_ok=True)
    stored = args.salida / "filas.json"
    if args.reusar:
        saved = json.loads(stored.read_text(encoding="utf-8"))
        fit_rows, test_rows = saved["fit"], saved["test"]
    else:
        kept_fit, kept_test = [], []
        if args.anadir:
            saved = json.loads(stored.read_text(encoding="utf-8"))
            new = set(args.estrategias)
            kept_fit = [r for r in saved["fit"] if r["strategy"] not in new]
            kept_test = [r for r in saved["test"] if r["strategy"] not in new]
        full = library_path()
        if not full.exists():
            build(args.datos / args.ajuste, full)
        libraries = vendor_libraries(full, args.salida)
        fit_rows, test_rows = [], []
        for strategy in args.estrategias:
            print(f"Recogiendo {strategy}…")
            fit_rows += collect(
                args.datos / args.ajuste, strategy, args.degradaciones, libraries=libraries
            )
            os.environ["TRAZIA_RAG_LIBRARY"] = str(full)
            test_rows += collect(args.datos / args.prueba, strategy, args.degradaciones)
        fit_rows, test_rows = kept_fit + fit_rows, kept_test + test_rows
        stored.write_text(json.dumps({"fit": fit_rows, "test": test_rows}), encoding="utf-8")
    manifest = json.loads((args.datos / args.ajuste / "manifest.json").read_text(encoding="utf-8"))
    vendors = {case["tag"]: case["vendor"] for case in manifest["cases"]}
    calibration = fit(fit_rows, vendors)
    evaluation = evaluate(test_rows, calibration)
    met = {
        s: {
            "ece": m["ece_calibrated"] is not None and m["ece_calibrated"] < TARGET_ECE,
            "coverage": m["interval_coverage"] is not None
            and m["interval_coverage"] >= calibration.level,
        }
        for s, m in evaluation.items()
    }
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "synthetic": True,
        "fitted_on": args.ajuste,
        "evaluated_on": args.prueba,
        "level": calibration.level,
        "targets": {"ece": TARGET_ECE, "coverage": calibration.level, "risk": TARGET_RISK},
        "targets_met": met,
        "calibration_sha256": calibration.sha256,
        "evaluation": evaluation,
        "evaluation_on_fit_set": evaluate(fit_rows, calibration),
    }
    args.salida.mkdir(parents=True, exist_ok=True)
    (args.salida / "calibracion.json").write_text(
        json.dumps(calibration.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (args.salida / "informe.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(to_markdown(report))
    print(f"Parámetros en {args.salida / 'calibracion.json'} (sha256 {calibration.sha256[:12]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
