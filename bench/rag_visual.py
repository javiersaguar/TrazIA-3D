"""ColQwen2 frente a la huella ligera para la recuperación de C (ROADMAP 2.5).

    uv run --extra train python -m bench.rag_visual --datos ../TrazIA-3D/generated/synthetic_v2

1. Biblioteca de S-dev (rev1 vectorial) con el sha256 y la ruta de cada PDF.
2. Recuperación: para cada GA (rev1 y rev2, las tres degradaciones) de S-dev y S-reservado, el
   caso elegido por cada método, sin el propio equipo. En S-dev el acierto es elegir un caso del
   mismo proveedor.
3. Umbral «no hay caso parecido», fijado solo en S-dev: positivos, la mejor puntuación con la
   biblioteca entera; negativos, la mejor sin ningún caso del mismo proveedor (lo que pasa con un
   proveedor nuevo). Se elige el umbral que maximiza aciertos − falsas alarmas (índice de Youden)
   y se mira qué parte de S-reservado (proveedores nuevos) aceptaría.
4. Resultado de C: `bench.estudio` solo con `c_rag`, una vez con cada método, misma biblioteca y
   misma calibración.

Deja `recuperacion.json`, `estudio-huella/`, `estudio-colqwen2/` e `informe.json` en `--salida`.
"""

import argparse
import io
import json
import os
import time
from pathlib import Path
from statistics import fmean, median

import pdfplumber

from trazia.ingest import ingest_bytes
from trazia.rag import visual as colqwen
from trazia.rag.library import build
from trazia.strategies.c_rag import (
    MIN_SIMILARITY,
    MIN_VISUAL_SIMILARITY,
    light_best,
    visual_best,
)

SETS = ("s-dev", "s-reservado")


def _lines(data: bytes, name: str, doc_id: str):
    bundle = ingest_bytes(data, name, doc_id, "1")
    if bundle.lines:
        return bundle.lines
    from trazia.ocr import OcrUnavailable, ocr_pdf_lines

    try:
        return ocr_pdf_lines(data, doc_id)
    except OcrUnavailable:
        return []


def retrieval(data_root: Path, library: dict, log=print) -> list[dict]:
    rows = []
    for name in SETS:
        root = data_root / name
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        for case in manifest["cases"]:
            tag = case["tag"]
            vendor = case.get("vendor") or "?"
            entries = [e for e in library["entries"] if e["equipment_id"] != tag.lower()]
            strangers = [e for e in entries if e.get("vendor") != vendor]
            for style in manifest["styles"]:
                for rev in ("1", "2"):
                    path = root / style / tag / f"GAD_{tag}_rev{rev}.pdf"
                    if not path.exists():
                        continue
                    data = path.read_bytes()
                    with pdfplumber.open(io.BytesIO(data)) as pdf:
                        pages = len(pdf.pages)
                    lines = _lines(data, path.name, f"GA-{tag}")
                    started = time.perf_counter()
                    light = light_best(data, pages, lines, entries)
                    light_s = time.perf_counter() - started
                    started = time.perf_counter()
                    seen = visual_best(data, pages, entries)
                    visual_s = time.perf_counter() - started
                    if name == "s-dev":
                        light_out = _pick(light_best(data, pages, lines, strangers))
                        visual_out = _pick(visual_best(data, pages, strangers))
                    else:
                        light_out = visual_out = None
                    rows.append(
                        {
                            "set": name,
                            "style": style,
                            "tag": tag,
                            "rev": rev,
                            "vendor": vendor,
                            "light": _pick(light),
                            "colqwen2": _pick(seen),
                            "light_vendor_out": light_out,
                            "colqwen2_vendor_out": visual_out,
                            "seconds": {"light": round(light_s, 3), "colqwen2": round(visual_s, 3)},
                        }
                    )
            log(f"  {name} {tag} ({vendor})")
    return rows


def _pick(best) -> dict | None:
    if best is None:
        return None
    score, page, entry = best
    return {
        "score": round(score, 4),
        "page": page,
        "tag": entry["tag"],
        "vendor": entry.get("vendor"),
    }


def summarize(rows: list[dict]) -> dict:
    out = {}
    for name in SETS:
        mine = [r for r in rows if r["set"] == name]
        if not mine:
            continue
        by = {}
        for method in ("light", "colqwen2"):
            scores = [r[method]["score"] for r in mine if r[method]]
            entry = {
                "n": len(mine),
                "score_median": round(median(scores), 4) if scores else None,
                "score_min": round(min(scores), 4) if scores else None,
                "score_max": round(max(scores), 4) if scores else None,
                "seconds_mean": round(fmean(r["seconds"][method] for r in mine), 3),
            }
            if name == "s-dev":
                styles = sorted({r["style"] for r in mine})
                entry["same_vendor"] = _rate(mine, method)
                entry["same_vendor_by_style"] = {
                    s: _rate([r for r in mine if r["style"] == s], method) for s in styles
                }
                right = [r[method]["score"] for r in mine if _right(r, method)]
                wrong = [r[method]["score"] for r in mine if r[method] and not _right(r, method)]
                entry["score_right_min"] = round(min(right), 4) if right else None
                entry["score_wrong_max"] = round(max(wrong), 4) if wrong else None
            if method == "light":
                entry["accepted"] = round(
                    sum(
                        r["light"] is not None and r["light"]["score"] >= MIN_SIMILARITY
                        for r in mine
                    )
                    / len(mine),
                    4,
                )
            by[method] = entry
        out[name] = by
    return out


