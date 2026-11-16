# Databricks notebook source
# MAGIC %md
# MAGIC # TrazIA-3D · 03 · Evaluar el lote contra los IFC de TR
# MAGIC
# MAGIC Compara la salida de `01_procesar_lote` con los IFC de referencia que entregue Técnicas
# MAGIC Reunidas. Para cada equipo cuyo tag aparece en el nombre de un IFC se toma su última
# MAGIC revisión correcta y se mide:
# MAGIC
# MAGIC - **dimensiones principales** (diámetro y longitud de virola): error en mm y relativo;
# MAGIC - **boquillas**: cuántas casan, faltan o sobran, y el error de posición (mm), de azimut
# MAGIC   (°) y de diámetro;
# MAGIC - **convenio de azimut**: el que encaja en cada equipo y el que sale por **exclusión de
# MAGIC   uno** (el más frecuente en los demás equipos). La cifra que se presenta es la segunda;
# MAGIC - **superficie completa**: los dos IFC en el mismo marco y distancia entre superficies
# MAGIC   (Chamfer, percentil 95 y Hausdorff muestreado, en mm), con un **mapa de calor 3D**.
# MAGIC
# MAGIC Sin IFC de TR (carpeta `referencias` vacía), el notebook fabrica referencias de ensayo
# MAGIC con los IFC del propio lote, sin nombres, movidos y girados 90°. Deben dar error ~0 y
# MAGIC convenio `offset 90`: sirve para comprobar el notebook, no mide nada.
# MAGIC
# MAGIC Los mapas y la tabla muestran geometría de TR: se quedan en Databricks. Al asistente
# MAGIC de código solo va la última celda (`docs/FLUJO_IA.md`).

# COMMAND ----------

# MAGIC %pip install -q -r ./requirements.txt

# COMMAND ----------

try:
    dbutils.library.restartPython()  # noqa: F821 - solo existe en Databricks
except NameError:
    pass

# COMMAND ----------

import json
import os
import sys
from pathlib import Path


def raiz_del_repo() -> Path:
    inicio = Path(globals().get("__file__", Path.cwd() / "x")).resolve().parent
    for carpeta in (inicio, *inicio.parents):
        if (carpeta / "pyproject.toml").is_file() and (carpeta / "src" / "trazia").is_dir():
            return carpeta
    raise RuntimeError(f"No encuentro la raíz de TrazIA-3D subiendo desde {inicio}")


def parametro(nombre: str, defecto: str, etiqueta: str) -> str:
    try:
        dbutils.widgets.text(nombre, defecto, etiqueta)  # noqa: F821
        return dbutils.widgets.get(nombre).strip()  # noqa: F821
    except NameError:
        return os.environ.get(f"TRAZIA_NB_{nombre.upper()}", defecto).strip()


RAIZ = raiz_del_repo()
for ruta in (RAIZ / "src", RAIZ):  # trazia y bench
    if str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))

LOTE = Path(parametro("lote", "/tmp/trazia/salida", "Salida de 01 (/Volumes/...)"))
REFERENCIAS = parametro("referencias", "", "IFC de TR (/Volumes/...; vacío = ensayo)")
REVISION = parametro("revision", "ultima", "Revisión («ultima» o etiqueta)")
MUESTRAS = int(parametro("muestras", "4000", "Muestras por superficie") or 4000)
ESCALA_MM = float(parametro("escala_mm", "50", "Tope de color del mapa (mm)") or 50)
MAPAS = Path(parametro("mapas", "/tmp/trazia/mapas", "Carpeta de mapas HTML"))

if not (LOTE / "resumen.json").is_file():
    raise FileNotFoundError(f"No hay {LOTE / 'resumen.json'}: ejecuta antes 01_procesar_lote")
for carpeta in (LOTE, MAPAS):
    if carpeta.resolve().is_relative_to(RAIZ.resolve()):
        raise ValueError("Ni la salida ni los mapas pueden estar dentro del repositorio")

# COMMAND ----------

from bench.evaluar import evaluar, referencias_de_ensayo  # noqa: E402

if REFERENCIAS:
    REFERENCIAS = Path(REFERENCIAS)
    ENSAYO = False
else:
    REFERENCIAS = Path("/tmp/trazia/referencias_ensayo")
    ENSAYO = True
    n = referencias_de_ensayo(LOTE, REFERENCIAS, revision=REVISION)
    print(f"ENSAYO: {n} referencias fabricadas con el propio lote en {REFERENCIAS}.")
