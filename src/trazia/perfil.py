"""Perfil de un dataset: qué hay en la carpeta sin enseñar ningún documento.

Pensado para la primera hora del evento: se ejecuta en Databricks sobre el volumen de TR
(`databricks/02_perfil_dataset.py`) o en local con `trazia perfil <carpeta>`, y responde a lo que
decide la estrategia: cuántos equipos y revisiones hay, qué tipos de documento, qué PDF son
vectoriales y cuáles escaneados, tamaños y giros de página, unidades, notación de boquillas,
idioma, hojas de los XLSX y si vienen IFC de referencia.

La salida son solo recuentos. No lleva nombres de archivo, rutas, tags ni textos: los nombres
se reducen a su forma (`GAD_A-9_rev9.pdf`), así que se puede pegar al asistente de código
(docs/FLUJO_IA.md). Aun así, hay que leerlo antes de pegarlo.
"""

import hashlib
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median

from .ingest import IMAGE_SUFFIXES
from .lote import NAME

MM_POR_PT = 25.4 / 72
TEXTO_MINIMO = 25  # caracteres por página para contarla como página con capa de texto
TRAZOS_MINIMOS = 50  # líneas, curvas y rectángulos para que una página sin texto sea vectorial
# Formatos ISO 216 en mm (lado corto, lado largo); se admite un 4 % de margen.
FORMATOS = {"A4": (210, 297), "A3": (297, 420), "A2": (420, 594), "A1": (594, 841)}
FORMATOS["A0"] = (841, 1189)
PALABRAS_CLAVE = ("GAD", "GA", "HDM", "VESOR", "ESTRUCTURA", "REV")
# Patrones contados por documento: dicen qué reglas de lectura hacen falta, no qué pone.
PATRONES = {
    "unidad_mm": re.compile(r"\d\s*mm\b", re.I),
    "unidad_pulgadas": re.compile(r"\d\s*(?:\"|''|”|in\b|inch)", re.I),
    "fracciones": re.compile(r"\b\d+\s*/\s*(?:2|4|8|16)\b"),
    "coma_decimal": re.compile(r"\b\d+,\d{1,3}\b(?!,)"),
    "punto_decimal": re.compile(r"\b\d+\.\d{1,3}\b"),
    "dn": re.compile(r"\bDN\s*\d+", re.I),
    "nps": re.compile(r"\bNPS\s*\d+|\b\d+\s*(?:\"|”)\s*(?:NPS|SCH)", re.I),
    "clase_brida": re.compile(r"\b(?:150|300|600|900|1500|2500)\s*(?:#|lbs?\b)|\bCLASS\s*\d", re.I),
    "pn": re.compile(r"\bPN\s*\d+", re.I),
    "marca_boquilla": re.compile(r"\bN\d{1,3}[A-Z]?\b"),
    "azimut_grados": re.compile(r"\d\s*°"),
    "nube_o_delta": re.compile(r"[Δ△]"),
}
IDIOMA = {
    "es": re.compile(
        r"\b(?:boquilla|tubuladura|virola|fondo|faldón|cajetín|plano|espesor)\b", re.I
    ),
    "en": re.compile(r"\b(?:nozzle|shell|head|skirt|drawing|thickness|schedule)\b", re.I),
}


def forma(texto: str) -> str:
    """Forma de un nombre: letras → A y cifras → 9 en tramos; se conservan las palabras del reto."""

    def tramo(m: re.Match) -> str:
        palabra = m[0]
        if palabra.upper() in PALABRAS_CLAVE:
            return palabra
        if palabra.lower().startswith("rev") and palabra[3:].isalnum():
            return "rev" + ("9" if palabra[3:].isdigit() else "A")
        return re.sub(r"[A-Za-z]+", "A", re.sub(r"\d+", "9", palabra))

    return re.sub(r"[A-Za-z0-9]+", tramo, texto)


def _formato(ancho_mm: float, alto_mm: float) -> str:
    corto, largo = sorted((ancho_mm, alto_mm))
    for nombre, (c, lg) in FORMATOS.items():
        if abs(corto - c) <= 0.04 * c and abs(largo - lg) <= 0.04 * lg:
            return nombre
    if any(abs(corto - c) <= 0.04 * c and largo > lg for c, lg in FORMATOS.values()):
        return "alargado"
    return "otro"


def _distribucion(valores: list[float]) -> dict | None:
    if not valores:
        return None
    ordenados = sorted(valores)
    return {
        "n": len(ordenados),
        "min": round(ordenados[0], 2),
        "mediana": round(median(ordenados), 2),
        "max": round(ordenados[-1], 2),
    }


