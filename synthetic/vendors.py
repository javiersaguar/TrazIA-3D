"""Ocho estilos de «proveedor» para el generador v2 (DEC-21).

Cada estilo cambia lo que cambia de verdad entre fabricantes: idioma de las cabeceras, unidades
(mm, pulgadas, pies-pulgadas), separadores decimales y de miles, posición y orden de la tabla de
boquillas, origen de las cotas de boquilla (suelo o línea de tangencia inferior), convenio de
orientación (antihorario desde +X o rumbo horario desde el norte), cotas con texto girado u
horizontal y cajetín.

Dos estilos están RESERVADOS: nunca se usan para desarrollar ni para entrenar. Solo miden
generalización (conjunto S-reservado). Los proveedores son ficticios.
"""

from dataclasses import dataclass, field
from fractions import Fraction

MM_PER_INCH = 25.4
DN_STEPS = (50, 80, 100, 150, 200, 250, 300)
NPS = {50: '2"', 80: '3"', 100: '4"', 150: '6"', 200: '8"', 250: '10"', 300: '12"'}


@dataclass(frozen=True)
class Column:
    header: str
    key: str  # mark, size, projection, elevation, azimuth, service, rating
    width: int


@dataclass(frozen=True)
class Vendor:
    key: str
    name: str
    reserved: bool
    lang: str  # "en" | "es"
    length_unit: str  # "mm" | "in" | "ftin"
    nozzle_size: str  # "dn" | "dn_prefix" | "nps"
    pressure_unit: str  # "barg" | "bar(g)" | "psig"
    temperature_unit: str  # "C" | "F"
    weight_unit: str  # "kg" | "lb"
    decimal: str  # "." | ","
    thousands: str  # "" | "." | ","
    table_title: str
    columns: tuple[Column, ...]
    table_position: str  # "right" | "left" | "bottom" | "page2"
    elevation_datum: str  # "ground" | "btl"
    azimuth_convention: str  # "ccw_x" | "cw_north"
    dim_text: str  # "rotated" | "horizontal"
    diameter_style: str  # "id_label" | "dim_line" | "id_dots"
    tl_label: str
    design_title: str
    design_labels: dict[str, str]
    skirt_label: str  # con {t}
    title_block: dict[str, str]
    notes: tuple[str, ...]
    views: tuple[str, str]  # alzado, planta
    sheet_label: str = "SHEET"
    services: tuple[str, ...] = field(
        default=("INLET", "OUTLET", "VENT", "DRAIN", "INSTR.", "MANWAY", "SPARE", "RELIEF")
    )

    @property
    def imperial(self) -> bool:
        return self.length_unit in ("in", "ftin")


EN_DESIGN = {
    "design_pressure": "DESIGN PRESSURE",
    "design_temperature": "DESIGN TEMPERATURE",
    "material": "SHELL MATERIAL",
    "operating_weight": "OPERATING WEIGHT",
    "heads": "HEADS",
}
ES_DESIGN = {
    "design_pressure": "PRESIÓN DE DISEÑO",
    "design_temperature": "TEMPERATURA DE DISEÑO",
    "material": "MATERIAL ENVOLVENTE",
    "operating_weight": "PESO EN OPERACIÓN",
    "heads": "FONDOS",
}
ES_SERVICES = (
    "ENTRADA",
    "SALIDA",
    "VENTEO",
    "DRENAJE",
    "INSTR.",
    "BOCA HOMBRE",
    "RESERVA",
    "ALIVIO",
)

