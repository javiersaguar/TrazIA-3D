"""Estrategia D (tareas 2.6 y 3.2): fusión, restricciones y memoria solo de revisiones aprobadas."""

import json

import pytest

from bench.estudio import reviewed_by_oracle
from synthetic.sets import generate_set
from trazia.extraction import Candidate
from trazia.ingest import ingest_bytes
from trazia.model import Source
from trazia.pipeline import InputDocument, process
from trazia.strategies.base import StrategyContext
from trazia.strategies.d_hibrido import HybridStrategy, fuse


def cand(value, channel, conf=0.8, bbox=(0.1, 0.1, 0.2, 0.12), text=None, path="height"):
    source = Source(document_id="GA", page=1, locator="t", bbox=bbox, confidence=conf)
    return Candidate(
        path=path,
        value=value,
        unit="mm",
        source=source,
        channel=channel,
        text_original=text if text is not None else str(value),
    )


def test_agreeing_independent_channels_reinforce_each_other():
    [chosen], conflicts = fuse(
        [cand(8000.0, "tabla", 0.8), cand(8000.0, "rag", 0.7, bbox=(0.5, 0.5, 0.6, 0.52))]
    )
    assert chosen.source.confidence == pytest.approx(1 - 0.2 * 0.3)
    assert not conflicts and "Coinciden" in chosen.explanation


def test_two_channels_reading_the_same_text_are_one_piece_of_evidence():
    [chosen], _ = fuse([cand(8000.0, "tabla", 0.8), cand(8000.0, "rag", 0.7)])
    assert chosen.source.confidence == pytest.approx(0.8)


def test_geometry_confirms_or_overrules_and_conflicts_are_explained():
    measured = cand(7999.9, "geometria", 0.6, text="")
    [ok], _ = fuse([cand(8000.0, "tabla", 0.8), measured])
    assert ok.value == 8000.0 and "confirma" in ok.explanation
    [fixed], conflicts = fuse([cand(9000.0, "tabla", 0.8), measured])
    assert fixed.value == 7999.9 and "height" in conflicts and fixed.alternatives
    [disputed], conflicts = fuse(
        [cand(8000.0, "tabla", 0.8), cand(8100.0, "ocr", 0.75, bbox=(0.5, 0.5, 0.6, 0.52))]
    )
    assert disputed.value == 8000.0 and "lecturas distintas" in disputed.explanation
    assert [a.value for a in disputed.alternatives] == [8100.0]


def test_dn_out_of_series_loses_against_a_normalised_reading():
    [chosen], _ = fuse(
        [
            cand(123.0, "ocr", 0.8, path="nozzles.N1.diameter"),
            cand(150.0, "rag", 0.7, bbox=(0.5, 0.5, 0.6, 0.52), path="nozzles.N1.diameter"),
        ]
    )
    assert chosen.value == 150.0


@pytest.fixture(scope="module")
def dev_set(tmp_path_factory):
    root = tmp_path_factory.mktemp("v2")
    generate_set("s-dev", root, cases=6, degradations=("vectorial",))
    return root / "s-dev"


def _run_case(dev_set, review_rev1):
    """Procesa rev1 y rev2 de un equipo; `review_rev1` decide qué recibe la rev2 como memoria."""
    manifest = json.loads((dev_set / "manifest.json").read_text(encoding="utf-8"))
    tag = manifest["cases"][1]["tag"]
    folder = dev_set / "vectorial" / tag
    truth = json.loads((dev_set / "truth" / f"{tag}.json").read_text(encoding="utf-8"))
    previous, events, result = None, [], None
    for rev in ("1", "2"):
        paths = sorted(folder.glob(f"*_rev{rev}.*"))
        ids = [("GA-" if p.name.startswith("GAD") else "HDM-") + tag for p in paths]
        result = process(
            [InputDocument(p.name, p.read_bytes(), i) for p, i in zip(paths, ids)],
            project_id="P",
            equipment_id=tag.lower(),
            revision=rev,
            strategy="d_hibrido",
            previous=previous,
            on_event=events.append,
        )
        assert result.revision is not None, result.error
        if rev == "1":
            previous = review_rev1(result.revision, truth["rev1"], list(zip(paths, ids)))
    return result, events


def test_hybrid_uses_memory_of_an_approved_previous_revision(dev_set, monkeypatch, tmp_path):
    monkeypatch.setenv("TRAZIA_RAG_LIBRARY", str(tmp_path / "sin-biblioteca.json"))
    approved = []

    def review(revision, truth, docs):
        approved.append(reviewed_by_oracle(revision, truth, docs))
        return approved[-1]

    result, events = _run_case(dev_set, review)
    assert approved[0] is not None and approved[0].approval is not None
    assert any(e.stage == "memory" and e.status == "ok" for e in events)
    assert all(c.explanation for c in result.candidates)


def test_hybrid_ignores_a_draft_previous_revision(dev_set, monkeypatch, tmp_path):
    monkeypatch.setenv("TRAZIA_RAG_LIBRARY", str(tmp_path / "sin-biblioteca.json"))
    result, events = _run_case(dev_set, lambda revision, truth, docs: revision)
    skipped = [e for e in events if e.stage == "memory"]
    assert [e.status for e in skipped] == ["omitido"]
    assert "borrador" in skipped[0].detail
    assert not any(c.channel == "memoria_revision" for c in result.candidates)
    assert any("Memoria de revisión omitida" in w for w in result.warnings)


def test_memory_does_not_bring_back_a_nozzle_whose_row_is_gone(dev_set, monkeypatch, tmp_path):
    monkeypatch.setenv("TRAZIA_RAG_LIBRARY", str(tmp_path / "sin-biblioteca.json"))
    approved = []

    def review(revision, truth, docs):
        approved.append(reviewed_by_oracle(revision, truth, docs))
        return approved[-1]

    _run_case(dev_set, review)
    previous = approved[0]
    gone = previous.equipment.nozzles[0].id
    tag = previous.equipment.id.upper()
    path = dev_set / "vectorial" / tag / f"GAD_{tag}_rev1.pdf"
    bundle = ingest_bytes(path.read_bytes(), path.name, f"GA-{tag}", "1")
    # El mismo plano, con la fila de esa boquilla ocupada por otra: el valor sigue en su región.
    lines = [
        line.model_copy(update={"text": "N99"}) if line.text.strip() == gone else line
        for line in bundle.lines
    ]
    ctx = StrategyContext(
        bundles=[bundle.model_copy(update={"lines": lines})],
        dataset="synthetic",
        previous=previous,
        providers=None,
        emit=lambda event: None,
        raw={},
        equipment_id=previous.equipment.id,
    )
    found = {c.path for c in HybridStrategy()._memory(ctx, {}).candidates}
    assert not any(p.startswith(f"nozzles.{gone}.") for p in found)
    assert any(p.startswith("nozzles.") for p in found)


def test_memory_is_refused_when_data_changed_after_approval(dev_set, monkeypatch, tmp_path):
    monkeypatch.setenv("TRAZIA_RAG_LIBRARY", str(tmp_path / "sin-biblioteca.json"))

    def tampered(revision, truth, docs):
        approved = reviewed_by_oracle(revision, truth, docs)
        assert approved is not None
        changed = approved.model_copy(deep=True)
        changed.equipment.height.value += 100.0  # edición posterior sin volver a aprobar
        return changed

    _, events = _run_case(dev_set, tampered)
    [memory] = [e for e in events if e.stage == "memory"]
    assert memory.status == "omitido" and "cambiaron" in memory.detail
