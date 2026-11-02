"""Contraste CPU posterior de la propuesta D; etiquetas sintéticas, ninguna activación."""

import argparse
import hashlib
import json
from pathlib import Path

from evaluate_synthetic_feedback import labels
from measure_scale import tasks

from bench.calibrar import evaluate
from bench.recalibrar import propose
from trazia.calibration import load_calibration


def evaluate_feedback(measurements, data, output, base):
    if any(part.lower() == "private" for part in data.resolve().parts):
        raise ValueError("Solo corpus sintéticos públicos")
    parts = [
        json.loads((measurements / name / "triage.json").read_text(encoding="utf8"))
        for name in ("s-dev", "s-reservado")
    ]
    if not all(part.get("complete") and part.get("synthetic") for part in parts):
        raise ValueError("Se requieren las dos particiones sintéticas completas")
    if parts[0]["input_sha256"] != parts[1]["input_sha256"]:
        raise ValueError("Las particiones no pertenecen al mismo corpus")
    if len({part["metadata"]["source_tree_sha256"] for part in parts}) != 1:
        raise ValueError("La fuente de extracción cambió entre particiones")
    if any(
        part["metadata"]["calibration_sha256"] != (base.sha256 if base else None) for part in parts
    ):
        raise ValueError("La base no es la que produjo las predicciones")
    tagged, original_sets = [], []
    for name, part in zip(("s-dev", "s-reservado"), parts, strict=True):
        documents, originals = {}, set()
        for task in tasks(data, [name]):
            hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path, _ in task["files"]]
            documents.setdefault(task["tag"], set()).update(hashes)
            originals.update(hashes)
        tagged.append(
            [{**row, "document_hashes": sorted(documents[row["tag"]])} for row in labels(part)]
        )
        original_sets.append(originals)
    if original_sets[0] & original_sets[1]:
        raise ValueError("Hay originales compartidos con la prueba externa")
    if {r["tag"] for r in tagged[0]} & {r["tag"] for r in tagged[1]}:
        raise ValueError("Hay equipos compartidos con la prueba externa")
    candidate, report = propose(tagged[0], base)
    before = evaluate(tagged[1], base)
    after = evaluate(tagged[1], candidate) if candidate else None
    report.update(
        synthetic_simulation=True,
        human_sessions=0,
        activated=False,
        input_sha256=parts[0]["input_sha256"],
        extraction_source_sha256=parts[0]["metadata"]["source_tree_sha256"],
        evaluator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        training_equipment=sorted({r["tag"] for r in tagged[0]}),
        external_equipment=sorted({r["tag"] for r in tagged[1]}),
        shared_originals=0,
        external_before=before,
        external_after=after,
        base_sha256=base.sha256 if base else None,
        limitation=(
            "Solo campos emitidos contrastados con verdad sintética; no es una sesión humana"
        ),
    )
    output.mkdir(parents=True, exist_ok=True)
    if candidate:
        candidate.fitted_on = "Simulación de correcciones sintéticas; cero sesiones humanas"
        candidate.meta["synthetic_simulation"] = True
        report["candidate_sha256"] = candidate.sha256
        (output / "propuesta-d-no-activada.json").write_text(
            json.dumps(candidate.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf8"
        )
    (output / "evaluation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measurements", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = evaluate_feedback(
        args.measurements, args.data, args.output, load_calibration(args.base)
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
