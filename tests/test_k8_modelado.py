"""K8: edición estructural y GA desde IFC; todos los casos son sintéticos."""

import hashlib
import io
import xml.etree.ElementTree as ET
from uuid import uuid4

import pdfplumber
import pytest
from test_edicion_asistida import (
    ACTOR,
    BASE,
    apply,
    etag_of,
    headers,
    previewed,
    wait_job,
)
from test_edicion_asistida import client as edition_client
from test_plataforma_families import family_data

from trazia.design import ProposalInput, evaluate
from trazia.design.drawing import generate_ga
from trazia.design.intent import interpret
from trazia.design.proposal import evaluate_reversion
from trazia.ifc import build_ifc
from trazia.model import Revision


@pytest.fixture
def client(tmp_path):
    yield from edition_client.__wrapped__(tmp_path)


def run(operations, base=BASE, **extra):
    return evaluate(
        base,
        ProposalInput(operations=operations, reason="Prueba sintética", actor=ACTOR, **extra),
        proposal_id=uuid4().hex,
        label=base.revision + "-D1",
        created_at="2026-11-08T10:00:00Z",
        base_id="SYNTHETIC:BASE",
    )


def change(collection="nozzles", identity="N5", action="add", **parameters):
    return dict(
        action=action,
        collection=collection,
        id=identity,
        parameters={
            key: dict(
                value=value,
                unit="deg" if key == "azimuth" else "1" if key in {"dx", "dy", "dz"} else "mm",
            )
            for key, value in parameters.items()
        },
    )


def nozzle():
    return change(diameter=100, projection=200, elevation=4500, azimuth=45)


def revert(candidate, content, base=BASE):
    return evaluate_reversion(
        candidate,
        content,
        base,
        proposal_id="b" * 32,
        label="B-D2",
        created_at="2026-11-08T10:00:00Z",
        base_id="B-D1",
        actor=ACTOR,
        reason="Deshacer prueba sintética",
    )[0]


def test_batch_references_use_final_skirt_and_text_noop_is_honest():
    result, _ = run(
        [
            dict(target="total_height", value=10000, unit="mm"),
            dict(target="skirt_height", value=1500, unit="mm"),
            dict(target="nozzles.N1.elevation", value=1000, unit="mm", datum="tangente_inferior"),
        ]
    )
    assert result.status == "ready", result.issues
    assert result.candidate.equipment.total_height == 10000
    assert result.candidate.equipment.nozzles[0].elevation.value == 2500
    result, _ = run(
        [dict(target="attributes.material", value=BASE.equipment.attributes["material"].value)]
    )
    assert result.status == "invalid" and result.candidate is None


@pytest.mark.parametrize(
    "part",
    [
        nozzle(),
        change(identity="N4", action="remove"),
        change("platforms", "P1", x=1500, y=0, z=2500, size_x=1000, size_y=800, size_z=100),
        change(
            "ladders",
            "L1",
            x=1500,
            y=0,
            z=0,
            width=500,
            height=4000,
            rail_diameter=30,
            rung_spacing=300,
        ),
    ],
)
def test_parts_are_reversible_with_sources_and_ifc_identity(part):
    result, content = run(
        [], part_changes=[part], detail_level=3 if part["collection"] != "nozzles" else None
    )
    assert result.status == "ready", result.issues
    after = result.candidate
    before_ifc, after_ifc = build_ifc(BASE), build_ifc(after)
    common_before = {p.Name: p.GlobalId for p in before_ifc.by_type("IfcElement")}
    common_after = {p.Name: p.GlobalId for p in after_ifc.by_type("IfcElement")}
    for name in common_before.keys() & common_after.keys():
        assert common_before[name] == common_after[name]
    undone = revert(after, content)
    assert undone.status == "ready", undone.issues
    assert undone.candidate.equipment == BASE.equipment
    assert BASE.equipment.lod == 2 and after.approval is None


