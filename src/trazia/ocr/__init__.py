"""OCR de páginas sin capa de texto (DEC-06): líneas con caja normalizada que reutiliza B.

- RapidOCR (Apache-2.0, ONNX en CPU) por defecto. Se instala con el extra `ocr`.
- Caché por hash de la imagen y del motor en `generated/cache/ocr` (o `TRAZIA_OCR_CACHE`): una
  página escaneada se reconoce una sola vez aunque la lean varias estrategias.
- `TRAZIA_OCR_OFFLINE=1`: sin motor ni respuesta en caché, la página se devuelve vacía con aviso.

Las líneas llevan como confianza la del reconocedor; el localizador dice «OCR» para que la
procedencia sea visible en la revisión.
"""

from .engine import OcrLine, OcrUnavailable, ocr_image, ocr_pdf_lines

__all__ = ["OcrLine", "OcrUnavailable", "ocr_image", "ocr_pdf_lines"]
