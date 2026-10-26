"""Extractor de GA dibujados con capa de texto: tablas, cotas y cajetín, sin IA.

Lee lo que un delineante busca primero en un plano de disposición general:
- tabla de boquillas (columnas identificadas por las palabras de la cabecera),
- datos de diseño (etiqueta y valor en la misma fila),
- diámetro («ID 2000»), espesor de faldón («SKIRT t=20») y tag del cajetín,
- cotas verticales del alzado, asignadas por su posición frente a las líneas de tangencia (T.L.).

Las cotas giradas pueden llegar con los dígitos invertidos. Se prueban las dos lecturas y se
acepta la combinación que cumple faldón + virola + fondo = altura total. Si la cadena cuadra, la
confianza sube; si no, baja y el campo queda para revisión humana.

Validado solo con el conjunto sintético (docs/BENCH.md); hay que ajustarlo con el dataset real.
Cada valor conserva como evidencia la caja de la celda o texto del que sale.
"""

import itertools
import re
from collections import defaultdict

from ..extraction import Candidate
from ..ingest import Bundle, EvidenceLine
from ..model import Source

NUMBER = re.compile(r"^-?\d+(?:[.,]\d+)?$")
MARK = re.compile(r"^[A-Z]{1,2}\d{1,3}[A-Z]?$")
COLUMN_KEYS = (
    ("diameter", re.compile(r"\b(SIZE|DN|NPS)\b")),
    ("projection", re.compile(r"\bPROJ")),
    ("elevation", re.compile(r"\bELEV")),
    ("azimuth", re.compile(r"\b(ORIENT|AZIM|ANGLE)")),
)
DESIGN = (
    (
        "design_pressure",
        re.compile(r"DESIGN\s+PRESS"),
        re.compile(r"^(-?\d+(?:[.,]\d+)?)\s*(barg?|kpa|mpa)$", re.I),
    ),
    (
        "design_temperature",
        re.compile(r"DESIGN\s+TEMP"),
        re.compile(r"^(-?\d+(?:[.,]\d+)?)\s*°?\s*C$", re.I),
    ),
    (
        "operating_weight",
        re.compile(r"OPERAT\w*\s+WEIGHT"),
        re.compile(r"^(\d+(?:[.,]\d+)?)\s*kg$", re.I),
    ),
)
ROW_TOLERANCE = 0.006  # fracción de la altura de página


def _number(text: str) -> float | None:
    clean = text.replace("°", "").replace("º", "").strip()
    return float(clean.replace(",", ".")) if NUMBER.match(clean) else None


def _with_confidence(source: Source, confidence: float, locator: str) -> Source:
    return source.model_copy(update={"confidence": confidence, "locator": locator})


def _center_y(line: EvidenceLine) -> float:
    _, y0, _, y1 = line.source.bbox
    return (y0 + y1) / 2


def _rows(lines: list[EvidenceLine]) -> list[list[EvidenceLine]]:
    """Agrupa líneas en filas por su altura en la página y las ordena de izquierda a derecha."""
    rows: list[list[EvidenceLine]] = []
    for line in sorted(lines, key=_center_y):
        if rows and abs(_center_y(rows[-1][0]) - _center_y(line)) <= ROW_TOLERANCE:
            rows[-1].append(line)
        else:
            rows.append([line])
    return [sorted(r, key=lambda line: line.source.bbox[0]) for r in rows]


