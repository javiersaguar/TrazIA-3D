"""Ejecuta el pipeline real del núcleo sobre el conjunto sintético y lo puntúa contra la verdad.

El extractor es un parámetro: cualquier implementación de trazia.extraction.Extractor se mide
igual. Los tiempos son reales (ingesta + extracción + ensamblado + IFC).
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from synthetic.cases import VesselSpec, flatten, spec_from_dict, spec_to_revision
from trazia.extraction import Candidate, Extractor, LabelExtractor, assemble
from trazia.ifc import build_ifc
from trazia.ingest import ingest_bytes
from trazia.model import Revision
from trazia.revisions import compare

from .ifc_geometry import compare_models
from .metrics import angle_error, distance, nozzle_face_center, same_value

EXTRACTORS: dict[str, type] = {"etiquetas": LabelExtractor}
DIMENSIONS = ("diameter", "height", "head_depth", "skirt_height", "skirt_thickness")


@dataclass
class Extraction:
    candidates: dict[str, Candidate]
    conflicts: list[str]
    revision: Revision | None
    error: str | None
    seconds: float
    warnings: list[str] = field(default_factory=list)


def run_extraction(folder: Path, tag: str, rev: str, extractor: Extractor) -> Extraction:
    started = time.perf_counter()
    bundles, warnings = [], []
    for name, doc_id in (
        (f"GAD_{tag}_rev{rev}.pdf", f"GA-{tag}"),
        (f"HDM_{tag}_rev{rev}.xlsx", f"HDM-{tag}"),
    ):
        try:
            bundle = ingest_bytes((folder / name).read_bytes(), name, doc_id, rev)
        except ValueError as exc:  # incluye errores de validación del contrato
            first_line = str(exc).splitlines()[0]
            warnings.append(f"Ingesta fallida de {name}: {first_line}")
            continue
        warnings += bundle.warnings
        bundles.append(bundle)
    if not bundles:
        return Extraction(
            {},
            [],
            None,
            "Ingesta fallida de todos los documentos",
            time.perf_counter() - started,
            warnings,
        )
    chosen: dict[str, Candidate] = {}
    conflicts = []
    for c in extractor.extract(bundles):
        previous = chosen.get(c.path)
        if previous and (previous.value, previous.unit) != (c.value, c.unit):
            conflicts.append(c.path)
        chosen.setdefault(c.path, c)
    revision, error = None, None
    try:
        revision = assemble(
            bundles,
            list(chosen.values()),
            project_id="BENCH",
            equipment_id=tag.lower(),
            revision=rev,
            dataset="synthetic",
        )
        build_ifc(revision, draft=True)  # el IFC forma parte del coste por equipo
    except ValueError as exc:
        error = str(exc)
    return Extraction(chosen, conflicts, revision, error, time.perf_counter() - started, warnings)


def score_revision(extraction: Extraction, truth: VesselSpec) -> dict:
    expected = flatten(truth)
    fields_rows = []
    calibration = []
    for path, (value, unit) in expected.items():
        candidate = extraction.candidates.get(path)
        ok = (
            candidate is not None
            and candidate.unit == unit
            and same_value(candidate.value, value, unit)
        )
        if candidate is not None:
            calibration.append((candidate.source.confidence, ok))
        fields_rows.append({"path": path, "found": candidate is not None, "correct": ok})
    spurious = sorted(set(extraction.candidates) - set(expected))

    dims = []
    for key in DIMENSIONS:
        c = extraction.candidates.get(key)
        if c is not None and isinstance(c.value, float):
            dims.append({"field": key, "abs_error_mm": abs(c.value - getattr(truth, key))})

    nozzles = []
    predicted_diameter = extraction.candidates.get("diameter")
    for n in truth.nozzles:
        get = extraction.candidates.get
        elev, az = get(f"nozzles.{n.id}.elevation"), get(f"nozzles.{n.id}.azimuth")
        proj, dn = get(f"nozzles.{n.id}.projection"), get(f"nozzles.{n.id}.diameter")
        row = {"id": n.id, "detected": elev is not None and az is not None}
        if row["detected"] and proj is not None and predicted_diameter is not None:
            mine = nozzle_face_center(
                float(predicted_diameter.value),
                float(elev.value),
                float(az.value),
                float(proj.value),
            )
            real = nozzle_face_center(truth.diameter, n.elevation, n.azimuth, n.projection)
            row["position_error_mm"] = distance(mine, real)
        if row["detected"]:
            row["orientation_error_deg"] = angle_error(float(az.value), n.azimuth)
        row["dn_correct"] = dn is not None and same_value(dn.value, n.diameter, "mm")
        nozzles.append(row)
    predicted_ids = {p.split(".")[1] for p in extraction.candidates if p.startswith("nozzles.")}
    false_nozzles = sorted(predicted_ids - {n.id for n in truth.nozzles})

    ifc = None
    if extraction.revision is not None:
        reference = build_ifc(spec_to_revision(truth, extraction.revision.revision), draft=True)
        ifc = compare_models(build_ifc(extraction.revision, draft=True), reference)

    return {
        "fields": fields_rows,
        "spurious": spurious,
        "conflicts": extraction.conflicts,
        "calibration": calibration,
        "dimensions": dims,
        "nozzles": nozzles,
        "false_nozzles": false_nozzles,
        "ifc": ifc,
        "assembled": extraction.revision is not None,
        "error": extraction.error,
        "seconds": extraction.seconds,
        "warnings": extraction.warnings,
    }


def score_delta(first: Extraction, second: Extraction, expected: list[dict]) -> dict | None:
    """Cambios detectados frente a los esperados. Solo si las dos revisiones produjeron modelo."""
    if first.revision is None or second.revision is None:
        return None
    detected = compare(first.revision, second.revision)["changes"]
    mine = {(c["path"], c["operation"]): c for c in detected}
    truth = {(c["path"], c["operation"]): c for c in expected}
    tp = mine.keys() & truth.keys()
    magnitude = []
    for key in tp:
        a, b = mine[key], truth[key]
        if key[1] == "modified" and all(
            isinstance(x["value"], float)
            for x in (a["before"], a["after"], b["before"], b["after"])
        ):
            magnitude.append(
                abs(
                    (a["after"]["value"] - a["before"]["value"])
                    - (b["after"]["value"] - b["before"]["value"])
                )
            )
    return {
        "tp": len(tp),
        "fp": len(mine.keys() - truth.keys()),
        "fn": len(truth.keys() - mine.keys()),
        "false_positives": sorted(f"{p}:{o}" for p, o in mine.keys() - truth.keys()),
        "missed": sorted(f"{p}:{o}" for p, o in truth.keys() - mine.keys()),
        "magnitude_errors": magnitude,
    }


def run_bench(dataset: Path, extractor_name: str = "etiquetas") -> dict:
    manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
    extractor = EXTRACTORS[extractor_name]()
    results = {
        "dataset": str(dataset),
        "seed": manifest["seed"],
        "extractor": extractor_name,
        "styles": {},
    }
    for style in manifest["styles"]:
        cases = []
        for case in manifest["cases"]:
            tag = case["tag"]
            truth = json.loads((dataset / "truth" / f"{tag}.json").read_text(encoding="utf-8"))
            spec1, spec2 = spec_from_dict(truth["rev1"]), spec_from_dict(truth["rev2"])
            folder = dataset / style / tag
            first = run_extraction(folder, tag, "1", extractor)
            second = run_extraction(folder, tag, "2", extractor)
            cases.append(
                {
                    "tag": tag,
                    "rev1": score_revision(first, spec1),
                    "rev2": score_revision(second, spec2),
                    "delta": score_delta(first, second, truth["changes"]),
                    "expected_changes": len(truth["changes"]),
                }
            )
        results["styles"][style] = cases
    return results
