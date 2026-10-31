"""Convenio interno explícito y conversión desde un Norte declarado, nunca inferido."""

import math


def internal_azimuth(bearing: float, *, north_deg: float | None, clockwise: bool = True):
    if north_deg is None:
        raise ValueError("Falta declarar el Norte de planta; no se puede convertir el azimut")
    if not all(math.isfinite(v) for v in (bearing, north_deg)):
        raise ValueError("Los ángulos deben ser finitos")
    return (north_deg - bearing if clockwise else north_deg + bearing) % 360


def nozzle_position(radius_mm: float, elevation_mm: float, azimuth_deg: float):
    if not all(math.isfinite(v) for v in (radius_mm, elevation_mm, azimuth_deg)):
        raise ValueError("Las coordenadas deben ser finitas")
    angle = math.radians(azimuth_deg)
    return (radius_mm * math.cos(angle), radius_mm * math.sin(angle), elevation_mm)


def ifc_meters(point_mm):
    if len(point_mm) != 3 or not all(math.isfinite(v) for v in point_mm):
        raise ValueError("Se necesitan tres coordenadas finitas en mm")
    return tuple(v / 1000 for v in point_mm)


def web_coordinates(point_mm):
    x, y, z = ifc_meters(point_mm)
    return x, z, -y


def metadata(north_deg=None):
    if north_deg is not None and not math.isfinite(north_deg):
        raise ValueError("Norte de planta inválido")
    return {
        "OriginInputMM": "[0,0,0] · centro del equipo en cota de apoyo",
        "VerticalAxis": "+Z",
        "AzimuthZero": "+X",
        "AzimuthSense": "CCW viewed from +Z",
        "InputLengthUnit": "mm",
        "IFCLengthUnit": "m",
        "WebAxes": "(x,z,-y), m",
        "PlantNorthDeclared": north_deg is not None,
        "PlantNorthInternalDeg": north_deg % 360 if north_deg is not None else None,
        "TRReferenceVerified": False,
    }