class DrawingExtractor:
    def extract(self, bundles: list[Bundle]) -> list[Candidate]:
        result: list[Candidate] = []
        for bundle in bundles:
            if bundle.media_type != "pdf":
                continue
            pages = defaultdict(list)
            for line in bundle.lines:
                if line.source.bbox is not None:
                    pages[line.source.page].append(line)
            for lines in pages.values():
                rows = _rows(lines)
                result += self._nozzle_table(rows)
                result += self._design_data(rows)
                result += self._labels(lines)
                result += self._vertical_dimensions(lines)
        return result

    # Tabla de boquillas ---------------------------------------------------------------------
    def _nozzle_table(self, rows: list[list[EvidenceLine]]) -> list[Candidate]:
        out: list[Candidate] = []
        for index, row in enumerate(rows):
            start = next((i for i, c in enumerate(row) if "MARK" in c.text.upper()), None)
            if start is None:
                continue
            # La tabla empieza en la celda MARK: lo que quede a su izquierda es otro dibujo.
            cells = row[start:]
            header = " ".join(line.text.upper() for line in cells)
            if "ELEV" not in header:
                continue
            order = sorted(
                ((m.start(), key) for key, pattern in COLUMN_KEYS if (m := pattern.search(header))),
            )
            keys = [key for _, key in order]
            left = cells[0].source.bbox[0] - 0.01
            right = max(line.source.bbox[2] for line in cells) + 0.05
            for full_row in rows[index + 1 :]:
                data = [
                    c for c in full_row if c.source.bbox[0] >= left and c.source.bbox[2] <= right
                ]
                if not data:
                    continue
                mark = data[0].text.strip().upper()
                if not MARK.match(mark):
                    break
                numeric = [(cell, _number(cell.text)) for cell in data[1:]]
                numeric = [(cell, value) for cell, value in numeric if value is not None]
                for key, (cell, value) in zip(keys, numeric, strict=False):
                    out.append(
                        Candidate(
                            path=f"nozzles.{mark}.{key}",
                            value=value,
                            unit="deg" if key == "azimuth" else "mm",
                            source=_with_confidence(
                                cell.source, 0.9, f"Tabla de boquillas · {mark}"
                            ),
                        )
                    )
        return out

    # Datos de diseño ------------------------------------------------------------------------
    def _design_data(self, rows: list[list[EvidenceLine]]) -> list[Candidate]:
        out: list[Candidate] = []
        pairs = [(row[i], row[i + 1]) for row in rows for i in range(len(row) - 1)]
        for label_cell, value in pairs:
            label = label_cell.text.upper()
            for key, label_pattern, value_pattern in DESIGN:
                if label_pattern.search(label) and (m := value_pattern.match(value.text.strip())):
                    unit = (
                        {"barg": "bar", "kpa": "kPa", "mpa": "MPa"}.get(m[2].lower(), m[2])
                        if key == "design_pressure"
                        else ("C" if key == "design_temperature" else "kg")
                    )
                    out.append(
                        Candidate(
                            path=f"attributes.{key}",
                            value=float(m[1].replace(",", ".")),
                            unit=unit,
                            source=_with_confidence(
                                value.source, 0.9, f"Datos de diseño · {label_cell.text}"
                            ),
                        )
                    )
            if re.search(r"\bMATERIAL\b", label) and value.text.strip():
                out.append(
                    Candidate(
                        path="attributes.material",
                        value=value.text.strip(),
                        unit="1",
                        source=_with_confidence(
                            value.source, 0.85, f"Datos de diseño · {label_cell.text}"
                        ),
                    )
                )
        return out

    # Rótulos sueltos: diámetro, espesor de faldón y tag del cajetín -------------------------
    def _labels(self, lines: list[EvidenceLine]) -> list[Candidate]:
        out: list[Candidate] = []
        for line in lines:
            text = line.text.strip()
            if m := re.fullmatch(r"(?:ID|OD|Ø|DIA\.?)\s*[:=]?\s*(\d+(?:[.,]\d+)?)", text, re.I):
                out.append(
                    Candidate(
                        path="diameter",
                        value=float(m[1].replace(",", ".")),
                        unit="mm",
                        source=_with_confidence(line.source, 0.85, "Cota de diámetro"),
                    )
                )
            if m := re.fullmatch(r"SKIRT\s*t\s*=\s*(\d+(?:[.,]\d+)?)", text, re.I):
                out.append(
                    Candidate(
                        path="skirt_thickness",
                        value=float(m[1].replace(",", ".")),
                        unit="mm",
                        source=_with_confidence(line.source, 0.85, "Rótulo del faldón"),
                    )
                )
            if text.upper() == "EQUIPMENT":
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
                            Candidate(
                                path="tag",
                                value=tag.text.strip(),
                                unit="1",
                                source=_with_confidence(tag.source, 0.85, "Cajetín · equipo"),
                            )
                        )
        return out

    # Cotas verticales del alzado ------------------------------------------------------------
    def _vertical_dimensions(self, lines: list[EvidenceLine]) -> list[Candidate]:
        tangents = sorted(
            _center_y(line) for line in lines if line.text.strip().upper() in ("T.L.", "TL")
        )
        tangents_found = len(tangents) >= 2
        top_tl, bottom_tl = (tangents[0], tangents[-1]) if tangents_found else (0.0, 1.0)
        vertical = []
        for line in lines:
            x0, y0, x1, y1 = line.source.bbox
            digits = line.text.strip()
            # Al menos dos dígitos: descarta marcas sueltas como el número del triángulo Δ.
            if digits.isdigit() and len(digits) >= 2 and (y1 - y0) > 1.5 * (x1 - x0):
                readings = {float(r) for r in (digits, digits[::-1]) if not r.startswith("0")}
                if readings:
                    vertical.append((line, sorted(readings)))
        roles: dict[str, list] = {"skirt_height": [], "head_depth": [], "between": []}
        if tangents_found:
            for line, readings in vertical:
                y = _center_y(line)
                if y > bottom_tl:
                    roles["skirt_height"].append((line, readings))
                elif y < top_tl:
                    roles["head_depth"].append((line, readings))
                else:
                    roles["between"].append((line, readings))
        elif len(vertical) >= 4:
            # Sin las dos T.L. (rótulos solapados): la cota más alta es el fondo, la más baja el
            # faldón y la comprobación de la cadena decide el resto.
            ordered = sorted(vertical, key=lambda item: _center_y(item[0]))
            roles = {
                "head_depth": [ordered[0]],
                "skirt_height": [ordered[-1]],
                "between": ordered[1:-1],
            }
        if not roles["between"]:
            return []
        # Sin cadena comprobable se usa la cota interior entre tangentes como virola (la más
        # exterior suele ser la altura total), con confianza baja.
        between = sorted(roles["between"], key=lambda item: item[0].source.bbox[0])
        shell = between[-1]
        skirt = roles["skirt_height"][0] if roles["skirt_height"] else None
        head = roles["head_depth"][0] if roles["head_depth"] else None

        chosen: dict[str, tuple[EvidenceLine, float]] = {}
        consistent = False
        # Se prueban todas las asignaciones de cotas a papeles y de lecturas a valores; vale la
        # primera en la que faldón + virola + fondo = total.
        for o_item, t_item in itertools.permutations(roles["between"], 2):
            for s_item, h_item in itertools.product(roles["skirt_height"], roles["head_depth"]):
                for s, t, h, o in itertools.product(s_item[1], t_item[1], h_item[1], o_item[1]):
                    if abs(s + t + h - o) < 0.5 and t > max(s, h):
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
            for key, item in (("skirt_height", skirt), ("height", shell), ("head_depth", head)):
                if item:
                    chosen[key] = (item[0], item[1][-1])
        confidence = 0.95 if consistent else 0.5
        note = "cadena de cotas comprobada" if consistent else "lectura ambigua sin comprobación"
        return [
            Candidate(
                path=key,
                value=value,
                unit="mm",
                source=_with_confidence(
                    line.source, confidence, f"Cota vertical del alzado · {note}"
                ),
            )
            for key, (line, value) in chosen.items()
        ]