@pytest.mark.parametrize(
    "parts,extra",
    [
        ([change(identity="N4")], {}),
        ([change(identity="shell")], {}),
        ([change(identity="NX", action="remove")], {}),
        ([change(identity="N3", action="remove"), change(identity="N4", action="remove")], {}),
        ([change("platforms", "P1", x=0, y=0, z=0, size_x=100, size_y=100, size_z=10)], {}),
        ([change(diameter=-100, projection=200, elevation=4500, azimuth=0)], {}),
        ([nozzle(), nozzle()], {}),
    ],
)
def test_invalid_structural_batches_never_yield_candidate(parts, extra):
    result, _ = run([], part_changes=parts, **extra)
    assert result.status == "invalid" and result.candidate is None


@pytest.mark.parametrize(
    "kind,path,value",
    [
        ("horizontal_vessel", "horizontal.length", 7000),
        ("column", "column.sections.upper.height", 5000),
        ("tank", "tank.height", 8000),
        ("pump", "envelope.origin.x", -2500),
        ("compressor", "envelope.size.x", 2500),
        ("generic", "envelope.size.z", 4500),
    ],
)
def test_family_catalog_edits_existing_parametric_geometry(kind, path, value):
    base = Revision.model_validate(
        family_data(kind, 1 if kind in {"pump", "compressor", "generic"} else 2)
    )
    result, _ = run([dict(target=path, value=value, unit="mm")], base)
    assert result.status == "ready", result.issues
    assert build_ifc(result.candidate).by_type("IfcElement")


@pytest.mark.parametrize(
    "kind,xyz,direction",
    [
        ("horizontal_vessel", (2000, 1000, 1800), (0, 1, 0)),
        ("column", (1000, 0, 1500), (1, 0, 0)),
        ("tank", (3000, 0, 2000), (1, 0, 0)),
    ],
)
def test_explicit_connections_require_surface_and_derive_elevation(kind, xyz, direction):
    base = Revision.model_validate(family_data(kind))
    params = dict(zip(("x", "y", "z", "dx", "dy", "dz"), (*xyz, *direction)))
    part = change(diameter=100, projection=200, **params)
    result, _ = run([], base, part_changes=[part])
    assert result.status == "ready", result.issues
    moved, _ = run(
        [dict(target="nozzles.N5.position.z", value=xyz[2] + 100, unit="mm")], result.candidate
    )
    # Horizontal: moving only Z leaves the cylindrical surface; rejected rather than snapped.
    if kind == "horizontal_vessel":
        assert moved.status == "invalid"
    else:
        assert moved.status == "ready", moved.issues
        assert moved.candidate.equipment.nozzles[0].elevation.value == xyz[2] + 100
        assert any(o["id"].startswith("derived-") for o in moved.operations)
    part["parameters"]["x"]["value"] = 99999
    invalid, _ = run([], base, part_changes=[part])
    assert invalid.candidate is None


@pytest.mark.parametrize(
    "kind,path,value",
    [
        ("horizontal_vessel", "horizontal.length", 1000),
        ("column", "column.sections.lower.diameter", 2500),
        ("tank", "tank.roof_height", 0),
        ("generic", "envelope.size.x", -1),
    ],
)
def test_family_constraints_are_enforced_on_whole_candidate(kind, path, value):
    base = Revision.model_validate(family_data(kind, 1 if kind == "generic" else 2))
    result, _ = run([dict(target=path, value=value, unit="mm")], base)
    assert result.status == "invalid" and result.candidate is None


def test_removed_parts_and_accessories_have_viewer_semantics():
    from trazia.api.change_proposals import element_map

    result, _ = run([], part_changes=[change(identity="N4", action="remove")])
    mapping = element_map(BASE, result.candidate, result, build_ifc(result.candidate))
    removed = next(p for p in mapping if p["part"] == "N4")
    assert removed["semantic_id"] == "nozzle:N4" and removed["removed"]
    assert removed["existed_before"] and not removed["in_ifc"]
    assert removed["operations"] == ["part-1"]
    result, _ = run(
        [],
        detail_level=3,
        part_changes=[
            change("platforms", "P1", x=1500, y=0, z=2500, size_x=1000, size_y=800, size_z=100)
        ],
    )
    mapping = element_map(BASE, result.candidate, result, build_ifc(result.candidate))
    platform = next(p for p in mapping if p["part"] == "platform-P1")
    assert platform["semantic_id"] == "element:platform-P1" and platform["in_ifc"]


