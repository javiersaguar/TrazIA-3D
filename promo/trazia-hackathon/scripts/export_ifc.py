"""Exporta la geometría teselada de los IFC sintéticos de TrazIA-3D a JSON para Remotion.

Una malla por producto (GlobalId, tipo IFC, nombre), en metros, eje Y hacia arriba (three.js).
Se usa la misma teselación de IfcOpenShell que el producto; no se dibuja geometría aparte.
Uso: python export_ifc.py <rev_a.ifc> <rev_b.ifc> <salida_dir>
"""

import json
import sys
from pathlib import Path

import ifcopenshell
import ifcopenshell.geom


def export(path: Path) -> dict:
    model = ifcopenshell.open(str(path))
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    out = []
    for product in model.by_type("IfcProduct"):
        if not product.Representation:
            continue
        try:
            shape = ifcopenshell.geom.create_shape(settings, product)
        except Exception as exc:  # noqa: BLE001 - se informa y se sigue
            print("sin geometría:", product.is_a(), product.Name, exc)
            continue
        verts = shape.geometry.verts  # x, y, z (Z arriba) en metros
        faces = shape.geometry.faces
        # Z arriba (IFC) -> Y arriba (three.js): (x, y, z) -> (x, z, -y)
        v = []
        for i in range(0, len(verts), 3):
            x, y, z = verts[i], verts[i + 1], verts[i + 2]
            v += [round(x, 4), round(z, 4), round(-y, 4)]
        out.append({
            "id": product.GlobalId,
            "type": product.is_a(),
            "name": product.Name or "",
            "description": getattr(product, "Description", None) or "",
            "v": v,
            "f": list(faces),
        })
    return {"source": path.name, "schema": model.schema, "products": out}


def main() -> None:
    a, b, dst = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    dst.mkdir(parents=True, exist_ok=True)
    for src, name in ((a, "rev_a.json"), (b, "rev_b.json")):
        data = export(src)
        (dst / name).write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
        print(name, len(data["products"]), "productos")
        for p in data["products"]:
            ys = p["v"][1::3]
            print(f"  {p['type']:<26} {p['name'][:34]:<34} tris={len(p['f'])//3:<5} y=[{min(ys):.2f},{max(ys):.2f}] {p['id']}")


if __name__ == "__main__":
    main()
