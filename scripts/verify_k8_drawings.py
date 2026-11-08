"""Evidencia reproducible CPU; fixtures sintéticos públicos, sin proveedores de visión.

uv run --extra dev --extra api python scripts/verify_k8_drawings.py
"""

import hashlib
import json
import sys
import time
from pathlib import Path

import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from test_plataforma_families import family_data  # noqa: E402

from trazia.design.drawing import generate_ga  # noqa: E402
from trazia.ifc import build_ifc  # noqa: E402
from trazia.model import Revision, load_revision  # noqa: E402


def main():
    output = ROOT / "docs/evidencias/k8"
    output.mkdir(parents=True, exist_ok=True)
    measurements = []
    for kind in (
        "vertical_vessel",
        "horizontal_vessel",
        "column",
        "tank",
        "pump",
        "compressor",
        "generic",
    ):
        revision = (
            load_revision(ROOT / "examples/vessel_rev_b.json")
            if kind == "vertical_vessel"
            else Revision.model_validate(
                family_data(kind, 1 if kind in {"pump", "compressor", "generic"} else 2)
            )
        )
        started = time.perf_counter()
        content = build_ifc(revision, draft=True).to_string().encode()
        built = time.perf_counter()
        result = generate_ga(content, revision)
        completed = time.perf_counter()
        (output / f"{kind}.pdf").write_bytes(result["pdf"])
        (output / f"{kind}.svg").write_bytes(result["svg"])
        (output / f"{kind}.json").write_text(
            json.dumps(result["manifest"], indent=2, ensure_ascii=False) + "\n", encoding="utf8"
        )
        with pdfium.PdfDocument(result["pdf"]) as document:
            page = document[0]
            try:
                bitmap = page.render(scale=1.2)
                bitmap.to_pil().save(output / f"{kind}.png")
                bitmap.close()
            finally:
                page.close()
        measurements.append(
            dict(
                kind=kind,
                ifc_seconds=round(built - started, 4),
                drawing_seconds=round(completed - built, 4),
                ifc_bytes=len(content),
                pdf_bytes=len(result["pdf"]),
                ifc_sha256=hashlib.sha256(content).hexdigest(),
                scale=result["manifest"]["scale"],
                pieces=len(result["manifest"]["pieces"]),
            )
        )
    (output / "mediciones.json").write_text(
        json.dumps({"dataset": "synthetic", "gpu": False, "measurements": measurements}, indent=2)
        + "\n",
        encoding="utf8",
    )
    print(json.dumps(measurements, indent=2))


if __name__ == "__main__":
    main()
