"""Conversión de correcciones numéricas antes de validar el contrato canónico."""

from fastapi import HTTPException

from trazia.units import UnitError, normalize


def normalize_patch(target, body):
    if body.value is None and body.unit is not None and body.unit != target.unit:
        raise HTTPException(422, "Cambiar la unidad requiere indicar también el valor")
    if body.value is None or not isinstance(target.value, (int, float)):
        return body.value, body.unit, body.source
    magnitude = {
        "mm": "length",
        "deg": "angle",
        "bar": "pressure",
        "bara": "pressure",
        "C": "temperature",
        "kg": "mass",
    }.get(target.unit)
    if magnitude is None:
        return body.value, body.unit, body.source
    raw = str(body.value) + (" " + body.unit if body.unit else "")
    try:
        result = normalize(raw, magnitude, decimal=body.decimal_separator, default_unit=target.unit)
        if result.notices:
            raise UnitError("; ".join(result.notices) + "; introduce una unidad explícita")
    except UnitError as exc:
        raise HTTPException(422, str(exc)) from exc
    source = (body.source or target.source).model_copy(
        update={
            "unit_original": result.unit_original,
            "text_original": raw,
            "channel": "humano",
            "grounded": None,
            "strategy": None,
            "model": None,
            "prompt_sha256": None,
        }
    )
    return result.value, result.unit, source
