"""Compara lectores CPU existentes sin modificar ni entrenar sus estrategias."""

import argparse
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from cpu_quality import summary
from triage_scale import replay


def partition(args):
    report, data, output, dataset, strategy, scope = args
    return replay(report, data, output, sets=[dataset], strategy=strategy, all_cases=scope == "all")


def measure(report, data, output, *, strategies, sets, scope="all", workers=4):
    output.mkdir(parents=True, exist_ok=True)
    jobs = [
        (report, data, output / strategy / dataset, dataset, strategy, scope)
        for strategy in strategies
        for dataset in sets
    ]
    started = time.perf_counter()
    results = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(partition, job) for job in jobs]
        for future in as_completed(futures):
            results.append(future.result())
    comparison = {}
    for strategy in strategies:
        reports = [r for r in results if r["strategy"] == strategy]
        rows = [row for r in reports for row in r["rows"]]
        comparison[strategy] = {
            "summary": summary(rows),
            "by_dataset": {r["sets"][0]: r["quality_summary"] for r in reports},
        }
    result = {
        "synthetic": True,
        "providers": [],
        "gpu": False,
        "scope": scope,
        "complete": all(r["complete"] for r in results),
        "workers": workers,
        "wall_seconds": time.perf_counter() - started,
        "input_sha256": sorted({r["input_sha256"] for r in results}),
        "comparison": comparison,
        "limitation": "Paralelismo por conjunto; no mide Redis ni aísla causalidad de cachés",
    }
    (output / "comparison.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--strategies", nargs="+", default=["d_hibrido", "b_reglas+ocr"])
    p.add_argument(
        "--sets", nargs="+", default=["s-dev", "s-reservado", "s-mecanico", "s-adversarial"]
    )
    p.add_argument("--scope", choices=["all", "previous_errors"], default="all")
    p.add_argument("--workers", type=int, default=4)
    args = p.parse_args()
    if os.getenv("CUDA_VISIBLE_DEVICES") != "-1" or not 1 <= args.workers <= 4:
        p.error("CPU exclusivamente; CUDA_VISIBLE_DEVICES=-1 y entre 1 y 4 workers")
    allowed = {
        "d_hibrido",
        "b_reglas",
        "b_reglas+ocr",
        "d_hibrido-geometria",
        "d_hibrido+heuristica",
        "a_geometria",
    }
    if not set(args.strategies).issubset(allowed):
        p.error("Solo lectores CPU existentes autorizados")
    result = measure(
        args.report,
        args.data,
        args.output,
        strategies=args.strategies,
        sets=args.sets,
        scope=args.scope,
        workers=args.workers,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
