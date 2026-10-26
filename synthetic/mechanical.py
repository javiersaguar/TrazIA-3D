"""Equipos mecánicos sintéticos: bomba centrífuga horizontal con bancada (conjunto S-mecánico).

El contrato 0.2 solo modela recipientes verticales; para mecánicos el producto entrega envolvente
(LOD 1) y bridas de conexión. La verdad usa rutas propias: envelope.*, baseplate.height,
shaft_height, nozzles.S|D.* y attributes.*. Origen de coordenadas: extremo de la bancada del lado
de la bomba, en el eje longitudinal, a cota de la cara inferior de la bancada. X a lo largo de la
bancada, Z hacia arriba.
"""

import io
import random
from dataclasses import asdict, dataclass, replace

from reportlab.lib.colors import HexColor
from reportlab.pdfgen.canvas import Canvas

from .render_v2 import PAGE_H, PAGE_W, Overlay, _delta, _footer
from .vendors import (
    DN_STEPS,
    Vendor,
    fmt_length,
    fmt_number,
    fmt_size,
    fmt_weight,
    snap_imperial,
)

INK = HexColor("#1b2a38")
FAINT = HexColor("#8a99a8")
ACCENT = HexColor("#0b6e8f")
MOTORS_KW = (7.5, 11, 15, 18.5, 22, 30, 37, 45, 55, 75, 90, 110, 132, 160)
CASINGS = ("ASTM A216 WCB", "ASTM A351 CF8M", "ASTM A487 CA6NM")
LENGTHS = (
    "base_length",
    "base_width",
    "base_height",
    "shaft_height",
    "motor_half",
    "suction_x",
    "discharge_x",
    "discharge_z",
)


@dataclass(frozen=True)
class PumpSpec:
    tag: str
    base_length: float
    base_width: float
    base_height: float
    shaft_height: float  # eje sobre la cara inferior de la bancada
    motor_half: float  # radio aparente del motor: su parte superior marca la altura total
    suction_dn: int
    suction_x: float  # brida de aspiración frontal, mirando a −X
    discharge_dn: int
    discharge_x: float
    discharge_z: float  # cara de la brida de impulsión, mirando a +Z
    flow: float  # m³/h
    head: float  # m
    motor_power: float  # kW
    operating_weight: float  # kg
    material: str

    @property
    def overall_height(self) -> float:
        return max(self.discharge_z, self.shaft_height + self.motor_half)


def flatten_pump(spec: PumpSpec) -> dict[str, tuple[float | str, str]]:
    return {
        "tag": (spec.tag, "1"),
        "envelope.length": (float(spec.base_length), "mm"),
        "envelope.width": (float(spec.base_width), "mm"),
        "envelope.height": (float(spec.overall_height), "mm"),
        "baseplate.height": (float(spec.base_height), "mm"),
        "shaft_height": (float(spec.shaft_height), "mm"),
        "nozzles.S.diameter": (float(spec.suction_dn), "mm"),
        "nozzles.S.x": (float(spec.suction_x), "mm"),
        "nozzles.S.y": (0.0, "mm"),
        "nozzles.S.z": (float(spec.shaft_height), "mm"),
        "nozzles.D.diameter": (float(spec.discharge_dn), "mm"),
        "nozzles.D.x": (float(spec.discharge_x), "mm"),
        "nozzles.D.y": (0.0, "mm"),
        "nozzles.D.z": (float(spec.discharge_z), "mm"),
        "attributes.flow": (float(spec.flow), "m3/h"),
        "attributes.head": (float(spec.head), "m"),
        "attributes.motor_power": (float(spec.motor_power), "kW"),
        "attributes.operating_weight": (float(spec.operating_weight), "kg"),
        "attributes.material": (spec.material, "1"),
    }


def _snap(spec: PumpSpec, vendor: Vendor) -> PumpSpec:
    if not vendor.imperial:
        return spec
    return replace(spec, **{k: snap_imperial(getattr(spec, k)) for k in LENGTHS})


