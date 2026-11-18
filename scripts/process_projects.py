"""Definición de tres complejos sintéticos. Coordenadas y dimensiones en metros."""

from dataclasses import dataclass

Point = tuple[float, float, float]


@dataclass(frozen=True)
class Equipment:
    tag: str
    name: str
    family: str
    xy: tuple[float, float]
    size: Point  # largo X, ancho Y, alto Z
    service: str


@dataclass(frozen=True)
class Line:
    tag: str
    start: str
    end: str
    fluid: str
    dn: int
    rack_y: float
    rack_z: float


@dataclass(frozen=True)
class Change:
    tag: str
    label: str
    property: str
    before: float
    after: float
    unit: str


@dataclass(frozen=True)
class Project:
    id: str
    code: str
    name: str
    setting: str
    description: str
    deck: float
    equipment: tuple[Equipment, ...]
    lines: tuple[Line, ...]
    changes: tuple[Change, ...]


PROJECTS = (
    Project(
        "plataforma-marina",
        "SIM-MAR",
        "Plataforma marina de producción",
        "Mar abierto",
        "Colector de producción, separación de crudo, gas y agua, compresión y bombeo de crudo.",
        7.0,
        (
            Equipment(
                "M-101",
                "Colector de producción",
                "manifold",
                (-26, 2),
                (5, 4, 3),
                "Entrada multifásica",
            ),
            Equipment(
                "V-110",
                "Separador trifásico",
                "horizontal",
                (-15, 2),
                (9, 3.3, 4.2),
                "Separación primaria",
            ),
            Equipment(
                "V-120",
                "Depurador de gas",
                "vertical",
                (-3, 2),
                (3, 3, 7.4),
                "Retención de arrastres",
            ),
            Equipment(
                "K-130",
                "Compresor centrífugo",
                "compressor",
                (7, 2),
                (7, 4.2, 3.9),
                "Gas de exportación",
            ),
            Equipment(
                "E-140",
                "Aeroenfriador de descarga",
                "air-cooler",
                (20, 2),
                (8, 5.6, 5),
                "Enfriamiento de gas",
            ),
            Equipment(
                "P-150", "Bombeo de crudo", "pump", (-3, 15), (6, 3.2, 2.5), "Salida de crudo"
            ),
            Equipment(
                "H-160",
                "Hidrociclones de agua",
                "cyclone",
                (16, 15),
                (6.2, 3.8, 4),
                "Agua producida",
            ),
        ),
        (
            Line("MP-01", "M-101", "V-110", "Mezcla", 550, -4, 3.5),
            Line("GS-02", "V-110", "V-120", "Gas", 400, -6, 4.2),
            Line("GS-03", "V-120", "K-130", "Gas", 450, -4, 3.5),
            Line("GS-04", "K-130", "E-140", "Gas", 450, -5, 4.5),
            Line("OL-05", "V-110", "P-150", "Crudo", 350, 8.5, 2.9),
            Line("WP-06", "V-110", "H-160", "Agua", 300, 10, 3.8),
        ),
        (
            Change("V-110", "Ampliar la virola del separador", "width", 3.3, 4.1, "m"),
            Change("GS-04", "Elevar el tramo en rack del gas de descarga", "rack_z", 4.5, 6.2, "m"),
        ),
    ),
    Project(
        "planta-desierto",
        "SIM-DES",
        "Planta de tratamiento de gas",
        "Desierto",
        "Recepción de gas húmedo, deshidratación, compresión y recuperación de condensados.",
        0.35,
        (
            Equipment(
                "V-210",
                "Separador de entrada",
                "horizontal",
                (-25, 2),
                (8, 3.1, 4.1),
                "Gas húmedo y condensado",
            ),
            Equipment(
                "F-220",
                "Filtro coalescente",
                "vertical",
                (-14, 2),
                (2.6, 2.6, 6),
                "Protección de la columna",
            ),
            Equipment(
                "C-230",
                "Columna de deshidratación TEG",
                "column",
                (-4, 2),
                (3.5, 3.5, 15),
                "Retirada de humedad",
            ),
            Equipment(
                "K-240",
                "Compresor de gas seco",
                "compressor",
                (8, 2),
                (7.8, 4.2, 4.1),
                "Gas tratado",
            ),
            Equipment(
                "E-250",
                "Banco de aeroenfriamiento",
                "air-cooler",
                (22, 2),
                (9.5, 6.4, 5.1),
                "Refrigeración por aire",
            ),
            Equipment(
                "T-260",
                "Tanque de condensado",
                "tank",
                (-14, 17),
                (8.8, 8.8, 6.5),
                "Almacenamiento intermedio",
            ),
            Equipment(
                "P-270",
                "Bombas de condensado",
                "pump",
                (6, 17),
                (6.4, 3.4, 2.3),
                "Trasiego de líquido",
            ),
        ),
        (
            Line("WG-11", "V-210", "F-220", "Gas", 450, -4, 3.8),
            Line("WG-12", "F-220", "C-230", "Gas", 400, -5, 3.8),
            Line("DG-13", "C-230", "K-240", "Gas", 400, -6, 4.6),
            Line("DG-14", "K-240", "E-250", "Gas", 450, -4.5, 4.6),
            Line("CL-15", "V-210", "T-260", "Condensado", 300, 9, 2.8),
            Line("CL-16", "T-260", "P-270", "Condensado", 250, 14, 2.5),
        ),
        (
            Change("C-230", "Elevar la columna y su plataforma de acceso", "height", 15, 17.5, "m"),
            Change("DG-14", "Sustituir el spool y sus bridas", "dn", 450, 600, "mm"),
        ),
    ),
    Project(
        "terminal-costera",
        "SIM-GNL",
        "Terminal costera de almacenamiento",
        "Costa",
        "Muelles, brazos marinos, tanques de GNL, trasiego y tratamiento de gas de evaporación.",
        0.6,
        (
            Equipment(
                "LA-310",
                "Brazo marino de descarga",
                "arm",
                (-27, 2),
                (5, 4, 11),
                "Recepción desde buque",
            ),
            Equipment(
                "M-320",
                "Colector criogénico",
                "manifold",
                (-13, 2),
                (5.5, 4, 3.5),
                "Distribución de GNL",
            ),
            Equipment(
                "T-330",
                "Tanque criogénico A",
                "tank",
                (0, 8),
                (13, 13, 10.5),
                "Contención primaria",
            ),
            Equipment(
                "T-340",
                "Tanque criogénico B",
                "tank",
                (18, 8),
                (13, 13, 10.5),
                "Almacenamiento en paralelo",
            ),
            Equipment(
                "P-350",
                "Bombas de trasiego",
                "pump",
                (-1, -10),
                (6.6, 4, 2.9),
                "Envío a vaporización",
            ),
            Equipment(
                "E-360",
                "Banco de vaporización",
                "vaporizer",
                (14, -10),
                (8, 5.4, 4.8),
                "Entrega de gas",
            ),
            Equipment(
                "K-370",
                "Compresor de gas de evaporación",
                "compressor",
                (27, -10),
                (6.8, 4, 3.8),
                "Retorno de vapores",
            ),
        ),
        (
            Line("LNG-21", "LA-310", "M-320", "GNL", 550, -2.5, 3.2),
            Line("LNG-22", "M-320", "T-330", "GNL", 450, -0.5, 4.2),
            Line("LNG-23", "M-320", "T-340", "GNL", 450, -3.5, 4.2),
            Line("LNG-24", "T-330", "P-350", "GNL", 400, -5.5, 2.8),
            Line("LNG-25", "P-350", "E-360", "GNL", 450, -15, 3.3),
            Line("BOG-26", "T-340", "K-370", "Gas", 300, -5.5, 5.8),
            Line("BOG-27", "K-370", "M-320", "Gas", 350, -18, 5.2),
        ),
        (
            Change(
                "T-340", "Aumentar la envolvente vertical del tanque B", "height", 10.5, 12.1, "m"
            ),
            Change(
                "LNG-21",
                "Desviar el tramo de descarga hacia el borde del muelle",
                "rack_y",
                -2.5,
                -5,
                "m",
            ),
        ),
    ),
    Project(
        "refineria-activa",
        "SIM-REF",
        "Ampliación de una refinería",
        "Complejo industrial",
        "Inserción de un tren de tratamiento entre colectores y equipos que ya están en servicio.",
        0.35,
        (
            Equipment(
                "M-410",
                "Colector de alimentación",
                "manifold",
                (-26, 2),
                (5.8, 4, 3.1),
                "Entrada de destilados",
            ),
            Equipment(
                "P-420", "Bombas de alimentación", "pump", (-16, 2), (6.6, 3.5, 2.4), "Impulsión"
            ),
            Equipment(
                "E-430",
                "Intercambiador de recuperación térmica",
                "horizontal",
                (-5, 2),
                (8.5, 3.3, 4.2),
                "Recuperación de calor",
            ),
            Equipment(
                "R-440",
                "Reactor de tratamiento",
                "column",
                (7, 2),
                (4, 4, 13),
                "Tratamiento de destilado",
            ),
            Equipment(
                "V-450", "Separador de producto", "vertical", (18, 2), (3, 3, 7), "Separación"
            ),
            Equipment(
                "E-460",
                "Aeroenfriador de producto",
                "air-cooler",
                (24, 16),
                (8, 5.6, 4.8),
                "Acondicionamiento",
            ),
            Equipment(
                "T-470", "Tanque de producto", "tank", (4, 17), (10, 10, 7), "Almacenamiento"
            ),
        ),
        (
            Line("LP-31", "M-410", "P-420", "Crudo", 350, -4, 3.1),
            Line("LP-32", "P-420", "E-430", "Crudo", 350, -5, 4.1),
            Line("LP-33", "E-430", "R-440", "Crudo", 400, -6.5, 4.5),
            Line("LP-34", "R-440", "V-450", "Crudo", 420, -4, 3.8),
            Line("LP-35", "V-450", "E-460", "Condensado", 350, 10, 3.9),
            Line("LP-36", "E-460", "T-470", "Condensado", 400, 22, 3.3),
        ),
        (
            Change("R-440", "Elevar la plataforma del reactor", "height", 13, 15, "m"),
            Change("LP-33", "Elevar la conexión con la unidad existente", "rack_z", 4.5, 6, "m"),
        ),
    ),
)
