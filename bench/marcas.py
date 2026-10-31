"""Mide el lector de marcas de revisión (ROADMAP F.5) sobre los GA sintéticos.

    uv run python -m bench.marcas --datos generated/synthetic_v2

- Detección: los Δ dibujados por el generador se sacan del PDF vectorial por su color (solo aquí,
  como verdad); el lector no usa el color. Se mide en vectorial y en los escaneados.
- Asociación: con la verdad de cambios y la lectura de la rev2 de `d_hibrido` (vectorial), qué
  cambios caen junto a una marca y cuántas marcas quedan sin cambio.

**Datos sintéticos.** El generador solo dibuja Δ, no nubes.
"""

import argparse
import io
import json
import os
from pathlib import Path

import pdfplumber

from trazia.extractors.revision_marks import _overlap, check_changes, find_marks
from trazia.pipeline import InputDocument, process

from .estudio import DATASET_NAMES

GENERATOR_RED = (0.760784, 0.254902, 0.047059)  # synthetic/render_v2.py: REVISION


def drawn_deltas(pdf: bytes) -> list[tuple[int, tuple]]:
    out = []
    with pdfplumber.open(io.BytesIO(pdf)) as document:
        for number, page in enumerate(document.pages, start=1):
            for curve in page.curves:
                color = tuple(round(c, 6) for c in curve.get("stroking_color") or ())
                if color == GENERATOR_RED and len(curve.get("pts") or []) == 4:
                    w, h = float(page.width), float(page.height)
                    box = (curve["x0"] / w, curve["top"] / h, curve["x1"] / w, curve["bottom"] / h)
                    out.append((number, box))
    return out


def _match(found, truth) -> int:
    used: set[int] = set()
    for mark in found:
        for i, (page, box) in enumerate(truth):
            if i not in used and page == mark.page and _overlap(_grow(box), mark.bbox):
                used.add(i)
                break
    return len(used)


def _grow(box, margin=0.01):
    return (box[0] - margin, box[1] - margin, box[2] + margin, box[3] + margin)


def measure(root: Path, degradations: list[str]) -> dict:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    result = {}
    for degradation in degradations:
        found_total = truth_total = matched = false = unread = 0
        covered = changes_with_box = orphans = cases = 0
        for case in manifest["cases"]:
            tag = case["tag"]
            folder = root / degradation / tag
            ga = folder / f"GAD_{tag}_rev2.pdf"
            if not ga.exists():
                continue
            cases += 1
            data = ga.read_bytes()
            truth = drawn_deltas((root / "vectorial" / tag / ga.name).read_bytes())
            reading = find_marks(data)
            found = [m for m in reading.marks if m.kind == "delta"]
            unread += len(reading.unread_pages)
            hits = _match(found, truth)
            found_total += len(found)
            truth_total += len(truth)
            matched += hits
            false += len(found) - hits
            if degradation != "vectorial":
                continue
            facts = json.loads((root / "truth" / f"{tag}.json").read_text(encoding="utf-8"))
            changed = {c["path"] for c in facts["changes"] if c.get("after") is not None}
            docs = [InputDocument(ga.name, data, f"GA-{tag}")]
            hdm = folder / f"HDM_{tag}_rev2.xlsx"
            if hdm.exists():
                docs.append(InputDocument(hdm.name, hdm.read_bytes(), f"HDM-{tag}"))
            read = process(
                docs, project_id="F5", equipment_id=tag.lower(), revision="2", strategy="d_hibrido"
            )
            located = []
            for candidate in read.candidates:
                if candidate.path not in changed:
                    continue
                sources = [candidate.source, *[a.source for a in candidate.alternatives]]
                places = [
                    {"page": src.page, "bbox": src.bbox}
                    for src in sources
                    if src.document_id == f"GA-{tag}" and src.bbox
                ]
                if places:
                    located.append({"path": candidate.path, "locations": places})
            check = check_changes(located, reading)
            changes_with_box += len(located)
            covered += len(located) - len(check["unmarked_changes"])
            orphans += len(check["marks_without_change"])
        entry = {
            "cases": cases,
            "deltas_drawn": truth_total,
            "deltas_found": found_total,
            "recall": round(matched / truth_total, 4) if truth_total else None,
            "precision": round(matched / found_total, 4) if found_total else None,
            "false_marks": false,
            "unread_pages": unread,
        }
        if degradation == "vectorial":
            entry.update(
                changes_located=changes_with_box,
                changes_next_to_a_mark=round(covered / changes_with_box, 4)
                if changes_with_box
                else None,
                marks_without_change=orphans,
            )
        result[degradation] = entry
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Mide el lector de marcas de revisión (F.5)")
    parser.add_argument("--datos", type=Path, default=Path("generated/synthetic_v2"))
    parser.add_argument("--conjuntos", nargs="+", default=["S-dev", "S-reservado"])
    parser.add_argument(
        "--degradaciones", nargs="+", default=["vectorial", "escaneado_limpio", "escaneado_pobre"]
    )
    parser.add_argument("--salida", type=Path, default=Path("generated/marcas/marcas.json"))
    args = parser.parse_args(argv)
    os.environ.setdefault("TRAZIA_CALIBRATION", "off")
    report = {"synthetic": True}
    for name in args.conjuntos:
        root = args.datos / name
        report[DATASET_NAMES.get(root.name, name)] = measure(root, args.degradaciones)
        print(name, json.dumps(report[DATASET_NAMES.get(root.name, name)], ensure_ascii=False))
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Informe: {args.salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
