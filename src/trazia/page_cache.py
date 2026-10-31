"""Caché compartida de etapas deterministas por página; formato JSON, sin pickle."""

import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4

from PIL import Image

from .ocr.page_signature import page_signature


def path_for(page, namespace, dpi):
    signature = page_signature(page, dpi)
    if signature is None:
        return None
    root = Path(
        os.getenv("TRAZIA_PAGE_CACHE")
        or (Path(os.getenv("TRAZIA_OCR_CACHE", "generated/cache/ocr")) / "page-stages")
    )
    key = hashlib.sha256(f"{namespace}:{signature}".encode()).hexdigest()
    return root / namespace / key[:2] / key


def memo_page(page, namespace, compute, *, dpi=1):
    path = path_for(page, namespace, dpi)
    if path:
        try:
            envelope = json.loads(path.read_text(encoding="utf8"))
            content = envelope["json"]
            if hashlib.sha256(content.encode()).hexdigest() == envelope["sha256"]:
                return json.loads(content)
        except (OSError, ValueError, KeyError, TypeError):
            pass
    result = compute()
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(result, allow_nan=False, sort_keys=True)
        envelope = {"json": content, "sha256": hashlib.sha256(content.encode()).hexdigest()}
        temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
        try:
            temporary.write_text(json.dumps(envelope), encoding="utf8")
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    return result


def render_page(page, dpi):
    path = path_for(page, "raster-v1", dpi)
    if path:
        try:
            with Image.open(path) as image:
                return image.convert("RGB")
        except (OSError, ValueError):
            pass
    image = page.to_image(resolution=dpi).original.convert("RGB")
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
        try:
            image.save(temporary, format="PNG")
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    return image
