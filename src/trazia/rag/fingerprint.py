"""Huella de página para recuperar el GA más parecido (sin modelo; ColSmol es opcional).

Dos señales, las dos baratas y deterministas:
- visual: densidad de tinta en una rejilla de 48×34 celdas sobre la página A3 apaisada; recoge
  la disposición (dónde están el alzado, la planta, la tabla y el cajetín);
- vocabulario: palabras de las líneas de texto (capa de texto u OCR) sin números; recoge el idioma
  y las cabeceras del proveedor.
"""

import io
import math
import re

import numpy as np
import pdfplumber

GRID = (34, 48)  # filas, columnas
WORD = re.compile(r"[A-ZÁÉÍÓÚÑ]{3,}")


def visual(pdf: bytes, page: int, dpi: int = 40) -> list[float]:
    with pdfplumber.open(io.BytesIO(pdf)) as document:
        image = document.pages[page - 1].to_image(resolution=dpi).original.convert("L")
    ink = np.array(image) < 160
    rows, cols = GRID
    h, w = ink.shape
    cells = [
        ink[r * h // rows : (r + 1) * h // rows, c * w // cols : (c + 1) * w // cols].mean()
        for r in range(rows)
        for c in range(cols)
    ]
    vector = np.sqrt(np.array(cells, dtype=float))  # comprime el peso de las zonas muy densas
    norm = np.linalg.norm(vector)
    return (vector / norm).round(5).tolist() if norm else vector.tolist()


def words(texts: list[str]) -> list[str]:
    return sorted({w for text in texts for w in WORD.findall(text.upper())})


def similarity(a_visual, a_words, b_visual, b_words) -> float:
    """0–1: 70 % disposición visual (coseno) y 30 % vocabulario (Jaccard)."""
    cos = float(np.dot(a_visual, b_visual)) if a_visual and b_visual else 0.0
    sa, sb = set(a_words), set(b_words)
    jaccard = len(sa & sb) / len(sa | sb) if sa | sb else 0.0
    return 0.7 * max(0.0, cos) + 0.3 * jaccard


def cosine(a, b) -> float:
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
    return sum(x * y for x, y in zip(a, b, strict=False)) / (na * nb) if na and nb else 0.0
