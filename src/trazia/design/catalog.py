"""Matriz familia × operación × restricciones de la edición asistida (K.0).

Solo se ofrecen operaciones con cobertura verificada por pruebas. Una familia sin entrada
geométrica aquí no admite cambios de geometría todavía; sus atributos técnicos sí.
"""

from dataclasses import asdict, dataclass

from trazia.model import Equipment

# Unidad canónica del contrato → magnitud de trazia.units.normalize.
MAGNITUDES = {
    "mm": "length",
    "deg": "angle",
    "bar": "pressure",
    "bara": "pressure",
    "C": "temperature",
    "kg": "mass",
}

DATUM_GROUND = "suelo"
DATUM_TANGENT = "tangente_inferior"
AZIMUTH_INTERNAL = "interno"
AZIMUTH_NORTH = "norte"


@dataclass(frozen=True)
class Target:
    """Una operación admitida sobre un equipo concreto."""

    target: str  # clave que recibe la API; coincide con la ruta del campo salvo derivadas
    path: str  # campo que se modifica
    label: str
    group: str  # "equipo", "boquilla:<id>" o "atributos"
    unit: str  # unidad canónica del contrato
    magnitude: str | None  # None = texto
    rule: str  # restricción local; las relaciones se validan sobre el lote completo
    minimum: float | None = None
    exclusive_minimum: bool = False
    maximum: float | None = None
    exclusive_maximum: bool = False
    derived: bool = False
    datums: tuple[str, ...] = ()
    affects: tuple[str, ...] = ()  # piezas del IFC que se regeneran
    text: bool = False

    def describe(self, current) -> dict:
        data = asdict(self)
        data["datums"] = list(self.datums)
        data["affects"] = list(self.affects)
        data["current"] = current
        return data


VESSEL = (
    Target(
        "diameter",
        "diameter",
        "Diámetro interior de la virola",
        "equipo",
        "mm",
        "length",
        "Mayor que 2 × espesor de faldón, 2 × profundidad de fondo y cada boquilla radial.",
        0,
        True,
        affects=("shell", "bottom_head", "top_head", "skirt", "*nozzles"),
    ),
    Target(
        "height",
        "height",
        "Longitud entre tangentes (virola)",
        "equipo",
        "mm",
        "length",
        "Positiva. No es la altura total: las boquillas conservan su elevación absoluta.",
        0,
        True,
        affects=("shell", "top_head"),
    ),
    Target(
        "total_height",
        "height",
        "Altura total sobre el suelo",
        "equipo",
        "mm",
        "length",
        "Se resuelve cambiando solo la longitud entre tangentes: "
        "total = faldón + longitud + fondo superior.",
        0,
        True,
        derived=True,
        affects=("shell", "top_head"),
    ),
    Target(
        "head_depth",
        "head_depth",
        "Profundidad de los fondos",
        "equipo",
        "mm",
        "length",
        "Positiva, hasta el radio y menor que la altura del faldón.",
        0,
        True,
        affects=("bottom_head", "top_head"),
    ),
    Target(
        "skirt_height",
        "skirt_height",
        "Altura del faldón (suelo → tangente inferior)",
        "equipo",
        "mm",
        "length",
        "Mayor que la profundidad del fondo. Desplaza la virola; "
        "las boquillas conservan su elevación sobre el suelo.",
        0,
        True,
        affects=("shell", "bottom_head", "top_head", "skirt"),
    ),
    Target(
        "skirt_thickness",
        "skirt_thickness",
        "Espesor del faldón",
        "equipo",
        "mm",
        "length",
        "Positivo y menor que el radio.",
        0,
        True,
        affects=("skirt",),
    ),
)


def _nozzle_targets(equipment: Equipment, nozzle) -> list[Target]:
    group, base = f"boquilla:{nozzle.id}", f"nozzles.{nozzle.id}"
    affects = (nozzle.id, f"{nozzle.id}/flange") if nozzle.flange else (nozzle.id,)
    result = [
        Target(
            f"{base}.diameter",
            f"{base}.diameter",
            f"{nozzle.id} · diámetro",
            group,
            "mm",
            "length",
            "Positivo, menor que el diámetro de la virola y que la brida si existe.",
            0,
            True,
            affects=affects,
        ),
        Target(
            f"{base}.projection",
            f"{base}.projection",
            f"{nozzle.id} · proyección",
            group,
            "mm",
            "length",
            "Positiva y no menor que el espesor de la brida.",
            0,
            True,
            affects=affects,
        ),
    ]
    if nozzle.position is None:
        # Con posición explícita la elevación y el azimut dejan de ser independientes.
        result += [
            Target(
                f"{base}.elevation",
                f"{base}.elevation",
                f"{nozzle.id} · elevación",
                group,
                "mm",
                "length",
                "Sobre el suelo local (z = 0, base del faldón) o sobre la tangente inferior. "
                "El eje debe quedar dentro de la virola con su radio.",
                0,
                datums=(DATUM_GROUND, DATUM_TANGENT),
                affects=affects,
            ),
            Target(
                f"{base}.azimuth",
                f"{base}.azimuth",
                f"{nozzle.id} · azimut",
                group,
                "deg",
                "angle",
                "Convenio interno: 0° = +X, 90° = +Y, antihorario visto desde +Z. "
                "El Norte de planta no está verificado y no se admite como referencia.",
                0,
                maximum=360,
                exclusive_maximum=True,
                datums=(AZIMUTH_INTERNAL,),
                affects=affects,
            ),
        ]
    for name in ("service", "rating"):
        attribute = getattr(nozzle, name)
        if attribute is not None:
            result.append(
                _attribute_target(f"{base}.{name}", f"{nozzle.id} · {name}", group, attribute)
            )
    return result


