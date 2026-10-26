"""Interfaz 2 de COORDINACION-BACKEND.md: proveedores de visión intercambiables.

Todos devuelven lo mismo: JSON validado contra el esquema pedido, cajas normalizadas 0–1 (origen
arriba a la izquierda, como `Source.bbox`), tokens, segundos y coste en euros.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol


class VisionError(RuntimeError):
    """El proveedor respondió mal o no está disponible."""


class VisionUnavailable(VisionError):
    """Sin servicio (o modo sin conexión sin respuesta en caché)."""


class PolicyError(PermissionError):
    """La política de confidencialidad (DEC-31) impide enviar este documento al proveedor."""


@dataclass
class ProviderResult:
    data: Any  # JSON validado contra el esquema
    provider: str
    model: str
    prompt_sha256: str
    seconds: float = 0.0
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_eur: float = 0.0
    cached: bool = False
    external: bool = False
    warnings: list[str] = field(default_factory=list)

    def to_cache(self) -> dict:
        return {
            "data": self.data,
            "provider": self.provider,
            "model": self.model,
            "prompt_sha256": self.prompt_sha256,
            "seconds": self.seconds,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "cost_eur": self.cost_eur,
            "external": self.external,
        }

    @classmethod
    def from_cache(cls, raw: dict) -> "ProviderResult":
        return cls(**raw, cached=True)


class VisionProvider(Protocol):
    name: str  # "ollama:qwen3-vl:4b", "gemini:…", "mistral-ocr:…", "plataforma:…"
    external: bool  # True si los datos salen del equipo

    def read(
        self, image_png: bytes, task: str, schema: dict, *, page_ref: str
    ) -> ProviderResult: ...
