"""Familias industriales y variantes de implantación. Todas las cotas son sintéticas."""

from dataclasses import dataclass

Point = tuple[float, float, float]


@dataclass(frozen=True)
class Part:
    name: str
    low: Point
    high: Point
    axis: str = ""
    ends: tuple[float, float] = (1, 1)


@dataclass(frozen=True)
class Design:
    tag: str
    name: str
    size: Point
    parts: tuple[Part, ...]


@dataclass(frozen=True)
class Family:
    id: str
    name: str
    parts: tuple[str, ...]
    designs: tuple[Design, Design]


def box(name, low, high):
    return Part(name, low, high)


def round_part(name, low, high, axis="z", ends=(1, 1)):
    return Part(name, low, high, axis, ends)


def base(height=7):
    return box("Bancada", (0, 0, 0), (100, 100, height))


def cooler(fans, overhead):
    deck = 65 if overhead else 92
    return (
        box("Haz aleteado", (0, 0, deck - 13), (100, 100, deck)),
        box("Colector", (0, 0, deck - 20), (10, 100, deck - 2)),
        box("Colector opuesto", (90, 0, deck - 20), (100, 100, deck - 2)),
        *(
            box(f"Apoyo {i + 1}", (x, y, 0), (x + 6, y + 8, deck - 13))
            for i, (x, y) in enumerate(((0, 0), (94, 0), (0, 92), (94, 92)))
        ),
        *(
            round_part(
                f"Anillo ventilador {i + 1}",
                (x - 18, 9, deck if overhead else 46),
                (x + 18, 91, 100 if overhead else deck - 13),
            )
            for i, x in enumerate(fans)
        ),
    )


def evaporation(recirculation):
    parts = (
        base(),
        box("Apoyo de calandria", (18, 32, 7), (36, 68, 18)),
        box("Apoyo de separador", (66, 28, 7), (86, 72, 18)),
        round_part("Calandria", (9, 15, 18), (44, 85, 100)),
        round_part("Separador", (55, 6, 18), (96, 94, 67)),
        round_part("Conducto de vapor", (40, 46, 52), (60, 54, 60), "x"),
    )
    if recirculation:
        return parts + (
            round_part("Ramificación inferior", (23, 43, 11), (82, 57, 18), "x"),
            round_part("Cuerpo de recirculación", (48, 33, 7), (69, 67, 24), "x"),
        )
    return parts + (round_part("Distribuidor", (18, 29, 91), (35, 71, 100)),)


def filter_bank(count):
    return (
        base(),
        round_part("Colector", (0, 45, 33), (100, 55, 44), "x"),
        *(
            part
            for i in range(count)
            for part in (
                round_part(f"Carcasa {i + 1}", (14 + 44 * i, 0, 7), (42 + 44 * i, 100, 91)),
                round_part(f"Tapa {i + 1}", (12 + 44 * i, 0, 91), (44 + 44 * i, 100, 100)),
            )
        ),
    )


def cyclone(name, x, span):
    return (
        round_part(f"{name} - cuerpo", (x, 5, 53), (x + span, 95, 85)),
        round_part(f"{name} - cono", (x, 5, 12), (x + span, 95, 53), ends=(0.20, 1)),
        round_part(f"{name} - descarga", (x + 0.4 * span, 41, 0), (x + 0.6 * span, 59, 12)),
        round_part(
            f"{name} - salida superior", (x + 0.32 * span, 34, 85), (x + 0.68 * span, 66, 100)
        ),
        box(f"{name} - entrada lateral", (x, 0, 65), (x + span, 30, 76)),
    )


