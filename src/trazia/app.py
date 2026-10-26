"""Espacio local de revisión. Ejecutar con `trazia serve`."""

import hashlib
import json
from pathlib import Path

import streamlit as st

from trazia.extraction import LabelExtractor, assemble
from trazia.ifc import build_ifc
from trazia.ingest import ingest_bytes, render_evidence
from trazia.model import Revision, fields, load_revision
from trazia.review import approve
from trazia.revisions import compare
from trazia.viewer import figure, meshes_from_ifc

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples"
LABELS = {
    "tag": "Tag",
    "diameter": "Diámetro exterior",
    "height": "Longitud de virola",
    "head_depth": "Profundidad de fondos",
    "skirt_height": "Altura del faldón",
    "skirt_thickness": "Espesor del faldón",
}


def install(revision: Revision, originals: dict):
    st.session_state["revision_json"] = revision.model_dump_json()
    st.session_state["originals"] = originals
    st.session_state["editor_generation"] = st.session_state.get("editor_generation", 0) + 1


def demo(letter):
    revision = load_revision(EXAMPLES / f"vessel_rev_{letter.lower()}.json")
    originals = {
        d.id: {"filename": d.filename, "data": (EXAMPLES / "documents" / d.filename).read_bytes()}
        for d in revision.documents
    }
    install(revision, originals)


def artifacts(revision):
    key = revision.model_dump_json()
    if st.session_state.get("artifact_key") != key:
        content = build_ifc(revision, draft=revision.approval is None).to_string()
        st.session_state["artifact_key"] = key
        st.session_state["ifc_content"] = content
        st.session_state["meshes"] = meshes_from_ifc(content)
    return st.session_state["ifc_content"], st.session_state["meshes"]


def field_rows(revision):
    return [
        {
            "campo": path,
            "valor": str(f.value),
            "unidad": f.unit,
            "confianza": f.source.confidence,
            "revisado": f.source.reviewed,
            "origen": f.source.document_id,
        }
        for path, f in fields(revision.equipment).items()
    ]


def update_values(revision, rows):
    updated = revision.model_copy(deep=True)
    updated.approval = None
    lookup = fields(updated.equipment)
    for row in rows:
        item = lookup[row["campo"]]
        value = float(row["valor"]) if isinstance(item.value, float) else str(row["valor"])
        if (value, row["unidad"]) != (item.value, item.unit):
            item.value, item.unit = value, row["unidad"]
            item.source.reviewed = False
    return Revision.model_validate_json(updated.model_dump_json())


def show_evidence(revision, path):
    item = fields(revision.equipment)[path]
    source = item.source
    st.caption(f"{source.document_id} · {source.locator} · score {source.confidence:.2f}")
    original = st.session_state.get("originals", {}).get(source.document_id)
    document = next(d for d in revision.documents if d.id == source.document_id)
    if not original:
        st.info("Vincula el original en Documentos para inspeccionar esta evidencia.")
        return
    if hashlib.sha256(original["data"]).hexdigest() != document.sha256:
        st.error("La huella del original no coincide con el JSON.")
        return
    if source.page:
        st.image(
            render_evidence(original["data"], original["filename"], source.page, source.bbox),
            caption=f"{document.filename} · página {source.page}",
            width="stretch",
        )
    else:
        bundle = ingest_bytes(
            original["data"], original["filename"], document.id, document.revision
        )
        lines = [
            line.text
            for line in bundle.lines
            if line.source.sheet == source.sheet and line.source.cell == source.cell
        ]
        st.code("\n".join(lines) or "Localizador sin coincidencia", language="text")
    st.caption("La confianza del baseline es un score heurístico, todavía sin calibrar.")


