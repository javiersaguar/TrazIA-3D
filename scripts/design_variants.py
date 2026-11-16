"""Variantes del catálogo. Medidas y formas conceptuales de autoría propia."""

from dataclasses import replace

from industrial_designs import (
    Design,
    base,
    box,
    cooler,
    cyclone,
    dosing,
    dryer,
    evaporation,
    extraction,
    mixer,
    round_part,
    tower,
)


def place(parts, low, high, prefix):
    """Repite un módulo en otra posición sin cambiar su lista de componentes."""

    def transform(point):
        return tuple(lo + (hi - lo) * v / 100 for lo, hi, v in zip(low, high, point))

    return tuple(
        replace(
            part, name=f"{prefix} · {part.name}", low=transform(part.low), high=transform(part.high)
        )
        for part in parts
    )


def pot(agitated):
    supports = (
        (
            box("Pata izquierda", (8, 35, 0), (20, 61, 24)),
            box("Pata derecha", (80, 35, 0), (92, 61, 24)),
            box("Pata posterior", (44, 81, 0), (56, 93, 24)),
        )
        if agitated
        else (round_part("Faldón", (2, 2, 0), (98, 98, 30)),)
    )
    return (
        *supports,
        round_part("Fondo inferior", (0, 0, 17), (100, 100, 30), ends=(0.45, 1)),
        round_part("Virola", (0, 0, 30), (100, 100, 77)),
        round_part("Fondo superior", (0, 0, 77), (100, 100, 88), ends=(1, 0.5)),
        round_part("Conexión lateral", (81, 41, 49), (100, 59, 59), "x"),
        box("Accionamiento", (40, 40, 88), (60, 60, 100))
        if agitated
        else round_part("Salida superior", (41, 41, 88), (59, 59, 100)),
        *(
            (round_part("Segunda conexión", (0, 38, 62), (12, 62, 72), "x"),)
            if not agitated
            else ()
        ),
    )


def horizontal(saddles, boot):
    return (
        round_part("Fondo izquierdo", (0, 0, 34), (8, 100, 90), "x", (0.28, 1)),
        round_part("Virola", (8, 0, 34), (92, 100, 90), "x"),
        round_part("Fondo derecho", (92, 0, 34), (100, 100, 90), "x", (1, 0.28)),
        round_part("Entrada", (24, 37, 90), (30, 63, 100)),
        round_part("Salida", (71, 41, 90), (77, 59, 100)),
        *(box(f"Silleta {i + 1}", (x - 4, 18, 0), (x + 4, 82, 40)) for i, x in enumerate(saddles)),
        *((round_part("Bota inferior", (42, 28, 9), (57, 72, 34)),) if boot else ()),
    )


def column(packed):
    head = round_part("Cabezal", (12, 12, 91), (88, 88, 100), ends=(1, 0.42))
    shell = round_part("Columna", (12, 12, 0), (88, 88, 91))
    if packed:
        return (
            shell,
            head,
            *(
                round_part(f"Brida de registro {i + 1}", (0, 0, z), (100, 100, z + 1.5))
                for i, z in enumerate((25, 54, 78))
            ),
            round_part("Entrada lateral", (86, 38, 19), (100, 62, 23), "x"),
        )
    return (
        *place((shell, head), (0, 0, 0), (71, 100, 100), "Torre"),
        round_part("Rehervidor lateral", (75, 31, 0), (100, 72, 37)),
        round_part("Retorno", (60, 45, 30), (88, 58, 35), "x"),
    )


def heat_exchange(vertical):
    if vertical:
        return (
            base(),
            box("Pedestal", (29, 29, 7), (71, 71, 17)),
            round_part("Carcasa vertical", (12, 12, 17), (88, 88, 83)),
            round_part("Brida inferior", (0, 0, 17), (100, 100, 22)),
            round_part("Brida superior", (0, 0, 78), (100, 100, 83)),
            round_part("Canal superior", (23, 23, 83), (77, 77, 100), ends=(1, 0.52)),
        )
    return (
        base(),
        box("Apoyo", (38, 23, 7), (62, 77, 27)),
        round_part("Cuerpo espiral", (3, 17, 20), (97, 83, 100), "y"),
        round_part("Tapa frontal", (0, 0, 16), (100, 18, 100), "y"),
        round_part("Conexión central", (35, 0, 46), (65, 23, 68), "y"),
        round_part("Conexión posterior", (46, 80, 66), (70, 100, 89), "y"),
    )