VENDORS: dict[str, Vendor] = {
    v.key: v
    for v in (
        # 1 · El estilo del generador v1: inglés, mm, tabla arriba a la derecha.
        Vendor(
            key="atlas",
            name="Atlas Fabricators (ficticio)",
            reserved=False,
            lang="en",
            length_unit="mm",
            nozzle_size="dn",
            pressure_unit="barg",
            temperature_unit="C",
            weight_unit="kg",
            decimal=".",
            thousands="",
            table_title="NOZZLE SCHEDULE",
            columns=(
                Column("MARK", "mark", 50),
                Column("SIZE DN", "size", 70),
                Column("PROJ.", "projection", 70),
                Column("ELEV.", "elevation", 80),
                Column("ORIENT.", "azimuth", 70),
                Column("SERVICE", "service", 120),
            ),
            table_position="right",
            elevation_datum="ground",
            azimuth_convention="ccw_x",
            dim_text="rotated",
            diameter_style="id_label",
            tl_label="T.L.",
            design_title="DESIGN DATA",
            design_labels=EN_DESIGN,
            skirt_label="SKIRT t={t}",
            title_block={"equipment": "EQUIPMENT", "document": "DOCUMENT", "title": "TITLE"},
            notes=(
                "NOTES",
                "1. ALL DIMENSIONS IN MM UNLESS OTHERWISE NOTED.",
                "2. ELEVATIONS FROM GROUND (Z = 0). T.L. = TANGENT LINE.",
                "3. ORIENTATION COUNTER-CLOCKWISE FROM 0°.",
            ),
            views=("ELEVATION", "PLAN · ORIENTATION"),
        ),
        # 2 · Español, coma decimal, punto de miles en pesos, tabla a la izquierda.
        Vendor(
            key="iberica",
            name="Calderería Ibérica (ficticio)",
            reserved=False,
            lang="es",
            length_unit="mm",
            nozzle_size="dn_prefix",
            pressure_unit="bar(g)",
            temperature_unit="C",
            weight_unit="kg",
            decimal=",",
            thousands=".",
            table_title="TABLA DE TOBERAS",
            columns=(
                Column("MARCA", "mark", 50),
                Column("DN", "size", 60),
                Column("SALIENTE", "projection", 70),
                Column("COTA", "elevation", 70),
                Column("ORIENTACIÓN", "azimuth", 80),
                Column("SERVICIO", "service", 110),
            ),
            table_position="left",
            elevation_datum="ground",
            azimuth_convention="ccw_x",
            dim_text="rotated",
            diameter_style="dim_line",
            tl_label="L.T.",
            design_title="DATOS DE DISEÑO",
            design_labels=ES_DESIGN,
            skirt_label="FALDÓN e={t}",
            title_block={"equipment": "EQUIPO", "document": "DOCUMENTO", "title": "TÍTULO"},
            notes=(
                "NOTAS",
                "1. COTAS EN MM SALVO INDICACIÓN.",
                "2. COTAS DE TOBERAS DESDE EL SUELO (Z = 0). L.T. = LÍNEA DE TANGENCIA.",
                "3. ORIENTACIÓN EN SENTIDO ANTIHORARIO DESDE 0°.",
            ),
            views=("ALZADO", "PLANTA · ORIENTACIÓN"),
            sheet_label="HOJA",
            services=ES_SERVICES,
        ),
        # 3 · Pulgadas con fracciones, NPS, psig y °F; orden de columnas distinto.
        Vendor(
            key="gulf",
            name="Gulf Coast Vessels (ficticio)",
            reserved=False,
            lang="en",
            length_unit="in",
            nozzle_size="nps",
            pressure_unit="psig",
            temperature_unit="F",
            weight_unit="lb",
            decimal=".",
            thousands=",",
            table_title="NOZZLE TABLE",
            columns=(
                Column("NOZ", "mark", 45),
                Column("SIZE (NPS)", "size", 70),
                Column("ORIENTATION", "azimuth", 80),
                Column("ELEVATION", "elevation", 80),
                Column("STANDOUT", "projection", 70),
                Column("DESCRIPTION", "service", 100),
            ),
            table_position="right",
            elevation_datum="ground",
            azimuth_convention="ccw_x",
            dim_text="rotated",
            diameter_style="id_label",
            tl_label="T.L.",
            design_title="DESIGN CONDITIONS",
            design_labels={**EN_DESIGN, "material": "MATERIAL (SHELL)"},
            skirt_label="SKIRT t={t}",
            title_block={"equipment": "ITEM NO.", "document": "DWG NO.", "title": "TITLE"},
            notes=(
                "NOTES",
                "1. ALL DIMENSIONS IN INCHES UNLESS NOTED.",
                "2. ELEVATIONS FROM GRADE. T.L. = TANGENT LINE.",
                "3. ORIENTATION COUNTER-CLOCKWISE FROM 0°.",
            ),
            views=("ELEVATION", "ORIENTATION"),
        ),
        # 4 · Pies-pulgadas, columna de rating y servicio delante.
        Vendor(
            key="prairie",
            name="Prairie Process Equipment (ficticio)",
            reserved=False,
            lang="en",
            length_unit="ftin",
            nozzle_size="nps",
            pressure_unit="psig",
            temperature_unit="F",
            weight_unit="lb",
            decimal=".",
            thousands=",",
            table_title="CONNECTION LIST",
            columns=(
                Column("ITEM", "mark", 45),
                Column("SERVICE", "service", 90),
                Column("NPS", "size", 45),
                Column("RATING", "rating", 55),
                Column("ELEV.", "elevation", 80),
                Column("ANGLE", "azimuth", 55),
                Column("PROJ.", "projection", 70),
            ),
            table_position="bottom",
            elevation_datum="ground",
            azimuth_convention="ccw_x",
            dim_text="rotated",
            diameter_style="id_label",
            tl_label="TL",
            design_title="DESIGN DATA",
            design_labels=EN_DESIGN,
            skirt_label="SKIRT t={t}",
            title_block={"equipment": "TAG", "document": "DRAWING", "title": "TITLE"},
            notes=(
                "NOTES",
                "1. DIMENSIONS IN FEET AND INCHES.",
                "2. ELEVATIONS FROM GRADE.",
                "3. ANGLES COUNTER-CLOCKWISE FROM 0°.",
            ),
            views=("ELEVATION", "PLAN"),
        ),
        # 5 · Texto de cotas horizontal, diámetro con línea de cota, tabla abajo.
        Vendor(
            key="nordic",
            name="Nordic Tankworks (ficticio)",
            reserved=False,
            lang="en",
            length_unit="mm",
            nozzle_size="dn",
            pressure_unit="barg",
            temperature_unit="C",
            weight_unit="kg",
            decimal=".",
            thousands=" ",
            table_title="NOZZLES",
            columns=(
                Column("POS", "mark", 45),
                Column("DN", "size", 50),
                Column("LENGTH", "projection", 65),
                Column("LEVEL", "elevation", 65),
                Column("ANGLE", "azimuth", 60),
                Column("PURPOSE", "service", 100),
            ),
            table_position="bottom",
            elevation_datum="ground",
            azimuth_convention="ccw_x",
            dim_text="horizontal",
            diameter_style="dim_line",
            tl_label="T.L.",
            design_title="DESIGN DATA",
            design_labels=EN_DESIGN,
            skirt_label="SKIRT t={t}",
            title_block={"equipment": "EQUIPMENT", "document": "DOCUMENT", "title": "TITLE"},
            notes=(
                "NOTES",
                "1. DIMENSIONS IN MM.",
                "2. LEVELS FROM GROUND (Z = 0).",
                "3. ANGLES COUNTER-CLOCKWISE FROM 0°.",
            ),
            views=("ELEVATION", "ORIENTATION"),
        ),
        # 6 · Español, dos hojas (tabla en la hoja 2), cotas desde la tangente inferior.
        Vendor(
            key="levante",
            name="Equipos de Levante (ficticio)",
            reserved=False,
            lang="es",
            length_unit="mm",
            nozzle_size="dn",
            pressure_unit="bar(g)",
            temperature_unit="C",
            weight_unit="kg",
            decimal=",",
            thousands="",
            table_title="CONEXIONES",
            columns=(
                Column("MARCA", "mark", 50),
                Column("DN", "size", 50),
                Column("SALIENTE", "projection", 70),
                Column("COTA DESDE L.T.I.", "elevation", 110),
                Column("ORIENT.", "azimuth", 60),
                Column("SERVICIO", "service", 110),
            ),
            table_position="page2",
            elevation_datum="btl",
            azimuth_convention="ccw_x",
            dim_text="rotated",
            diameter_style="id_label",
            tl_label="L.T.",
            design_title="DATOS DE DISEÑO",
            design_labels=ES_DESIGN,
            skirt_label="FALDÓN e={t}",
            title_block={"equipment": "EQUIPO", "document": "PLANO", "title": "TÍTULO"},
            notes=(
                "NOTAS",
                "1. COTAS EN MM.",
                "2. COTAS DE CONEXIONES DESDE LA LÍNEA DE TANGENCIA INFERIOR (L.T.I.).",
                "3. ORIENTACIÓN ANTIHORARIA DESDE 0°.",
            ),
            views=("ALZADO", "PLANTA"),
            sheet_label="HOJA",
            services=ES_SERVICES,
        ),
        # 7 · RESERVADO. Rumbo horario desde el norte, cotas desde la tangente inferior.
        Vendor(
            key="meridian",
            name="Meridian Pressure Systems (ficticio)",
            reserved=True,
            lang="en",
            length_unit="mm",
            nozzle_size="dn",
            pressure_unit="barg",
            temperature_unit="C",
            weight_unit="kg",
            decimal=".",
            thousands=",",
            table_title="NOZZLE LIST",
            columns=(
                Column("REF", "mark", 45),
                Column("NB", "size", 45),
                Column("BEARING", "azimuth", 65),
                Column("HEIGHT ABOVE BTL", "elevation", 105),
                Column("OUTSTAND", "projection", 70),
                Column("DUTY", "service", 90),
            ),
            table_position="left",
            elevation_datum="btl",
            azimuth_convention="cw_north",
            dim_text="horizontal",
            diameter_style="id_dots",
            tl_label="BTL/TTL",
            design_title="PROCESS & MECHANICAL DESIGN",
            design_labels={
                "design_pressure": "PRESSURE (DESIGN)",
                "design_temperature": "TEMPERATURE (DESIGN)",
                "material": "PLATE MATERIAL",
                "operating_weight": "WEIGHT - OPERATING",
                "heads": "END TYPE",
            },
            skirt_label="SKIRT {t} THK",
            title_block={"equipment": "TAG No.", "document": "DRG No.", "title": "DESCRIPTION"},
            notes=(
                "GENERAL NOTES",
                "1. DIMENSIONS IN MILLIMETRES.",
                "2. NOZZLE HEIGHTS ABOVE BOTTOM TANGENT LINE (BTL).",
                "3. BEARINGS CLOCKWISE FROM PLANT NORTH.",
            ),
            views=("SIDE VIEW", "PLAN VIEW (N UP)"),
        ),
        # 8 · RESERVADO. Español con tamaños en pulgadas y longitudes en mm, cotas horizontales.
        Vendor(
            key="cantabrico",
            name="Talleres del Cantábrico (ficticio)",
            reserved=True,
            lang="es",
            length_unit="mm",
            nozzle_size="nps",
            pressure_unit="bar(g)",
            temperature_unit="C",
            weight_unit="kg",
            decimal=",",
            thousands=".",
            table_title="RELACIÓN DE TUBULADURAS",
            columns=(
                Column("Nº", "mark", 40),
                Column("SERVICIO", "service", 100),
                Column("Ø NOM.", "size", 55),
                Column("ALTURA", "elevation", 70),
                Column("ÁNGULO", "azimuth", 60),
                Column("LONGITUD", "projection", 70),
            ),
            table_position="bottom",
            elevation_datum="ground",
            azimuth_convention="ccw_x",
            dim_text="horizontal",
            diameter_style="dim_line",
            tl_label="L.T.",
            design_title="CONDICIONES DE DISEÑO",
            design_labels={
                "design_pressure": "PRESIÓN DISEÑO",
                "design_temperature": "TEMP. DISEÑO",
                "material": "MATERIAL VIROLA",
                "operating_weight": "PESO SERVICIO",
                "heads": "FONDOS",
            },
            skirt_label="FALDÓN {t} mm",
            title_block={"equipment": "Nº EQUIPO", "document": "Nº PLANO", "title": "DENOMINACIÓN"},
            notes=(
                "NOTAS",
                "1. COTAS EN MM. DIÁMETROS NOMINALES EN PULGADAS.",
                "2. ALTURAS DESDE EL NIVEL DE SUELO.",
                "3. ÁNGULOS ANTIHORARIOS DESDE 0°.",
            ),
            views=("ALZADO", "PLANTA"),
            sheet_label="HOJA",
            services=ES_SERVICES,
        ),
    )
}

