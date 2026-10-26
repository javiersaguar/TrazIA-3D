"""Visión (DEC-03, 04 y 31): proveedores intercambiables, caché, política y mosaicos."""

from .base import PolicyError, ProviderResult, VisionError, VisionProvider, VisionUnavailable
from .prompts import TASKS
from .providers import GeminiProvider, MistralOCRProvider, OllamaProvider, get_provider
from .reader import PageReading, read_page, render_page

__all__ = [
    "TASKS",
    "GeminiProvider",
    "MistralOCRProvider",
    "OllamaProvider",
    "PageReading",
    "PolicyError",
    "ProviderResult",
    "VisionError",
    "VisionProvider",
    "VisionUnavailable",
    "get_provider",
    "read_page",
    "render_page",
]