def storage(dome):
    if dome:
        return (
            round_part("Virola", (0, 0, 0), (100, 100, 79)),
            round_part("Hombro del domo", (0, 0, 79), (100, 100, 91), ends=(1, 0.78)),
            round_part("Corona del domo", (11, 11, 91), (89, 89, 97), ends=(1, 0.32)),
            round_part("Respiradero", (43, 43, 97), (57, 57, 100)),
            round_part("Registro", (7, 11, 14), (26, 28, 24), "y"),
        )
    return (
        base(),
        box("Depósito", (0, 0, 7), (100, 100, 92)),
        box("Cubierta", (0, 0, 92), (100, 100, 95)),
        round_part("Acceso", (19, 23, 95), (35, 47, 100)),
        *(
            box(f"Rigidizador {i + 1}", (x, 0, 7), (x + 3, 8, 92))
            for i, x in enumerate((18, 39, 60, 81))
        ),
    )


def pump(vertical):
    if vertical:
        return (
            round_part("Base de montaje", (0, 0, 0), (100, 100, 8)),
            round_part("Cuerpo vertical", (22, 22, 8), (78, 78, 68)),
            round_part("Motor superior", (18, 18, 68), (82, 82, 100)),
            round_part("Descarga lateral", (63, 36, 45), (100, 64, 57), "x"),
        )
    return (
        base(),
        box("Carcasa de engranajes", (4, 0, 9), (40, 100, 70)),
        round_part("Acoplamiento", (40, 31, 25), (65, 69, 48), "x"),
        round_part("Motor", (65, 18, 9), (100, 82, 65), "x"),
        round_part("Boquilla superior", (12, 30, 70), (31, 70, 100)),
    )


def centrifugal_compressor():
    return (
        base(),
        box("Soporte central", (11, 16, 7), (47, 84, 25)),
        round_part("Carcasa centrífuga", (0, 0, 24), (49, 100, 82), "x"),
        round_part("Descarga", (16, 31, 75), (26, 66, 100)),
        round_part("Acoplamiento", (49, 38, 44), (68, 62, 62), "x"),
        round_part("Accionamiento", (68, 15, 23), (100, 85, 83), "x"),
        box("Pedestal del accionamiento", (76, 33, 7), (92, 67, 28)),
    )


BASE_FAMILY_NAMES = {
    "vertical": "Recipientes verticales",
    "horizontal": "Recipientes horizontales",
    "column": "Columnas",
    "exchanger": "Intercambiadores",
    "tank": "Tanques",
    "pump": "Bombas",
    "compressor": "Compresores",
    "generic": "Envolventes de reserva",
}


