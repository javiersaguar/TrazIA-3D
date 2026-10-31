"""Extractor de GA dibujados con capa de texto (o con líneas de OCR): estrategia B, sin IA.

Lee lo que un delineante busca primero en un plano de disposición general:
- tabla de boquillas: cada columna se reconoce por su cabecera (español o inglés) y cada celda se
  asigna a la columna que tiene encima, no por orden;
- datos de diseño: etiqueta y valor en la misma fila, con psig, °F, lb y coma decimal;
- diámetro, espesor de faldón y tag del cajetín;
- cotas verticales del alzado, con el texto girado u horizontal, asignadas por su altura frente a
  las líneas de tangencia y comprobadas con la cadena faldón + virola + fondo = total.

Si las cotas de boquilla van referidas a la tangente inferior (lo dice una nota o la cabecera),
se les suma el faldón y la transformación queda explicada en el candidato.

Vocabulario: sale de los seis proveedores públicos del generador v2 (S-dev) y de términos
genéricos de calderería. A propósito NO incluye el de los dos proveedores reservados, que miden
generalización (docs/BENCH.md). Validado solo con datos sintéticos.
"""

import itertools
import re
from collections import defaultdict
from dataclasses import dataclass

from ..extraction import Candidate
from ..ingest import Bundle, EvidenceLine
from ..model import Source
from .units import (
    parse_angle,
    parse_length,
    parse_length_any_direction,
    parse_nominal_size,
    parse_pressure,
    parse_temperature,
    parse_weight,
)

MARK = re.compile(r"^[A-Z]{1,2}\d{1,3}[A-Z]?$")
MARK_HEADER = re.compile(r"^(MARK|MARCA|NOZ\.?|ITEM|POS\.?)$")
COLUMNS = (
    ("diameter", re.compile(r"\b(SIZE|DN|NPS)\b")),
    ("projection", re.compile(r"\b(PROJ|SALIENTE|STANDOUT|LENGTH)")),
    ("elevation", re.compile(r"\b(ELEV|COTA|LEVEL)")),
    ("azimuth", re.compile(r"\b(ORIENT|AZIM|ANGLE)")),
)
DESIGN = (
    ("design_pressure", re.compile(r"DESIGN\s+PRESS|PRESI[OÓ]N\s+DE\s+DISE")),
    ("design_temperature", re.compile(r"DESIGN\s+TEMP|TEMPERATURA\s+DE\s+DISE")),
    ("operating_weight", re.compile(r"OPERAT\w*\s+WEIGHT|PESO\s+EN\s+OPERACI")),
    ("material", re.compile(r"\bMATERIAL\b")),
)
TANGENTS = {"T.L.", "TL", "L.T."}
TAG_LABELS = {"EQUIPMENT", "EQUIPO", "ITEMNO", "TAG"}  # comparadas sin espacios ni puntos
DIAMETER = re.compile(r"^(?:I\.?D\.?|Ø|DIA\.?)\s*[:=]?\s*(.+)$", re.I)
# El OCR lee «Ø3700» como «03700»: en un plano no se escriben ceros a la izquierda.
OCR_DIAMETER = re.compile(r"^[0OΦφ⌀]\s?([1-9]\d{2,4})$")
SKIRT = re.compile(r"^(?:SKIRT|FALD[OÓ]N)\s*(?:t|e)?\s*=?\s*(.+?)\s*(?:THK\.?|mm)?$", re.I)
SPANISH = re.compile(r"DISEÑO|NOTAS|COTAS|TOBERAS|CONEXIONES|FALDÓN|PLANO")
BTL_NOTE = re.compile(r"TANGENCIA\s+INFERIOR|BOTTOM\s+TANGENT|L\.T\.I\.")
DIMENSION_TEXT = re.compile(r"^[\d\s'\"/\-.,]+$")
ROW_TOLERANCE = 0.006  # fracción de la altura de página


