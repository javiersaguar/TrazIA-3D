"""F.5: cruce real de originales, páginas y evidencias sin modificar revisiones."""

import hashlib
import io
from pathlib import Path

from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas

from trazia.model import Document, fields, load_revision
from trazia.revisions import compare

ROOT = Path(__file__).resolve().parents[1]


def pdf(deltas=(), *, raster=False, pages=1):
    buffer = io.BytesIO()
    canvas = Canvas(buffer, pagesize=(200, 200))
    for _ in range(pages):
        if raster:
            canvas.drawImage(ImageReader(Image.new("RGB", (200, 200), "white")), 0, 0, 200, 200)
        canvas.setFont("Helvetica", 6)
        canvas.drawString(5, 190, "SYNTHETIC - UNIT FIXTURE")
        for x, y in deltas:
            path = canvas.beginPath()
            path.moveTo(x, y)
            path.lineTo(x + 12, y)
            path.lineTo(x + 6, y + 10)
            path.close()
            canvas.drawPath(path, stroke=1, fill=0)
        canvas.showPage()
    canvas.save()
    return buffer.getvalue()


def revisions(data):
    before = load_revision(ROOT / "examples/vessel_rev_a.json")
    after = before.model_copy(deep=True)
    after.revision = "B"
    identity = after.equipment.height.source.document_id
    after.documents = [
        Document(
            id=d.id,
            filename=d.filename,
            revision="B",
            sha256=hashlib.sha256(data).hexdigest(),
            page_count=1,
        )
        if d.id == identity
        else d
        for d in after.documents
    ]
    after.equipment.height.value += 10
    after.equipment.height.source.bbox = (0.1, 0.2, 0.2, 0.25)
    after.equipment.height.source.page = 1
    after.equipment.height.alternatives = []
    after.equipment.diameter.value += 10
    after.equipment.diameter.source.bbox = (0.1, 0.45, 0.2, 0.5)
    after.equipment.diameter.source.page = 1
    after.equipment.diameter.alternatives = []
    return before, after, {hashlib.sha256(data).hexdigest(): data}, identity


def marks(before, after, originals):
    return compare(before, after, originals=originals, include_visual=False)["layers"][
        "revision_marks"
    ]


def test_real_vector_marks_cover_changes_and_flag_orphans_without_mutation():
    a, b, originals, identity = revisions(pdf([(60, 150), (150, 30)]))
    fingerprint = b.fingerprint()
    result = marks(a, b, originals)
    assert result["status"] == "ok" and len(result["documents"][0]["marks"]) == 2
    assert [c["path"] for c in result["unmarked_changes"]] == ["diameter"]
    assert result["unmarked_changes"][0]["document_id"] == identity
    assert len(result["marks_without_change"]) == 1
    assert result["coordinate_frame"] == "after-page" and not result["is_design_validation"]
    assert b.fingerprint() == fingerprint and b.approval is None


def test_same_page_in_another_document_cannot_cover_the_change():
    a, b, originals, identity = revisions(pdf([(150, 30)]))
    other = pdf([(60, 150)])
    sha = hashlib.sha256(other).hexdigest()
    b.documents.append(
        Document(id="OTHER", filename="other.pdf", revision="B", sha256=sha, page_count=1)
    )
    originals[sha] = other
    result = marks(a, b, originals)
    assert {c["path"] for c in result["unmarked_changes"] if c["document_id"] == identity} == {
        "height",
        "diameter",
    }
    assert any(m["document_id"] == "OTHER" for m in result["marks_without_change"])


def test_hash_mismatch_and_missing_original_do_not_generate_discrepancies():
    a, b, originals, _ = revisions(pdf([(60, 150)]))
    result = marks(a, b, {key: b"changed" for key in originals})
    assert result["status"] == "unavailable" and result["documents"][0]["status"] == "hash_mismatch"
    assert not result["unmarked_changes"] and not result["marks_without_change"]
    assert marks(a, b, {})["documents"][0]["status"] == "missing_original"
    assert marks(a, b, None)["status"] == "missing_originals"


def test_hybrid_scan_is_unknown_even_with_vector_text_and_delta():
    a, b, originals, _ = revisions(pdf([(60, 150)], raster=True))
    result = marks(a, b, originals)
    assert result["status"] == "partial"
    assert result["documents"][0]["unread_pages"] == [1]
    assert not result["unmarked_changes"] and not result["marks_without_change"]


def test_unread_page_limit_does_not_flag_change_outside_processed_pages():
    a, b, originals, _ = revisions(pdf([(60, 150)], pages=101))
    b.equipment.height.source.page = 101
    result = marks(a, b, originals)
    assert result["status"] == "partial"
    assert result["documents"][0]["pages_truncated"]
    assert 101 in result["documents"][0]["unread_pages"]
    assert not any(c["path"] == "height" for c in result["unmarked_changes"])


def test_removed_field_does_not_use_old_coordinates_on_the_new_drawing():
    a, b, originals, _ = revisions(pdf([(60, 150)]))
    del b.equipment.attributes["material"]
    result = marks(a, b, originals)
    assert "attributes.material" in result["unlocated_changes"]


def test_unchanged_location_of_same_nozzle_is_a_valid_hint():
    a, b, originals, _ = revisions(pdf([(60, 150)]))
    b.equipment.height.value = a.equipment.height.value
    b.equipment.diameter.value = a.equipment.diameter.value
    nozzle = b.equipment.nozzles[0]
    nozzle.elevation.value += 10
    for path, field in fields(b.equipment).items():
        if path.startswith(f"nozzles.{nozzle.id}."):
            field.source.bbox = (0.1, 0.7, 0.2, 0.75)
            field.alternatives = []
    nozzle.diameter.source.bbox = (0.1, 0.2, 0.2, 0.25)
    result = marks(a, b, originals)
    assert not result["unmarked_changes"] and not result["marks_without_change"]