def model_tab(revision):
    equipment = revision.equipment
    content, meshes = artifacts(revision)
    left, right = st.columns([1.65, 1], gap="large")
    with left:
        st.subheader(f"{equipment.tag.value} / revisión {revision.revision}")
        st.caption("IFC4 generado · arrastra para orbitar · rueda para acercar")
        components = ["Todo el equipo", *[m["component"] for m in meshes]]
        selected = st.selectbox("Inspeccionar componente", components)
        st.plotly_chart(
            figure(meshes, None if selected == "Todo el equipo" else selected),
            width="stretch",
            key="main_model",
            config={"displaylogo": False},
        )
        a, b, c = st.columns(3)
        a.metric("Diámetro", f"{equipment.diameter.value / 1000:g} m")
        b.metric("Altura total", f"{equipment.total_height / 1000:g} m")
        c.metric("Boquillas", len(equipment.nozzles))
        a, b = st.columns(2)
        with a:
            st.download_button(
                "Descargar IFC" + (" · DRAFT" if revision.approval is None else " · aprobado"),
                content.encode(),
                file_name=f"{equipment.tag.value}_{revision.revision}.ifc",
                mime="application/x-step",
                width="stretch",
            )
        with b:
            st.download_button(
                "Descargar JSON trazable",
                revision.model_dump_json(indent=2),
                file_name=f"revision_{revision.revision}.json",
                mime="application/json",
                width="stretch",
            )
    with right:
        st.subheader("Datos y evidencia")
        generation = st.session_state.get("editor_generation", 0)
        with st.form(f"fields_{generation}"):
            edited = st.data_editor(
                field_rows(revision),
                hide_index=True,
                width="stretch",
                height=340,
                disabled=["campo", "confianza", "revisado", "origen"],
                key=f"data_editor_{generation}",
            )
            st.caption("Edita valores y unidades; guardar invalida la aprobación anterior.")
            if st.form_submit_button("Guardar correcciones"):
                try:
                    install(update_values(revision, edited), st.session_state["originals"])
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))
        path = st.selectbox(
            "Ver evidencia del campo",
            list(fields(equipment)),
            format_func=lambda p: LABELS.get(p, p),
        )
        show_evidence(revision, path)
    st.divider()
    if revision.approval:
        st.success(
            f"Aprobado por {revision.approval.reviewer} · {revision.approval.timestamp.isoformat()}"
        )
    else:
        st.subheader("Checkpoint humano")
        st.caption("La previsualización y las descargas actuales son borradores.")
        reviewer = st.text_input("Nombre del revisor")
        confirmed = st.checkbox(
            "He revisado los valores, unidades, geometría y evidencias de esta revisión"
        )
        if st.button("Aprobar esta versión", disabled=not confirmed or len(reviewer.strip()) < 2):
            try:
                originals = {k: v["data"] for k, v in st.session_state["originals"].items()}
                install(approve(revision, reviewer, originals), st.session_state["originals"])
                st.rerun()
            except ValueError as error:
                st.error(str(error))


