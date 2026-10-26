"""Agrega los resultados por estilo con la estructura de la rúbrica del jurado."""

from datetime import datetime, timezone

from .metrics import brier, ece, mean_or_none, prf, reliability


def _pct(x):
    return None if x is None else round(100 * x, 1)


def summarize(results: dict) -> dict:
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset": results["dataset"],
        "seed": results["seed"],
        "extractor": results["extractor"],
        "styles": {},
    }
    for style, cases in results["styles"].items():
        revisions = [c[k] for c in cases for k in ("rev1", "rev2")]
        fields = [f for r in revisions for f in r["fields"]]
        geometry_fields = [f for f in fields if not f["path"].startswith(("attributes.", "tag"))]
        attribute_fields = [f for f in fields if f["path"].startswith("attributes.")]
        nozzles = [n for r in revisions for n in r["nozzles"]]
        dims = [d for r in revisions for d in r["dimensions"]]
        pairs = [tuple(p) for r in revisions for p in r["calibration"]]
        ifc_rows = [e for r in revisions if r["ifc"] for e in r["ifc"]["elements"]]
        deltas = [c["delta"] for c in cases if c["delta"] is not None]
        tp = sum(d["tp"] for d in deltas)
        fp = sum(d["fp"] for d in deltas)
        fn = sum(d["fn"] for d in deltas)
        # Solo revisiones que llegan a IFC: un fallo rápido no es rendimiento
        seconds = [r["seconds"] for r in revisions if r["assembled"]]
        false_nozzles = sum(len(r["false_nozzles"]) for r in revisions)
        detected = sum(n["detected"] for n in nozzles)

        def rate(rows, key):
            return sum(r[key] for r in rows) / len(rows) if rows else None

        summary["styles"][style] = {
            "equipment": len(cases),
            "revisions": len(revisions),
            "models_built": sum(r["assembled"] for r in revisions),
            "geometry": {
                "field_coverage": rate(geometry_fields, "found"),
                "field_accuracy": rate(geometry_fields, "correct"),
                "dimension_mae_mm": mean_or_none(d["abs_error_mm"] for d in dims),
                "nozzle_recall": detected / len(nozzles) if nozzles else None,
                "nozzle_precision": detected / (detected + false_nozzles)
                if detected + false_nozzles
                else None,
                "nozzle_position_mae_mm": mean_or_none(
                    n["position_error_mm"] for n in nozzles if "position_error_mm" in n
                ),
                "nozzle_orientation_mae_deg": mean_or_none(
                    n["orientation_error_deg"] for n in nozzles if "orientation_error_deg" in n
                ),
                "nozzle_dn_accuracy": rate(nozzles, "dn_correct"),
                "ifc_element_recall": rate(ifc_rows, "found"),
                "ifc_mean_iou": mean_or_none(e["iou"] for e in ifc_rows),
                "ifc_center_error_mm": mean_or_none(
                    e["center_error_mm"] for e in ifc_rows if e["center_error_mm"] is not None
                ),
            },
            "attributes": {
                "coverage": rate(attribute_fields, "found"),
                "accuracy_value_unit": rate(attribute_fields, "correct"),
                "ece": ece(pairs),
                "brier": brier(pairs),
                "calibration_points": len(pairs),
                "reliability": reliability(pairs),
            },
            "delta": {
                "evaluable_equipment": len(deltas),
                **prf(tp, fp, fn),
                "magnitude_mae": mean_or_none(m for d in deltas for m in d["magnitude_errors"]),
            },
            "scale": {
                "seconds_per_revision": mean_or_none(seconds),
                "revisions_per_hour": 3600 / mean_or_none(seconds) if seconds else None,
                "llm_calls": 0,
                "cost_eur": 0.0,
            },
            "failures": sorted({r["error"] for r in revisions if r["error"]})[:5],
        }
    return summary


