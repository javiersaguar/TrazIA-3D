"""Evaluación posterior sobre verdad sintética; nunca interviene en la predicción."""

import math
from collections import Counter

from trazia.model import fields

GEOMETRY = ("diameter", "height", "head_depth", "skirt_height", "skirt_thickness")


def expected_fields(truth):
    if "base_length" in truth:
        return {
            "tag": (truth["tag"], "1"),
            "envelope.size.x": (truth["base_length"], "mm"),
            "envelope.size.y": (truth["base_width"], "mm"),
            "envelope.size.z": (
                max(truth["discharge_z"], truth["shaft_height"] + truth["motor_half"]),
                "mm",
            ),
            **{
                f"nozzles.{name}.{key}": (value, "mm")
                for name, values in {
                    "S": {
                        "diameter": truth["suction_dn"],
                        "x": truth["suction_x"],
                        "y": 0,
                        "z": truth["shaft_height"],
                    },
                    "D": {
                        "diameter": truth["discharge_dn"],
                        "x": truth["discharge_x"],
                        "y": 0,
                        "z": truth["discharge_z"],
                    },
                }.items()
                for key, value in values.items()
            },
        }
    result = {key: (truth[key], "mm") for key in GEOMETRY if key in truth}
    if "tag" in truth:
        result["tag"] = (truth["tag"], "1")
    for nozzle in truth.get("nozzles", []):
        for key in ("diameter", "projection", "elevation", "azimuth"):
            if key in nozzle:
                result[f"nozzles.{nozzle['id']}.{key}"] = (
                    nozzle[key],
                    "deg" if key == "azimuth" else "mm",
                )
        for vector, unit in (("position", "mm"), ("direction", "1")):
            for axis, value in nozzle.get(vector, {}).items():
                result[f"nozzles.{nozzle['id']}.{vector}.{axis}"] = (value, unit)
    for vector in ("origin", "size"):
        for axis, value in truth.get("envelope", {}).get(vector, {}).items():
            result[f"envelope.{vector}.{axis}"] = (value, "mm")
    return result


def correct(value, expected, unit):
    if isinstance(value, str) or isinstance(expected, str):
        return str(value).strip().upper() == str(expected).strip().upper()
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        return False
    delta = abs(float(value) - expected)
    if unit == "deg":
        delta = min(delta % 360, 360 - delta % 360)
    return delta <= (1e-6 if unit == "1" else 0.5)


def evaluate_prediction(revision, candidates, truth):
    expected = expected_fields(truth)
    predicted = fields(revision.equipment) if revision else {c.path: c for c in candidates}
    extra_nozzles = sorted(p for p in predicted if p.startswith("nozzles.") and p not in expected)
    rows = []
    for path, (value, unit) in expected.items():
        found = predicted.get(path)
        candidate = next((c for c in candidates if c.path == path), None)
        raw = found.source.confidence_raw if found else None
        if raw is None and found:
            raw = found.source.confidence
        channel = None if candidate is None else candidate.channel
        rows.append(
            {
                "path": path,
                "expected": value,
                "unit": unit,
                "prediction": found.value if found else None,
                "present": found is not None,
                "correct": bool(found and found.unit == unit and correct(found.value, value, unit)),
                "channel": channel or (found.source.channel if found else None),
                "raw": raw if raw is not None else (found.source.confidence if found else None),
                "extractor_raw": candidate.confidence_raw if candidate else None,
                "confidence": found.source.confidence if found else None,
                "state": found.state if found else None,
                "source": found.source.model_dump(mode="json") if found else None,
            }
        )
    geometry = [r for r in rows if r["path"] in GEOMETRY or r["path"].startswith("envelope.")]
    present = sum(r["present"] for r in rows) + len(extra_nozzles)
    good = sum(r["correct"] for r in rows)
    return {
        "expected_fields": len(rows),
        "present_fields": present,
        "correct_fields": good,
        "precision_returned_fields": good / present if present else None,
        "recall_correct_fields": good / len(rows) if rows else None,
        "all_geometry_correct": bool(geometry) and all(r["correct"] for r in geometry),
        "all_fields_correct": all(r["correct"] for r in rows) and not extra_nozzles,
        "extra_nozzle_fields": extra_nozzles,
        "not_evaluated_paths": sorted(set(predicted) - set(expected) - set(extra_nozzles)),
        "evaluated_scope": "tag, geometría principal/envolvente y boquillas; sin atributos HDM",
        "tolerance": "0.5 mm, 0.5 grados circulares, 1e-6 para direcciones; texto exacto",
        "rows": rows,
    }


def summary(rows):
    expected = sum(r["quality"]["expected_fields"] for r in rows)
    present = sum(r["quality"]["present_fields"] for r in rows)
    good = sum(r["quality"]["correct_fields"] for r in rows)
    drafts = [r for r in rows if r["status"] == "draft"]
    return {
        "revisions": len(rows),
        "statuses": dict(Counter(r["status"] for r in rows)),
        "expected_fields": expected,
        "present_fields": present,
        "correct_fields": good,
        "precision_returned_fields": good / present if present else None,
        "recall_correct_fields": good / expected if expected else None,
        "drafts_all_geometry_correct": sum(r["quality"]["all_geometry_correct"] for r in drafts),
        "drafts_all_fields_correct": sum(r["quality"]["all_fields_correct"] for r in drafts),
        "pipeline_seconds_sum": sum(r["run"]["seconds"] for r in rows)
        if all(isinstance(r["run"].get("seconds"), (int, float)) for r in rows)
        else None,
        "external_calls": sum(r["run"]["external_calls"] for r in rows)
        if all(isinstance(r["run"].get("external_calls"), int) for r in rows)
        else None,
        "cost_for_1600_engineering_valid_ifc": None,
        "engineering_accuracy_verified": False,
    }
