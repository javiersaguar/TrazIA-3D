"""Interfaz `trazia.pipeline.process` (contrato con el Agente Plataforma)."""

from pathlib import Path

from bench.support import is_cited, is_supported
from trazia import pipeline
from trazia.extraction import Candidate
from trazia.ingest import ingest_bytes
from trazia.model import Source
from trazia.pipeline import InputDocument, process
from trazia.reconcile import resolve

DOCS = Path(__file__).resolve().parents[1] / "examples" / "documents"


def demo_documents(rev: str = "A") -> list[InputDocument]:
    return [
        InputDocument(
            f"GAD_V-101_rev{rev}.pdf", (DOCS / f"GAD_V-101_rev{rev}.pdf").read_bytes(), "GA-V101"
        ),
        InputDocument(
            f"HDM_V-101_rev{rev}.xlsx", (DOCS / f"HDM_V-101_rev{rev}.xlsx").read_bytes(), "HDM-V101"
        ),
    ]


def test_process_builds_a_draft_revision_with_stage_events():
    events = []
    result = process(
        demo_documents(),
        project_id="DEMO-PLANT",
        equipment_id="vessel-001",
        revision="A",
        strategy="b_reglas",
        on_event=events.append,
    )
    assert result.error is None
    assert result.revision is not None
    assert result.revision.equipment.tag.value == "V-101"
    assert result.revision.approval is None
    stages = [e.stage for e in events]
    for stage in (
        "ingest",
        "classify",
        "extract_labels",
        "extract_tables",
        "extract_hdm",
        "reconcile",
        "family",
        "ifc",
        "validate",
    ):
        assert stage in stages, stage
    assert all(e.status in ("ok", "omitido", "error") for e in events)
    assert result.run.strategy == "b_reglas"
    assert result.run.seconds > 0
    assert result.run.external_calls == 0
    assert result.run.cost_eur == 0.0 and result.run.accounting_complete  # local: cero explícito


def test_candidates_carry_channel_strategy_and_raw_confidence():
    result = process(
        demo_documents(),
        project_id="DEMO-PLANT",
        equipment_id="vessel-001",
        revision="A",
        strategy="b_reglas",
    )
    channels = {c.channel for c in result.candidates}
    assert {"texto", "hoja_datos"} <= channels
    assert all(c.strategy == "b_reglas" for c in result.candidates)
    assert all(c.confidence_raw is not None for c in result.candidates)


def test_default_strategy_falls_back_to_b_with_a_warning_until_d_exists():
    result = process(
        demo_documents(), project_id="DEMO-PLANT", equipment_id="vessel-001", revision="A"
    )
    assert result.revision is not None
    assert (
        any("D aún no está implementada" in w for w in result.warnings)
        or result.run.strategy == "d_hibrido"
    )


def test_the_tag_falls_back_to_the_filename_when_no_document_has_it(monkeypatch):
    # Sin la calibración local de generated/: con ella, el tag del nombre (confianza 0,6) queda
    # «abstenido» en vez de «candidato». Los dos piden revisión; la prueba no depende de la máquina.
    monkeypatch.setenv("TRAZIA_CALIBRATION", "off")
    original = pipeline._ground

    def without_tag(*args, **kwargs):  # como un plano sin cajetín
        return [c for c in original(*args, **kwargs) if c.path != "tag"]

    monkeypatch.setattr(pipeline, "_ground", without_tag)
    result = process(
        demo_documents(), project_id="P", equipment_id="v-101", revision="A", strategy="b_reglas"
    )
    assert result.error is None
    tag = result.revision.equipment.tag
    assert tag.value == "V-101"
    assert tag.source.bbox is None and tag.source.locator.startswith(pipeline.FILENAME_LOCATOR)
    assert tag.state == "candidate" and result.revision.pending_review()
    assert any("nombre del archivo" in w for w in result.warnings)
    [cited] = [c for c in result.candidates if c.path == "tag"]
    assert is_cited(cited)
    bundle = ingest_bytes(demo_documents()[0].data, "GAD_V-101_revA.pdf", "GA-V101", "A")
    assert is_supported(cited, bundle) is True
    assert is_supported(cited.model_copy(update={"value": "P-999"}), bundle) is False


def test_a_tag_read_from_a_document_keeps_priority_over_the_filename():
    documents = [
        InputDocument(d.filename.replace("V-101", "X-999"), d.data, d.document_id)
        for d in demo_documents()
    ]
    result = process(documents, project_id="P", equipment_id="v-101", revision="A")
    assert result.revision.equipment.tag.value == "V-101"


def test_bad_inputs_return_errors_instead_of_raising():
    unknown = process(
        demo_documents(), project_id="P", equipment_id="e", revision="A", strategy="no-existe"
    )
    assert unknown.revision is None and "Estrategia desconocida" in unknown.error

    broken = process(
        [InputDocument("GAD_X_rev1.pdf", b"no es un pdf", "GA-X")],
        project_id="P",
        equipment_id="e",
        revision="1",
        strategy="b_reglas",
    )
    assert broken.revision is None
    assert broken.error


def test_conflicting_readings_are_flagged_not_silently_chosen():
    def cand(value, confidence, channel):
        source = Source(document_id="GA", page=1, locator="t", confidence=confidence)
        return Candidate(path="diameter", value=value, unit="mm", source=source, channel=channel)

    resolution = resolve(
        [cand(2000.0, 0.9, "tabla"), cand(2100.0, 0.6, "cota"), cand(2000.0, 0.7, "texto")]
    )
    [chosen] = resolution.chosen
    assert chosen.value == 2000.0
    assert resolution.conflicts == ["diameter"]
    assert [a.value for a in chosen.alternatives] == [2100.0]
    assert "lecturas distintas" in chosen.explanation