@dataclass(frozen=True)
class DocContext:
    decimal: str  # "," en documentos en español
    btl_datum: bool  # cotas de boquilla desde la tangente inferior


def _center_y(line: EvidenceLine) -> float:
    _, y0, _, y1 = line.source.bbox
    return (y0 + y1) / 2


def _rows(lines: list[EvidenceLine]) -> list[list[EvidenceLine]]:
    rows: list[list[EvidenceLine]] = []
    for line in sorted(lines, key=_center_y):
        if rows and abs(_center_y(rows[-1][0]) - _center_y(line)) <= ROW_TOLERANCE:
            rows[-1].append(line)
        else:
            rows.append([line])
    return [sorted(r, key=lambda line: line.source.bbox[0]) for r in rows]


def _first_word(text: str) -> str:
    words = text.strip().upper().split()
    return words[0] if words else ""


def _source(line: EvidenceLine, confidence: float, locator: str) -> Source:
    return line.source.model_copy(update={"confidence": confidence, "locator": locator})


def _candidate(path, value, unit, line, confidence, locator, **extra) -> Candidate:
    return Candidate(
        path=path,
        value=value,
        unit=unit,
        source=_source(line, confidence, locator),
        text_original=line.text,
        **extra,
    )


def document_context(lines: list[EvidenceLine]) -> DocContext:
    text = " ".join(line.text.upper() for line in lines)
    return DocContext(
        decimal="," if SPANISH.search(text) else ".",
        btl_datum=bool(BTL_NOTE.search(text)),
    )


