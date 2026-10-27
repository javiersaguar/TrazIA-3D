"""Interfaz `trazia.pipeline.process` (contrato con el Agente Plataforma)."""

from pathlib import Path

from trazia.extraction import Candidate
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
