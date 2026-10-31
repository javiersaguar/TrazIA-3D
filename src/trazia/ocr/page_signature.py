"""Huella conservadora del contenido renderizable; no depende de IDs de objetos PDF."""

import hashlib
import json

from pdfminer.pdftypes import PDFObjRef, PDFStream
from pdfminer.psparser import PSLiteral


def page_signature(page, dpi: int) -> str | None:
    memo, visiting = {}, set()

    def canonical(value):
        if isinstance(value, PDFObjRef):
            key = value.objid
            if key in visiting:
                raise ValueError("Recurso PDF cíclico: usar render normal")
            if key not in memo:
                visiting.add(key)
                memo[key] = canonical(value.resolve())
                visiting.remove(key)
            return memo[key]
        if isinstance(value, PDFStream):
            return {
                "stream": hashlib.sha256(value.get_data()).hexdigest(),
                "attrs": canonical({k: v for k, v in value.attrs.items() if k != "Length"}),
            }
        if isinstance(value, PSLiteral):
            return {"literal": str(value.name)}
        if isinstance(value, bytes):
            return {"bytes": hashlib.sha256(value).hexdigest()}
        if isinstance(value, dict):
            return {str(k): canonical(v) for k, v in sorted(value.items())}
        if isinstance(value, (list, tuple)):
            return [canonical(v) for v in value]
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        raise ValueError("Tipo PDF desconocido: usar render normal")

    try:
        attrs = page.page_obj.attrs
        data = {
            "format": 1,
            "dpi": dpi,
            "renderer": "pdfplumber-default-v1",
            "mediabox": page.mediabox,
            "cropbox": page.cropbox,
            "rotation": page.rotation,
            "contents": canonical(page.page_obj.contents),
            "resources": canonical(page.page_obj.resources),
            "extra": canonical(
                {k: attrs[k] for k in ("Annots", "Group", "UserUnit") if k in attrs}
            ),
        }
        return hashlib.sha256(
            json.dumps(data, sort_keys=True, allow_nan=False).encode()
        ).hexdigest()
    except (ValueError, TypeError, RecursionError, KeyError, AttributeError):
        return None  # La duda invalida la optimización, nunca la evidencia.
