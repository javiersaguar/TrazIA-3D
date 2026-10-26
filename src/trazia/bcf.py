"""Exportación BCF 2.1: un topic por cambio, cámara y selección por GUID."""

import io
import json
import zipfile
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid5
from xml.etree.ElementTree import Element, SubElement, tostring

import numpy as np

from .ifc import build_ifc, stable_guid
from .model import Revision
from .revisions import compare
from .viewer import meshes_from_ifc


def _text(parent, name, value):
    node = SubElement(parent, name)
    node.text = str(value)
    return node


def _xml(element):
    return tostring(element, encoding="utf-8", xml_declaration=True)


def export_bcf(
    before: Revision, after: Revision, report=None, *, author="Javier Saguar Antona"
) -> bytes:
    if not author.strip():
        raise ValueError("BCF requiere autor de creación")
    report = report if report is not None else compare(before, after)
    base = f"{after.project_id}/equipment/{after.equipment.id}"
    old = {m["guid"]: m for m in meshes_from_ifc(build_ifc(before).to_string())}
    new = {m["guid"]: m for m in meshes_from_ifc(build_ifc(after).to_string())}
    namespace = f"trazia-bcf:{before.fingerprint()}:{after.fingerprint()}"
    version = Element("Version", VersionId="2.1")
    _text(version, "DetailedVersion", "2.1")
    project = Element("ProjectExtension")
    identity = str(uuid5(NAMESPACE_URL, after.project_id))
    _text(SubElement(project, "Project", ProjectId=identity), "Name", after.project_id)
    _text(project, "ExtensionSchema", "")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("bcf.version", _xml(version))
        archive.writestr("project.bcfp", _xml(project))
        for index, change in enumerate(report["changes"]):
            path = change["path"]
            topic_id = str(uuid5(NAMESPACE_URL, f"{namespace}:{path}"))
            view_id = str(uuid5(NAMESPACE_URL, f"{namespace}:{path}:view"))
            component_key = base
            if path.startswith("nozzles."):
                nozzle_id = path.split(".")[1]
                nozzle = next(
                    (
                        n
                        for n in after.equipment.nozzles + before.equipment.nozzles
                        if n.id == nozzle_id
                    ),
                    None,
                )
                component_key += f"/nozzle/{getattr(nozzle, 'stable_id', None) or nozzle_id}"
            guid = stable_guid(component_key)
            selected = new.get(guid) or old.get(guid)
            if selected is None:
                guid = stable_guid(base)
                selected = new.get(guid) or old[guid]
            points = np.asarray(selected["vertices"]).reshape(-1, 3)
            low, high = points.min(axis=0), points.max(axis=0)
            center = (low + high) / 2
            scale = max(1.0, float(np.max(high - low)) * 1.6)
            offset = np.array([1.0, -1.0, 0.7]) * scale
            direction = -offset / np.linalg.norm(offset)
            up = np.array([0.0, 0.0, 1.0])
            up -= direction * np.dot(up, direction)
            up /= np.linalg.norm(up)
            markup = Element("Markup")
            header = SubElement(markup, "Header")
            file = SubElement(
                header,
                "File",
                IfcProject=stable_guid(f"{after.project_id}/project"),
                isExternal="true",
            )
            _text(file, "Filename", f"{after.equipment.tag.value}_{after.revision}_DRAFT.ifc")
            topic = SubElement(
                markup, "Topic", Guid=topic_id, TopicType="Change", TopicStatus="Open"
            )
            _text(topic, "Title", f"{after.equipment.tag.value} · {path}")
            _text(topic, "Index", index + 1)
            _text(topic, "Labels", "DRAFT")
            _text(topic, "CreationDate", datetime.now(timezone.utc).isoformat())
            _text(topic, "CreationAuthor", author.strip())
            _text(
                topic,
                "Description",
                json.dumps(
                    {
                        "from_revision": before.revision,
                        "to_revision": after.revision,
                        "change": change,
                        "before_sha256": before.fingerprint(),
                        "after_sha256": after.fingerprint(),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            )
            for document in after.documents:
                ref = SubElement(topic, "DocumentReference", isExternal="true")
                _text(ref, "ReferencedDocument", f"urn:sha256:{document.sha256}")
                _text(ref, "Description", f"{document.filename} · revisión {document.revision}")
            view = SubElement(markup, "Viewpoints", Guid=view_id)
            _text(view, "Viewpoint", "viewpoint.bcfv")
            _text(view, "Index", index + 1)
            info = Element("VisualizationInfo", Guid=view_id)
            components = SubElement(info, "Components")
            SubElement(SubElement(components, "Selection"), "Component", IfcGuid=guid)
            SubElement(components, "Visibility", DefaultVisibility="true")
            camera = SubElement(info, "OrthogonalCamera")
            for name, values in (
                ("CameraViewPoint", center + offset),
                ("CameraDirection", direction),
                ("CameraUpVector", up),
            ):
                node = SubElement(camera, name)
                for axis, value in zip("XYZ", values):
                    _text(node, axis, float(value))
            _text(camera, "ViewToWorldScale", scale)
            archive.writestr(f"{topic_id}/markup.bcf", _xml(markup))
            archive.writestr(f"{topic_id}/viewpoint.bcfv", _xml(info))
    return output.getvalue()