def random_pump(rng: random.Random, index: int, vendor: Vendor) -> PumpSpec:
    base_height = rng.randrange(150, 301, 10)
    shaft = base_height + rng.randrange(250, 701, 10)
    suction = rng.choice(DN_STEPS[1:])
    discharge = DN_STEPS[max(0, DN_STEPS.index(suction) - 1)]
    suction_x = rng.randrange(80, 301, 10)
    spec = PumpSpec(
        tag=f"P-{300 + index}{rng.choice('AB')}",
        base_length=rng.randrange(1200, 3201, 50),
        base_width=rng.randrange(500, 1201, 50),
        base_height=base_height,
        shaft_height=shaft,
        motor_half=rng.randrange(200, 451, 10),
        suction_dn=suction,
        suction_x=suction_x,
        discharge_dn=discharge,
        discharge_x=suction_x + rng.randrange(150, 401, 10),
        discharge_z=shaft + rng.randrange(250, 501, 10),
        flow=rng.randrange(20, 801, 5),
        head=rng.randrange(20, 151),
        motor_power=rng.choice(MOTORS_KW),
        operating_weight=rng.randrange(400, 6001, 10),
        material=rng.choice(CASINGS),
    )
    return _snap(spec, vendor)


def mutate_pump(rng: random.Random, spec: PumpSpec, vendor: Vendor) -> PumpSpec:
    """Revisión 2: entre 1 y 2 cambios (motor mayor, impulsión mayor, bancada, brida movida)."""
    ops = ["motor", "discharge_dn", "base", "move_discharge"]
    rng.shuffle(ops)
    current = spec
    for op in ops[: rng.randint(1, 2)]:
        if op == "motor" and current.motor_power < MOTORS_KW[-1]:
            power = MOTORS_KW[MOTORS_KW.index(current.motor_power) + 1]
            weight = current.operating_weight + rng.randrange(50, 401, 10)
            current = replace(current, motor_power=power, operating_weight=weight)
        elif op == "discharge_dn" and current.discharge_dn < current.suction_dn:
            current = replace(current, discharge_dn=current.suction_dn)
        elif op == "base":
            current = replace(
                current, base_length=current.base_length + rng.randrange(100, 301, 50)
            )
        elif op == "move_discharge":
            current = replace(current, discharge_x=current.discharge_x + rng.randrange(50, 151, 10))
    if current == spec:
        current = replace(spec, operating_weight=spec.operating_weight + 100)
    return _snap(current, vendor)


def pump_to_dict(spec: PumpSpec) -> dict:
    return asdict(spec)


def pump_from_dict(data: dict) -> PumpSpec:
    return PumpSpec(**data)


# Dibujo --------------------------------------------------------------------------------------
def _hdim(canvas: Canvas, vendor: Vendor, x0: float, x1: float, y: float, mm: float) -> None:
    canvas.setStrokeColor(INK)
    canvas.setFillColor(INK)
    canvas.setLineWidth(0.6)
    canvas.line(x0, y, x1, y)
    for x, d in ((x0, 1), (x1, -1)):
        canvas.line(x, y, x + 6 * d, y + 3)
        canvas.line(x, y, x + 6 * d, y - 3)
        canvas.line(x, y - 6, x, y + 6)
    canvas.setFont("Helvetica", 9)
    canvas.drawCentredString((x0 + x1) / 2, y + 5, fmt_length(mm, vendor))


def _vdim(canvas: Canvas, vendor: Vendor, x: float, z0: float, z1: float, mm: float) -> None:
    canvas.setStrokeColor(INK)
    canvas.setFillColor(INK)
    canvas.setLineWidth(0.6)
    canvas.line(x, z0, x, z1)
    for z, d in ((z0, 1), (z1, -1)):
        canvas.line(x - 3, z + 6 * d, x, z)
        canvas.line(x + 3, z + 6 * d, x, z)
    canvas.setFont("Helvetica", 9)
    if vendor.dim_text == "horizontal":
        canvas.drawRightString(x - 5, (z0 + z1) / 2 - 3, fmt_length(mm, vendor))
        return
    canvas.saveState()
    canvas.translate(x - 4, (z0 + z1) / 2)
    canvas.rotate(90)
    canvas.drawCentredString(0, 0, fmt_length(mm, vendor))
    canvas.restoreState()


