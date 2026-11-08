"""Rasteriza los PDF GA sintéticos (rev A y B) y extrae las regiones de evidencia de cada campo."""

import json
import sys
from pathlib import Path

import pypdfium2 as pdfium

root, dst = Path(sys.argv[1]), Path(sys.argv[2])
dst.mkdir(parents=True, exist_ok=True)
for rev in ("A", "B"):
    pdf = pdfium.PdfDocument(str(root / f"web/public/demo/docs/GAD_V-101_rev{rev}.pdf"))
    print(rev, "páginas", len(pdf))
    for i in range(len(pdf)):
        page = pdf[i]
        w, h = page.get_size()
        scale = 4200 / w
        img = page.render(scale=scale).to_pil().convert("RGB")
        out = dst / f"ga-rev{rev.lower()}-p{i + 1}.png"
        img.save(out, optimize=True)
        print("  ", out.name, img.size, f"{w:.0f}x{h:.0f}pt")

fields = []
data = json.loads((root / "web/public/demo/json/vessel_rev_a.json").read_text(encoding="utf-8"))


def walk(node, path=""):
    if isinstance(node, dict):
        if "value" in node and isinstance(node.get("source"), dict):
            s = node["source"]
            fields.append(
                {
                    "path": path,
                    "value": node.get("value"),
                    "unit": node.get("unit"),
                    "page": s.get("page"),
                    "bbox": s.get("bbox"),
                    "kind": s.get("kind") or s.get("type"),
                    "text": s.get("text") or s.get("snippet"),
                    "confidence": node.get("confidence") or node.get("score"),
                }
            )
        for k, v in node.items():
            walk(v, f"{path}.{k}" if path else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, f"{path}[{i}]")


walk(data)
(dst / "evidence-rev-a.json").write_text(
    json.dumps(fields, ensure_ascii=False, indent=1), encoding="utf-8"
)
for f in fields:
    print(
        f"{f['path']:<40} {str(f['value']):<12} {f['unit'] or '':<5} p{f['page']} {f['bbox']} {(f['text'] or '')[:40]}"  # noqa: E501
    )
