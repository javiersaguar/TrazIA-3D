"""Lote sintético contra la API real; no sustituye trabajos fallidos por resultados.

Usar una API aislada: crea documentos y revisiones nuevas. Solo biblioteca estándar.
"""

import argparse
import hashlib
import json
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import Counter, defaultdict
from pathlib import Path

TERMINAL = {"done", "error", "cancelled", "timeout"}


def tasks(data, sets, *, cases_limit=None, degradations=None):
    output = []
    for name in sets:
        root = data / name
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf8"))
        if manifest.get("synthetic") is not True:
            raise ValueError("El lote de escala solo acepta manifiestos sintéticos")
        for case in manifest["cases"][:cases_limit]:
            for level in manifest["styles"]:
                if degradations and level not in degradations:
                    continue
                for revision in ("1", "2"):
                    folder = root / level / case["tag"]
                    files = [(folder / f"GAD_{case['tag']}_rev{revision}.pdf", f"GA-{case['tag']}")]
                    hdm = folder / f"HDM_{case['tag']}_rev{revision}.xlsx"
                    if hdm.exists():
                        files.append((hdm, f"HDM-{case['tag']}"))
                    if any(not p.is_file() for p, _ in files):
                        raise ValueError("Falta un original del lote")
                    output.append(
                        {
                            "dataset": name,
                            "tag": case["tag"],
                            "degradation": level,
                            "revision": revision,
                            "files": files,
                        }
                    )
    return output


def summarise(rows, seconds, upload_seconds):
    states = Counter(row["status"] for row in rows)
    durations = [row["seconds_turnaround"] for row in rows]
    known_cost = [
        row["run"]["cost_eur"]
        for row in rows
        if row.get("run") and row["run"].get("cost_eur") is not None
    ]
    total = len(rows)
    groups = defaultdict(list)
    for row in rows:
        groups[(row["dataset"], row["tag"], row["degradation"])].append(row)
    pairs = []
    for (dataset, tag, level), items in sorted(groups.items()):
        values = [
            i["run"]["cost_eur"]
            for i in items
            if i.get("run") and i["run"].get("cost_eur") is not None
        ]
        pairs.append(
            {
                "dataset": dataset,
                "tag": tag,
                "degradation": level,
                "revisions": len(items),
                "done": sum(i["status"] == "done" for i in items),
                "seconds_turnaround_sum": sum(i["seconds_turnaround"] for i in items),
                "cost_eur": sum(values) if len(values) == len(items) else None,
            }
        )
    throughput = total / seconds if seconds else 0
    return {
        "revisions": total,
        "equipment": len({(r["dataset"], r["tag"]) for r in rows}),
        "conditions": len(groups),
        "statuses": dict(states),
        "successful_lods": dict(
            Counter(str(row.get("lod", "unknown")) for row in rows if row["status"] == "done")
        ),
        "errors_by_message": dict(
            Counter(row.get("error") or row["status"] for row in rows if row["status"] != "done")
        ),
        "seconds_batch": seconds,
        "seconds_upload": upload_seconds,
        "throughput_terminal_per_second": throughput,
        "seconds_turnaround_mean": statistics.fmean(durations) if durations else None,
        "seconds_turnaround_p95": sorted(durations)[
            min(len(durations) - 1, int(len(durations) * 0.95))
        ]
        if durations
        else None,
        "cost_eur": sum(known_cost) if len(known_cost) == total and total else None,
        "jobs_without_cost": total - len(known_cost),
        "external_calls_known": sum((r.get("run") or {}).get("external_calls", 0) for r in rows),
        "jobs_with_incomplete_accounting": sum(
            not (r.get("run") or {}).get("accounting_complete", False) for r in rows
        ),
        "projection_400x4": {
            "measured": False,
            "seconds_for_1600_terminal_jobs": 1600 / throughput if throughput else None,
            "seconds_for_1600_valid_ifc": 1600 / throughput
            if throughput and states.get("done") == total
            else None,
            "cost_eur": sum(known_cost) / total * 1600
            if total and len(known_cost) == total
            else None,
            "limitation": (
                "Extrapolación de este lote y estrategia. "
                "Las terminaciones incluyen errores; no prueban 1600 modelos válidos."
            ),
        },
        "per_equipment_condition": pairs,
    }


