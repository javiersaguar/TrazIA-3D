"""Ingesta: tipo real del archivo, PDF cifrados, imágenes y duplicados (ROADMAP A.1, A.6 y A.7)."""

import io
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from trazia.ingest import image_to_pdf, ingest_bytes
from trazia.pipeline import InputDocument, process

DOCS = Path(__file__).resolve().parents[1] / "examples" / "documents"


def _image(fmt: str, frames: int = 1) -> bytes:
    pages = []
    for i in range(frames):
        page = Image.new("RGB", (400, 200), "white")
        ImageDraw.Draw(page).text((20, 80), f"N{i + 1} 2000 mm", fill="black")
        pages.append(page)
    buffer = io.BytesIO()
    pages[0].save(buffer, fmt, save_all=frames > 1, append_images=pages[1:])
    return buffer.getvalue()


def test_the_extension_must_match_the_content():
    xlsx = (DOCS / "HDM_V-101_revA.xlsx").read_bytes()
    with pytest.raises(ValueError, match="No es un PDF válido"):
        ingest_bytes(xlsx, "GAD_V-101_revA.pdf", "GA", "A")
    with pytest.raises(ValueError, match="No es un PNG válido"):
        ingest_bytes(b"%PDF-1.7 ...", "GAD_V-101.png", "GA", "A")


def test_old_excel_and_macro_books_are_refused_with_a_reason():
    with pytest.raises(ValueError, match="guardarlo como .xlsx"):
        ingest_bytes(b"\xd0\xcf\x11\xe0 viejo", "HDM_V-101.xls", "HDM", "A")
    with pytest.raises(ValueError, match="macros no se ejecutan"):
        ingest_bytes(b"PK\x03\x04 con macros", "HDM_V-101.xlsm", "HDM", "A")


def test_a_password_protected_pdf_is_refused_with_a_reason(monkeypatch):
    # Sin pypdf no hay cómo cifrar aquí: se simula la excepción que da pdfminer sin contraseña.
    import pdfplumber
    from pdfminer.pdfdocument import PDFPasswordIncorrect

    def locked(*args, **kwargs):
        raise PDFPasswordIncorrect

    monkeypatch.setattr(pdfplumber, "open", locked)
    with pytest.raises(ValueError, match="cifrado con contraseña"):
        ingest_bytes((DOCS / "GAD_V-101_revA.pdf").read_bytes(), "GAD_V-101_revA.pdf", "GA", "A")


@pytest.mark.parametrize(("fmt", "suffix"), [("PNG", ".png"), ("JPEG", ".jpg"), ("TIFF", ".tif")])
def test_images_are_accepted(fmt, suffix):
    bundle = ingest_bytes(_image(fmt), f"GAD_V-101_revA{suffix}", "GA", "A")
    assert bundle.document.page_count == 1
    assert any("PDF escaneado" in w for w in bundle.warnings)


def test_a_multipage_tiff_becomes_a_scanned_pdf_of_the_same_size():
    pdf = image_to_pdf(_image("TIFF", frames=3))
    bundle = ingest_bytes(pdf, "GAD_V-101_revA.pdf", "GA", "A")
    assert bundle.document.page_count == 3
    assert not bundle.lines  # sin capa de texto: la estrategia pasa al OCR
    import pdfplumber

    with pdfplumber.open(io.BytesIO(pdf)) as document:
        assert document.pages[0].to_image(resolution=200).original.size == (400, 200)


def test_the_pipeline_reads_an_image_as_a_scan_and_keeps_the_original_hash(monkeypatch):
    import hashlib

    from trazia import pipeline

    seen = {}

    class Spy:  # se queda con lo que llega a la estrategia
        def run(self, ctx):
            seen["ctx"] = ctx
            raise RuntimeError("fin de la prueba")

    monkeypatch.setattr(pipeline, "get_strategy", lambda name: Spy())
    png = _image("PNG")
    events = []
    process(
        [InputDocument("GAD_V-101_revA.png", png, "GA-V101")],
        project_id="P",
        equipment_id="v-101",
        revision="A",
        strategy="b_reglas",
        on_event=events.append,
    )
    assert [e.status for e in events if e.stage == "ingest"] == ["ok"]
    [bundle] = seen["ctx"].bundles
    assert bundle.media_type == "pdf" and not bundle.lines  # escaneado: B pasa al OCR
    assert bundle.document.filename == "GAD_V-101_revA.png"
    assert bundle.document.sha256 == hashlib.sha256(png).hexdigest()
    assert seen["ctx"].raw["GA-V101"].startswith(b"%PDF-")


def test_a_duplicated_document_is_read_once():
    ga = (DOCS / "GAD_V-101_revA.pdf").read_bytes()
    hdm = (DOCS / "HDM_V-101_revA.xlsx").read_bytes()
    events = []
    result = process(
        [
            InputDocument("GAD_V-101_revA.pdf", ga, "GA-V101"),
            InputDocument("GAD_V-101_revA (copia).pdf", ga, "GA-V101-2"),
            InputDocument("HDM_V-101_revA.xlsx", hdm, "HDM-V101"),
        ],
        project_id="P",
        equipment_id="v-101",
        revision="A",
        strategy="b_reglas",
        on_event=events.append,
    )
    assert any("idéntico a GAD_V-101_revA.pdf" in w for w in result.warnings)
    assert [e.status for e in events if e.stage == "ingest"].count("omitido") == 1
    assert result.revision is not None
    assert {d.id for d in result.revision.documents} == {"GA-V101", "HDM-V101"}
