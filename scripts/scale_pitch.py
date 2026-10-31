"""Inventario de fallos y presupuesto paramétrico desde un lote sintético ya medido."""

import argparse
import json
import math
from collections import Counter
from pathlib import Path


def reason(error):
    if "al menos tres boquillas" in error:
        return (
            "boquillas_incompletas",
            "Contrastar la tabla y las elevaciones de boquillas; Lectura.",
        )
    if "Faltan datos explícitos" in error:
        return "campos_ausentes", "Leer los campos indicados en PDF/HDM; no rellenar por defecto."
    if any(text in error for text in ("virola", "suelo", "fondo", "diámetro")):
        return (
            "geometria_incoherente",
            "Contrastar cota, unidad, diámetro y orientación; revisar fusión.",
        )
    return "otro", "Revisar el error y sus eventos sin sustituirlo por un modelo ilustrativo."


def analyse(
    report,
    *,
    equipment=400,
    revisions=4,
    worker_rate=None,
    human_minutes=None,
    human_rate=None,
    fixed_cost=None,
):
    if report.get("synthetic") is not True:
        raise ValueError("Solo se admiten informes sintéticos")
    rows = report["rows"]
    planned = report["planned_revisions"]
    complete = report.get("complete") is True and len(rows) == planned
    done = sum(r["status"] == "done" and not r.get("inspection_error") for r in rows)
    failures = []
    for row in rows:
        if row["status"] == "done" and not row.get("inspection_error"):
            continue
        category, action = reason(row.get("error") or row.get("inspection_error") or row["status"])
        failures.append(
            {
                **{
                    key: row[key] for key in ("dataset", "tag", "degradation", "revision", "job_id")
                },
                "category": category,
                "error": row.get("error") or row.get("inspection_error"),
                "action": action,
                "dataset_kind": "synthetic",
                "input_sha256": report["input_sha256"],
            }
        )
    summary = report["summary"]
    target = equipment * revisions
    terminal_seconds = summary["seconds_batch"] / len(rows) * target if complete and rows else None
    workers = report.get("deployment", {}).get("workers")
    compute = (
        terminal_seconds * workers / 3600 * worker_rate
        if terminal_seconds is not None and workers and worker_rate is not None
        else None
    )
    providers = (
        summary["cost_eur"] / len(rows) * target
        if complete and rows and summary.get("cost_eur") is not None
        else None
    )
    human = (
        equipment * human_minutes / 60 * human_rate
        if human_minutes is not None and human_rate is not None
        else None
    )
    costs = {
        "compute_eur": compute,
        "providers_eur": providers,
        "human_eur": human,
        "fixed_infrastructure_eur": fixed_cost,
    }
    total = sum(costs.values()) if all(v is not None for v in costs.values()) else None
    return {
        "synthetic": True,
        "strategy": report["strategy"],
        "input_sha256": report["input_sha256"],
        "measured": {
            "planned": planned,
            "terminal": len(rows),
            "draft_ifc": done,
            "errors": len(failures),
            "batch_seconds": summary["seconds_batch"],
            "workers": workers,
            "error_categories": dict(Counter(f["category"] for f in failures)),
        },
        "acceptance": {
            "all_revisions_have_draft_ifc": complete and done == planned,
            "engineering_accuracy_verified": False,
        },
        "project_scenario": {
            "measured": False,
            "equipment": equipment,
            "revisions_each": revisions,
            "terminal_jobs": target,
            "terminal_seconds": terminal_seconds,
            "valid_ifc_seconds": None,
            "valid_ifc_total_cost_eur": None,
            "assumptions": {
                "eur_worker_hour": worker_rate,
                "human_minutes_per_equipment_all_revisions": human_minutes,
                "eur_human_hour": human_rate,
                "fixed_infrastructure_eur": fixed_cost,
            },
            "components": costs,
            "total_scenario_eur": total,
            "limit": (
                "Extrapolación de terminaciones, incluidas fallidas; "
                "no presupuesto de IFC válidos. "
                "CPU compartida. Tiempo humano sin medir."
            ),
        },
    }, failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", required=True, type=Path)
    parser.add_argument("--salida", required=True, type=Path)
    parser.add_argument("--pendientes", type=Path)
    parser.add_argument("--equipos", type=int, default=400)
    parser.add_argument("--revisiones", type=int, default=4)
    parser.add_argument("--eur-worker-hora", type=float)
    parser.add_argument("--minutos-humanos-equipo", type=float)
    parser.add_argument("--eur-revisor-hora", type=float)
    parser.add_argument("--infra-fija-eur", type=float)
    parser.add_argument("--exigir-todos", action="store_true")
    args = parser.parse_args()
    if args.equipos < 1 or args.revisiones < 1:
        parser.error("Equipos y revisiones deben ser positivos")
    rates = [
        args.eur_worker_hora,
        args.minutos_humanos_equipo,
        args.eur_revisor_hora,
        args.infra_fija_eur,
    ]
    if any(v is not None and (v < 0 or not math.isfinite(v)) for v in rates):
        parser.error("Las hipótesis deben ser finitas y no negativas")
    result, failures = analyse(
        json.loads(args.entrada.read_text(encoding="utf8")),
        equipment=args.equipos,
        revisions=args.revisiones,
        worker_rate=args.eur_worker_hora,
        human_minutes=args.minutos_humanos_equipo,
        human_rate=args.eur_revisor_hora,
        fixed_cost=args.infra_fija_eur,
    )
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    if args.pendientes:
        args.pendientes.parent.mkdir(parents=True, exist_ok=True)
        args.pendientes.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in failures), encoding="utf8"
        )
    print(json.dumps(result["measured"], ensure_ascii=False))
    return (
        2 if args.exigir_todos and not result["acceptance"]["all_revisions_have_draft_ifc"] else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
