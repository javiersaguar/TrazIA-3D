"""Genera un conjunto sintético reproducible con la convención de nombres del dataset del reto.

Estructura de salida:
    <salida>/manifest.json
    <salida>/<estilo>/<TAG>/GAD_<TAG>_rev1.pdf, GAD_<TAG>_rev2.pdf
    <salida>/<estilo>/<TAG>/HDM_<TAG>_rev1.xlsx, HDM_<TAG>_rev2.xlsx
    <salida>/truth/<TAG>.json   (valores verdaderos de rev1 y rev2 y cambios esperados)
"""

import json
import random
from pathlib import Path

from .cases import expected_changes, flatten, mutate, random_case, spec_to_dict
from .render import STYLES, write_ga, write_hdm


def generate(output: Path, cases: int, seed: int, styles: tuple[str, ...] = STYLES) -> dict:
    rng = random.Random(seed)
    output.mkdir(parents=True, exist_ok=True)
    (output / "truth").mkdir(exist_ok=True)
    manifest = {"seed": seed, "styles": list(styles), "cases": []}
    used: set[str] = set()
    for index in range(cases):
        rev1 = random_case(rng, index)
        while rev1.tag in used:
            rev1 = random_case(rng, index + len(used) * 7)
        used.add(rev1.tag)
        rev2 = mutate(rng, rev1)
        changes = expected_changes(rev1, rev2)
        changed_paths = {c["path"] for c in changes}
        truth = {
            "tag": rev1.tag,
            "rev1": spec_to_dict(rev1),
            "rev2": spec_to_dict(rev2),
            "changes": changes,
            "fields": len(flatten(rev1)),
        }
        (output / "truth" / f"{rev1.tag}.json").write_text(
            json.dumps(truth, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        for style in styles:
            folder = output / style / rev1.tag
            folder.mkdir(parents=True, exist_ok=True)
            write_ga(folder / f"GAD_{rev1.tag}_rev1.pdf", rev1, "1", style)
            write_ga(folder / f"GAD_{rev1.tag}_rev2.pdf", rev2, "2", style, changed_paths)
            write_hdm(folder / f"HDM_{rev1.tag}_rev1.xlsx", rev1)
            write_hdm(folder / f"HDM_{rev1.tag}_rev2.xlsx", rev2)
        manifest["cases"].append(
            {"tag": rev1.tag, "changes": len(changes), "nozzles": len(rev1.nozzles)}
        )
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
