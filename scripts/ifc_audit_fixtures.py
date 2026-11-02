"""Definiciones sintéticas públicas para auditar exportación, no lecturas de planos."""

import hashlib
import json
from pathlib import Path

from trazia.model import Revision, load_revision

CASES = (
    "vertical",
    "horizontal",
    "column",
    "tank_conical",
    "tank_domed",
    "pump",
    "compressor",
    "generic",
)


def fixture(name):
    if name == "vertical":
        return load_revision(Path(__file__).resolve().parents[1] / "examples/vessel_rev_b.json")

    def field(value, unit="mm"):
        return {
            "value": value,
            "unit": unit,
            "source": {
                "document_id": "AUDIT",
                "page": 1,
                "locator": "Definición paramétrica sintética de auditoría",
                "confidence": 1.0,
            },
        }

    def vector(x, y, z, unit="mm"):
        return {a: field(v, unit) for a, v in zip("xyz", (x, y, z))}

    kind = {"horizontal": "horizontal_vessel", "tank_conical": "tank", "tank_domed": "tank"}.get(
        name, name
    )
    equipment = {
        "id": "audit-001",
        "tag": field("AUDIT-001", "1"),
        "kind": kind,
        "lod": 1 if kind in ("pump", "compressor", "generic") else 2,
        "attributes": {
            "material": field("SYNTHETIC-STEEL", "1"),
            "design_pressure": field(16, "bar"),
        },
        "nozzles": [
            {
                "id": "N1",
                "diameter": field(200),
                "projection": field(400),
                "elevation": field(1500),
                "azimuth": field(0, "deg"),
                "position": vector(1000, 0, 1500),
                "direction": vector(1, 0, 0, "1"),
            }
        ],
    }
    if equipment["lod"] == 1:
        equipment["envelope"] = {"origin": vector(-1000, 500, 0), "size": vector(2000, 3000, 4000)}
    elif kind == "horizontal_vessel":
        equipment["horizontal"] = {
            k: field(v)
            for k, v in {
                "diameter": 2000,
                "length": 6000,
                "head_depth": 500,
                "support_height": 800,
                "saddle_width": 400,
                "saddle_span": 1400,
            }.items()
        }
        equipment["horizontal"]["saddle_positions"] = [field(1200), field(4800)]
    elif kind == "column":
        equipment["column"] = {
            "sections": [
                {"id": "lower", "diameter": field(2000), "height": field(3000)},
                {
                    "id": "transition",
                    "diameter": field(2000),
                    "top_diameter": field(1200),
                    "height": field(1000),
                },
                {"id": "upper", "diameter": field(1200), "height": field(4000)},
            ]
        }
    elif kind == "tank":
        equipment["tank"] = {
            "diameter": field(6000),
            "height": field(7000),
            "roof": "domed" if name == "tank_domed" else "conical",
            "roof_height": field(1000),
        }
    else:
        raise ValueError("Fixture desconocida")
    definition = json.dumps(equipment, sort_keys=True).encode()
    return Revision.model_validate(
        {
            "schema_version": "0.3",
            "project_id": "SYNTHETIC-IFC-AUDIT",
            "revision": "A",
            "dataset": "synthetic",
            "equipment": equipment,
            "documents": [
                {
                    "id": "AUDIT",
                    "filename": name + ".json",
                    "revision": "A",
                    "sha256": hashlib.sha256(definition).hexdigest(),
                    "page_count": 1,
                }
            ],
        }
    )
