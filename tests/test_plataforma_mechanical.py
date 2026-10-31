import json

import ifcopenshell

from synthetic.sets import generate_set
from trazia.extraction import assemble
from trazia.extractors import DrawingExtractor
from trazia.ifc import build_ifc
from trazia.ingest import ingest_bytes
from trazia.pipeline import InputDocument, process


def test_unknown_title_label_uses_an_unambiguous_tag_without_filename_hints():
    from trazia.ingest import Bundle, EvidenceLine
    from trazia.model import Document, Source

    def line(text, y):
        return EvidenceLine(
            text=text,
            source=Source(
                document_id="GA",
                page=1,
                locator="Texto",
                bbox=(0.7, y, 0.8, y + 0.01),
                confidence=0.75,
            ),
        )

    bundle = Bundle(
        document=Document(
            id="GA", filename="unrelated.pdf", revision="1", sha256="a" * 64, page_count=1
        ),
        media_type="pdf",
        lines=[line("IDENTIFICADOR", 0.8), line("R-300B", 0.83)],
    )
    tags = [c for c in DrawingExtractor().extract([bundle]) if c.path == "tag"]
    assert len(tags) == 1 and tags[0].value == "R-300B"
    bundle.lines.append(line("V-999", 0.5))
    assert not any(c.path == "tag" for c in DrawingExtractor().extract([bundle]))


def test_pump_envelope_is_read_from_explicit_dimensions_with_stable_ifc(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAZIA_CALIBRATION", "off")
    generate_set("s-mecanico", tmp_path, cases=6, degradations=("vectorial",))
    root = tmp_path / "s-mecanico"
    for folder in (root / "vectorial").iterdir():
        truth = json.loads((root / "truth" / f"{folder.name}.json").read_text(encoding="utf-8"))
        guids = []
        for rev in ("1", "2"):
            pdf = folder / f"GAD_{folder.name}_rev{rev}.pdf"
            result = process(
                [InputDocument(pdf.name, pdf.read_bytes(), "GA")],
                project_id="TEST",
                equipment_id=folder.name,
                revision=rev,
                strategy="b_reglas",
            )
            assert result.error is None, result.error
            equipment = result.revision.equipment
            expected = truth[f"rev{rev}"]
            assert equipment.kind == "pump" and equipment.lod == 1
            assert equipment.envelope.size.x.value == expected["base_length"]
            assert equipment.envelope.size.y.value == expected["base_width"]
            assert equipment.envelope.size.z.value == max(
                expected["discharge_z"], expected["shaft_height"] + expected["motor_half"]
            )
            assert equipment.envelope.origin.x.state == "assumed"
            assert equipment.nozzles == [] and result.revision.approval is None
            path = build_ifc(result.revision, draft=True)
            model = ifcopenshell.file.from_string(path.to_string())
            guids.append([p.GlobalId for p in model.by_type("IfcBuildingElementProxy")])
        assert guids[0] == guids[1]


def test_missing_pump_dimension_never_produces_a_plausible_default(tmp_path):
    generate_set("s-mecanico", tmp_path, cases=1, degradations=("vectorial",))
    pdf = next((tmp_path / "s-mecanico/vectorial").glob("*/GAD_*rev1.pdf"))
    bundle = ingest_bytes(pdf.read_bytes(), pdf.name, "GA", "1")
    bundle.lines = [line for line in bundle.lines if line.text.strip() != "PLAN"]
    candidates = DrawingExtractor().extract([bundle])
    assert not any(c.path.startswith("envelope.") for c in candidates)
    import pytest

    with pytest.raises(ValueError, match="Faltan datos explícitos"):
        assemble([bundle], candidates, project_id="TEST", equipment_id="pump", revision="1")
