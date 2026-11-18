"""Integridad del catálogo de proyectos y lectura de sus documentos de equipo."""

import json
from pathlib import Path
from zipfile import ZipFile

import ifcopenshell
import pytest
from openpyxl import load_workbook

from trazia.pipeline import InputDocument, process

ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads(
    (ROOT / "web/src/features/process-projects/catalog.json").read_text(encoding="utf-8")
)


@pytest.mark.parametrize("project", CATALOG, ids=lambda project: project["id"])
def test_process_project_revisions_keep_ports_and_guid(project):
    folder = ROOT / "web/public/demo/proceso" / project["id"]
    identities = []
    for item in project["states"].values():
        path = folder / item["file"]
        assert path.stat().st_size == item["bytes"] <= 1_350_000
        assert item["triangles"] <= 45_000
        model = ifcopenshell.open(str(path))
        physical = [p for p in model.by_type("IfcElement") if p.Representation]
        identities.append({p.Name: p.GlobalId for p in physical})
        ports = model.by_type("IfcRelConnectsPorts")
        assert len(ports) == 2 * len(project["lines"])
        for link in ports:
            first = link.RelatingPort.ObjectPlacement.RelativePlacement.Location.Coordinates
            second = link.RelatedPort.ObjectPlacement.RelativePlacement.Location.Coordinates
            assert first == second
    assert identities and all(identity == identities[0] for identity in identities)
    assert len(identities[0]) == len(project["equipment"]) + len(project["lines"]) + 1


@pytest.mark.parametrize("project", CATALOG, ids=lambda project: project["id"])
def test_project_dossier_and_pipeline_envelope(project):
    folder = ROOT / "web/public/demo/proceso" / project["id"]
    tag = next(
        change["tag"]
        for change in project["changes"]
        if change["tag"] in project["documents"]["A"]["equipment"]
    )
    sizes = []
    for rev in ("A", "B"):
        docs = project["documents"][rev]
        files = docs["equipment"][tag]
        with ZipFile(folder / docs["archive"]) as dossier:
            assert len(dossier.namelist()) == 3 + 2 * len(project["equipment"])
            assert dossier.read(files["plan"]) == (folder / files["plan"]).read_bytes()
            name = project["states"]["00" if rev == "A" else "11"]["file"]
            assert dossier.read(name) == (folder / name).read_bytes()
        result = process(
            [
                InputDocument(name, (folder / name).read_bytes(), field)
                for field, name in files.items()
            ],
            project_id=project["code"],
            equipment_id=tag,
            revision=rev,
            strategy="b_reglas",
            dataset="synthetic",
        )
        assert result.revision is not None, result.error
        assert result.revision.approval is None
        assert result.revision.equipment.tag.value == tag
        envelope = result.revision.equipment.envelope
        assert envelope is not None and result.revision.equipment.lod == 1
        sizes.append(tuple(getattr(envelope.size, axis).value for axis in "xyz"))
        book = load_workbook(folder / files["workbook"], read_only=True)
        try:
            rows = dict((name, value) for name, value, _ in book["Envolvente"].values)
            assert sizes[-1] == tuple(rows[f"ENVELOPE_SIZE_{axis}"] for axis in "XYZ")
        finally:
            book.close()
    assert sizes[0] != sizes[1]