if not REFERENCIAS.is_dir():
    raise FileNotFoundError(f"No existe la carpeta de referencias {REFERENCIAS}")

evaluacion = evaluar(
    LOTE, REFERENCIAS, revision=REVISION, muestras=MUESTRAS, mapas=MAPAS, escala_mm=ESCALA_MM
)
destino = LOTE / ("evaluacion_ensayo.json" if ENSAYO else "evaluacion_tr.json")
destino.write_text(json.dumps(evaluacion, ensure_ascii=False, indent=2), encoding="utf-8")
print(
    f"{len(evaluacion['equipos'])} equipos evaluados · sin referencia: "
    f"{len(evaluacion['sin_referencia'])} · sin revisión correcta: "
    f"{len(evaluacion['sin_revision_correcta'])} · IFC sin equipo: {evaluacion['ifc_sin_equipo']}"
)
print(f"Detalle en {destino}")

# COMMAND ----------

from html import escape  # noqa: E402


def numero(valor, formato=".0f", sufijo=""):
    return "" if valor is None else f"{valor:{formato}}{sufijo}"


def dimension(d) -> str:
    return f"{numero(d['error_mm'])} mm · {numero(d['error_relativo'], '.1%')}"


def fila_html(e) -> list[str]:
    if "dimensiones" not in e:
        return [e["tag"], e["revision"], "sin medir", *[""] * 8, "; ".join(e["notas"])]
    d, b, s = e["dimensiones"], e.get("boquillas") or {}, e.get("superficie") or {}
    conv = e["convencion"]["exclusion"] or e["convencion"]["ajustada"] or {}
    return [
        e["tag"],
        e["revision"],
        dimension(d["diameter"]),
        dimension(d["height"]),
        f"{b.get('emparejadas', '')}/{b.get('faltan', '')}/{b.get('sobran', '')}",
        numero(b.get("error_posicion_medio_mm"), ".0f", " mm"),
        numero(b.get("error_azimut_medio_deg"), ".1f", "°"),
        f"{conv.get('sign', '')}·{conv.get('offset', '')} "
        + ("estable" if e["convencion"]["estable"] else e["convencion"]["cifra"]),
        numero(s.get("chamfer_mm"), ".0f", " mm"),
        numero(s.get("p95_mm"), ".0f", " mm"),
        "; ".join(e["notas"]),
    ]


CABECERA = ("Equipo", "Rev", "Diámetro", "Virola", "Boquillas ok/faltan/sobran", "Posición")
CABECERA += ("Azimut", "Convenio", "Chamfer", "P95", "Notas")
filas = [fila_html(e) for e in evaluacion["equipos"]]
html = "<table><thead><tr>" + "".join(f"<th>{c}</th>" for c in CABECERA) + "</tr></thead><tbody>"
html += "".join("<tr>" + "".join(f"<td>{escape(str(c))}</td>" for c in f) + "</tr>" for f in filas)
html += "</tbody></table>"
try:
    displayHTML(("<p><b>ENSAYO</b>: referencias fabricadas.</p>" if ENSAYO else "") + html)  # noqa: F821
except NameError:
    for f in filas:
        print(" | ".join(str(c) for c in f))
print(json.dumps(evaluacion["agregado"], ensure_ascii=False, indent=1))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Mapas de calor
# MAGIC
# MAGIC Nuestro modelo coloreado por su distancia a la referencia (0 a `escala_mm`), con el IFC
# MAGIC de TR en gris translúcido. Rojo = lo que sobra o está desplazado; las zonas grises sin
# MAGIC color encima son lo que no hemos modelado.

# COMMAND ----------

for e in evaluacion["equipos"]:
    if not e.get("mapa"):
        continue
    try:
        displayHTML(Path(e["mapa"]).read_text(encoding="utf-8"))  # noqa: F821
    except NameError:
        print(f"Mapa de {e['tag']}: {e['mapa']}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Resumen para el asistente de código
# MAGIC
# MAGIC Alias `E01`, `E02`… como en `01_procesar_lote`, errores relativos de las dimensiones y
# MAGIC errores en mm de boquillas y superficie. Sin tags, archivos ni dimensiones. Léelo antes
# MAGIC de pegarlo.

# COMMAND ----------

from bench.evaluar import resumen_compartible  # noqa: E402

print(json.dumps(resumen_compartible(evaluacion), ensure_ascii=False, indent=1))
