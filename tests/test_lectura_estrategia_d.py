"""Estrategia D (tarea 2.6): fusión con verificación cruzada, restricciones y memoria."""

import json

import pytest

from synthetic.sets import generate_set
from trazia.extraction import Candidate
from trazia.model import Source
from trazia.pipeline import InputDocument, process
from trazia.strategies.d_hibrido import fuse


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


def test_hybrid_builds_both_revisions_and_uses_revision_memory(dev_set, monkeypatch, tmp_path):
    monkeypatch.setenv("TRAZIA_RAG_LIBRARY", str(tmp_path / "sin-biblioteca.json"))
    manifest = json.loads((dev_set / "manifest.json").read_text(encoding="utf-8"))
    tag = manifest["cases"][1]["tag"]
    folder = dev_set / "vectorial" / tag
    previous, events = None, []
    for rev in ("1", "2"):
        docs = [
            InputDocument(
                p.name, p.read_bytes(), ("GA-" if p.name.startswith("GAD") else "HDM-") + tag
            )
            for p in sorted(folder.glob(f"*_rev{rev}.*"))
        ]
        result = process(
            docs,
            project_id="P",
            equipment_id=tag.lower(),
            revision=rev,
            strategy="d_hibrido",
            previous=previous,
            on_event=events.append,
        )
        assert result.revision is not None, result.error
        previous = result.revision
    assert any(e.stage == "memory" and e.status == "ok" for e in events)
    assert all(c.explanation for c in result.candidates)
