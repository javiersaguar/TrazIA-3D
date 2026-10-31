"""Compara estados de lotes sintéticos; no atribuye causalidad ni precisión de ingeniería."""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def key(row):
    return tuple(row[name] for name in ("dataset", "tag", "degradation", "revision"))


def index(report):
    if report.get("synthetic") is not True:
        raise ValueError("Solo informes sintéticos")
    result = {key(row): row for row in report["rows"]}
    if len(result) != len(report["rows"]):
        raise ValueError("Hay revisiones duplicadas en el informe")
    if not report["complete"] or len(result) != report["planned_revisions"]:
        raise ValueError("No se comparan lotes incompletos como si estuviesen terminados")
    return result


def compare(before, after):
    old, new = index(before), index(after)
    if old.keys() != new.keys() or before["input_sha256"] != after["input_sha256"]:
        raise ValueError("No coincide el conjunto de revisiones y documentos")
    transitions, changes = Counter(), []
    for identity in sorted(old):
        a, b = old[identity], new[identity]
        transitions[f"{a['status']} -> {b['status']}"] += 1
        if (a["status"], a.get("lod"), a.get("error"), a.get("inspection_error")) != (
            b["status"],
            b.get("lod"),
            b.get("error"),
            b.get("inspection_error"),
        ):
            changes.append(
                {
                    **dict(zip(("dataset", "tag", "degradation", "revision"), identity)),
                    "before": {k: a.get(k) for k in ("status", "lod", "error", "inspection_error")},
                    "after": {k: b.get(k) for k in ("status", "lod", "error", "inspection_error")},
                }
            )
    return {
        "transitions": dict(transitions),
        "changes": changes,
        "same_status_lod_error": not changes,
    }


def by_equipment(report):
    groups = defaultdict(list)
    for row in report["rows"]:
        groups[(row["dataset"], row["tag"])].append(row)
    result = []
    for (dataset, tag), rows in sorted(groups.items()):

        def total(getter):
            values = [getter(row) for row in rows]
            return sum(values) if all(v is not None for v in values) else None

        result.append(
            {
                "dataset": dataset,
                "tag": tag,
                "revisions": len(rows),
                "statuses": dict(Counter(r["status"] for r in rows)),
                "lods": dict(Counter(str(r.get("lod")) for r in rows if r["status"] == "done")),
                "pipeline_seconds_sum": total(lambda r: (r.get("run") or {}).get("seconds")),
                "job_elapsed_seconds_sum": total(lambda r: r.get("job_elapsed_seconds")),
                "turnaround_seconds_sum": total(lambda r: r.get("seconds_turnaround")),
                "provider_cost_eur": total(lambda r: (r.get("run") or {}).get("cost_eur")),
                "cache_hits": sum(r.get("cache_hit") is True for r in rows)
                if all(isinstance(r.get("cache_hit"), bool) for r in rows)
                else None,
            }
        )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uno", required=True, type=Path)
    parser.add_argument("--cuatro", required=True, type=Path)
    parser.add_argument("--anterior", required=True, type=Path)
    parser.add_argument("--salida", required=True, type=Path)
    args = parser.parse_args()
    one, four, old = [
        json.loads(p.read_text(encoding="utf8")) for p in (args.uno, args.cuatro, args.anterior)
    ]
    result = {
        "synthetic": True,
        "input_sha256": one["input_sha256"],
        "comparison_workers": compare(one, four),
        "comparison_previous_heuristic_to_learned": compare(old, four),
        "speedup_observed": one["summary"]["seconds_batch"] / four["summary"]["seconds_batch"],
        "runs": [
            {
                "workers": n,
                "deployment": r.get("deployment"),
                "summary": {
                    k: v for k, v in r["summary"].items() if k != "per_equipment_condition"
                },
                "equipment": by_equipment(r),
            }
            for n, r in ((1, one), (4, four))
        ],
        "limit": (
            "Host compartido; cambian fusión, calibración y código. No es un efecto causal aislado."
        ),
    }
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(
        json.dumps(
            {
                "speedup": result["speedup_observed"],
                "transitions": result["comparison_previous_heuristic_to_learned"]["transitions"],
            }
        )
    )


if __name__ == "__main__":
    main()
