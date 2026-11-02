"""Ablación de feedback sintético aislado; no crea sesiones humanas ni activa modelos."""

import argparse
import hashlib
import json
import os
import random
import sys
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from cpu_quality import summary
from triage_scale import replay

from trazia.api.extraction_feedback import channel_priorities
from trazia.calibration import conformal, load_calibration
from trazia.feedback import Feedback, extraction_prompt, using
from trazia.vision.prompts import TASKS


def labels(report):
    result = []
    for case in report["rows"]:
        for row in case["quality"]["rows"]:
            if not row["present"] or row["raw"] is None:
                continue
            raw = row["source"].get("confidence_raw")
            if raw is None:
                raw = row["raw"]
            kind = conformal.kind_of(row["prediction"], row["unit"])
            residual = (
                conformal.residual(kind, row["prediction"], row["expected"])
                if kind and isinstance(row["prediction"], (int, float))
                else None
            )
            result.append(
                {
                    **row,
                    "raw": raw,
                    "tag": case["tag"],
                    "strategy": report.get("strategy", "d_hibrido"),
                    "media": "scan"
                    if case["degradation"].startswith("escaneado")
                    and row["source"]["document_id"].startswith("GA-")
                    else "vector",
                    "kind": kind,
                    "value_kind": kind,
                    "residual": residual,
                }
            )
    return result


def paired_bootstrap(before, after, seed=2026, samples=2000):
    groups = defaultdict(list)
    own = {(r["tag"], r["degradation"], r["revision"]): r for r in before}
    if not own or set(own) != {(r["tag"], r["degradation"], r["revision"]) for r in after}:
        raise ValueError("La comparación pareada requiere los mismos casos completos")
    for r in after:
        b = own[(r["tag"], r["degradation"], r["revision"])]
        groups[r["tag"]].append(
            r["quality"]["recall_correct_fields"] - b["quality"]["recall_correct_fields"]
        )
    values = [sum(v) / len(v) for v in groups.values()]
    rng = random.Random(seed)
    draws = sorted(sum(rng.choice(values) for _ in values) / len(values) for _ in range(samples))
    return {
        "equipment": len(values),
        "mean_delta": sum(values) / len(values),
        "ci95": [draws[int(0.025 * samples)], draws[int(0.975 * samples)]],
        "bootstrap_samples": samples,
        "seed": seed,
        "unit": "fraction of expected fields correct",
        "grouping": "equipment; revisions and styles stay together",
    }


def profile_run(args):
    report, data, output, examples, priorities, name = args
    feedback = Feedback(
        examples=tuple(examples),
        priorities=priorities,
        stats={"synthetic_simulation": True, "human_sessions": 0},
    )
    result = replay(report, data, output, sets=["s-reservado"], all_cases=True, feedback=feedback)
    result["profile_name"] = name
    return result


