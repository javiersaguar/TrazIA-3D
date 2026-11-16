# Databricks notebook source
# MAGIC %md
# MAGIC # TrazIA-3D · 01 · Procesar un lote
# MAGIC
# MAGIC Lee una carpeta con los documentos del reto (normalmente un volumen de Unity Catalog,
# MAGIC `/Volumes/<catálogo>/<esquema>/<volumen>/...`), agrupa por equipo y revisión según el
# MAGIC nombre (`GAD_<TAG>_rev<R>.pdf`, `HDM_<TAG>_rev<R>.xlsx`, `VESOR_<TAG>.pdf`…) y deja en
# MAGIC la salida, por equipo, el contrato `revision.json`, el `modelo.ifc` DRAFT validado, los
# MAGIC eventos del pipeline y la comparación entre revisiones consecutivas. Al final escribe
# MAGIC `resumen.csv` y `resumen.json`.
# MAGIC
# MAGIC Parámetros (widgets arriba del notebook):
# MAGIC - **entrada**: carpeta de documentos. Vacía = `examples/documents` del repo (sintéticos).
# MAGIC - **salida**: carpeta de resultados. Conviene un volumen para que persista; vacía =
# MAGIC   `/tmp/trazia/salida`, que se pierde al cerrar la sesión.
# MAGIC - **estrategia**: `d_hibrido` (recomendada), `b_reglas`, `c_rag`, `a_geometria`…
# MAGIC - **dataset**: `real` para los datos de TR, `synthetic` para los ejemplos.
# MAGIC - **tags**: equipos a procesar separados por comas; vacío = todos.
# MAGIC - **procesos**: equipos en paralelo (1 = secuencial).
# MAGIC - **proveedores**: proveedores de visión separados por comas (vacío = ninguno, sin
# MAGIC   llamadas externas). Con datos de TR, solo los servicios de la plataforma autorizados.
# MAGIC
# MAGIC No se escriben resultados dentro de la carpeta Git: ni datos de TR ni IFC van al repo.
# MAGIC Fuera de Databricks los widgets se sustituyen por variables `TRAZIA_NB_<NOMBRE>`.

# COMMAND ----------

# MAGIC %pip install -q -r ./requirements.txt

# COMMAND ----------

try:
    dbutils.library.restartPython()  # noqa: F821 - solo existe en Databricks
except NameError:
    pass

# COMMAND ----------

import os
import sys
import time
from pathlib import Path


def raiz_del_repo() -> Path:
    inicio = Path(globals().get("__file__", Path.cwd() / "x")).resolve().parent
    for carpeta in (inicio, *inicio.parents):
        if (carpeta / "pyproject.toml").is_file() and (carpeta / "src" / "trazia").is_dir():
            return carpeta
    raise RuntimeError(f"No encuentro la raíz de TrazIA-3D subiendo desde {inicio}")


def parametro(nombre: str, defecto: str, etiqueta: str, opciones=None) -> str:
    try:
        if opciones:
            dbutils.widgets.dropdown(nombre, defecto, opciones, etiqueta)  # noqa: F821
        else:
            dbutils.widgets.text(nombre, defecto, etiqueta)  # noqa: F821
        return dbutils.widgets.get(nombre).strip()  # noqa: F821
    except NameError:
        return os.environ.get(f"TRAZIA_NB_{nombre.upper()}", defecto).strip()


RAIZ = raiz_del_repo()
if str(RAIZ / "src") not in sys.path:
    sys.path.insert(0, str(RAIZ / "src"))
os.environ.setdefault("TRAZIA_WARMUP", "0")

from trazia.strategies import STRATEGIES  # noqa: E402

