"""Biblioteca de equipos aprobados para la estrategia C.

    uv run python -m trazia.rag.library --conjunto generated/synthetic_v2/s-dev

Por cada equipo aprobado (aquí, la rev1 de S-dev con su verdad) se guarda:
- la huella de su página GA (`fingerprint.visual` y vocabulario), y el sha256 y la ruta del PDF
  para la recuperación visual con ColQwen2 (`rag.visual`, ROADMAP 2.5);
- su plantilla de lectura: para cada campo verificado, la región donde se leyó, el tipo de valor,
  la celda de la marca si es una boquilla y las transformaciones aprendidas (cotas de boquilla
  desde la tangente inferior, separador decimal).

Solo entran campos cuya lectura coincide con la verdad aprobada: la plantilla nunca enseña errores.
La biblioteca es sintética; el día 1 se construye con los equipos reales (exclusión de uno).
"""

import argparse
import hashlib
import json
from pathlib import Path

from ..extractors.drawing import document_context
from ..ingest import ingest_bytes
from .fingerprint import visual, words

MOVING = {"height", "skirt_height", "head_depth", "diameter", "skirt_thickness"}


def _matches(value, truth) -> bool:
    if isinstance(truth, str) or isinstance(value, str):
        return str(value).strip().upper() == str(truth).strip().upper()
    return abs(float(value) - float(truth)) <= max(1.0, 0.005 * abs(float(truth)))


def build_entry(tag: str, folder: Path, truth: dict, flatten) -> dict | None:
    from ..pipeline import InputDocument, process  # aquí: el pipeline importa las estrategias

    ga = folder / f"GAD_{tag}_rev1.pdf"
    data = ga.read_bytes()
    docs = [InputDocument(ga.name, data, f"GA-{tag}")]
    result = process(
        docs, project_id="LIB", equipment_id=tag.lower(), revision="1", strategy="b_reglas"
    )
    expected = flatten(truth)
    bundle = ingest_bytes(data, ga.name, f"GA-{tag}", "1")
    ctx = document_context(bundle.lines)
    fields = {}
    page = None
    for c in result.candidates:
        if c.path not in expected or c.source.bbox is None or c.source.page is None:
            continue
        if not _matches(c.value, expected[c.path][0]):
            continue
        page = page or c.source.page
        entry = {
            "page": c.source.page,
            "bbox": list(c.source.bbox),
            "unit": c.unit,
            "moving": c.path in MOVING,
        }
        if c.text_original and c.unit == "mm":
            from ..extractors.units import parse_length

            straight = parse_length(c.text_original.strip(), decimal=ctx.decimal)
            # Texto girado leído al revés: la plantilla recuerda en qué sentido se lee.
            entry["reversed"] = straight is None or abs(straight - float(c.value)) > 0.5
        if c.path.startswith("nozzles."):
            mark = c.path.split(".")[1]
            row_y = (c.source.bbox[1] + c.source.bbox[3]) / 2
            cell = min(
                (
                    line
                    for line in bundle.lines
                    if line.text.strip().upper() == mark
                    and line.source.page == c.source.page
                    and abs((line.source.bbox[1] + line.source.bbox[3]) / 2 - row_y) < 0.006
                ),
                key=lambda line: line.source.bbox[0],
                default=None,
            )
            if cell is None:
                continue
            entry["mark_bbox"] = list(cell.source.bbox)
            if c.explanation and "tangente inferior" in c.explanation:
                entry["datum"] = "btl"
        fields[c.path] = entry
    if not fields:
        return None
    ga_page = page or 1
    return {
        "tag": tag,
        "equipment_id": tag.lower(),
        "page": ga_page,
        "sha256": hashlib.sha256(data).hexdigest(),
        "source": str(ga),
        "decimal": ctx.decimal,
        "visual": visual(data, ga_page),
        "words": words([line.text for line in bundle.lines if line.source.page == ga_page]),
        "fields": fields,
    }


def build(dataset: Path, out: Path) -> dict:
    from synthetic.cases import flatten, spec_from_dict

    manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
    entries = []
    for case in manifest["cases"]:
        tag = case["tag"]
        truth = json.loads((dataset / "truth" / f"{tag}.json").read_text(encoding="utf-8"))
        entry = build_entry(
            tag, dataset / "vectorial" / tag, truth["rev1"], lambda t: flatten(spec_from_dict(t))
        )
        if entry:
            entry["vendor"] = truth.get("vendor")
            entries.append(entry)
    library = {"source": str(dataset), "synthetic": True, "entries": entries}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(library, ensure_ascii=False) + "\n", encoding="utf-8")
    return library


def load(path: Path) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Construye la biblioteca de la estrategia C")
    parser.add_argument("--conjunto", type=Path, default=Path("generated/synthetic_v2/s-dev"))
    parser.add_argument("--salida", type=Path, default=Path("generated/rag/biblioteca.json"))
    args = parser.parse_args(argv)
    library = build(args.conjunto, args.salida)
    total = sum(len(e["fields"]) for e in library["entries"])
    print(f"{len(library['entries'])} equipos, {total} campos con plantilla en {args.salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
