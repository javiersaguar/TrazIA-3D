"""Configuración común de los puntos de entrada, sin modificar proveedores de Lectura."""

import os


def offline() -> bool:
    return os.getenv("TRAZIA_OFFLINE", "").strip().lower() in {"1", "true", "yes"}


def configure_offline() -> None:
    if offline():
        os.environ["TRAZIA_VISION_OFFLINE"] = "1"


# Módulos que el primer trabajo importaría en frío (medido en WSL el 16/11/2026: scipy.optimize
# ~0,85 s, ifcopenshell ~0,6 s, OpenCV y el pipeline). Precargarlos no cambia ningún resultado.
WARM_MODULES = ("trazia.pipeline", "trazia.ifc", "scipy.optimize", "cv2")


def warm_up() -> list[str]:
    """Carga lo que el primer trabajo pagaría en frío: módulos pesados, el registro de unidades
    y el motor OCR (~3 s al crear las sesiones ONNX). Devuelve lo que quedó cargado.

    Cada pieza es opcional: si falta un extra, se omite sin error. `TRAZIA_WARMUP=0` lo desactiva.
    """
    if os.getenv("TRAZIA_WARMUP", "1").strip().lower() in {"0", "false", "no"}:
        return []
    import importlib

    loaded = []
    for name in WARM_MODULES:
        try:
            importlib.import_module(name)
            loaded.append(name)
        except ImportError:
            pass
    from .units import registry

    registry()
    loaded.append("pint")
    try:
        from .ocr.engine import OcrUnavailable, _rapidocr

        try:
            _rapidocr()
            loaded.append("ocr")
        except OcrUnavailable:
            pass
    except ImportError:
        pass
    return loaded
