"""Recuperación visual de C con ColQwen2 detrás de un interruptor (ROADMAP 2.5).

El modelo no se carga aquí: los vectores de página se sustituyen por unos fijos. Lo que se prueba
es la caché, MaxSim, el interruptor, el umbral y la vuelta a la huella ligera.
"""

import hashlib
import json

import numpy as np
import pytest

from synthetic.sets import generate_set
from trazia.ingest import ingest_bytes
from trazia.pipeline import InputDocument, process
from trazia.rag import visual as colqwen
from trazia.rag.library import build
from trazia.strategies import c_rag


@pytest.fixture(scope="module")
def library(tmp_path_factory):
    root = tmp_path_factory.mktemp("rag-visual")
    generate_set("s-dev", root, cases=12, degradations=("vectorial",))  # dos por proveedor
    path = root / "biblioteca.json"
    build(root / "s-dev", path)
    manifest = json.loads((root / "s-dev" / "manifest.json").read_text(encoding="utf-8"))
    return root / "s-dev", path, manifest["cases"][6]["tag"]  # segundo caso de atlas


@pytest.fixture(autouse=True)
def _own_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAZIA_RAG_VISUAL_CACHE", str(tmp_path / "colqwen2"))
    monkeypatch.setenv("TRAZIA_CALIBRATION", "off")


def _run(dataset, tag, events):
    pdf = dataset / "vectorial" / tag / f"GAD_{tag}_rev1.pdf"
    return process(
        [InputDocument(pdf.name, pdf.read_bytes(), "GA")],
        project_id="P",
        equipment_id=tag.lower(),
        revision="1",
        strategy="c_rag",
        on_event=events.append,
    )


def _unit(rows):
    rows = np.asarray(rows, dtype=np.float32)
    return (rows / np.linalg.norm(rows, axis=1, keepdims=True)).astype(np.float16)


def test_maxsim_is_one_for_the_same_page_and_low_for_unrelated_ones():
    a = _unit(np.eye(4)[:3])
    assert colqwen.maxsim(a, a) == pytest.approx(1.0, abs=1e-3)
    assert colqwen.maxsim(a, _unit([[0, 0, 0, 1]])) == pytest.approx(0.0, abs=1e-3)


def test_page_vectors_come_from_the_cache_without_loading_the_model(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAZIA_RAG_VISUAL_CACHE", str(tmp_path))
    stored = _unit([[1, 0], [0, 1]])
    np.save(tmp_path / f"{colqwen.page_key(b'%PDF-1.7 x', 1)}.npy", stored)

    def no_model():
        raise AssertionError("no debe cargar el modelo con la página en caché")

    monkeypatch.setattr(colqwen, "_model", no_model)
    assert np.array_equal(colqwen.embed_page(b"%PDF-1.7 x", 1), stored)


def test_library_entries_keep_the_pdf_hash_and_path(library):
    dataset, path, tag = library
    for entry in json.loads(path.read_text(encoding="utf-8"))["entries"]:
        pdf = dataset / "vectorial" / entry["tag"] / f"GAD_{entry['tag']}_rev1.pdf"
        assert entry["sha256"] == hashlib.sha256(pdf.read_bytes()).hexdigest()
        assert entry["source"] == str(pdf)


def test_switch_off_by_default_means_the_light_fingerprint(library, monkeypatch):
    dataset, path, tag = library
    monkeypatch.setenv("TRAZIA_RAG_LIBRARY", str(path))
    monkeypatch.delenv("TRAZIA_RAG_RETRIEVAL", raising=False)
    monkeypatch.setattr(c_rag, "visual_best", lambda *a: pytest.fail("ColQwen2 sin pedirlo"))
    events = []
    _run(dataset, tag, events)
    assert next(e for e in events if e.stage == "rag").status == "ok"


def test_colqwen2_chooses_the_case_and_the_light_fingerprint_gives_the_confidence(
    library, monkeypatch
):
    dataset, path, tag = library
    entries = json.loads(path.read_text(encoding="utf-8"))["entries"]
    # Se fuerza a ColQwen2 a elegir un caso distinto del que elige la huella.
    pdf = (dataset / "vectorial" / tag / f"GAD_{tag}_rev1.pdf").read_bytes()
    lines = ingest_bytes(pdf, f"GAD_{tag}_rev1.pdf", "GA", "1").lines
    others = [e for e in entries if e["equipment_id"] != tag.lower()]
    by_light = c_rag.light_best(pdf, 1, lines, others)[2]["tag"]
    wanted = next(e["tag"] for e in others if e["tag"] != by_light)
    monkeypatch.setenv("TRAZIA_RAG_LIBRARY", str(path))
    monkeypatch.setenv("TRAZIA_RAG_RETRIEVAL", "colqwen2")
    monkeypatch.setattr(colqwen, "embed_page", lambda data, page: _unit([[1, 0]]))
    monkeypatch.setattr(
        colqwen,
        "entry_vectors",
        lambda e: _unit([[1, 0]] if e["tag"] == wanted else [[0, 1]]),
    )
    events = []
    result = _run(dataset, tag, events)
    rag = next(e for e in events if e.stage == "rag")
    assert rag.status == "ok" and f"Plantilla de {wanted} " in rag.detail
    picked = next(e for e in others if e["tag"] == wanted)
    expected = round(min(0.85, 0.5 + 0.4 * c_rag.light_score(pdf, 1, lines, picked)), 3)
    confidences = {c.source.confidence for c in result.candidates if c.channel == "rag"}
    assert expected in confidences  # sale de la huella del par elegido, no de MaxSim = 1


def test_below_the_visual_threshold_c_abstains(library, monkeypatch):
    dataset, path, tag = library
    monkeypatch.setenv("TRAZIA_RAG_LIBRARY", str(path))
    monkeypatch.setenv("TRAZIA_RAG_RETRIEVAL", "colqwen2")
    monkeypatch.setattr(c_rag, "MIN_VISUAL_SIMILARITY", 0.5)
    monkeypatch.setattr(colqwen, "embed_page", lambda data, page: _unit([[1, 0]]))
    monkeypatch.setattr(colqwen, "entry_vectors", lambda e: _unit([[0, 1]]))
    events = []
    result = _run(dataset, tag, events)
    rag = next(e for e in events if e.stage == "rag")
    assert rag.status == "omitido" and "ColQwen2" in rag.detail
    assert not [c for c in result.candidates if c.channel == "rag"]


def test_without_colqwen2_c_falls_back_to_the_light_fingerprint(library, monkeypatch):
    dataset, path, tag = library
    monkeypatch.setenv("TRAZIA_RAG_LIBRARY", str(path))
    monkeypatch.setenv("TRAZIA_RAG_RETRIEVAL", "colqwen2")

    def unavailable(data, page):
        raise colqwen.VisualUnavailable("Falta el extra train (torch y transformers)")

    monkeypatch.setattr(colqwen, "embed_page", unavailable)
    events = []
    _run(dataset, tag, events)
    rag = [e for e in events if e.stage == "rag"]
    assert rag[0].status == "error" and "huella ligera" in rag[0].detail
    assert rag[-1].status == "ok"