def dryer(spray):
    if spray:
        return (
            round_part("Cámara superior", (0, 0, 49), (100, 100, 90)),
            round_part("Tolva cónica", (0, 0, 9), (100, 100, 49), ends=(0.26, 1)),
            round_part("Cabezal", (36, 36, 90), (64, 64, 100)),
            round_part("Descarga", (37, 37, 0), (63, 63, 9)),
        )
    return (
        base(),
        box("Plenum", (0, 0, 7), (100, 100, 30)),
        box("Cámara de lecho", (0, 0, 30), (100, 100, 66)),
        box("Cubierta", (0, 0, 66), (100, 100, 82)),
        round_part("Extracción de aire", (56, 19, 82), (68, 81, 100)),
    )


def mixer(injection):
    return (
        round_part("Camisa", (0, 10, 10), (100, 90, 76), "x"),
        round_part("Brida de entrada", (0, 0, 0), (6, 100, 86), "x"),
        round_part("Brida de salida", (94, 0, 0), (100, 100, 86), "x"),
        *((round_part("Ramal de adición", (26, 30, 72), (40, 70, 100)),) if injection else ()),
    )


def dosing(pumps):
    return (
        base(),
        box("Panel de montaje", (0, 86, 7), (100, 100, 100)),
        box("Armario de control", (64, 50, 58), (100, 86, 100)),
        round_part("Colector inferior", (0, 18, 19), (100, 26, 26), "x"),
        *(
            box(f"Bomba dosificadora {i + 1}", (x, 0, 34), (x + 25, 52, 65))
            for i, x in enumerate(pumps)
        ),
    )


def tower(induced):
    fans = (
        (round_part("Ventilador superior", (16, 7, 82), (84, 93, 100)),)
        if induced
        else (round_part("Ventilador frontal", (26, 0, 38), (74, 17, 75), "y"),)
    )
    return (
        box("Balsa", (0, 0, 0), (100, 100, 18)),
        box("Carcasa", (0, 17, 18), (100, 100, 82 if induced else 100)),
        box("Entrada de aire", (6, 0, 23), (94, 17, 37)),
        *fans,
    )


def extraction(cells):
    span = 100 / cells
    return (
        base(),
        *(
            part
            for i in range(cells)
            for part in (
                box(f"Decantador {i + 1}", (i * span, 0, 7), ((i + 1) * span, 100, 55)),
                round_part(
                    f"Cámara de mezcla {i + 1}",
                    (i * span + 2, 8, 55),
                    (i * span + span * 0.35, 52, 82),
                ),
                box(
                    f"Accionamiento {i + 1}",
                    (i * span + 4, 17, 82),
                    (i * span + span * 0.23, 42, 100),
                ),
            )
        ),
    )