def _attribute_target(path: str, label: str, group: str, attribute) -> Target:
    numeric = isinstance(attribute.value, (int, float)) and not isinstance(attribute.value, bool)
    magnitude = MAGNITUDES.get(attribute.unit) if numeric else None
    if numeric and magnitude is None:
        rule = "Número en la misma unidad registrada; sin conversión disponible."
    elif magnitude:
        rule = (
            f"Se normaliza a {attribute.unit}; la presión absoluta y la manométrica no se mezclan."
        )
    else:
        rule = "Texto de 1 a 200 caracteres."
    return Target(path, path, label, group, attribute.unit, magnitude, rule, text=not numeric)


def geometry_supported(equipment: Equipment) -> bool:
    return equipment.lod == 1 or equipment.kind in {
        "vertical_vessel",
        "horizontal_vessel",
        "column",
        "tank",
    }


def targets(equipment: Equipment) -> dict[str, Target]:
    from trazia.model import fields

    result: list[Target] = []
    if equipment.kind == "vertical_vessel" and equipment.lod >= 2:
        result += VESSEL
    for nozzle in equipment.nozzles if equipment.lod >= 2 else []:
        result += _nozzle_targets(equipment, nozzle)
    prefixes = ("horizontal.", "column.", "tank.", "envelope.", "platforms.", "ladders.")
    for path, value in fields(equipment).items():
        if path.startswith(prefixes) or ".position." in path or ".direction." in path:
            group = "equipo"
            if path.startswith(("platforms.", "ladders.")):
                group = "pieza:" + ":".join(path.split(".")[:2])
            elif path.startswith("nozzles."):
                group = "boquilla:" + path.split(".")[1]
            signed = ".origin." in path or ".position." in path or ".direction." in path
            minimum = None if signed else 0
            result.append(
                Target(
                    path,
                    path,
                    path,
                    group,
                    value.unit,
                    "length" if value.unit == "mm" else None,
                    "Validación conjunta de dimensiones, soportes y continuidad de la familia.",
                    minimum,
                    not signed and not path.endswith("roof_height"),
                    affects=(
                        (path.split(".")[1],)
                        if path.startswith("nozzles.")
                        else (
                            ("platform-" if path.startswith("platforms.") else "ladder-")
                            + path.split(".")[1],
                        )
                        if path.startswith(("platforms.", "ladders."))
                        else ("*family",)
                    ),
                )
            )
    for key, attribute in equipment.attributes.items():
        result.append(
            _attribute_target(f"attributes.{key}", key.replace("_", " "), "atributos", attribute)
        )
    return {t.target: t for t in result}


def part_capabilities(equipment: Equipment) -> dict:
    supported = equipment.lod >= 2 and equipment.kind in {
        "vertical_vessel",
        "horizontal_vessel",
        "column",
        "tank",
    }
    return {
        "collections": ["nozzles", "platforms", "ladders"] if supported else [],
        "requires_lod3": ["platforms", "ladders"],
        "existing": {
            name: [item.id for item in getattr(equipment, name)]
            for name in ("nozzles", "platforms", "ladders")
        },
        "notice": "Piezas paramétricas, no edición libre. Plataformas y "
        "escaleras requieren aceptar LOD 3.",
    }


FAMILY_MATRIX = {
    "vertical_vessel (LOD 2/3)": "Virola, fondos, faldón, boquillas, plataformas y escaleras.",
    "horizontal_vessel (LOD 2/3)": "Dimensiones y silletas; piezas con posición explícita.",
    "column (LOD 2/3)": "Dimensiones de tramos y continuidad; piezas con posición explícita.",
    "tank (LOD 2/3)": "Dimensiones y altura del techo existente; piezas con posición explícita.",
    "cualquier familia (LOD 1)": "Origen y tamaño de la envolvente; sin piezas detalladas.",
    "pump, compressor, generic": "Envolvente LOD 1 y atributos; no se "
    "inventan interiores mecánicos.",
}