VARIANTS = {
    "vertical": (
        Design("BC-V103", "Recipiente agitado sobre patas", (1950, 5100, 1950), pot(True)),
        Design("BC-V104", "Separador vertical de doble entrada", (2400, 7900, 2400), pot(False)),
    ),
    "horizontal": (
        Design(
            "BC-H103",
            "Separador horizontal con bota",
            (7900, 3250, 2350),
            horizontal((23, 78), True),
        ),
        Design(
            "BC-H104",
            "Recipiente horizontal sobre tres silletas",
            (11400, 3650, 2750),
            horizontal((19, 50, 81), False),
        ),
    ),
    "column": (
        Design("BC-C103", "Columna de relleno con registros", (2600, 14300, 2600), column(True)),
        Design("BC-C104", "Columna con rehervidor lateral", (4500, 18700, 3000), column(False)),
    ),
    "exchanger": (
        Design(
            "BC-E103", "Intercambiador tubular vertical", (1900, 5800, 1900), heat_exchange(True)
        ),
        Design(
            "BC-E104", "Intercambiador espiral compacto", (2250, 2530, 1290), heat_exchange(False)
        ),
    ),
    "tank": (
        Design(
            "BC-T103", "Tanque atmosférico de techo abovedado", (9900, 7800, 9900), storage(True)
        ),
        Design(
            "BC-T104", "Tanque rectangular con rigidizadores", (6100, 2700, 3900), storage(False)
        ),
    ),
    "pump": (
        Design("BC-P103", "Bomba horizontal de engranajes", (1760, 1200, 840), pump(False)),
        Design("BC-P104", "Bomba vertical multietapa", (920, 2150, 920), pump(True)),
    ),
    "compressor": (
        Design(
            "BC-K103",
            "Compresor centrífugo de una etapa",
            (3540, 2340, 1700),
            centrifugal_compressor(),
        ),
        Design(
            "BC-K104",
            "Módulo de compresión dúplex",
            (6800, 2740, 3400),
            (
                base(4),
                *place(centrifugal_compressor(), (0, 0, 4), (100, 44, 100), "Tren A"),
                *place(centrifugal_compressor(), (0, 56, 4), (100, 100, 100), "Tren B"),
            ),
        ),
    ),
    "generic": (
        Design(
            "BC-G103",
            "Envolvente de caseta con marquesina",
            (5300, 3150, 2900),
            (
                base(),
                box("Volumen de caseta", (4, 18, 7), (96, 100, 91)),
                box("Volumen de marquesina", (0, 0, 91), (100, 100, 100)),
            ),
        ),
        Design(
            "BC-G104",
            "Reserva de implantación en dos niveles",
            (6300, 4800, 3200),
            (
                box("Nivel inferior", (0, 0, 0), (100, 100, 54)),
                box("Nivel superior retranqueado", (34, 13, 54), (100, 100, 100)),
            ),
        ),
    ),
    "air-cooler": (
        Design(
            "BC-AC103",
            "Aeroenfriador inducido de tres ventiladores",
            (16500, 4900, 4750),
            cooler((19, 50, 81), True),
        ),
        Design(
            "BC-AC104",
            "Dos haces de aeroenfriamiento en paralelo",
            (11900, 4950, 7800),
            (
                *place(cooler((28, 72), False), (0, 0, 0), (100, 42, 100), "Haz A"),
                *place(cooler((28, 72), False), (0, 58, 0), (100, 100, 100), "Haz B"),
            ),
        ),
    ),
    "evaporator": (
        Design(
            "BC-EV103",
            "Evaporador de doble efecto",
            (9200, 10000, 4450),
            (
                *place(evaporation(False), (0, 0, 0), (46, 100, 100), "Efecto 1"),
                *place(evaporation(False), (52, 0, 0), (100, 100, 88), "Efecto 2"),
                round_part("Colector entre efectos", (35, 44, 50), (65, 56, 57), "x"),
            ),
        ),
        Design(
            "BC-EV104",
            "Evaporador compacto con separador elevado",
            (4850, 11350, 3400),
            (
                base(),
                box("Bastidor del separador", (55, 28, 7), (93, 72, 56)),
                round_part("Calandria", (2, 18, 7), (42, 82, 86)),
                round_part("Separador elevado", (53, 0, 54), (100, 100, 100)),
                round_part("Interconexión", (36, 42, 65), (61, 58, 71), "x"),
            ),
        ),
    ),
    "filter": (
        Design(
            "BC-FI103",
            "Banco de filtros de tres carcasas",
            (3000, 2070, 1000),
            (
                base(),
                round_part("Colector", (0, 43, 39), (100, 57, 47), "x"),
                *(
                    round_part(f"Carcasa {i + 1}", (x, 0, 7), (x + 23, 100, 90))
                    for i, x in enumerate((3, 38, 73))
                ),
                *(
                    round_part(f"Tapa {i + 1}", (x, 0, 90), (x + 27, 100, 100))
                    for i, x in enumerate((1, 36, 71))
                ),
            ),
        ),
        Design(
            "BC-FI104",
            "Filtro horizontal de cartuchos",
            (1940, 1310, 910),
            (
                base(),
                box("Soporte", (20, 23, 7), (72, 77, 38)),
                round_part("Carcasa", (0, 4, 31), (92, 96, 91), "x"),
                round_part("Tapa extraíble", (90, 0, 24), (100, 100, 98), "x"),
                round_part("Entrada superior", (27, 35, 91), (38, 65, 100)),
            ),
        ),
    ),
    "centrifuge": (
        Design(
            "BC-CE103",
            "Centrífuga vertical con descarga inferior",
            (2820, 2800, 1850),
            (
                base(),
                box("Bastidor", (0, 11, 7), (100, 89, 33)),
                round_part("Canasta exterior", (12, 0, 33), (79, 100, 86)),
                round_part("Tapa", (12, 0, 86), (79, 100, 95)),
                box("Módulo de accionamiento", (74, 25, 33), (100, 75, 100)),
            ),
        ),
        Design(
            "BC-CE104",
            "Decantador con motor acoplado",
            (5750, 2400, 1980),
            (
                base(),
                box("Apoyo", (15, 24, 7), (92, 76, 26)),
                round_part("Tambor cilíndrico", (0, 0, 26), (52, 100, 90), "x"),
                round_part("Tramo cónico", (52, 0, 26), (70, 100, 90), "x", (1, 0.46)),
                round_part("Acoplamiento", (70, 38, 47), (76, 62, 69), "x"),
                round_part("Motor", (76, 21, 26), (100, 79, 90), "x"),
                round_part("Admisión superior", (29, 39, 90), (38, 61, 100)),
            ),
        ),
    ),
    "cyclone": (
        Design(
            "BC-CY103",
            "Separador multiciclónico de tres cámaras",
            (5950, 6400, 2750),
            (
                *(
                    part
                    for i, x in enumerate((0, 36, 72))
                    for part in cyclone(f"Ciclón {i + 1}", x, 28)
                ),
                box("Conducto común", (0, 10, 92), (100, 90, 100)),
            ),
        ),
        Design(
            "BC-CY104",
            "Ciclón con tolva de recogida",
            (2800, 7650, 2480),
            (
                *place(cyclone("Ciclón", 0, 100), (0, 0, 22), (100, 100, 100), "Superior"),
                round_part("Tolva", (21, 21, 8), (79, 79, 22), ends=(1, 0.33)),
                box("Depósito inferior", (21, 21, 0), (79, 79, 9)),
            ),
        ),
    ),
    "dryer": (
        Design(
            "BC-SE103",
            "Secador rotativo sobre rodillos",
            (10500, 4550, 3350),
            (
                base(),
                round_part("Tambor", (0, 5, 21), (100, 95, 91), "x"),
                *(
                    round_part(f"Aro {i + 1}", (x, 0, 17), (x + 4, 100, 95), "x")
                    for i, x in enumerate((22, 72))
                ),
                *(
                    box(f"Apoyo {i + 1}", (x, 20, 7), (x + 12, 80, 26))
                    for i, x in enumerate((18, 68))
                ),
                round_part("Salida de aire", (82, 35, 89), (91, 65, 100)),
            ),
        ),
        Design(
            "BC-SE104",
            "Lecho fluido con módulo de salida",
            (7950, 3180, 2610),
            (
                *place(dryer(False), (0, 0, 0), (77, 100, 100), "Principal"),
                box("Módulo de salida", (77, 8, 7), (100, 92, 67)),
                box("Cubierta de descarga", (77, 8, 67), (100, 92, 74)),
            ),
        ),
    ),
    "static-mixer": (
        Design(
            "BC-ME103",
            "Mezclador estático vertical",
            (740, 2450, 725),
            (
                round_part("Tubo vertical", (13, 13, 5), (87, 87, 95)),
                round_part("Brida inferior", (0, 0, 0), (100, 100, 5)),
                round_part("Brida superior", (0, 0, 95), (100, 100, 100)),
                round_part("Ramal lateral", (77, 34, 28), (100, 66, 38), "x"),
            ),
        ),
        Design(
            "BC-ME104",
            "Mezclador en línea de dos etapas",
            (4350, 820, 710),
            (
                *place(mixer(True), (0, 0, 0), (47, 100, 100), "Etapa A"),
                *place(mixer(True), (53, 0, 0), (100, 100, 100), "Etapa B"),
                round_part("Manguito intermedio", (47, 10, 10), (53, 90, 76), "x"),
            ),
        ),
    ),
    "dosing-skid": (
        Design(
            "BC-DO103",
            "Dosificación con depósito de preparación",
            (3100, 2200, 1350),
            (
                *place(dosing((10, 43)), (0, 0, 0), (62, 100, 100), "Panel"),
                *place(storage(True), (62, 5, 0), (100, 95, 72), "Depósito"),
            ),
        ),
        Design(
            "BC-DO104",
            "Módulo de dosificación con dos circuitos",
            (4900, 2350, 1750),
            (
                base(5),
                *place(dosing((13,)), (0, 0, 5), (48, 100, 100), "Circuito A"),
                *place(dosing((10, 43)), (52, 0, 5), (100, 100, 100), "Circuito B"),
            ),
        ),
    ),
    "cooling-tower": (
        Design(
            "BC-TR103",
            "Torre inducida de dos celdas",
            (9850, 6150, 5300),
            (
                *place(tower(True), (0, 0, 0), (50, 100, 100), "Celda A"),
                *place(tower(True), (50, 0, 0), (100, 100, 100), "Celda B"),
            ),
        ),
        Design(
            "BC-TR104",
            "Torre de tiro forzado con ventilación doble",
            (6550, 4850, 4560),
            (
                *tower(False)[:-1],
                round_part("Ventilador izquierdo", (7, 0, 36), (41, 17, 76), "y"),
                round_part("Ventilador derecho", (59, 0, 36), (93, 17, 76), "y"),
            ),
        ),
    ),
    "mixer-settler": (
        Design(
            "BC-EX103", "Batería de extracción de tres etapas", (15700, 2530, 2740), extraction(3)
        ),
        Design(
            "BC-EX104",
            "Mezclador-decantador con depósito auxiliar",
            (7400, 2750, 2680),
            (
                *place(extraction(1), (0, 0, 0), (72, 100, 100), "Extractor"),
                round_part("Depósito auxiliar", (77, 14, 0), (100, 86, 75)),
                round_part("Interconexión", (68, 44, 33), (86, 56, 43), "x"),
            ),
        ),
    ),
}