def threshold(rows: list[dict], method: str) -> dict:
    """Umbral de S-dev con el índice de Youden y su efecto en S-reservado."""
    dev = [r for r in rows if r["set"] == "s-dev" and r[method] and r[f"{method}_vendor_out"]]
    positives = [r[method]["score"] for r in dev]
    negatives = [r[f"{method}_vendor_out"]["score"] for r in dev]
    if not dev:
        return {}

    def rates(t):
        return (
            sum(s >= t for s in positives) / len(positives),
            sum(s >= t for s in negatives) / len(negatives),
        )

    best = max(sorted(set(positives + negatives)), key=lambda t: rates(t)[0] - rates(t)[1])
    auc = fmean(1.0 if p > n else 0.5 if p == n else 0.0 for p in positives for n in negatives)
    held = [r[method]["score"] for r in rows if r["set"] == "s-reservado" and r[method]]
    out = {"auc": round(auc, 4), "fitted": round(best, 4)}
    for label, t in (("fitted", best), ("current", MIN_SIMILARITY if method == "light" else None)):
        if t is None:
            continue
        hit, false_alarm = rates(t)
        out[label + "_rates"] = {
            "threshold": round(t, 4),
            "s_dev_accepted": round(hit, 4),
            "s_dev_vendor_out_accepted": round(false_alarm, 4),
            "s_reservado_accepted": round(sum(s >= t for s in held) / len(held), 4)
            if held
            else None,
        }
    return out


def _right(row, method) -> bool:
    pick = row[method]
    return pick is not None and pick["vendor"] == row["vendor"]


def _rate(rows, method) -> float | None:
    return round(sum(_right(r, method) for r in rows) / len(rows), 4) if rows else None


def study(data_root: Path, out: Path, mode: str, log=print) -> dict:
    from bench.estudio import run_study

    os.environ["TRAZIA_RAG_RETRIEVAL"] = mode
    try:
        result = run_study(data_root, list(SETS), ["c_rag"], log=log)
    finally:
        os.environ.pop("TRAZIA_RAG_RETRIEVAL", None)
    out.mkdir(parents=True, exist_ok=True)
    (out / "estudio.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="ColQwen2 frente a la huella en C (2.5)")
    parser.add_argument("--datos", type=Path, default=Path("generated/synthetic_v2"))
    parser.add_argument("--salida", type=Path, default=Path("generated/rag-visual"))
    parser.add_argument("--sin-estudio", action="store_true", help="Solo la recuperación")
    parser.add_argument("--modos", nargs="+", default=["huella", "colqwen2"])
    parser.add_argument(
        "--reusar", action="store_true", help="Biblioteca y recuperación ya hechas en --salida"
    )
    args = parser.parse_args(argv)
    args.salida.mkdir(parents=True, exist_ok=True)
    library_file = args.salida / "biblioteca.json"
    rows_file = args.salida / "recuperacion.json"
    if args.reusar and library_file.exists() and rows_file.exists():
        rows = json.loads(rows_file.read_text(encoding="utf-8"))
    else:
        library = build(args.datos / "s-dev", library_file)
        print(f"· biblioteca: {len(library['entries'])} casos en {library_file}")
        print("· recuperación")
        rows = retrieval(args.datos, library)
        rows_file.write_text(
            json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
    os.environ["TRAZIA_RAG_LIBRARY"] = str(library_file)
    report_file = args.salida / "informe.json"
    old = json.loads(report_file.read_text(encoding="utf-8")) if report_file.exists() else {}
    report = {
        "model": colqwen.MODEL,
        "dpi": colqwen.DPI,
        "min_visual_similarity": MIN_VISUAL_SIMILARITY,
        "retrieval": summarize(rows),
        "threshold": {m: threshold(rows, m) for m in ("light", "colqwen2")},
    }
    report["study"] = old.get("study", {})
    if not args.sin_estudio:
        for mode in args.modos:
            print(f"· estudio de C con {mode}")
            result = study(args.datos, args.salida / f"estudio-{mode}", mode)
            report["study"][mode] = {"min_visual_similarity": MIN_VISUAL_SIMILARITY, **result}
    report_file.write_text(
        json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(json.dumps(report["threshold"], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