def _cuenta(contador: Counter) -> dict:
    return dict(sorted(contador.items(), key=lambda kv: (-kv[1], str(kv[0]))))


def _perfil_pdf(path: Path, max_paginas: int) -> dict:
    import pdfplumber

    paginas, textos = [], []
    with pdfplumber.open(path) as pdf:
        total = len(pdf.pages)
        for page in pdf.pages[:max_paginas]:
            chars = page.chars
            girados = sum(1 for c in chars if not c.get("upright", True))
            trazos = len(page.lines) + len(page.curves) + len(page.rects)
            if len(chars) >= TEXTO_MINIMO:
                tipo = "texto"
            elif trazos >= TRAZOS_MINIMOS:
                tipo = "vectorial_sin_texto"  # texto convertido en curvas: el OCR lo tiene que leer
            elif page.images:
                tipo = "raster"
            else:
                tipo = "vacia"
            paginas.append(
                {
                    "tipo": tipo,
                    "formato": _formato(
                        float(page.width) * MM_POR_PT, float(page.height) * MM_POR_PT
                    ),
                    "apaisada": page.width > page.height,
                    "rotacion": int(page.rotation or 0) % 360,
                    "texto_girado": bool(chars) and girados / len(chars) > 0.2,
                    "imagenes": len(page.images),
                    "caracteres": len(chars),
                }
            )
            if tipo == "texto":
                textos.append(page.extract_text() or "")
            page.close()  # libera la caché de objetos: los planos A1 pesan mucho
    tipos = {p["tipo"] for p in paginas}
    if tipos <= {"texto", "vacia"}:
        clase = "vectorial"
    elif tipos & {"raster", "vectorial_sin_texto"} and "texto" in tipos:
        clase = "mixto"
    elif "vectorial_sin_texto" in tipos and "raster" not in tipos:
        clase = "vectorial_sin_texto"
    else:
        clase = "escaneado"
    return {"paginas": total, "leidas": paginas, "clase": clase, "texto": "\n".join(textos)}


def _perfil_xlsx(path: Path) -> dict:
    from openpyxl import load_workbook

    libro = load_workbook(path, read_only=True, data_only=True)
    try:
        hojas = [{"filas": h.max_row or 0, "columnas": h.max_column or 0} for h in libro.worksheets]
        texto = []
        for hoja in libro.worksheets[:5]:
            for fila in hoja.iter_rows(max_row=400, values_only=True):
                texto.extend(str(v) for v in fila if v is not None)
    finally:
        libro.close()
    return {"hojas": hojas, "texto": "\n".join(texto)}


def _perfil_imagen(path: Path) -> dict:
    from PIL import Image

    with Image.open(path) as imagen:
        dpi = imagen.info.get("dpi")
        return {
            "megapixeles": imagen.width * imagen.height / 1e6,
            "dpi": round(float(dpi[0])) if dpi else None,
            "fotogramas": getattr(imagen, "n_frames", 1),
        }


def _error(exc: Exception) -> str:
    texto = str(exc).lower()
    if "password" in texto or "encrypt" in texto:
        return "cifrado"
    return type(exc).__name__