def _fmt(value, kind="num"):
    if value is None:
        return "—"
    if kind == "pct":
        return f"{_pct(value):.1f} %".replace(".", ",")
    if kind == "int":
        return f"{value:,.0f}".replace(",", ".")
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def to_markdown(summary: dict) -> str:
    styles = list(summary["styles"])
    s = summary["styles"]

    def row(label, getter, kind="num"):
        return f"| {label} | " + " | ".join(_fmt(getter(s[st]), kind) for st in styles) + " |"

    header = "| Métrica | " + " | ".join(styles) + " |\n|" + " --- |" * (len(styles) + 1)
    lines = [
        "# GA2MODEL Bench · conjunto sintético",
        "",
        f"Generado {summary['generated_at']} · extractor `{summary['extractor']}` · "
        f"semilla {summary['seed']} · `{summary['dataset']}`",
        "",
        "> **Datos sintéticos.** Estos números miden el pipeline sobre documentos generados "
        "con verdad conocida. No son precisión sobre planos de Técnicas Reunidas.",
        "",
        "Estilos: **rotulado** (parámetros escritos como «ETIQUETA = valor»), "
        "**plano** (GA dibujado con cotas y tabla de boquillas) y "
        "**escaneado** (el plano como imagen, sin capa de texto).",
        "",
        "## Volumen",
        "",
        header,
        row("Equipos", lambda x: x["equipment"], "int"),
        row("Revisiones", lambda x: x["revisions"], "int"),
        row("Revisiones con modelo IFC", lambda x: x["models_built"], "int"),
        "",
        "## Fidelidad geométrica · 35 %",
        "",
        header,
        row("Campos geométricos encontrados", lambda x: x["geometry"]["field_coverage"], "pct"),
        row("Campos geométricos correctos", lambda x: x["geometry"]["field_accuracy"], "pct"),
        row("Error medio en dimensiones (mm)", lambda x: x["geometry"]["dimension_mae_mm"]),
        row("Boquillas detectadas (recall)", lambda x: x["geometry"]["nozzle_recall"], "pct"),
        row("Boquillas detectadas (precisión)", lambda x: x["geometry"]["nozzle_precision"], "pct"),
        row(
            "Error de posición de boquilla (mm)", lambda x: x["geometry"]["nozzle_position_mae_mm"]
        ),
        row("Error de orientación (°)", lambda x: x["geometry"]["nozzle_orientation_mae_deg"]),
        row("DN correcto", lambda x: x["geometry"]["nozzle_dn_accuracy"], "pct"),
        row("Elementos IFC presentes", lambda x: x["geometry"]["ifc_element_recall"], "pct"),
        row("IoU medio de cajas IFC", lambda x: x["geometry"]["ifc_mean_iou"]),
        row("Error de centro IFC (mm)", lambda x: x["geometry"]["ifc_center_error_mm"]),
        "",
        "## Extracción de atributos · 25 %",
        "",
        header,
        row("Atributos encontrados", lambda x: x["attributes"]["coverage"], "pct"),
        row("Valor + unidad correctos", lambda x: x["attributes"]["accuracy_value_unit"], "pct"),
        row("ECE (calibración)", lambda x: x["attributes"]["ece"]),
        row("Brier", lambda x: x["attributes"]["brier"]),
        row("Puntos de calibración", lambda x: x["attributes"]["calibration_points"], "int"),
        "",
        "## Actualización incremental · 20 %",
        "",
        header,
        row(
            "Equipos evaluables (rev1 y rev2 con modelo)",
            lambda x: x["delta"]["evaluable_equipment"],
            "int",
        ),
        row("Precisión de cambios", lambda x: x["delta"]["precision"], "pct"),
        row("Recall de cambios", lambda x: x["delta"]["recall"], "pct"),
        row("F1", lambda x: x["delta"]["f1"], "pct"),
        row("Error en la magnitud del cambio", lambda x: x["delta"]["magnitude_mae"]),
        "",
        "## Arquitectura y escalado · 10 %",
        "",
        header,
        row(
            "Segundos por revisión con modelo (ingesta → IFC)",
            lambda x: x["scale"]["seconds_per_revision"],
        ),
        row("Revisiones por hora (1 proceso)", lambda x: x["scale"]["revisions_per_hour"], "int"),
        row("Llamadas a modelos de IA", lambda x: x["scale"]["llm_calls"], "int"),
        "",
        "## Lectura",
        "",
        "- El extractor de etiquetas solo entiende el estilo rotulado. En «plano» y "
        "«escaneado» la geometría queda sin extraer: ese hueco es lo que deben cubrir "
        "los extractores de tablas, OCR y visión (ROADMAP B.1), y este bench los medirá "
        "con las mismas métricas.",
        "- La confianza actual es un 0,75 fijo: el ECE mide cuánto se aleja de la tasa "
        "real de acierto.",
        "- Sin dos modelos válidos no hay delta evaluable; por eso la columna puede quedar vacía.",
        "",
    ]
    failures = {st: s[st]["failures"] for st in styles if s[st]["failures"]}
    if failures:
        lines += ["## Motivos de fallo más frecuentes", ""]
        for st, items in failures.items():
            lines += [f"- **{st}**: " + "; ".join(items)]
        lines.append("")
    return "\n".join(lines)