def render_pump(
    spec: PumpSpec,
    revision: str,
    vendor: Vendor,
    *,
    changed: set[str] | None = None,
    overlay: Overlay | None = None,
) -> tuple[bytes, dict]:
    changed = changed or set()
    es = vendor.lang == "es"
    buffer = io.BytesIO()
    canvas = Canvas(buffer, pagesize=(PAGE_W, PAGE_H), invariant=1)
    canvas.setTitle(f"Synthetic pump GA {spec.tag} rev {revision}")
    canvas.setStrokeColor(INK)
    canvas.setLineWidth(1.2)
    canvas.rect(20, 20, PAGE_W - 40, PAGE_H - 40)

    # Alzado lateral: escala común para longitud y altura.
    scale = min(560 / spec.base_length, 330 / spec.overall_height)
    x0, z0 = 120, 380
    L, B = spec.base_length * scale, spec.base_height * scale
    shaft = z0 + spec.shaft_height * scale
    canvas.setFillColor(HexColor("#dfe6ec"))
    canvas.rect(x0, z0, L, B, fill=1)
    pump_x = x0 + (spec.suction_x + 0.5 * (spec.discharge_x - spec.suction_x)) * scale
    radius = max(18, (spec.shaft_height - spec.base_height) * scale * 0.6)
    canvas.setFillColor(HexColor("#f1f5f8"))
    canvas.circle(pump_x, shaft, radius, fill=1)
    motor_x = pump_x + radius + 30
    motor_half = spec.motor_half * scale
    canvas.rect(motor_x, shaft - motor_half, max(40, x0 + L - motor_x - 10), 2 * motor_half, fill=1)
    canvas.setStrokeColor(ACCENT)
    canvas.setLineWidth(1.4)
    sx = x0 + spec.suction_x * scale
    canvas.line(sx, shaft - 12, sx, shaft + 12)
    canvas.line(sx, shaft, pump_x - radius, shaft)
    dx, dz = x0 + spec.discharge_x * scale, z0 + spec.discharge_z * scale
    canvas.line(dx - 12, dz, dx + 12, dz)
    canvas.line(dx, dz, dx, shaft + radius * 0.6)
    canvas.setFillColor(ACCENT)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(sx - 14, shaft + 16, "S")
    canvas.drawString(dx + 14, dz + 4, "D")
    canvas.setStrokeColor(FAINT)
    canvas.setDash(6, 3)
    canvas.line(x0 - 20, shaft, x0 + L + 20, shaft)
    canvas.setDash()
    _hdim(canvas, vendor, x0, x0 + L, z0 - 40, spec.base_length)
    _vdim(canvas, vendor, x0 - 30, z0, shaft, spec.shaft_height)
    _vdim(canvas, vendor, x0 - 70, z0, z0 + spec.overall_height * scale, spec.overall_height)
    _vdim(canvas, vendor, x0 + L + 30, z0, z0 + B, spec.base_height)
    if changed & {"envelope.length"}:
        _delta(canvas, x0 + L / 2 + 40, z0 - 30, revision)
    canvas.setFillColor(INK)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(x0, z0 - 70, "ALZADO LATERAL" if es else "SIDE ELEVATION")

    # Planta
    py = 120
    W = spec.base_width * scale
    canvas.setStrokeColor(INK)
    canvas.setLineWidth(1)
    canvas.setFillColor(HexColor("#dfe6ec"))
    canvas.rect(x0, py, L, W, fill=1)
    _vdim(canvas, vendor, x0 + L + 30, py, py + W, spec.base_width)
    canvas.setFillColor(INK)
    canvas.drawString(x0, py - 30, "PLANTA" if es else "PLAN")

    # Tabla de conexiones con coordenadas
    tx, ty = 760, 760
    cols = (
        ("MARCA" if es else "MARK", 45),
        ("SERVICIO" if es else "SERVICE", 85),
        ("DN" if vendor.nozzle_size != "nps" else "NPS", 45),
        ("X", 65),
        ("Y", 50),
        ("Z", 65),
    )
    rows = (
        (
            "S",
            "ASPIRACIÓN" if es else "SUCTION",
            spec.suction_dn,
            spec.suction_x,
            spec.shaft_height,
        ),
        (
            "D",
            "IMPULSIÓN" if es else "DISCHARGE",
            spec.discharge_dn,
            spec.discharge_x,
            spec.discharge_z,
        ),
    )
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(tx, ty + 14, "CONEXIONES" if es else "CONNECTIONS")
    width = sum(w for _, w in cols)
    canvas.setStrokeColor(INK)
    canvas.setLineWidth(0.6)
    canvas.rect(tx, ty - 18 * 3, width, 18 * 3)
    x = tx
    canvas.setFont("Helvetica-Bold", 8)
    for name, w in cols:
        canvas.drawString(x + 4, ty - 12, name)
        x += w
        canvas.line(x, ty, x, ty - 54)
    canvas.setFont("Helvetica", 8)
    for i, (mark, service, dn, nx, nz) in enumerate(rows):
        y = ty - 18 * (i + 1)
        canvas.setFillColor(INK)
        canvas.setStrokeColor(INK)
        canvas.setFont("Helvetica", 8)
        canvas.line(tx, y, tx + width, y)
        values = (
            mark,
            service,
            fmt_size(dn, vendor),
            fmt_length(nx, vendor),
            "0",
            fmt_length(nz, vendor),
        )
        x = tx
        for (_, w), value in zip(cols, values, strict=True):
            canvas.drawString(x + 4, y - 12, value)
            x += w
        if any(p.startswith(f"nozzles.{mark}.") for p in changed):
            _delta(canvas, tx + width + 6, y - 14, revision)

    # Datos de la bomba
    power_decimals = 0 if float(spec.motor_power).is_integer() else 1
    data = (
        ("CAUDAL NOMINAL" if es else "RATED FLOW", f"{fmt_number(spec.flow, vendor)} m³/h", "flow"),
        (
            "ALTURA DIFERENCIAL" if es else "DIFFERENTIAL HEAD",
            f"{fmt_number(spec.head, vendor)} m",
            "head",
        ),
        (
            "POTENCIA MOTOR" if es else "MOTOR RATING",
            f"{fmt_number(spec.motor_power, vendor, power_decimals)} kW",
            "motor_power",
        ),
        (
            "PESO EN OPERACIÓN" if es else "OPERATING WEIGHT",
            fmt_weight(spec.operating_weight, vendor),
            "operating_weight",
        ),
        ("MATERIAL CARCASA" if es else "CASING MATERIAL", spec.material, "material"),
    )
    dy = ty - 120
    canvas.setFillColor(INK)
    canvas.setStrokeColor(INK)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(tx, dy + 14, "DATOS DE LA BOMBA" if es else "PUMP DATA")
    for i, (k, v, key) in enumerate(data):
        y = dy - 16 * i
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(INK)
        canvas.setStrokeColor(INK)
        canvas.line(tx, y - 4, tx + 330, y - 4)
        canvas.drawString(tx + 4, y, k)
        canvas.drawString(tx + 180, y, v)
        if f"attributes.{key}" in changed:
            _delta(canvas, tx + 336, y - 2, revision)
    notes = (
        (
            "NOTAS",
            "1. ORIGEN: EXTREMO DE BANCADA LADO BOMBA, CARA INFERIOR.",
            "2. COTAS SEGÚN UNIDADES DEL PLANO.",
        )
        if es
        else (
            "NOTES",
            "1. DATUM: PUMP END OF BASEPLATE, UNDERSIDE.",
            "2. DIMENSIONS PER DRAWING UNITS.",
        )
    )
    canvas.setFont("Helvetica", 8)
    for i, line in enumerate(notes):
        canvas.drawString(tx, 520 - 13 * i, line)

    # Cajetín
    w = PAGE_W
    canvas.rect(w - 360, 30, 330, 90)
    canvas.line(w - 360, 75, w - 30, 75)
    canvas.line(w - 200, 30, w - 200, 120)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(FAINT)
    canvas.drawString(w - 355, 110, vendor.title_block["equipment"])
    canvas.drawString(w - 195, 110, vendor.title_block["document"])
    canvas.drawString(w - 195, 65, "REV")
    canvas.setFillColor(INK)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(w - 355, 88, spec.tag)
    canvas.drawString(w - 195, 88, f"GAD-{spec.tag}")
    canvas.setFont("Helvetica", 9)
    canvas.drawString(w - 355, 42, "BOMBA CENTRÍFUGA" if es else "CENTRIFUGAL PUMP")
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(w - 195, 42, revision)
    if overlay:
        overlay(canvas, 1)
    _footer(canvas)
    canvas.showPage()
    canvas.save()
    return buffer.getvalue(), {"pages": 1, "ga_pages": [1]}
