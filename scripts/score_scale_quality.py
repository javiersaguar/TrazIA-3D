"""Contrasta después del lote los JSON sintéticos realmente devueltos por la API."""

import argparse
import hashlib
import json
from pathlib import Path

from cpu_quality import evaluate_prediction, summary
from measure_scale import tasks

from trazia.model import Revision

SETS = ["s-dev", "s-reservado", "s-mecanico", "s-adversarial"]


def identity(row):
    return tuple(str(row[key]) for key in ("dataset", "tag", "degradation", "revision"))


def score(report_path, data, output):
    report = json.loads(report_path.read_text(encoding="utf8"))
    if not report.get("synthetic") or not report.get("complete"):
        raise ValueError("Solo se evalúan lotes sintéticos completos")
    identities = {identity(row) for row in report["rows"]}
    if len(identities) != len(report["rows"]):
        raise ValueError("El lote contiene revisiones duplicadas")
    plan = [task for task in tasks(data, SETS) if identity(task) in identities]
    if {identity(task) for task in plan} != identities:
        raise ValueError("Faltan originales sintéticos del lote")
    fingerprint = hashlib.sha256()
    for task in plan:
        for file, _ in task["files"]:
            fingerprint.update(
                file.relative_to(data).as_posix().encode()
                + hashlib.sha256(file.read_bytes()).digest()
            )
    if fingerprint.hexdigest() != report["input_sha256"]:
        raise ValueError("La huella de originales no coincide con la medición")
    rows = []
    for original in report["rows"]:
        model = None
        artifact = original.get("model_artifact")
        if original["status"] == "done":
            if not artifact:
                raise ValueError("Falta un JSON exportado; repetir con --guardar-modelos")
            path = (report_path.parent / artifact).resolve()
            if not path.is_relative_to(report_path.parent.resolve()):
                raise ValueError("El modelo archivado sale del directorio del lote")
            model = Revision.model_validate_json(path.read_bytes())
            if model.dataset != "synthetic":
                raise ValueError("El modelo no está etiquetado como sintético")
        truth_path = data / original["dataset"] / "truth" / (original["tag"] + ".json")
        truth_bytes = truth_path.read_bytes()
        truth = json.loads(truth_bytes)["rev" + str(original["revision"])]
        rows.append(
            {key: original[key] for key in ("dataset", "tag", "degradation", "revision")}
            | {
                "status": "draft" if model else "error",
                "error": original.get("error"),
                "run": original.get("run") or {},
                "unplaced_nozzles": model.unplaced_nozzles if model else None,
                "model_sha256": hashlib.sha256(path.read_bytes()).hexdigest() if model else None,
                "quality": evaluate_prediction(model, [], truth),
                "truth_sha256_after_prediction": hashlib.sha256(truth_bytes).hexdigest(),
            }
        )
    result = {
        "synthetic": True,
        "input_sha256": report["input_sha256"],
        "gt_used_for_prediction": False,
        "scope": "Solo modelos exportados por la API; errores cuentan como campos ausentes",
        "engineering_accuracy_verified": False,
        "measurement_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
        "summary": summary(rows),
        "rows": rows,
    }
    drafts = [row for row in rows if row["status"] == "draft"]
    result["summary"]["drafts_with_unplaced_nozzles"] = sum(
        bool(row["unplaced_nozzles"]) for row in drafts
    )
    result["summary"]["drafts_all_fields_correct_and_no_unplaced_nozzles"] = sum(
        row["quality"]["all_fields_correct"] and not row["unplaced_nozzles"] for row in drafts
    )
    result["measurement_inspection_differences"] = [
        {
            "dataset": original["dataset"],
            "tag": original["tag"],
            "degradation": original["degradation"],
            "revision": original["revision"],
            "reported_unplaced": original.get("unplaced_nozzles"),
            "archived_unplaced": len(row["unplaced_nozzles"]),
        }
        for original, row in zip(report["rows"], rows)
        if row["status"] == "draft"
        and original.get("unplaced_nozzles") != len(row["unplaced_nozzles"])
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("report", "data", "output"):
        parser.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(score(args.report, args.data, args.output)["summary"], ensure_ascii=False))