def perfilar(carpeta: Path, *, max_paginas: int = 30) -> dict:
    """Recuentos agregados de todo lo que hay en `carpeta` (recursivo)."""
    carpeta = Path(carpeta)
    if not carpeta.is_dir():
        raise FileNotFoundError(f"No existe la carpeta {carpeta}")
    inicio = time.perf_counter()
    extension, tipo_doc, formas_fuera, formas_tag, formas_rev = (Counter() for _ in range(5))
    tamanos, hashes, errores = [], Counter(), Counter()
    revisiones = defaultdict(set)
    tipos_por_tag = defaultdict(set)
    sin_revision = Counter()
    ifc_tags, ifc_esquemas = [], Counter()
    pdf = {
        "documentos": 0,
        "clase": Counter(),
        "paginas_por_documento": [],
        "pagina_tipo": Counter(),
        "formato": Counter(),
        "apaisadas": 0,
        "rotacion": Counter(),
        "texto_girado": 0,
        "caracteres_por_pagina": [],
        "truncados": 0,
    }
    xlsx = {"documentos": 0, "hojas": Counter(), "filas": [], "columnas": []}
    imagenes = {"documentos": 0, "megapixeles": [], "dpi": Counter(), "multipagina": 0}
    patrones = Counter()
    idioma = Counter()
    con_texto = 0
    for path in sorted(carpeta.rglob("*")):
        if not path.is_file() or path.name.startswith("."):
            continue
        sufijo = path.suffix.lower() or "(sin extensión)"
        extension[sufijo] += 1
        tamanos.append(path.stat().st_size / 1e6)
        with path.open("rb") as handle:
            hashes[hashlib.file_digest(handle, "sha256").hexdigest()] += 1
        match = NAME.match(path.name)
        if sufijo == ".ifc":
            ifc_tags.append(path.stem)
            try:
                with path.open(encoding="utf-8", errors="ignore") as handle:
                    cabecera = handle.read(4000)
                esquema = re.search(r"FILE_SCHEMA\s*\(\s*\(\s*'([^']+)'", cabecera)
                ifc_esquemas[esquema[1].upper() if esquema else "desconocido"] += 1
            except OSError as exc:
                errores[_error(exc)] += 1
            continue
        if match:
            kind = match["kind"].upper()
            tipo_doc[kind] += 1
            tag = match["tag"]
            tipos_por_tag[tag].add("GA" if kind in ("GA", "GAD") else kind)
            formas_tag[forma(tag)] += 1
            if match["rev"]:
                revisiones[tag].add(match["rev"])
                formas_rev[forma(match["rev"])] += 1
            else:
                sin_revision[kind] += 1
        else:
            formas_fuera[forma(path.stem) + path.suffix.lower()] += 1
        texto = ""
        try:
            if sufijo == ".pdf":
                datos = _perfil_pdf(path, max_paginas)
                pdf["documentos"] += 1
                pdf["clase"][datos["clase"]] += 1
                pdf["paginas_por_documento"].append(datos["paginas"])
                pdf["truncados"] += datos["paginas"] > max_paginas
                for pagina in datos["leidas"]:
                    pdf["pagina_tipo"][pagina["tipo"]] += 1
                    pdf["formato"][pagina["formato"]] += 1
                    pdf["apaisadas"] += pagina["apaisada"]
                    pdf["rotacion"][pagina["rotacion"]] += 1
                    pdf["texto_girado"] += pagina["texto_girado"]
                    pdf["caracteres_por_pagina"].append(pagina["caracteres"])
                texto = datos["texto"]
            elif sufijo == ".xlsx":
                datos = _perfil_xlsx(path)
                xlsx["documentos"] += 1
                xlsx["hojas"][len(datos["hojas"])] += 1
                xlsx["filas"].extend(h["filas"] for h in datos["hojas"])
                xlsx["columnas"].extend(h["columnas"] for h in datos["hojas"])
                texto = datos["texto"]
            elif sufijo in IMAGE_SUFFIXES:
                datos = _perfil_imagen(path)
                imagenes["documentos"] += 1
                imagenes["megapixeles"].append(datos["megapixeles"])
                imagenes["dpi"][datos["dpi"] or "sin dato"] += 1
                imagenes["multipagina"] += datos["fotogramas"] > 1
        except Exception as exc:  # un archivo roto no detiene el perfil: se cuenta su categoría
            errores[_error(exc)] += 1
            continue
        if texto:
            con_texto += 1
            for nombre, patron in PATRONES.items():
                patrones[nombre] += bool(patron.search(texto))
            for lengua, patron in IDIOMA.items():
                idioma[lengua] += bool(patron.search(texto))

    def tag_normalizado(texto: str) -> str:
        return re.sub(r"[^A-Z0-9]", "", texto.upper())

    tags = set(tipos_por_tag)
    normalizados = {tag_normalizado(t) for t in tags}
    ifc_con_equipo = sum(
        any(n and n in tag_normalizado(stem) for n in normalizados) for stem in ifc_tags
    )
    por_equipo = [len(revisiones.get(t, ())) or 1 for t in tags]
    etiquetas = {r.upper() for rs in revisiones.values() for r in rs}
    return {
        "segundos": round(time.perf_counter() - inicio, 1),
        "archivos": {
            "total": sum(extension.values()),
            "por_extension": _cuenta(extension),
            "megabytes": _distribucion(tamanos),
            "duplicados_exactos": sum(n - 1 for n in hashes.values() if n > 1),
            "errores_de_lectura": _cuenta(errores),
            "con_nombre_del_reto": sum(tipo_doc.values()),
            "formas_fuera_del_reto": _cuenta(formas_fuera),
        },
        "equipos": {
            "total": len(tags),
            "revisiones_por_equipo": _cuenta(Counter(por_equipo)),
            "etiquetas_de_revision": len(etiquetas),
            "forma_de_revision": _cuenta(formas_rev),
            "forma_de_tag": _cuenta(formas_tag),
            "documentos_por_tipo": _cuenta(tipo_doc),
            "sin_revision_por_tipo": _cuenta(sin_revision),
            "combinaciones_de_tipos": _cuenta(
                Counter("+".join(sorted(t)) for t in tipos_por_tag.values())
            ),
            "sin_ga": sum("GA" not in t for t in tipos_por_tag.values()),
        },
        "ifc": {
            "archivos": len(ifc_tags),
            "esquema": _cuenta(ifc_esquemas),
            "con_equipo_del_lote": ifc_con_equipo,
        },
        "pdf": {
            "documentos": pdf["documentos"],
            "clase": _cuenta(pdf["clase"]),
            "paginas_por_documento": _distribucion(pdf["paginas_por_documento"]),
            "documentos_truncados": pdf["truncados"],
            "paginas_leidas": sum(pdf["pagina_tipo"].values()),
            "tipo_de_pagina": _cuenta(pdf["pagina_tipo"]),
            "formato_de_pagina": _cuenta(pdf["formato"]),
            "apaisadas": pdf["apaisadas"],
            "rotacion_declarada": _cuenta(pdf["rotacion"]),
            "con_texto_girado": pdf["texto_girado"],
            "caracteres_por_pagina": _distribucion(pdf["caracteres_por_pagina"]),
        },
        "xlsx": {
            "documentos": xlsx["documentos"],
            "hojas_por_libro": _cuenta(xlsx["hojas"]),
            "filas_por_hoja": _distribucion(xlsx["filas"]),
            "columnas_por_hoja": _distribucion(xlsx["columnas"]),
        },
        "imagenes": {
            "documentos": imagenes["documentos"],
            "megapixeles": _distribucion(imagenes["megapixeles"]),
            "dpi": _cuenta(imagenes["dpi"]),
            "multipagina": imagenes["multipagina"],
        },
        "contenido": {
            "documentos_con_texto": con_texto,
            "documentos_con_patron": _cuenta(patrones),
            "idioma": _cuenta(idioma),
        },
    }