class DrawingExtractor:
    def extract(self, bundles: list[Bundle]) -> list[Candidate]:
        result: list[Candidate] = []
        for bundle in bundles:
            if bundle.media_type != "pdf":
                continue
            lines = [line for line in bundle.lines if line.source.bbox is not None]
            ctx = document_context(lines)
            pages = defaultdict(list)
            for line in lines:
                pages[line.source.page].append(line)
            found: list[Candidate] = []
            for page_lines in pages.values():
                from .mechanical import pump_envelope

                mechanical = pump_envelope(page_lines, ctx.decimal)
                if mechanical is not None:
                    found += mechanical
                    found += self._design_data(_rows(page_lines), ctx)
                    continue
                rows = _rows(page_lines)
                table, region = self._nozzle_table(rows, ctx)
                found += table
                found += self._design_data(rows, ctx)
                labels = self._labels(page_lines, ctx)
                found += labels
                diameter = next((c.value for c in labels if c.path == "diameter"), None)
                two_to_one = any("2:1" in line.text for line in page_lines)
                found += self._vertical_dimensions(
                    page_lines, ctx, region, diameter if two_to_one else None
                )
            result += self._apply_datum(found, ctx)
        return result

    # Tabla de boquillas ---------------------------------------------------------------------
    def _nozzle_table(self, rows, ctx: DocContext):
        out: list[Candidate] = []
        region: list[tuple[float, float, float, float]] = []
        for index, row in enumerate(rows):
            start = next(
                (i for i, c in enumerate(row) if MARK_HEADER.match(_first_word(c.text))), None
            )
            if start is None:
                continue
            # La cabecera son celdas contiguas: lo que queda más allá de un hueco grande es otro
            # bloque del plano (notas, cajetín) que comparte la misma altura.
            header = [row[start]]
            for cell in row[start + 1 :]:
                if cell.source.bbox[0] - header[-1].source.bbox[2] > 0.06:
                    break
                header.append(cell)
            columns = self._columns(header)
            if not any(key == "elevation" for _, key in columns):
                continue
            left = header[0].source.bbox[0] - 0.01
            right = max(c.source.bbox[2] for c in header) + 0.06
            mark_x = header[0].source.bbox[0]
            top, bottom = header[0].source.bbox[1], header[0].source.bbox[3]
            for data_row in rows[index + 1 :]:
                cells = [c for c in data_row if left <= c.source.bbox[0] <= right]
                if not cells:
                    continue
                first = min(cells, key=lambda c: abs(c.source.bbox[0] - mark_x))
                mark = first.text.strip().upper().replace(" ", "")
                if not MARK.match(mark) and MARK.match(mark[::-1]):
                    mark = mark[::-1]  # OCR: «4N» por «N4», mismo texto con el orden cambiado
                aligned = abs(first.source.bbox[0] - mark_x) <= 0.02
                if not (MARK.match(mark) and aligned):
                    values = [c for c in cells if self._column_for(c, columns) is not None]
                    if len(values) >= 2:
                        continue  # fila de la tabla con la marca ilegible: no se inventa
                    break
                bottom = max(bottom, *(c.source.bbox[3] for c in cells))
                for cell in cells:
                    if cell is first:
                        continue
                    key = self._column_for(cell, columns)
                    if key is None:
                        continue
                    parsed = self._cell_value(key, cell.text, ctx)
                    if parsed is None:
                        continue
                    value, unit = parsed
                    out.append(
                        _candidate(
                            f"nozzles.{mark}.{key}",
                            value,
                            unit,
                            cell,
                            0.9,
                            f"Tabla de boquillas · {mark}",
                        )
                    )
            region.append((left, top - 0.01, right, bottom + 0.005))
        return out, region

    @staticmethod
    def _columns(header: list[EvidenceLine]) -> list[tuple[float, str]]:
        """(x de inicio, campo) por cabecera. Si dos cabeceras salieron unidas en una sola línea,
        la posición de cada una se estima por la proporción de caracteres."""
        columns = []
        for cell in header:
            text = cell.text.upper()
            x0, _, x1, _ = cell.source.bbox
            for key, pattern in COLUMNS:
                for match in pattern.finditer(text):
                    x = x0 + (x1 - x0) * match.start() / max(1, len(text))
                    if not any(k == key for _, k in columns):
                        columns.append((x, key))
                    break
        return sorted(columns)

    @staticmethod
    def _column_for(cell: EvidenceLine, columns) -> str | None:
        x = cell.source.bbox[0]
        best = min(columns, key=lambda c: abs(c[0] - x), default=None)
        return best[1] if best and abs(best[0] - x) < 0.02 else None

    @staticmethod
    def _cell_value(key: str, text: str, ctx: DocContext):
        if key == "diameter":
            dn = parse_nominal_size(text)
            return None if dn is None else (float(dn), "mm")
        if key == "azimuth":
            angle = parse_angle(text)
            return None if angle is None else (angle, "deg")
        length = parse_length(text, decimal=ctx.decimal)
        return None if length is None else (round(length, 3), "mm")

    # Datos de diseño ------------------------------------------------------------------------
    def _design_data(self, rows, ctx: DocContext) -> list[Candidate]:
        out: list[Candidate] = []
        for row in rows:
            for label_cell, value in zip(row, row[1:], strict=False):
                label = label_cell.text.upper()
                for key, pattern in DESIGN:
                    if not pattern.search(label):
                        continue
                    locator = f"Datos de diseño · {label_cell.text}"
                    if key == "material":
                        text = value.text.strip()
                        if text and not text[0].isdigit():
                            out.append(
                                _candidate("attributes.material", text, "1", value, 0.85, locator)
                            )
                        break
                    parser = {
                        "design_pressure": (parse_pressure, "bar"),
                        "design_temperature": (parse_temperature, "C"),
                        "operating_weight": (parse_weight, "kg"),
                    }[key]
                    parsed = parser[0](value.text, decimal=ctx.decimal)
                    if parsed is not None:
                        number, unit_original = parsed
                        out.append(
                            _candidate(
                                f"attributes.{key}",
                                round(number, 4),
                                parser[1],
                                value,
                                0.9,
                                locator,
                                unit_original=unit_original,
                            )
                        )
                    break
        return out

    # Rótulos sueltos: diámetro, espesor de faldón y tag del cajetín -------------------------
    def _labels(self, lines: list[EvidenceLine], ctx: DocContext) -> list[Candidate]:
        out: list[Candidate] = []
        for line in lines:
            text = line.text.strip()
            if (m := DIAMETER.match(text)) and (mm := parse_length(m[1], decimal=ctx.decimal)):
                out.append(
                    _candidate("diameter", round(mm, 3), "mm", line, 0.85, "Cota de diámetro")
                )
            elif line.source.locator.startswith("OCR") and (m := OCR_DIAMETER.match(text)):
                out.append(
                    _candidate(
                        "diameter",
                        float(m[1]),
                        "mm",
                        line,
                        0.7,
                        "Cota de diámetro (Ø leído como 0 por el OCR)",
                    )
                )
            elif (m := SKIRT.match(text)) and (mm := parse_length(m[1], decimal=ctx.decimal)):
                out.append(
                    _candidate(
                        "skirt_thickness", round(mm, 3), "mm", line, 0.85, "Rótulo del faldón"
                    )
                )
            if re.sub(r"[\s.]", "", text.upper()) in TAG_LABELS:
                x0, _, _, y1 = line.source.bbox
                below = [
                    other
                    for other in lines
                    if abs(other.source.bbox[0] - x0) < 0.01
                    and 0 < other.source.bbox[1] - y1 < 0.04
                ]
                if below:
                    tag = min(below, key=lambda o: o.source.bbox[1])
                    if re.fullmatch(r"[A-Za-z0-9_-]+", tag.text.strip()):
                        out.append(
                            _candidate("tag", tag.text.strip(), "1", tag, 0.85, "Cajetín · equipo")
                        )
        if not any(candidate.path == "tag" for candidate in out):
            # Un identificador aislado se puede leer sin conocer el rótulo del proveedor.
            # No usar el nombre del fichero ni escoger uno entre varios tags contradictorios.
            identifiers = {}
            for line in lines:
                text = line.text.strip().upper()
                if re.fullmatch(r"[A-Z]{1,4}\s*[-–]\s*\d{2,}(?:\s*[A-Z])?", text):
                    value = re.sub(r"\s", "", text).replace("–", "-")
                    identifiers.setdefault(value, line)
            if len(identifiers) == 1:
                value, line = next(iter(identifiers.items()))
                out.append(
                    _candidate("tag", value, "1", line, 0.75, "Identificador de equipo aislado")
                )
        return out

    # Cotas verticales del alzado ------------------------------------------------------------
    def _vertical_dimensions(
        self, lines, ctx: DocContext, tables, diameter: float | None = None
    ) -> list[Candidate]:
        def in_table(line):
            x0, y0, _, _ = line.source.bbox
            return any(a <= x0 <= c and b <= y0 <= d for a, b, c, d in tables)

        tangents = sorted(
            _center_y(line) for line in lines if line.text.strip().upper() in TANGENTS
        )
        dims = []
        for line in lines:
            text = line.text.strip()
            digits = sum(ch.isdigit() for ch in text)
            if digits < 2 or not DIMENSION_TEXT.match(text) or in_table(line):
                continue
            readings = parse_length_any_direction(text, decimal=ctx.decimal)
            if readings:
                dims.append((line, readings))
        roles: dict[str, list] = {"skirt_height": [], "head_depth": [], "between": []}
        if len(tangents) >= 2:
            top_tl, bottom_tl = tangents[0], tangents[-1]
            for line, readings in dims:
                y = _center_y(line)
                if y > bottom_tl:
                    roles["skirt_height"].append((line, readings))
                elif y < top_tl:
                    roles["head_depth"].append((line, readings))
                else:
                    roles["between"].append((line, readings))
        elif len(dims) >= 4:
            ordered = sorted(dims, key=lambda item: _center_y(item[0]))
            roles = {
                "head_depth": [ordered[0]],
                "skirt_height": [ordered[-1]],
                "between": ordered[1:-1],
            }
        if not roles["between"] and len(dims) == 3 and diameter:
            return self._derive_head(dims, float(diameter))
        if not roles["between"]:
            return []
        chosen: dict[str, tuple[EvidenceLine, float]] = {}
        consistent = False
        for o_item, t_item in itertools.permutations(roles["between"], 2):
            for s_item, h_item in itertools.product(roles["skirt_height"], roles["head_depth"]):
                for s, t, h, o in itertools.product(s_item[1], t_item[1], h_item[1], o_item[1]):
                    if abs(s + t + h - o) < 2.0 and t > max(s, h):
                        chosen = {
                            "skirt_height": (s_item[0], s),
                            "height": (t_item[0], t),
                            "head_depth": (h_item[0], h),
                        }
                        consistent = True
                        break
                if consistent:
                    break
            if consistent:
                break
        if not chosen:
            between = sorted(roles["between"], key=lambda item: item[0].source.bbox[0])
            for key, item in (
                ("skirt_height", roles["skirt_height"][0] if roles["skirt_height"] else None),
                ("height", between[-1]),
                ("head_depth", roles["head_depth"][0] if roles["head_depth"] else None),
            ):
                if item:
                    chosen[key] = (item[0], item[1][0])
        confidence = 0.95 if consistent else 0.5
        note = "cadena de cotas comprobada" if consistent else "lectura ambigua sin comprobación"
        return [
            _candidate(
                key, round(value, 3), "mm", line, confidence, f"Cota vertical del alzado · {note}"
            )
            for key, (line, value) in chosen.items()
        ]

    @staticmethod
    def _derive_head(dims, diameter: float) -> list[Candidate]:
        """Tres cotas legibles (faldón, virola y total) y un fondo 2:1 declarado en el plano.

        La cota del fondo es la más pequeña y la que más falla en el OCR. Si total − faldón −
        virola coincide con D/4 (±2 %), el fondo se deduce y se explica; si no, no se inventa.
        """
        skirt = max(dims, key=lambda item: _center_y(item[0]))  # la más baja del alzado
        rest = [item for item in dims if item is not skirt]
        for o_item, t_item in itertools.permutations(rest, 2):
            for s, t, o in itertools.product(skirt[1], t_item[1], o_item[1]):
                head = o - s - t
                if head > 0 and t > s and abs(head - diameter / 4) <= 0.02 * diameter / 4:
                    locator = "Cota vertical del alzado · cadena con fondo deducido"
                    total = o_item[0]
                    return [
                        _candidate("skirt_height", round(s, 3), "mm", skirt[0], 0.8, locator),
                        _candidate("height", round(t, 3), "mm", t_item[0], 0.8, locator),
                        _candidate(
                            "head_depth",
                            round(head, 3),
                            "mm",
                            total,
                            0.7,
                            "Fondo deducido de la cadena de cotas",
                            explanation=(
                                f"Deducido: total {o:g} − faldón {s:g} − virola {t:g} = "
                                f"{head:g} mm, igual a D/4 de un fondo 2:1 (D = {diameter:g} mm)."
                            ),
                        ),
                    ]
        return []

    # Origen de las cotas de boquilla --------------------------------------------------------
    @staticmethod
    def _apply_datum(found: list[Candidate], ctx: DocContext) -> list[Candidate]:
        if not ctx.btl_datum:
            return found
        skirt = next((c for c in found if c.path == "skirt_height"), None)
        out = []
        for c in found:
            if not (c.path.startswith("nozzles.") and c.path.endswith(".elevation")):
                out.append(c)
                continue
            if skirt is None:
                continue  # sin faldón no se puede pasar a cota desde el suelo: se abstiene
            out.append(
                c.model_copy(
                    update={
                        "value": round(float(c.value) + float(skirt.value), 3),
                        "explanation": (
                            f"Cota desde la tangente inferior ({c.text_original}) + faldón "
                            f"({skirt.value:g} mm), según la nota del plano."
                        ),
                        "source": c.source.model_copy(
                            update={"confidence": min(c.source.confidence, skirt.source.confidence)}
                        ),
                    }
                )
            )
        return out
