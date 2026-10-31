"""Prepara dos revisiones por B/CPU; no realiza ni simula la revisión humana."""

import argparse
import json
import os
import time
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from trazia.api import create_app
from trazia.model import Revision, fields, load_revision

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path, required=True)
    args = parser.parse_args()
    target = args.salida.resolve()
    if not target.is_relative_to(ROOT / "generated"):
        parser.error("El almacén piloto debe estar dentro de generated/")
    if target.exists() and any(target.iterdir()):
        parser.error("Usa un destino nuevo para conservar cualquier revisión anterior")
    os.environ["TRAZIA_QUEUE"] = "process"
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    result = {
        "dataset": "synthetic",
        "strategy": "b_reglas",
        "cpu_only": True,
        "human_sessions": 0,
        "human_review_seconds": None,
        "revisions": [],
    }
    with TestClient(create_app(root=ROOT, data_root=target, seed=False)) as client:
        for revision in ("A", "B"):
            fixture = load_revision(ROOT / "examples" / f"vessel_rev_{revision.lower()}.json")
            uploads = []
            for document in fixture.documents:
                content = (ROOT / "examples/documents" / document.filename).read_bytes()
                uploaded = client.post(
                    "/documents",
                    files={"file": (document.filename, content)},
                    data={"document_id": document.id, "revision": revision},
                    headers={"Idempotency-Key": uuid4().hex},
                )
                uploaded.raise_for_status()
                uploads.append(uploaded.json()["id"])
            job = client.post(
                "/equipment/V-101/jobs",
                headers={"Idempotency-Key": uuid4().hex},
                json={
                    "documents": uploads,
                    "revision": revision,
                    "strategy": "b_reglas",
                    "dataset": "synthetic",
                    "providers": [],
                    "max_attempts": 1,
                },
            )
            job.raise_for_status()
            identity = job.json()["job_id"]
            deadline = time.monotonic() + 180
            while True:
                status = client.get(f"/jobs/{identity}").json()
                if status["status"] in ("done", "error", "cancelled", "timeout"):
                    break
                if time.monotonic() >= deadline:
                    raise TimeoutError("No terminó la preparación del piloto")
                time.sleep(0.05)
            if status["status"] != "done":
                raise RuntimeError(f"Falló {revision}: {status['error']}")
            response = client.get(f"/equipment/V-101/revisions/{revision}")
            response.raise_for_status()
            model = Revision.model_validate_json(response.text)
            traced = fields(model.equipment)
            result["revisions"].append(
                {
                    "revision": revision,
                    "revision_id": status["revision_id"],
                    "job_id": identity,
                    "strategy": model.run.strategy,
                    "fields": len(traced),
                    "fields_with_raw_confidence": sum(
                        f.source.confidence_raw is not None for f in traced.values()
                    ),
                    "documents": [d.model_dump(mode="json") for d in model.documents],
                    "run": model.run.model_dump(mode="json"),
                    "approved": model.approval is not None,
                }
            )
    (target / "preparacion.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