def avisos(perfil: dict) -> list[str]:
    """Lecturas del perfil que cambian qué preparar: en palabras, sin datos del plano."""
    out = []
    pdf, equipos, archivos = perfil["pdf"], perfil["equipos"], perfil["archivos"]
    clase = pdf["clase"]
    if pdf["documentos"]:
        escaneados = clase.get("escaneado", 0) + clase.get("mixto", 0)
        if escaneados:
            out.append(
                f"{escaneados} de {pdf['documentos']} PDF escaneados o mixtos: OCR y detector "
                "en el camino crítico; medir tiempos con un equipo antes del lote completo."
            )
        if clase.get("vectorial_sin_texto"):
            out.append(
                f"{clase['vectorial_sin_texto']} PDF vectoriales sin capa de texto (texto en "
                "curvas): el pipeline los trata como escaneados."
            )
    if pdf["con_texto_girado"] or any(int(r) for r in pdf["rotacion_declarada"]):
        out.append("Hay páginas giradas o con texto girado: revisar A.5 (orientación).")
    if pdf["documentos_truncados"]:
        out.append(
            f"{pdf['documentos_truncados']} PDF con más páginas de las leídas: subir max_paginas "
            "si hace falta el perfil completo."
        )
    if archivos["formas_fuera_del_reto"]:
        total = sum(archivos["formas_fuera_del_reto"].values())
        out.append(
            f"{total} archivos no siguen GAD_/HDM_/VESOR_<TAG>_rev<R>: el lote los ignora. "
            "Mirar sus formas y, si son documentos, ampliar lote.NAME."
        )
    if equipos["sin_ga"]:
        out.append(
            f"{equipos['sin_ga']} equipos sin GA: no hay plano de partida para la geometría."
        )
    contenido = perfil["contenido"]["documentos_con_patron"]
    if contenido.get("unidad_pulgadas") or contenido.get("fracciones"):
        out.append("Aparecen pulgadas o fracciones: comprobar units.py con un caso sintético.")
    if contenido.get("coma_decimal"):
        out.append("Aparece coma decimal: comprobar que no se lee como separador de miles.")
    ifc = perfil["ifc"]
    if ifc["archivos"]:
        out.append(
            f"{ifc['archivos']} IFC en la carpeta ({ifc['con_equipo_del_lote']} casan con un "
            "equipo): usarlos con 03_evaluar_contra_tr."
        )
    if archivos["duplicados_exactos"]:
        out.append(f"{archivos['duplicados_exactos']} archivos duplicados byte a byte.")
    if archivos["errores_de_lectura"]:
        out.append(f"Archivos que no se pudieron leer: {archivos['errores_de_lectura']}.")
    return out