ENTRADA = parametro("entrada", "", "Entrada (/Volumes/...)")
SALIDA = parametro("salida", "", "Salida (/Volumes/...)")
ESTRATEGIA = parametro("estrategia", "d_hibrido", "Estrategia", sorted(STRATEGIES))
DATASET = parametro("dataset", "real", "Dataset", ["real", "synthetic"])
TAGS = [t.strip() for t in parametro("tags", "", "Tags (coma)").split(",") if t.strip()]
PROCESOS = int(parametro("procesos", "1", "Procesos") or 1)
PROVEEDORES = [p.strip() for p in parametro("proveedores", "", "Visión (coma)").split(",")]
PROVEEDORES = [p for p in PROVEEDORES if p] or None
TRABAJO = Path(parametro("trabajo", "/tmp/trazia/trabajo", "Cachés"))

if not ENTRADA:
    ENTRADA, DATASET = str(RAIZ / "examples" / "documents"), "synthetic"
    print("Sin entrada: se usan los ejemplos sintéticos del repo.")
if not SALIDA:
    SALIDA = "/tmp/trazia/salida"
    print("Sin salida: /tmp/trazia/salida es temporal y se pierde al cerrar la sesión.")
ENTRADA, SALIDA = Path(ENTRADA), Path(SALIDA)
if SALIDA.resolve().is_relative_to(RAIZ.resolve()):
    raise ValueError("La salida no puede estar dentro del repositorio: usa un volumen o /tmp")
if not ENTRADA.is_dir():
    raise FileNotFoundError(f"No existe la carpeta de entrada {ENTRADA}")
print(f"Entrada {ENTRADA}\nSalida  {SALIDA}\nEstrategia {ESTRATEGIA} · dataset {DATASET}")
print(f"Proveedores de visión: {', '.join(PROVEEDORES or []) or 'ninguno'}")

# COMMAND ----------

from trazia.lote import agrupar  # noqa: E402

grupos = agrupar(ENTRADA)
if TAGS:
    grupos = {t: r for t, r in grupos.items() if t.upper() in {x.upper() for x in TAGS}}
print(f"{len(grupos)} equipos, {sum(len(r) for r in grupos.values())} revisiones")
for tag, revisiones in grupos.items():
    for etiqueta, docs in revisiones.items():
        print(f"  {tag} rev{etiqueta}: {', '.join(d.path.name for d in docs)}")
assert grupos, "No hay documentos con nombres del reto (GAD_/HDM_/VESOR_<TAG>_rev<R>)"

# COMMAND ----------

from trazia.lote import procesar_carpeta  # noqa: E402

inicio = time.perf_counter()
filas = procesar_carpeta(
    ENTRADA,
    SALIDA,
    estrategia=ESTRATEGIA,
    proveedores=PROVEEDORES,
    dataset=DATASET,
    trabajo=TRABAJO,
    procesos=PROCESOS,
    tags=TAGS or None,
)
correctas = sum(f.estado == "ok" for f in filas)
print(
    f"{correctas} de {len(filas)} revisiones correctas en {time.perf_counter() - inicio:.0f} s."
    f" Resumen: {SALIDA / 'resumen.csv'}"
)

# COMMAND ----------

from html import escape  # noqa: E402

COLUMNAS = ("tag", "revision", "estado", "familia", "lod", "boquillas", "campos", "pendientes")
COLUMNAS += ("avisos", "cambios", "segundos", "error")


def celda(fila, columna) -> str:
    valor = getattr(fila, columna)
    return "" if valor is None else str(valor)


def tabla_html(filas) -> str:
    cabecera = "".join(f"<th>{c}</th>" for c in COLUMNAS)
    cuerpo = "".join(
        "<tr>" + "".join(f"<td>{escape(celda(f, c))}</td>" for c in COLUMNAS) + "</tr>"
        for f in filas
    )
    return f"<table><thead><tr>{cabecera}</tr></thead><tbody>{cuerpo}</tbody></table>"


try:
    displayHTML(tabla_html(filas))  # noqa: F821 - solo existe en Databricks
except NameError:
    for fila in filas:
        print(" | ".join(celda(fila, c) for c in COLUMNAS))
