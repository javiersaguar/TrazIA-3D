"""Copiloto local, herramientas de lectura y citas verificadas contra su contexto."""

from .models import CopilotAnswer
from .service import CopilotUnavailable, ask

__all__ = ["CopilotAnswer", "CopilotUnavailable", "ask"]