def documents_tab(revision):
    st.subheader("Del documento al dato")
    st.write(
        "Carga originales, conserva su huella y extrae candidatos con el baseline de etiquetas."
    )
    st.info(
        "El baseline reconoce etiquetas explícitas. OCR, interpretación de vistas "
        "y extracción con IA están pendientes; los valores desconocidos bloquean la construcción."
    )
    uploaded = st.file_uploader(
        "Planos y hojas de datos",
        type=["pdf", "xlsx", "png", "jpg", "jpeg"],
        accept_multiple_files=True,
    )
    a, b, c = st.columns(3)
    project = a.text_input("Proyecto", revision.project_id)
    equipment = b.text_input("ID estable del equipo", revision.equipment.id)
    rev = c.text_input("Revisión a construir", revision.revision)
    dataset = st.selectbox("Procedencia de los nuevos documentos", ["real", "synthetic"])
    metadata = []
    for index, file in enumerate(uploaded):
        a, b = st.columns([2, 1])
        identifier = a.text_input(
            f"ID documental · {file.name}", f"DOC-{index + 1}", key=f"id_{file.name}"
        )
        doc_revision = b.text_input(
            f"Revisión documental · {file.name}", rev, key=f"rev_{file.name}"
        )
        metadata.append((file, identifier, doc_revision))
    if st.button("Ingerir originales", disabled=not uploaded):
        try:
            ids = [item[1] for item in metadata]
            if len(ids) != len(set(ids)):
                raise ValueError("Los IDs documentales deben ser únicos")
            bundles = [
                ingest_bytes(f.getvalue(), f.name, key, doc_rev) for f, key, doc_rev in metadata
            ]
            st.session_state["bundles"] = bundles
            st.session_state["ingest_originals"] = {
                key: {"filename": f.name, "data": f.getvalue()} for f, key, _ in metadata
            }
            st.session_state["candidates"] = LabelExtractor().extract(bundles)
        except Exception as error:
            st.error(f"No se pudo ingerir: {error}")
    if "bundles" in st.session_state:
        bundles = st.session_state["bundles"]
        for bundle in bundles:
            st.caption(f"{bundle.document.filename} · SHA-256 {bundle.document.sha256}")
            for warning in bundle.warnings:
                st.warning(warning)
        candidates = st.session_state["candidates"]
        rows = [
            {
                "usar": True,
                "campo": p.path,
                "valor": str(p.value),
                "unidad": p.unit,
                "origen": p.source.document_id,
                "localizador": p.source.locator,
            }
            for p in candidates
        ]
        if rows:
            chosen = st.data_editor(
                rows,
                hide_index=True,
                disabled=["campo", "valor", "unidad", "origen", "localizador"],
                key="candidates_editor",
            )
            st.caption("Desmarca candidatos contradictorios antes de construir el borrador.")
            if st.button("Construir borrador desde candidatos", type="primary"):
                try:
                    selected = [
                        candidate for candidate, row in zip(candidates, chosen) if row["usar"]
                    ]
                    model = assemble(
                        bundles,
                        selected,
                        project_id=project,
                        equipment_id=equipment,
                        revision=rev,
                        dataset=dataset,
                    )
                    install(model, st.session_state["ingest_originals"])
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))
        else:
            st.warning(
                "No se encontraron parámetros compatibles. "
                "Requiere extracción asistida o un JSON revisado."
            )
    st.divider()
    st.subheader("Originales de la revisión actual")
    st.dataframe([d.model_dump() for d in revision.documents], hide_index=True, width="stretch")
    source_id = st.selectbox(
        "Vincular original a ID documental", [d.id for d in revision.documents]
    )
    original = st.file_uploader(
        "Original correspondiente al JSON",
        type=["pdf", "xlsx", "png", "jpg", "jpeg"],
        key="attach_original",
    )
    if st.button("Vincular y verificar original", disabled=original is None):
        document = next(d for d in revision.documents if d.id == source_id)
        if hashlib.sha256(original.getvalue()).hexdigest() != document.sha256:
            st.error("El SHA-256 no coincide con el documento declarado en el JSON.")
        else:
            st.session_state["originals"][source_id] = {
                "filename": document.filename,
                "data": original.getvalue(),
            }
            st.success("Original verificado y vinculado.")


