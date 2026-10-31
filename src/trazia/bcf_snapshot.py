"""BCF 2.1 de una captura real del visor y su cámara; no concede aprobación."""

import base64
import binascii
import io
import math
import zipfile
from datetime import datetime, timezone
from uuid import uuid4
from xml.etree.ElementTree import Element, SubElement, tostring

import numpy as np
from PIL import Image, UnidentifiedImageError


def snapshot_bcf(data):
    try:
        png = base64.b64decode(data.png_base64, validate=True)
        if not png.startswith(b"\x89PNG\r\n\x1a\n") or len(png) > 5 * 1024 * 1024:
            raise ValueError("La captura debe ser un PNG de hasta 5 MiB")
        with Image.open(io.BytesIO(png)) as image:
            if image.format != "PNG" or image.width * image.height > 16_000_000:
                raise ValueError("PNG demasiado grande")
            image.verify()
    except (binascii.Error, UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("Captura PNG no válida") from exc

    def ifc(v):
        x, y, z = v
        if not all(math.isfinite(n) and abs(n) <= 10_000_000 for n in v):
            raise ValueError("Cámara no finita")
        return np.array([x, -z, y], dtype=float)

    eye, target, up = ifc(data.eye), ifc(data.target), ifc(data.up)
    direction = target - eye
    if np.linalg.norm(direction) < 1e-6:
        raise ValueError("La cámara y su objetivo coinciden")
    direction /= np.linalg.norm(direction)
    up -= direction * np.dot(direction, up)
    if np.linalg.norm(up) < 1e-6:
        raise ValueError("Vector vertical de cámara degenerado")
    up /= np.linalg.norm(up)
    topic_id, view_id = str(uuid4()), str(uuid4())

    def node(parent, name, text=None, **attributes):
        result = SubElement(parent, name, **attributes)
        if text is not None:
            result.text = str(text)
        return result

    markup = Element("Markup")
    topic = node(markup, "Topic", Guid=topic_id, TopicType="Viewpoint", TopicStatus="Open")
    node(topic, "Title", "Captura IFC · DRAFT")
    node(topic, "CreationDate", datetime.now(timezone.utc).isoformat())
    node(topic, "CreationAuthor", data.actor)
    node(
        topic,
        "Description",
        "Captura del visor y selección por GUID; "
        "no acredita aprobación ni fidelidad de ingeniería.",
    )
    view = node(markup, "Viewpoints", Guid=view_id)
    node(view, "Viewpoint", "viewpoint.bcfv")
    node(view, "Snapshot", "snapshot.png")
    node(view, "Index", 1)
    info = Element("VisualizationInfo", Guid=view_id)
    components = node(info, "Components")
    node(node(components, "Selection"), "Component", IfcGuid=data.guid)
    node(components, "Visibility", DefaultVisibility="true")
    camera = node(info, "OrthogonalCamera")
    for name, values in (
        ("CameraViewPoint", eye),
        ("CameraDirection", direction),
        ("CameraUpVector", up),
    ):
        vector = node(camera, name)
        for axis, value in zip("XYZ", values):
            node(vector, axis, float(value))
    node(camera, "ViewToWorldScale", data.viewport_height / data.zoom)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "bcf.version",
            b'<?xml version="1.0"?><Version VersionId="2.1">'
            b"<DetailedVersion>2.1</DetailedVersion></Version>",
        )
        archive.writestr(
            f"{topic_id}/markup.bcf", tostring(markup, encoding="utf8", xml_declaration=True)
        )
        archive.writestr(
            f"{topic_id}/viewpoint.bcfv", tostring(info, encoding="utf8", xml_declaration=True)
        )
        archive.writestr(f"{topic_id}/snapshot.png", png)
    return output.getvalue()
