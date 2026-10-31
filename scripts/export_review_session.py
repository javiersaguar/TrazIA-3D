"""Exporta registros de sesiones manuales sintéticas; sin muestra no calcula tiempos."""

import argparse
import json
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def summarise(metrics, audits, current_fields):
    if metrics["dataset"] != "synthetic":
        raise ValueError("Solo se exporta el piloto sintético")
    sessions = [
        s for s in metrics["sessions"] if s["kind"] == "human" and s["finished_at"] is not None
    ]
    identities = {s["id"] for s in sessions}
    actions = [
        a
        for a in audits
        if a.get("review_session_id") in identities and not a["path"].startswith("$")
    ]
    used = {a["review_session_id"] for a in actions}
    sessions = [s for s in sessions if s["id"] in used]
    groups = defaultdict(list)
    for action in actions:
        groups[action["path"]].append(action)
    fields = []
    for path, items in sorted(groups.items()):
        for item in items:
            if (
                json.loads(item["before_json"])["dataset"] != "synthetic"
                or json.loads(item["after_json"])["dataset"] != "synthetic"
            ):
                raise ValueError("La auditoría contiene una revisión que no es sintética")
        known = [a["seconds"] for a in items if a.get("seconds") is not None]
        fields.append(
            {
                "path": path,
                "actions": len(items),
                "undo_actions": sum(a.get("undo_of") is not None for a in items),
                "seconds": sum(known) if len(known) == len(items) else None,
                "untimed_actions": len(items) - len(known),
            }
        )
    active = sum(s["active_seconds"] for s in sessions) if sessions else None
    wall = sum(s["finished_at"] - s["started_at"] for s in sessions) if sessions else None
    seconds = [f["seconds"] for f in fields]
    assigned = sum(seconds) if fields and all(s is not None for s in seconds) else None
    return {
        "revision_id": metrics["revision_id"],
        "equipment_tag": metrics["equipment_tag"],
        "equipment_identity": metrics["revision_id"].rsplit(":", 1)[0],
        "dataset": "synthetic",
        "completed_human_sessions_with_actions": len(sessions),
        "active_seconds": active,
        "wall_seconds_including_interruptions": wall,
        "action_seconds": assigned,
        "unassigned_active_seconds": max(0, active - assigned)
        if active is not None and assigned is not None
        else None,
        "fields_with_actions": len(fields),
        "fields_total": len(current_fields),
        "field_times": fields,
        "resolved_fields_with_actions": sum(
            path in groups and field["state"] in ("accepted", "corrected")
            for path, field in current_fields.items()
        ),
        "mean_action_seconds_per_distinct_field": assigned / len(fields)
        if assigned is not None and fields
        else None,
        "approved": metrics["approved"],
        "pending_fields": metrics["pending_fields"],
        "open_sessions": metrics.get("open_sessions"),
        "test_sessions": metrics.get("test_sessions"),
        "source": "active_client_reported; human participation self-declared",
        "field_time_scope": (
            "Tiempo activo atribuido a acciones, no permanencia visual en cada campo."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8030")
    parser.add_argument("--revisiones", nargs="+", default=["A", "B"])
    parser.add_argument("--salida", type=Path, required=True)
    args = parser.parse_args()
    target = args.salida.resolve()
    if target.exists() and any(target.iterdir()):
        parser.error("Usa un destino nuevo para conservar el registro original")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def get(path):
        with opener.open(args.api.rstrip("/") + path, timeout=30) as response:
            return json.load(response)

    rows, raw = [], {}
    for revision in args.revisiones:
        path = "/revisions/" + urllib.parse.quote(revision, safe="")
        metrics, audit = get(path + "/review-metrics"), get(path + "/audit")
        current_fields = get(path + "/fields")
        rows.append(summarise(metrics, audit["actions"], current_fields))
        raw[revision] = {"metrics": metrics, "audit": audit, "fields": current_fields}
    active = [r["active_seconds"] for r in rows if r["active_seconds"] is not None]
    equipment = {r["equipment_identity"] for r in rows if r["active_seconds"] is not None}
    per_equipment = []
    for identity in sorted({r["equipment_identity"] for r in rows}):
        members = [r for r in rows if r["equipment_identity"] == identity]
        times = [r["active_seconds"] for r in members if r["active_seconds"] is not None]
        wall_times = [
            r["wall_seconds_including_interruptions"]
            for r in members
            if r["wall_seconds_including_interruptions"] is not None
        ]
        per_equipment.append(
            {
                "equipment_identity": identity,
                "tags": sorted({r["equipment_tag"] for r in members}),
                "revisions": len(members),
                "timed_revisions": len(times),
                "active_seconds": sum(times) if times else None,
                "wall_seconds_including_interruptions": sum(wall_times) if wall_times else None,
            }
        )
    result = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "synthetic": True,
        "equipment_with_sample": len(equipment),
        "active_seconds": sum(active) if active else None,
        "revisions": rows,
        "all_revisions_approved": all(r["approved"] for r in rows),
        "equipment": per_equipment,
        "sample_complete_for_review_time": bool(rows)
        and all(
            r["active_seconds"] is not None
            and r["approved"]
            and r["pending_fields"] == 0
            and r["open_sessions"] == 0
            and r["resolved_fields_with_actions"] == r["fields_total"]
            and all(f["seconds"] is not None for f in r["field_times"])
            for r in rows
        ),
        "causal_impact_measured": False,
        "limit": (
            "Piloto de uso humano sobre sintéticos; no demuestra representatividad industrial."
        ),
    }
    target.mkdir(parents=True, exist_ok=True)
    (target / "registro-original.json").write_text(
        json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    (target / "tiempos.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )

    def display(seconds):
        return "Sin medir" if seconds is None else f"{seconds:.2f} s"

    lines = [
        "# Tiempos de revisión manual · sintéticos",
        "",
        f"Equipos con muestra: {len(equipment)}. "
        f"Tiempo activo total: {display(result['active_seconds'])}.",
        "",
        "| Revisión | Sesiones humanas | Campos con acciones | Tiempo activo | Aprobada |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['revision_id']} | {row['completed_human_sessions_with_actions']} | "
            f"{row['fields_with_actions']} | {display(row['active_seconds'])} | {row['approved']} |"
        )
    lines += [
        "",
        result["limit"],
        "Los tiempos por campo y la auditoría están en los JSON adjuntos.",
    ]
    (target / "tiempos.md").write_text("\n".join(lines) + "\n", encoding="utf8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if active else 2


if __name__ == "__main__":
    raise SystemExit(main())
