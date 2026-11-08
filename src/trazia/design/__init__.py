"""Edición asistida del modelo: operaciones de diseño trazables, separadas de la lectura."""

from .catalog import targets
from .proposal import ENGINE_VERSION, OperationInput, ProposalInput, catalog, evaluate
from .provenance import is_design, is_design_field

__all__ = [
    "ENGINE_VERSION",
    "OperationInput",
    "ProposalInput",
    "catalog",
    "evaluate",
    "is_design",
    "is_design_field",
    "targets",
]