PUBLIC = tuple(k for k, v in VENDORS.items() if not v.reserved)
RESERVED = tuple(k for k, v in VENDORS.items() if v.reserved)


# Formatos ------------------------------------------------------------------------------------
def snap_imperial(mm: float) -> float:
    """Ajusta a la rejilla de 1/16": así el valor en pulgadas del plano es exacto."""
    sixteenths = round(mm / MM_PER_INCH * 16)
    return sixteenths * MM_PER_INCH / 16


def _group(integer: int, sep: str) -> str:
    text = f"{integer:,}"
    return text.replace(",", sep) if sep else text.replace(",", "")


def fmt_number(value: float, v: Vendor, decimals: int = 0, group: bool = False) -> str:
    sign = "-" if value < 0 else ""
    value = abs(value)
    rounded = round(value, decimals)
    integer = int(rounded)
    text = _group(integer, v.thousands) if group else str(integer)
    if decimals:
        frac = f"{rounded - integer:.{decimals}f}"[2:]
        text += v.decimal + frac
    return sign + text


def _inches_fraction(total: Fraction) -> str:
    whole = int(total)
    rest = total - whole
    if rest == 0:
        return f"{whole}"
    return f"{whole} {rest.numerator}/{rest.denominator}" if whole else f"{rest}"


