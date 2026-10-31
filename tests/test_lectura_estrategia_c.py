"""Estrategia C (tarea 2.5): biblioteca aprobada, recuperación y región equivalente."""

import json

import pytest

from synthetic.cases import flatten, spec_from_dict
from synthetic.sets import generate_set
from trazia.pipeline import InputDocument, process
from trazia.rag.library import build


@pytest.fixture(scope="module")
def library(tmp_path_factory):
    root = tmp_path_factory.mktemp("rag")
    generate_set("s-dev", root, cases=12, degradations=("vectorial",))  # dos casos por proveedor
    path = root / "biblioteca.json"
    build(root / "s-dev", path)
    return root / "s-dev", path


def _run(dataset, tag, events=None):
    folder = dataset / "vectorial" / tag
    docs = [
        InputDocument(f"GAD_{tag}_rev1.pdf", (folder / f"GAD_{tag}_rev1.pdf").read_bytes(), "GA")
    ]
    return process(
        docs,
        project_id="P",
        equipment_id=tag.lower(),
        revision="1",
        strategy="c_rag",
        on_event=(events.append if events is not None else None),
    )


def test_c_reads_values_where_a_similar_approved_case_had_them(library, monkeypatch):
    dataset, path = library
    monkeypatch.setenv("TRAZIA_RAG_LIBRARY", str(path))
    manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
    case = manifest["cases"][6]  # segundo caso de atlas
    events = []
    result = _run(dataset, case["tag"], events)
    rag = next(e for e in events if e.stage == "rag")
    assert rag.status == "ok" and case["tag"] not in rag.detail  # nunca él mismo
    truth = json.loads((dataset / "truth" / f"{case['tag']}.json").read_text(encoding="utf-8"))
    expected = flatten(spec_from_dict(truth["rev1"]))
    found = {c.path: c for c in result.candidates}
    geometry = [p for p in expected if not p.startswith("attributes.") and p != "tag"]
    correct = sum(p in found and abs(float(found[p].value) - expected[p][0]) <= 1 for p in geometry)
    assert correct >= 0.9 * len(geometry)
    for c in found.values():  # todo valor lleva evidencia del documento actual
        assert c.channel == "rag" and c.text_original and c.grounded is True


def test_c_abstains_without_library(tmp_path, monkeypatch, library):
    dataset, _ = library
    monkeypatch.setenv("TRAZIA_RAG_LIBRARY", str(tmp_path / "no-existe.json"))
    manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
    result = _run(dataset, manifest["cases"][0]["tag"])
    assert [c.channel for c in result.candidates] == ["nombre_archivo"]
    assert result.revision is None
