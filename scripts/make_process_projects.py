"""Genera IFC, planos y libros de proyectos sintéticos desde una definición común."""

import json
from itertools import product
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from process_documents import equipment_pdf, equipment_workbook, project_pdf, workbook
from process_geometry import scene
from process_ifc import create_ifc
from process_projects import PROJECTS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web/public/demo/proceso"
INDEX = ROOT / "web/src/features/process-projects/catalog.json"
PRESET = {
    "plataforma-marina": "ocean",
    "planta-desierto": "desert",
    "terminal-costera": "coast",
    "refineria-activa": "industrial",
}


def generate(project):
    folder = OUT / project.id
    folder.mkdir(parents=True, exist_ok=True)
    states = {}
    documents = {}
    for choices in product((False, True), repeat=len(project.changes)):
        active = {change.tag for choice, change in zip(choices, project.changes) if choice}
        key = "".join("1" if choice else "0" for choice in choices)
        official = not active or len(active) == len(choices)
        rev = ("B" if active else "A") if official else f"Ensayo-{key}"
        equipment, lines, routes, parts = scene(project, active)
        path = folder / f"{project.code}-{rev}.ifc"
        triangles = create_ifc(path, project, rev, equipment, lines, routes, parts)
        size = path.stat().st_size
        if size > 1_350_000:
            raise ValueError(f"{path.name} excede el límite de 1,35 MB")
        states[key] = {"file": path.name, "bytes": size, "triangles": triangles}
        if not official:
            continue
        ga = f"GA_{project.code}_rev{rev}.pdf"
        data = f"Lista_{project.code}_rev{rev}.xlsx"
        project_pdf(folder / ga, project, rev, equipment, lines, routes, parts)
        workbook(folder / data, project, rev, equipment, lines, routes, parts)
        by_tag = {part.tag: part for part in parts}
        documents[rev] = {"plan": ga, "workbook": data, "equipment": {}}
        for eq in equipment.values():
            drawing = f"GAD_{eq.tag}_rev{rev}.pdf"
            hdm = f"HDM_{eq.tag}_rev{rev}.xlsx"
            equipment_pdf(folder / drawing, project, rev, eq, by_tag[eq.tag], lines, routes)
            equipment_workbook(folder / hdm, project, rev, eq, by_tag[eq.tag], lines, routes)
            documents[rev]["equipment"][eq.tag] = {"plan": drawing, "workbook": hdm}
        archive = f"{project.code}-dossier-{rev}.zip"
        with ZipFile(folder / archive, "w", compression=ZIP_DEFLATED) as bundle:
            members = [path.name, ga, data]
            for item in documents[rev]["equipment"].values():
                members.extend(item.values())
            for member in members:
                bundle.write(folder / member, arcname=member)
        documents[rev]["archive"] = archive
    return {
        "id": project.id,
        "code": project.code,
        "name": project.name,
        "setting": project.setting,
        "description": project.description,
        "preset": PRESET[project.id],
        "equipment": [
            {"tag": item.tag, "name": item.name, "family": item.family, "service": item.service}
            for item in project.equipment
        ],
        "lines": [
            {"tag": line.tag, "start": line.start, "end": line.end, "fluid": line.fluid}
            for line in project.lines
        ],
        "changes": [
            {"tag": c.tag, "label": c.label, "before": c.before, "after": c.after, "unit": c.unit}
            for c in project.changes
        ],
        "states": states,
        "documents": documents,
    }


def main():
    catalog = [generate(project) for project in PROJECTS]
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for entry in catalog:
        state = max(entry["states"].values(), key=lambda item: item["bytes"])
        print(
            f"{entry['code']}: {len(entry['equipment'])} equipos, {len(entry['lines'])} líneas, "
            f"máximo {state['bytes']:,} bytes y {state['triangles']:,} triángulos por IFC."
        )


if __name__ == "__main__":
    main()
