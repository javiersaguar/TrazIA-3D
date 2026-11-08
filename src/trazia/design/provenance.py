"""Filtro único que separa las órdenes de diseño de las correcciones de extracción.

Una orden de diseño no es evidencia de lo que dice el plano: no alimenta el registro de
correcciones, los ejemplos few-shot, la recalibración ni la prioridad de canales.
"""


def is_design(source) -> bool:
    if source is None:
        return False
    if isinstance(source, dict):
        return source.get("channel") == "diseno" or source.get("design") is not None
    return source.channel == "diseno" or getattr(source, "design", None) is not None


def is_design_field(field) -> bool:
    if field is None:
        return False
    if isinstance(field, dict):
        return is_design(field.get("source"))
    return is_design(field.source)
