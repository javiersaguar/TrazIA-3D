"""Reproduce fallos sintéticos en CPU; la GT se consulta solo después de extraer."""

import argparse
import hashlib
import json
import os
import platform
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from cpu_quality import evaluate_prediction, summary
from measure_scale import tasks


def replay(
    report_path,
    data,
    output,
    *,
    sets=("s-dev",),
    category="all",
    limit=None,
    strategy="d_hibrido",
    all_cases=False,
    feedback=None,
):
    from trazia.calibration import load_calibration
    from trazia.feedback import using
    from trazia.model import GEOMETRY_FIELDS
    from trazia.pipeline import InputDocument, process
    from trazia.strategies.fusion import load_fusion

    report = json.loads(report_path.read_text(encoding="utf8"))
    if report.get("synthetic") is not True or not report.get("complete"):
        raise ValueError("Se requiere un lote sintético completo")
    if any(part.lower() == "private" for part in data.resolve().parts):
        raise ValueError("Este diagnóstico no admite datos privados")
    known = ("s-dev", "s-reservado", "s-mecanico", "s-adversarial")
    names = {r["dataset"] for r in report["rows"]}
    if not names.issubset(known) or not set(sets).issubset(names):
        raise ValueError("Conjunto desconocido: solo corpus sintéticos identificados")
    groups = [name for name in known if name in names]
    schedule = tasks(data, groups)
    if len(schedule) != len(report["rows"]):
        raise ValueError("El informe no cubre todas las revisiones del conjunto")
    digest = hashlib.sha256()
    for task in schedule:
        for file, _ in task["files"]:
            digest.update(
                file.relative_to(data).as_posix().encode()
                + hashlib.sha256(file.read_bytes()).digest()
            )
    if digest.hexdigest() != report["input_sha256"]:
        raise ValueError("Los documentos no coinciden con el lote medido")
    identities = {
        (r["dataset"], r["tag"], r["degradation"], r["revision"]): r
        for r in report["rows"]
        if (all_cases or r["status"] == "error")
        and r["dataset"] in sets
        and (category == "all" or ("Faltan datos" in r["error"]) == (category == "missing"))
    }
    selected = [
        t
        for t in schedule
        if tuple(t[k] for k in ("dataset", "tag", "degradation", "revision")) in identities
    ][:limit]
    source = Path(sys.modules["trazia.model"].__file__).parent
    code = hashlib.sha256()
    for path in sorted(source.rglob("*.py")):
        code.update(path.relative_to(source).as_posix().encode() + path.read_bytes())
    calibration, fusion = load_calibration(), load_fusion()
    metadata = {
        "at": datetime.now(timezone.utc).isoformat(),
        "source_tree_sha256": code.hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "calibration_sha256": calibration.sha256 if calibration else None,
        "fusion_sha256": fusion.sha256 if fusion else None,
        "python": sys.version,
        "platform": platform.platform(),
        "cuda_visible_devices": os.getenv("CUDA_VISIBLE_DEVICES"),
        "measurement_image": os.getenv("TRAZIA_MEASUREMENT_IMAGE"),
        "source_overridden_by_readonly_mount": os.getenv("TRAZIA_SOURCE_MOUNTED") == "1",
        "feedback_sha256": feedback.sha256 if feedback else None,
        "feedback_experimental_only": feedback is not None,
    }
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for index, task in enumerate(selected):
        old = identities[tuple(task[k] for k in ("dataset", "tag", "degradation", "revision"))]
        started = time.perf_counter()
        with using(feedback):
            result = process(
                [InputDocument(p.name, p.read_bytes(), identity) for p, identity in task["files"]],
                project_id="SYNTHETIC-TRIAGE",
                equipment_id=task["tag"],
                revision=task["revision"],
                strategy=strategy,
                providers=[],
                dataset="synthetic",
            )
        # Verdad sintética usada exclusivamente como evaluación posterior, nunca como entrada.
        truth_path = data / task["dataset"] / "truth" / f"{task['tag']}.json"
        truth_bytes = truth_path.read_bytes()
        truth = json.loads(truth_bytes)[f"rev{task['revision']}"]
        candidates = [
            c.model_dump(mode="json") for c in result.candidates if c.path in GEOMETRY_FIELDS
        ]
        errors = {
            c["path"]: abs(float(c["value"]) - truth[c["path"]])
            for c in candidates
            if isinstance(c["value"], (int, float)) and c["path"] in truth and c["unit"] == "mm"
        }
        rows.append(
            {
                **{k: task[k] for k in ("dataset", "tag", "degradation", "revision")},
                "previous_error": old.get("error"),
                "error": result.error,
                "status": "draft" if result.revision else "error",
                "seconds": time.perf_counter() - started,
                "geometry_candidates": candidates,
                "geometry_absolute_errors_mm": errors,
                "ground_truth_after_extraction": {
                    k: truth[k] for k in GEOMETRY_FIELDS if k in truth
                },
                "warnings": result.warnings,
                "run": result.run.model_dump(mode="json"),
                "quality": evaluate_prediction(result.revision, result.candidates, truth),
                "truth_sha256_after_prediction": hashlib.sha256(truth_bytes).hexdigest(),
            }
        )
        if result.revision:
            path = (
                output
                / "models"
                / (
                    "__".join(task[k] for k in ("dataset", "tag", "degradation", "revision"))
                    + ".json"
                )
            )
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(result.revision.model_dump_json(indent=2), encoding="utf8")
        payload = {
            "metadata": metadata,
            "synthetic": True,
            "input_sha256": digest.hexdigest(),
            "planned": len(selected),
            "complete": len(rows) == len(selected),
            "strategy": strategy,
            "scope": "all" if all_cases else "previous_errors",
            "providers": [],
            "gt_used_for_prediction": False,
            "sets": list(sets),
            "category": category,
            "statuses": dict(Counter(r["status"] for r in rows)),
            "rows": rows,
            "quality_summary": summary(rows),
        }
        (output / "triage.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
        )
        print(
            f"Diagnóstico {index + 1}/{len(selected)}: "
            f"{task['tag']} rev{task['revision']} {rows[-1]['status']}",
            flush=True,
        )
    if not selected:
        raise ValueError("No hay casos fallidos en esa selección")
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sets", nargs="+", default=["s-dev"])
    parser.add_argument("--category", choices=["all", "missing", "geometry"], default="all")
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--strategy",
        default="d_hibrido",
        choices=[
            "d_hibrido",
            "b_reglas",
            "b_reglas+ocr",
            "d_hibrido-geometria",
            "d_hibrido+heuristica",
            "a_geometria",
        ],
    )
    parser.add_argument("--all-cases", action="store_true")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("El límite debe ser positivo")
    if os.getenv("CUDA_VISIBLE_DEVICES") != "-1":
        parser.error("Ejecutar con CUDA_VISIBLE_DEVICES=-1; diagnóstico exclusivamente CPU")
    replay(
        args.report,
        args.data,
        args.output,
        sets=args.sets,
        category=args.category,
        limit=args.limit,
        strategy=args.strategy,
        all_cases=args.all_cases,
    )


if __name__ == "__main__":
    main()