def run(
    api,
    data,
    sets,
    output,
    *,
    window=32,
    timeout=900,
    strategy: str = "d_hibrido",
    cases_limit=None,
    degradations=None,
):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def request(path, body=None, headers=None):
        req = urllib.request.Request(api + path, data=body, headers=headers or {})
        with opener.open(req, timeout=90) as response:
            return json.load(response)

    def post(path, body):
        return request(
            path,
            json.dumps(body).encode(),
            {"Content-Type": "application/json", "Idempotency-Key": str(uuid.uuid4())},
        )

    plan = tasks(data, sets, cases_limit=cases_limit, degradations=degradations)
    if not plan:
        raise ValueError("Lote vacío")
    run_id = uuid.uuid4().hex[:10]
    started = time.perf_counter()
    prepared = []
    source_hash = hashlib.sha256()
    for task in plan:
        documents = []
        for file, document_id in task["files"]:
            boundary = "trazia" + uuid.uuid4().hex
            content = file.read_bytes()
            source_hash.update(
                file.relative_to(data).as_posix().encode() + hashlib.sha256(content).digest()
            )
            parts = []
            for key, value in (("document_id", document_id), ("revision", task["revision"])):
                parts.append(
                    (
                        f"--{boundary}\r\n"
                        f'Content-Disposition: form-data; name="{key}"\r\n\r\n'
                        f"{value}\r\n"
                    ).encode()
                )
            parts.append(
                (
                    f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
                    f'filename="{file.name}"\r\n'
                    "Content-Type: application/octet-stream\r\n\r\n"
                ).encode()
                + content
                + b"\r\n"
            )
            parts.append(f"--{boundary}--\r\n".encode())
            result = request(
                "/documents",
                b"".join(parts),
                {
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                    "Idempotency-Key": str(uuid.uuid4()),
                },
            )
            documents.append(result["id"])
        prepared.append((task, documents))
    uploaded = time.perf_counter() - started
    pending = {}
    rows = []
    iterator = iter(prepared)
    exhausted = False
    while not exhausted or pending:
        if time.perf_counter() - started > timeout:
            raise TimeoutError("El lote no terminó; no se declara una medición completa")
        while len(pending) < window and not exhausted:
            item = next(iterator, None)
            if item is None:
                exhausted = True
                break
            task, docs = item
            stamp = time.perf_counter()
            project = f"S-{run_id}-{task['dataset']}-{task['degradation']}"
            body = {
                "documents": docs,
                "project_id": project,
                "equipment_id": task["tag"],
                "revision": task["revision"],
                "strategy": strategy,
                "providers": [],
                "dataset": "synthetic",
                "timeout_seconds": 180,
                "max_attempts": 1,
            }
            result = post(f"/equipment/{urllib.parse.quote(task['tag'])}/jobs", body)
            pending[result["job_id"]] = (task, stamp)
        for identity, (task, stamp) in list(pending.items()):
            job = request("/jobs/" + identity)
            if job["status"] in TERMINAL:
                model_info = {}
                if job["status"] == "done":
                    project = f"S-{run_id}-{task['dataset']}-{task['degradation']}"
                    try:
                        model = request(
                            f"/equipment/{urllib.parse.quote(task['tag'])}/revisions/{task['revision']}?"
                            + urllib.parse.urlencode({"project_id": project})
                        )
                        model_info = {
                            "lod": model["equipment"]["lod"],
                            "equipment_kind": model["equipment"]["kind"],
                        }
                    except urllib.error.HTTPError as error:
                        model_info = {
                            "inspection_error": (
                                f"HTTP {error.code}: no se pudo inspeccionar "
                                "el modelo con el tag solicitado"
                            )
                        }
                rows.append(
                    {k: v for k, v in task.items() if k != "files"}
                    | model_info
                    | {
                        "job_id": identity,
                        "status": job["status"],
                        "error": job["error"],
                        "run": job["run"],
                        "seconds_turnaround": time.perf_counter() - stamp,
                    }
                )
                del pending[identity]
                if len(rows) % 20 == 0:
                    print(f"Terminados {len(rows)}/{len(plan)}", flush=True)
        report = {
            "synthetic": True,
            "strategy": strategy,
            "run_id": run_id,
            "input_sha256": source_hash.hexdigest(),
            "complete": len(rows) == len(plan),
            "planned_revisions": len(plan),
            "rows": rows,
            "summary": summarise(rows, time.perf_counter() - started, uploaded),
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
        if pending:
            time.sleep(0.1)
    print(
        json.dumps(
            {
                "complete": report["complete"],
                "summary": {
                    k: v for k, v in report["summary"].items() if k != "per_equipment_condition"
                },
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--api", required=True)
    p.add_argument("--data", type=Path, default=Path("generated/synthetic_v2"))
    p.add_argument(
        "--sets", nargs="+", default=["s-dev", "s-reservado", "s-mecanico", "s-adversarial"]
    )
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--estrategia", default="d_hibrido", help="Estrategia de lectura del lote")
    p.add_argument("--casos", type=int, default=None, help="Primeros N equipos por conjunto")
    p.add_argument("--degradaciones", nargs="+", default=None)
    p.add_argument("--limite-segundos", type=int, default=7200, help="Tiempo máximo del lote")
    args = p.parse_args()
    if args.casos is not None and args.casos < 1:
        p.error("casos debe ser positivo")
    run(
        args.api.rstrip("/"),
        args.data,
        args.sets,
        args.output,
        strategy=args.estrategia,
        timeout=args.limite_segundos,
        cases_limit=args.casos,
        degradations=args.degradaciones,
    )


if __name__ == "__main__":
    main()
