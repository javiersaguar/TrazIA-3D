"""Ensayo sintético aislado del JSONL → recalibración; revisión simulada, no humana medida."""

import argparse
import hashlib
import json
import time
from pathlib import Path

from sqlmodel import Session

from bench.estudio import _documents, reviewed_by_oracle
from bench.recalibrar import main as recalibrate
from trazia.api.corrections import flush, record_change
from trazia.api.repository import revision_id
from trazia.model import fields
from trazia.pipeline import InputDocument, process
from trazia.store import AuditRecord, RevisionRecord, Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--casos", type=int, default=9)
    args = parser.parse_args()
    root = args.data / "s-dev"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("synthetic") is not True or args.casos < 6:
        parser.error("Se requiere S-dev sintético y al menos seis equipos")
    if (args.output / "store/trazia.sqlite3").exists():
        parser.error("Usa una salida nueva para no mezclar ensayos")
    started = time.perf_counter()
    store = Store(args.output / "store")
    ledger = args.output / "correcciones.jsonl"
    counts = {"revisions": 0, "approved_simulated": 0, "failed": 0}
    for case in manifest["cases"][: args.casos]:
        tag = case["tag"]
        truth = json.loads((root / "truth" / f"{tag}.json").read_text(encoding="utf-8"))
        for rev in ("1", "2"):
            docs = _documents(root / "vectorial" / tag, tag, rev)
            counts["revisions"] += 1
            result = process(
                [InputDocument(p.name, p.read_bytes(), identity) for p, identity in docs],
                project_id="FEEDBACK-SINTETICO",
                equipment_id=tag,
                revision=rev,
                strategy="b_reglas",
                dataset="synthetic",
            )
            approved = (
                reviewed_by_oracle(result.revision, truth[f"rev{rev}"], docs)
                if result.revision
                else None
            )
            if approved is None:
                counts["failed"] += 1
                continue
            for path, _ in docs:
                store.put(path.read_bytes())
            record = RevisionRecord(
                id=revision_id(approved),
                project_id=approved.project_id,
                equipment_id=tag,
                tag=tag,
                revision=rev,
                payload=approved.model_dump_json(),
            )
            with Session(store.engine) as session:
                session.add(record)
                session.flush()
                for path in fields(approved.equipment):
                    session.add(
                        AuditRecord(
                            revision_id=record.id,
                            path=path,
                            actor="Revisión simulada sintética",
                            before_json=result.revision.model_dump_json(),
                            after_json=approved.model_dump_json(),
                        )
                    )
                    record_change(
                        session,
                        record,
                        result.revision,
                        approved,
                        path,
                        "Revisión simulada sintética",
                    )
                session.commit()
            counts["approved_simulated"] += 1
    flush(store, ledger)
    recalibrate(
        [
            "--almacen",
            str(store.root),
            "--correcciones",
            str(ledger),
            "--salida",
            str(args.output / "candidate"),
        ]
    )
    report = json.loads((args.output / "candidate/informe.json").read_text(encoding="utf-8"))
    report.update(
        synthetic=True,
        human_review_simulated=True,
        dataset="S-dev/vectorial",
        manifest_sha256=hashlib.sha256((root / "manifest.json").read_bytes()).hexdigest(),
        counts=counts,
        seconds=time.perf_counter() - started,
    )
    (args.output / "resumen.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"counts": counts, "status": report["status"], "seconds": report["seconds"]}))


if __name__ == "__main__":
    main()