def revisions_tab(current):
    st.subheader("Qué cambió y qué afecta")
    a, b = st.columns(2)
    uploaded_a = a.file_uploader("Revisión anterior · JSON", type="json", key="before_json")
    uploaded_b = b.file_uploader("Revisión nueva · JSON", type="json", key="after_json")
    use_current = st.checkbox("Usar revisión actual como destino")
    try:
        before = (
            Revision.model_validate_json(uploaded_a.getvalue())
            if uploaded_a
            else load_revision(EXAMPLES / "vessel_rev_a.json")
        )
        after = (
            current
            if use_current
            else (
                Revision.model_validate_json(uploaded_b.getvalue())
                if uploaded_b
                else load_revision(EXAMPLES / "vessel_rev_b.json")
            )
        )
        report = compare(before, after)
        st.caption("Sin archivos cargados se comparan las revisiones sintéticas A y B.")
        a, b, c = st.columns(3)
        a.metric("Campos modificados", report["summary"]["changes"])
        b.metric("Con efecto geométrico", report["summary"]["geometry_changes"])
        c.metric("Documentos actualizados", report["summary"]["document_changes"])
        changed = set()
        for change in report["changes"]:
            path = change["path"]
            if path.startswith("nozzles."):
                changed.add(path.split(".")[1])
            elif change["affects_geometry"]:
                changed.update(("shell", "top_head", "bottom_head", "skirt"))
        for index, (column, revision) in enumerate(zip(st.columns(2), (before, after))):
            with column:
                st.caption(f"Revisión {revision.revision} · {revision.dataset}")
                meshes = meshes_from_ifc(build_ifc(revision, draft=True).to_string())
                st.plotly_chart(
                    figure(meshes, changed=changed),
                    width="stretch",
                    key=f"diff_{index}_{revision.revision}",
                    config={"displaylogo": False},
                )
        st.caption("Ámbar: componentes afectados por reglas. Se conserva la versión anterior.")
        rows = [
            {
                "campo": c["path"],
                "operación": c["operation"],
                "antes": json.dumps(c["before"], ensure_ascii=False),
                "después": json.dumps(c["after"], ensure_ascii=False),
                "impacto": c["impact"],
            }
            for c in report["changes"]
        ]
        st.dataframe(rows, hide_index=True, width="stretch")
        st.download_button(
            "Descargar informe de cambios",
            json.dumps(report, ensure_ascii=False, indent=2),
            file_name="delta.json",
            mime="application/json",
        )
        with st.expander("Evidencias y cambios documentales"):
            st.json(report)
    except ValueError as error:
        st.error(str(error))


def main():
    st.set_page_config(page_title="TrazIA-3D · Ingeniería trazable", page_icon="◈", layout="wide")
    st.markdown(
        """<style>
    .stApp {background:#f5f8fa;color:#172c3d}
    [data-testid="stSidebar"] {background:#e8eff3}
    h1,h2,h3 {letter-spacing:-.035em}
    .block-container {padding-top:2rem}
    </style>""",
        unsafe_allow_html=True,
    )
    if "revision_json" not in st.session_state:
        demo("A")
    with st.sidebar:
        st.markdown("## TrazIA<span style='color:#007e80'> / 3D</span>", unsafe_allow_html=True)
        st.caption("Del plano al modelo, con cada cambio trazado.")
        st.divider()
        letter = st.selectbox(
            "Caso de demostración", ["A", "B"], format_func=lambda s: f"V-101 · revisión {s}"
        )
        if st.button("Cargar demo sintética", width="stretch"):
            demo(letter)
            st.rerun()
        uploaded = st.file_uploader("Abrir revisión JSON", type="json")
        if st.button("Cargar JSON", disabled=uploaded is None, width="stretch"):
            try:
                install(Revision.model_validate_json(uploaded.getvalue()), {})
                st.rerun()
            except ValueError as error:
                st.error(str(error))
        st.divider()
        st.caption("Base local · recipiente vertical · IFC4")
        st.caption("Los documentos se procesan localmente. No hay llamadas a proveedores de IA.")
    revision = Revision.model_validate_json(st.session_state["revision_json"])
    st.title("Ingeniería que conserva su origen.")
    st.caption(
        f"{revision.project_id} / {revision.equipment.tag.value} / revisión {revision.revision} · "
        f"{'DATOS SINTÉTICOS' if revision.dataset == 'synthetic' else 'DOCUMENTOS REALES'} · "
        f"{'APROBADO' if revision.approval else 'DRAFT · PENDIENTE DE REVISIÓN'}"
    )
    model, documents, revisions = st.tabs(
        ["Modelo y revisión", "Documentos y extracción", "Cambios A → B"]
    )
    with model:
        model_tab(revision)
    with documents:
        documents_tab(revision)
    with revisions:
        revisions_tab(revision)


if __name__ == "__main__":
    main()