def test_undo_never_hides_unrelated_lod3_accessory():
    result, content = run(
        [],
        detail_level=3,
        part_changes=[
            change("platforms", "P1", x=1500, y=0, z=2500, size_x=1000, size_y=800, size_z=100)
        ],
    )
    current, _ = run(
        [],
        result.candidate,
        part_changes=[
            change(
                "ladders",
                "L1",
                x=1500,
                y=0,
                z=0,
                width=500,
                height=4000,
                rail_diameter=30,
                rung_spacing=300,
            )
        ],
    )
    undone = revert(current.candidate, content)
    assert undone.status == "invalid" and any(i["code"] == "lod_conflict" for i in undone.errors)


def test_chat_structural_drafts_never_apply_or_guess_missing_dimensions():
    draft = interpret(
        BASE, "Añade boquilla N5 diámetro 100 mm proyección 200 mm elevación 4500 mm azimut 45 deg"
    )
    assert not draft["clarifications"] and not draft["applied"]
    assert draft["part_changes"][0]["id"] == "N5"
    draft = interpret(BASE, "Elimina boquilla N4")
    assert draft["part_changes"][0]["action"] == "remove"
    draft = interpret(BASE, "Añade boquilla N5 diámetro 100 mm")
    assert draft["clarifications"] and not draft["part_changes"]
    draft = interpret(BASE, "Elimina boquilla N4 y aprueba")
    assert draft["rejected"] and not draft["part_changes"]


@pytest.mark.parametrize("kind", ["horizontal_vessel", "column", "tank", "generic"])
def test_ga_is_vector_a3_at_physical_scale_from_actual_ifc(kind):
    revision = Revision.model_validate(family_data(kind, 1 if kind == "generic" else 2))
    content = build_ifc(revision).to_string().encode()
    output = generate_ga(content, revision)
    manifest = output["manifest"]
    if kind == "generic":
        assert manifest["world_bounds_mm"]["size"] == pytest.approx([2000, 3000, 4000])
    assert manifest["ifc_sha256"] == hashlib.sha256(content).hexdigest()
    assert len(manifest["views"]) == 3 and manifest["pieces"]
    svg = ET.fromstring(output["svg"])
    assert svg.attrib["width"] == "420mm"
    assert len(svg.findall("{http://www.w3.org/2000/svg}line")) > 10
    with pdfplumber.open(io.BytesIO(output["pdf"])) as pdf:
        assert len(pdf.pages) == 1
        page = pdf.pages[0]
        assert page.width == pytest.approx(420 * 72 / 25.4, abs=0.01)
        assert "DRAFT" in page.extract_text() and "Escala 1:" in page.extract_text()
        assert len(page.lines) > 10
        # All physical dimensions and text stay on the paper.
        assert all(0 <= c["x0"] < c["x1"] <= page.width for c in page.chars)
    with pytest.raises(ValueError, match="escala"):
        generate_ga(content, revision, scale=1)


