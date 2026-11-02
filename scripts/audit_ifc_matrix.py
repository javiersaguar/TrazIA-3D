"""Matriz reproducible de conformidad interna IFC sintética, sin GPU ni visor externo."""

import argparse
import hashlib
import json
import time
from pathlib import Path

from ifc_audit_fixtures import CASES, fixture

from trazia.families.audit import audit_ifc
from trazia.ifc import build_ifc


def matrix(output):
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    started = time.perf_counter()
    for name in CASES:
        source = fixture(name)
        source_before = source.model_dump_json()
        for schema in ("IFC4", "IFC4X3", "IFC2X3"):
            for details in (False, True):
                stamp = time.perf_counter()
                model = build_ifc(source, schema=schema, details=details, draft=True)
                audit = audit_ifc(source, model)
                text = model.to_string().encode()
                file = output / f"{name}-{schema}-{'detail' if details else 'core'}.ifc"
                file.write_bytes(text)
                other = source.model_copy(deep=True)
                other.revision = "B"
                second = audit_ifc(
                    other, build_ifc(other, schema=schema, details=details, draft=True)
                )
                same = {k: v["guid"] for k, v in audit["components"].items()} == {
                    k: v["guid"] for k, v in second["components"].items()
                }
                audit.update(
                    case=name,
                    details=details,
                    guid_stable_across_revision=same,
                    guid_stable_across_schema=True,
                    seconds=time.perf_counter() - stamp,
                    artifact=file.name,
                    artifact_sha256=hashlib.sha256(text).hexdigest(),
                )
                audit["valid"] = audit["valid"] and second["valid"] and same
                rows.append(audit)
                (output / "matrix.json").write_text(
                    json.dumps({"complete": False, "rows": rows}, ensure_ascii=False, indent=2)
                    + "\n",
                    encoding="utf8",
                )
                print(name, schema, details, audit["valid"], flush=True)
        assert source.model_dump_json() == source_before, "La auditoría modificó la entrada"
    for name in CASES:
        for details in (False, True):
            group = [r for r in rows if r["case"] == name and r["details"] == details]
            keys = [{k: v["guid"] for k, v in r["components"].items()} for r in group]
            stable = all(k == keys[0] for k in keys)
            for row in group:
                row["guid_stable_across_schema"] = stable
                row["valid"] &= stable
    result = {
        "complete": True,
        "synthetic": True,
        "gpu": False,
        "cases": len(rows),
        "passed": sum(r["valid"] for r in rows),
        "seconds": time.perf_counter() - started,
        "bimvision_measured": False,
        "tr_reference_available": False,
        "rows": rows,
    }
    (output / "matrix.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    result = matrix(p.parse_args().output)
    raise SystemExit(0 if result["passed"] == result["cases"] else 1)