def fmt_length(mm: float, v: Vendor) -> str:
    if v.length_unit == "mm":
        if abs(mm - round(mm)) < 1e-6:
            return str(int(round(mm)))
        return fmt_number(mm, v, 1)
    sixteenths = Fraction(round(mm / MM_PER_INCH * 16), 16)
    if v.length_unit == "in":
        return _inches_fraction(sixteenths) + '"'
    if sixteenths < 12:  # por debajo de un pie se escribe solo en pulgadas
        return _inches_fraction(sixteenths) + '"'
    feet = int(sixteenths // 12)
    inches = sixteenths - 12 * feet
    return f"{feet}'-{_inches_fraction(inches)}\""


def fmt_size(dn: int, v: Vendor) -> str:
    if v.nozzle_size == "nps":
        return NPS[dn]
    return f"DN{dn}" if v.nozzle_size == "dn_prefix" else str(dn)


def fmt_pressure(bar: float, v: Vendor) -> str:
    if v.pressure_unit == "psig":
        return f"{fmt_number(bar * 14.5038, v, 1)} psig"
    return f"{fmt_number(bar, v, 0 if float(bar).is_integer() else 1)} {v.pressure_unit}"


def fmt_temperature(celsius: float, v: Vendor) -> str:
    if v.temperature_unit == "F":
        return f"{fmt_number(celsius * 1.8 + 32, v)} °F"
    return f"{fmt_number(celsius, v)} °C"


def fmt_weight(kg: float, v: Vendor) -> str:
    if v.weight_unit == "lb":
        return f"{fmt_number(kg * 2.204623, v, group=True)} lb"
    return f"{fmt_number(kg, v, group=True)} kg"


def printed_azimuth(azimuth: float, v: Vendor) -> float:
    """Ángulo tal como lo escribe el proveedor. La verdad es antihoraria desde +X."""
    if v.azimuth_convention == "cw_north":
        return (90 - azimuth) % 360
    return azimuth % 360


def fmt_angle(azimuth: float, v: Vendor) -> str:
    return f"{fmt_number(printed_azimuth(azimuth, v), v)}°"


def printed_elevation(elevation: float, skirt_height: float, v: Vendor) -> float:
    return elevation - skirt_height if v.elevation_datum == "btl" else elevation
