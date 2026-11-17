"""Exporta la especificación paramétrica de todos los diseños del catálogo para Modelo › Diseños.

    uv run python scripts/export_design_specs.py

Escribe `web/src/features/model-designs/design-specs.json`: por cada diseño, su envolvente en mm
(ancho X, alto Z, fondo Y, el mismo orden que `industrial_designs.Design.size`) y sus piezas en
porcentaje de la envolvente. La web genera con ellas el IFC4 en el navegador, con el mismo
algoritmo que `make_industrial_designs.mesh` y `web/scripts/export-industrial-ifc.mjs`, y el visor
lo lee como cualquier otro IFC.

- Diseños industriales y variantes: las piezas de `industrial_designs` y `design_variants`, las
  mismas que generan los IFC de `web/public/demo/industriales`.
- Bocetos GA (`make_design_sketches`): no tienen IFC publicado; se les asigna la plantilla de
  piezas de su familia sobre la envolvente que declara el boceto. Es geometría conceptual.
"""

import json
from pathlib import Path

from design_variants import (
    BASE_FAMILY_NAMES,
    VARIANTS,
    centrifugal_compressor,
    column,
    heat_exchange,
    horizontal,
    pot,
    pump,
    storage,
)
from industrial_designs import FAMILIES, Design, base, box
from make_design_sketches import SKETCHES

ROOT = Path(__file__).resolve().parents[1]
DESTINO = ROOT / "web" / "src" / "features" / "model-designs" / "design-specs.json"

# Plantilla de piezas para cada boceto, a partir de su variante (todas de autoría propia).
PLANTILLAS = {
    "separador": lambda: pot(False),
    "pulmon": lambda: pot(False),
    "tambor": lambda: horizontal((22, 78), False),
    "acumulador": lambda: horizontal((25, 75), False),
    "recta": lambda: column(False),
    "transicion": lambda: column(True),
    "carcasa": lambda: horizontal((20, 80), False),
    "placas": lambda: heat_exchange(False),
    "conico": lambda: storage(True),
    "plano": lambda: storage(True),
    "centrifuga": lambda: pump(False),
    "linea": lambda: pump(True),
    "tornillo": centrifugal_compressor,
    "alternativo": centrifugal_compressor,
    "modulo": lambda: (base(), box("Volumen de proceso", (0, 0, 7), (100, 100, 100))),
    "armario": lambda: (
        base(4),
        box("Armario", (0, 6, 4), (100, 100, 100)),
        box("Puerta frontal", (8, 0, 10), (92, 6, 94)),
    ),
}


def _spec(design: Design, family: str, origen: str, ifc: str | None) -> dict:
    return {
        "tag": design.tag,
        "family": family,
        "name": design.name,
        "origin": origen,
        "ifc": ifc,
        "size": list(design.size),
        "parts": [
            {
                "name": part.name,
                "low": list(part.low),
                "high": list(part.high),
                "axis": part.axis,
                "ends": list(part.ends),
            }
            for part in design.parts
        ],
    }


def especificaciones() -> dict:
    disenos = []
    nombres = {family.id: family.name for family in FAMILIES} | BASE_FAMILY_NAMES
    for sketch in SKETCHES:
        design = Design(
            sketch.tag,
            sketch.name,
            (sketch.width, sketch.height, sketch.depth),
            tuple(PLANTILLAS[sketch.variant]()),
        )
        disenos.append(_spec(design, sketch.family, "boceto", None))
    grupos = [(family.id, family.designs) for family in FAMILIES] + list(VARIANTS.items())
    for family_id, variantes in grupos:
        for design in variantes:
            ifc = f"/demo/industriales/{design.tag}-A.ifc"
            disenos.append(_spec(design, family_id, "industrial", ifc))
    etiquetas = [d["tag"] for d in disenos]
    if len(etiquetas) != len(set(etiquetas)):
        raise ValueError("Etiquetas repetidas en el catálogo")
    for d in disenos:
        for part in d["parts"]:
            if any(not 0 <= lo < hi <= 100 for lo, hi in zip(part["low"], part["high"])):
                raise ValueError(f"{d['tag']}: límites inválidos en {part['name']}")
    return {"families": nombres, "designs": disenos}


def main():
    datos = especificaciones()
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    contenido = json.dumps(datos, ensure_ascii=False, indent=1) + "\n"
    DESTINO.write_text(contenido, encoding="utf-8", newline="\n")
    print(f"{len(datos['designs'])} diseños en {DESTINO.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