def experiment(measurements, report, data, output, workers=3):
    started = time.perf_counter()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from bench.calibrar import evaluate
    from bench.recalibrar import propose

    train = json.loads((measurements / "d_hibrido/s-dev/triage.json").read_text(encoding="utf8"))
    test = json.loads(
        (measurements / "d_hibrido/s-reservado/triage.json").read_text(encoding="utf8")
    )
    if not train["complete"] or not test["complete"]:
        raise ValueError("Faltan particiones completas")
    if train["input_sha256"] != test["input_sha256"]:
        raise ValueError("Los corpus no coinciden")
    train_labels, test_labels = labels(train), labels(test)
    if {r["tag"] for r in train_labels} & {r["tag"] for r in test_labels}:
        raise ValueError("Equipos de entrenamiento y prueba se solapan")

    def document_hashes(partition):
        hashes = set()
        for case in partition["rows"]:
            folder = data / case["dataset"] / case["degradation"] / case["tag"]
            for prefix, suffix in [("GAD", "pdf"), ("HDM", "xlsx")]:
                file = folder / f"{prefix}_{case['tag']}_rev{case['revision']}.{suffix}"
                if file.is_file():
                    hashes.add(hashlib.sha256(file.read_bytes()).hexdigest())
        return hashes

    train_documents, test_documents = document_hashes(train), document_hashes(test)
    if train_documents & test_documents:
        raise ValueError("Un original aparece en ajuste y evaluación")
    channels = defaultdict(list)
    for row in train_labels:
        if row["channel"]:
            channels[row["channel"]].append((("S-dev", row["tag"]), row["correct"]))
    weights, stats = channel_priorities(channels)
    examples = [
        {
            "synthetic_simulation": True,
            "source": "synthetic ground truth, not human approval",
            "path": r["path"],
            "before": {"value": r["prediction"], "unit": r["unit"]},
            "after": {"value": r["expected"], "unit": r["unit"]},
            "evidence_text": r["source"].get("text_original") or r["source"]["locator"],
        }
        for r in train_labels
        if not r["correct"]
    ][:3]
    base = load_calibration()
    output.mkdir(parents=True, exist_ok=True)
    calibration_reports = {}
    for strategy in ("d_hibrido", "b_reglas+ocr"):
        partitions = [
            json.loads(
                (measurements / strategy / dataset / "triage.json").read_text(encoding="utf8")
            )
            for dataset in ("s-dev", "s-reservado")
        ]
        if not all(
            p["complete"] and p["input_sha256"] == train["input_sha256"] for p in partitions
        ):
            raise ValueError("La calibración requiere los mismos corpus completos")
        adjustment, holdout = map(labels, partitions)
        candidate, calibration_report = propose(adjustment, base)
        calibration_report.update(
            activated=False,
            synthetic_simulation=True,
            human_sessions=0,
            external_holdout_before=evaluate(holdout, base),
            external_holdout_after=evaluate(holdout, candidate) if candidate else None,
        )
        calibration_reports[strategy] = calibration_report
        if candidate:
            candidate.fitted_on = "Correcciones sintéticas simuladas; no revisión humana"
            candidate.meta["synthetic_simulation"] = True
            (output / f"candidate-calibration-{strategy}.json").write_text(
                json.dumps(candidate.to_dict(), ensure_ascii=False, indent=2) + "\n",
                encoding="utf8",
            )
    spec = TASKS["lineas"]
    with using(Feedback(examples=tuple(examples))):
        _, learned_prompt = extraction_prompt(spec)
    profiles = [
        ("priorities", [], weights),
        ("examples", examples, {}),
        ("combined", examples, weights),
    ]
    jobs = [(report, data, output / name, ex, pr, name) for name, ex, pr in profiles]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        runs = list(pool.map(profile_run, jobs))
    result = {
        "synthetic_simulation": True,
        "human_sessions": 0,
        "activated": False,
        "gpu": False,
        "production_store_modified": False,
        "input_sha256": train["input_sha256"],
        "baseline_metadata": train["metadata"],
        "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "train_equipment": sorted({r["tag"] for r in train_labels}),
        "test_equipment": sorted({r["tag"] for r in test_labels}),
        "train_fields": len(train_labels),
        "test_fields": len(test_labels),
        "shared_documents": len(train_documents & test_documents),
        "channel_priorities": weights,
        "channel_statistics": stats,
        "examples": examples,
        "baseline": summary(test["rows"]),
        "calibration": calibration_reports["d_hibrido"],
        "calibration_by_strategy": calibration_reports,
        "prompt_contract": {
            "base_sha256": spec.prompt_sha256,
            "with_examples_sha256": learned_prompt,
            "changed": spec.prompt_sha256 != learned_prompt,
            "provider_calls": 0,
        },
        "profiles": {},
        "limitation": (
            "Contexto experimental directo; sin sesiones ni autorización humana de producción. "
            "Sin proveedores de visión: few-shot solo prueba transporte del prompt, "
            "no eficacia visual."
        ),
    }
    for run in runs:
        delta = paired_bootstrap(test["rows"], run["rows"])
        result["profiles"][run["profile_name"]] = {
            "summary": summary(run["rows"]),
            "paired_recall": delta,
            "accepted_for_production": False,
        }
    result["wall_seconds"] = time.perf_counter() - started
    (output / "evaluation.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("measurements", "report", "data", "output"):
        p.add_argument("--" + key, type=Path, required=True)
    args = p.parse_args()
    if os.getenv("CUDA_VISIBLE_DEVICES") != "-1":
        p.error("Este experimento requiere CUDA_VISIBLE_DEVICES=-1")
    experiment(args.measurements, args.report, args.data, args.output)
