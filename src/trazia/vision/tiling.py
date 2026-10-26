"""Troceado de páginas A3 en mosaicos con solape y reproyección de cajas (DEC-04).

Un modelo de visión pequeño reescala la imagen: una hoja A3 entera pierde las cotas de 9 pt. Se
trocea en mosaicos con solape (para no cortar un texto sin verlo entero en algún mosaico), se lee
cada uno y las cajas se devuelven en coordenadas de página. Los duplicados de las zonas de solape
se funden por solape de cajas y texto igual.
"""

import io
from dataclasses import dataclass

from PIL import Image


@dataclass(frozen=True)
class Tile:
    image: Image.Image
    box: tuple[float, float, float, float]  # región de la página, normalizada 0–1

    def png(self) -> bytes:
        buffer = io.BytesIO()
        self.image.save(buffer, "PNG", optimize=True)
        return buffer.getvalue()

    def to_page(self, box: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
        """Caja normalizada dentro del mosaico → caja normalizada en la página."""
        x0, y0, x1, y1 = self.box
        w, h = x1 - x0, y1 - y0
        return (x0 + box[0] * w, y0 + box[1] * h, x0 + box[2] * w, y0 + box[3] * h)


def tiles(page: Image.Image, *, size: int = 1280, overlap: float = 0.15) -> list[Tile]:
    """Mosaicos de `size` px como máximo con `overlap` de solape entre vecinos."""
    width, height = page.size
    step = max(1, int(size * (1 - overlap)))

    def starts(total: int) -> list[int]:
        if total <= size:
            return [0]
        out = list(range(0, total - size, step))
        out.append(total - size)
        return sorted(set(out))

    out = []
    for top in starts(height):
        for left in starts(width):
            right, bottom = min(width, left + size), min(height, top + size)
            crop = page.crop((left, top, right, bottom))
            out.append(Tile(crop, (left / width, top / height, right / width, bottom / height)))
    return out


def iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def merge_duplicates(items: list[dict], *, threshold: float = 0.3) -> list[dict]:
    """Funde lecturas repetidas en zonas de solape (misma lectura, cajas que se solapan).

    Se queda la de caja más grande: en el borde de un mosaico el texto suele salir cortado.
    """
    kept: list[dict] = []
    for item in sorted(items, key=lambda i: -_area(i["box"])):
        text = _norm(item.get("text", ""))
        if any(
            _norm(k.get("text", "")) == text and iou(k["box"], item["box"]) > threshold
            for k in kept
        ):
            continue
        kept.append(item)
    return sorted(kept, key=lambda i: (i["box"][1], i["box"][0]))


def _area(box) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def _norm(text: str) -> str:
    return "".join(text.split()).upper()