FAMILIES = (
    Family(
        "air-cooler",
        "Aeroenfriadores",
        ("Haz aleteado", "Colectores", "Ventiladores", "Apoyos"),
        (
            Design(
                "BC-AC101",
                "Aeroenfriador de tiro inducido",
                (8200, 3300, 3300),
                cooler((50,), True),
            ),
            Design(
                "BC-AC102",
                "Aeroenfriador de tiro forzado doble",
                (11800, 4700, 4100),
                cooler((27, 73), False),
            ),
        ),
    ),
    Family(
        "evaporator",
        "Evaporadores",
        ("Calandria", "Separador", "Conducto de vapor"),
        (
            Design(
                "BC-EV101",
                "Evaporador de película descendente",
                (4100, 9800, 3100),
                evaporation(False),
            ),
            Design(
                "BC-EV102",
                "Evaporador de circulación forzada",
                (5600, 8100, 3700),
                evaporation(True),
            ),
        ),
    ),
    Family(
        "filter",
        "Filtros industriales",
        ("Carcasa", "Tapa", "Colector", "Bancada"),
        (
            Design("BC-FI101", "Filtro de bolsa simple", (880, 1650, 640), filter_bank(1)),
            Design("BC-FI102", "Filtro dúplex de bolsas", (2100, 1950, 820), filter_bank(2)),
        ),
    ),
    Family(
        "centrifuge",
        "Centrífugas",
        ("Carcasa", "Motor", "Soporte", "Descarga"),
        (
            Design(
                "BC-CE101",
                "Centrífuga decantadora horizontal",
                (5200, 1900, 1700),
                (
                    base(),
                    round_part("Carcasa horizontal", (0, 0, 37), (70, 100, 100), "x"),
                    box("Motor", (75, 22, 32), (100, 78, 73)),
                    box("Pedestal del motor", (79, 30, 7), (96, 70, 32)),
                    round_part("Acoplamiento", (70, 39, 54), (75, 61, 67), "x"),
                    box("Descarga", (12, 30, 7), (30, 70, 38)),
                    box("Soporte posterior", (59, 31, 7), (67, 69, 39)),
                ),
            ),
            Design(
                "BC-CE102",
                "Separador centrífugo de discos",
                (1800, 2250, 1600),
                (
                    base(),
                    box("Bastidor", (0, 0, 7), (100, 100, 39)),
                    round_part("Carcasa vertical", (14, 9, 39), (86, 91, 83)),
                    round_part("Conexión superior", (38, 36, 83), (62, 64, 100)),
                ),
            ),
        ),
    ),
    Family(
        "cyclone",
        "Separadores ciclónicos",
        ("Cuerpo", "Cono", "Entrada lateral", "Descarga"),
        (
            Design(
                "BC-CY101", "Ciclón de una cámara", (2300, 5600, 2050), cyclone("Ciclón", 0, 100)
            ),
            Design(
                "BC-CY102",
                "Batería de dos ciclones",
                (5200, 6000, 2300),
                (
                    *cyclone("Ciclón izquierdo", 0, 42),
                    *cyclone("Ciclón derecho", 58, 42),
                    box("Plenum común", (0, 8, 94), (100, 90, 100)),
                ),
            ),
        ),
    ),
    Family(
        "dryer",
        "Secadores industriales",
        ("Cámara", "Alimentación", "Salida de producto"),
        (
            Design("BC-SE101", "Secador por atomización", (5200, 11200, 5200), dryer(True)),
            Design("BC-SE102", "Secador de lecho fluido", (6100, 2900, 1900), dryer(False)),
        ),
    ),
    Family(
        "static-mixer",
        "Mezcladores estáticos",
        ("Camisa", "Bridas", "Ramal opcional"),
        (
            Design("BC-ME101", "Mezclador estático en línea", (1810, 370, 370), mixer(False)),
            Design("BC-ME102", "Mezclador en línea con ramal", (2420, 650, 510), mixer(True)),
        ),
    ),
    Family(
        "dosing-skid",
        "Módulos de dosificación",
        ("Panel", "Bombas", "Colector", "Armario"),
        (
            Design("BC-DO101", "Panel de dosificación simple", (1250, 1720, 700), dosing((13,))),
            Design(
                "BC-DO102", "Panel de dosificación dúplex", (2350, 1880, 1000), dosing((10, 43))
            ),
        ),
    ),
    Family(
        "cooling-tower",
        "Torres de refrigeración",
        ("Balsa", "Carcasa", "Ventilador", "Entrada de aire"),
        (
            Design(
                "BC-TR101",
                "Torre de refrigeración de tiro inducido",
                (4400, 5600, 4200),
                tower(True),
            ),
            Design(
                "BC-TR102",
                "Torre de refrigeración de tiro forzado",
                (3900, 4700, 3600),
                tower(False),
            ),
        ),
    ),
    Family(
        "mixer-settler",
        "Mezcladores-decantadores",
        ("Cámara de mezcla", "Decantador", "Accionamiento"),
        (
            Design(
                "BC-EX101", "Mezclador-decantador de una etapa", (5300, 1850, 2100), extraction(1)
            ),
            Design(
                "BC-EX102",
                "Batería de extracción de dos etapas",
                (10800, 2200, 2400),
                extraction(2),
            ),
        ),
    ),
)