def test_api_add_preview_apply_ga_download_and_revert(client):
    original = client.get("/equipment/V-101/revisions/B").json()
    proposal = previewed(
        client, dict(part_changes=[nozzle()], reason="Alta sintética", actor=ACTOR)
    )
    assert proposal["preview"]["elements"]
    applied = apply(client, proposal)
    assert applied.status_code == 201, applied.text
    identity = applied.json()["revision_id"]
    key = headers(etag_of(client, "B-D1"))
    start = client.post(f"/revisions/{identity}/ga-drawings", json={}, headers=key)
    assert start.status_code == 202, start.text
    assert (
        client.post(f"/revisions/{identity}/ga-drawings", json={}, headers=key).json()
        == start.json()
    )
    job = wait_job(client, start.json()["job_id"])
    assert job["status"] == "done", job
    files = client.get(f"/revisions/{identity}/ga-drawings").json()["files"]
    assert set(files) == {"pdf", "svg", "ifc", "manifest"}
    for key, file in files.items():
        response = client.get(file["url"])
        assert response.status_code == 200
        assert hashlib.sha256(response.content).hexdigest() == file["sha256"]
        assert response.headers["X-Derived-Document"] == "true"
    assert client.get("/equipment/V-101/revisions/B").json() == original
    undone = client.post(
        f"/change-proposals/{proposal['id']}/revert",
        json=dict(actor=ACTOR, reason="Deshacer alta sintética"),
        headers=headers(etag_of(client, "B-D1")),
    )
    assert undone.status_code == 201, undone.text
    assert undone.json()["status"] == "ready"
    reversal_id = undone.json()["id"]
    started = client.post(
        f"/change-proposals/{reversal_id}/preview", json={"express_rules": False}, headers=headers()
    )
    assert wait_job(client, started.json()["job_id"])["status"] == "done"
    ready = client.get(f"/change-proposals/{reversal_id}").json()
    restored = apply(client, ready)
    assert restored.status_code == 201, restored.text
    label = restored.json()["proposal"]["target_revision"]
    equipment = client.get(f"/equipment/V-101/revisions/{label}").json()["equipment"]
    assert equipment == original["equipment"]
    refused = client.post(
        "/documents",
        files={
            "file": ("ga_nuevo.pdf", client.get(files["pdf"]["url"]).content, "application/pdf")
        },
        headers=headers(),
    )
    assert refused.status_code == 422


def test_apply_rechecks_etag_inside_publication_transaction(client, monkeypatch):
    proposal = previewed(client)
    store = client.app.state.store
    original_put = store.put
    edited = []

    def interleaved_put(data):
        if not edited:
            edited.append(True)
            response = client.patch(
                "/revisions/B/fields/diameter",
                json=dict(state="accepted", action="accept", actor=ACTOR),
                headers=headers(etag_of(client)),
            )
            assert response.status_code == 200, response.text
        return original_put(data)

    monkeypatch.setattr(store, "put", interleaved_put)
    response = apply(client, proposal)
    assert response.status_code == 412, response.text
    assert edited
    assert client.get("/equipment/V-101/revisions/B-D1").status_code == 404


@pytest.mark.parametrize("interrupt", ["cancel", "stale"])
def test_drawing_never_publishes_after_cancel_or_revision_edit(client, monkeypatch, interrupt):
    from trazia.api import design_drawings

    original_build = design_drawings.build_drawing

    def interrupted_build(store, job_id, config):
        result = original_build(store, job_id, config)
        if interrupt == "cancel":
            response = client.post(f"/jobs/{job_id}/cancel", headers=headers())
        else:
            response = client.patch(
                "/revisions/B/fields/diameter",
                json=dict(state="accepted", action="accept", actor=ACTOR),
                headers=headers(etag_of(client)),
            )
        assert response.status_code in (200, 202), response.text
        return result

    monkeypatch.setattr(design_drawings, "build_drawing", interrupted_build)
    start = client.post("/revisions/B/ga-drawings", json={}, headers=headers(etag_of(client)))
    assert start.status_code == 202
    result = wait_job(client, start.json()["job_id"])
    assert result["status"] == ("cancelled" if interrupt == "cancel" else "error"), result
    assert not client.get("/revisions/B/ga-drawings").json()["files"]


def test_long_change_report_paginates_every_operation_without_clipping():
    from trazia.design.report import design_report

    evaluation, content = run([dict(target="height", value=7000, unit="mm")])
    template = content["operations"][0]
    content["reason"] = "Justificación sintética extensa para comprobar paginación. " * 15
    content["operations"] = [
        dict(
            template,
            id=f"op-{i}",
            label=f"CAMPO_UNICO_{i:02d} " + "Etiqueta larga de operación sintética " * 3,
        )
        for i in range(20)
    ]
    output = design_report(
        evaluation.candidate,
        content,
        {},
        meta=dict(generated_at="2026-11-08T10:00:00Z", order_sha256="a" * 64),
    )
    with pdfplumber.open(io.BytesIO(output)) as document:
        assert len(document.pages) >= 2
        text = "\n".join(page.extract_text() for page in document.pages)
        assert all(f"CAMPO_UNICO_{i:02d}" in text for i in range(20))
        assert all(
            0 <= c["top"] <= c["bottom"] <= page.height
            for page in document.pages
            for c in page.chars
        )
