"""Configuración común de los puntos de entrada, sin modificar proveedores de Lectura."""

import os


def offline() -> bool:
    return os.getenv("TRAZIA_OFFLINE", "").strip().lower() in {"1", "true", "yes"}


def configure_offline() -> None:
    if offline():
        os.environ["TRAZIA_VISION_OFFLINE"] = "1"
