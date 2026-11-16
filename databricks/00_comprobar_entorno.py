# Databricks notebook source
# MAGIC %md
# MAGIC # TrazIA-3D · 00 · Comprobar el entorno
# MAGIC
# MAGIC Instala las dependencias fijadas, comprueba versiones e importaciones y procesa los
# MAGIC documentos de ejemplo del repositorio (`examples/documents`, sintéticos) con las
# MAGIC estrategias B y D. Si este notebook acaba en verde, `01_procesar_lote` funcionará con
# MAGIC los datos del reto cambiando solo la ruta de entrada.
# MAGIC
# MAGIC Se abre desde la carpeta Git del repositorio: el notebook localiza la raíz subiendo
# MAGIC hasta `pyproject.toml`. También se puede ejecutar fuera de Databricks con
# MAGIC `python databricks/00_comprobar_entorno.py` (las celdas `%pip` se ignoran).

# COMMAND ----------

# MAGIC %pip install -q -r ./requirements.txt

# COMMAND ----------

try:
    dbutils.library.restartPython()  # noqa: F821 - solo existe en Databricks
except NameError:
    pass

# COMMAND ----------

import os
import platform
import sys
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def raiz_del_repo() -> Path:
    inicio = Path(globals().get("__file__", Path.cwd() / "x")).resolve().parent
    for carpeta in (inicio, *inicio.parents):
        if (carpeta / "pyproject.toml").is_file() and (carpeta / "src" / "trazia").is_dir():
            return carpeta
    raise RuntimeError(f"No encuentro la raíz de TrazIA-3D subiendo desde {inicio}")


RAIZ = raiz_del_repo()
if str(RAIZ / "src") not in sys.path:
    sys.path.insert(0, str(RAIZ / "src"))
os.environ.setdefault("TRAZIA_WARMUP", "0")
TRABAJO = Path(os.environ.get("TRAZIA_NB_TRABAJO", "/tmp/trazia/comprobacion"))
print("Raíz del repo:", RAIZ)
print("Python:", sys.version.split()[0], "·", platform.platform())
print("Trabajo temporal:", TRABAJO)

# COMMAND ----------

PAQUETES = (
    "pydantic",
    "ifcopenshell",
    "pdfplumber",
    "openpyxl",
    "pillow",
    "numpy",
    "scipy",
    "scikit-learn",
    "pint",
    "trimesh",
    "rtree",
    "opencv-python-headless",
    "onnxruntime",
    "rapidocr",
    "plotly",
    "pytest",
)
fijadas = {}
for linea in (RAIZ / "databricks" / "requirements.txt").read_text(encoding="utf-8").splitlines():
    nombre, _, resto = linea.partition("==")
    if resto and not linea.startswith("#"):
        fijadas.setdefault(nombre.strip().lower(), set()).add(resto.split(";")[0].strip())
faltan = []
for paquete in PAQUETES:
    try:
        instalada = version(paquete)
    except PackageNotFoundError:
        instalada = None
        faltan.append(paquete)
    esperada = fijadas.get(paquete, set())
    marca = "ok" if instalada in esperada else ("FALTA" if instalada is None else "distinta")
    print(f"{paquete:24} {instalada or '-':14} {marca}")
assert not faltan, f"Faltan paquetes: {faltan}. ¿Se ejecutó la celda %pip?"

# COMMAND ----------

import cv2  # noqa: E402
import ifcopenshell  # noqa: E402

from trazia.ingest import IMAGE_SUFFIXES  # noqa: E402
from trazia.ocr.engine import _rapidocr  # noqa: E402
from trazia.pipeline import process  # noqa: E402,F401
from trazia.strategies import STRATEGIES  # noqa: E402

print("IfcOpenShell", ifcopenshell.version, "· OpenCV", cv2.__version__)
print("Estrategias:", ", ".join(sorted(STRATEGIES)))
print("Imágenes admitidas:", IMAGE_SUFFIXES)
inicio = time.perf_counter()
_rapidocr()
print(f"Motor OCR cargado en {time.perf_counter() - inicio:.1f} s")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Prueba con los documentos de ejemplo
# MAGIC
# MAGIC `examples/documents` tiene el equipo V-101 en dos revisiones (plano GA y lista HDM).
# MAGIC Se procesa con B (reglas) y D (híbrido) y se comprueba que salen dos revisiones
# MAGIC correctas, dos IFC válidos y la comparación entre ellas.

# COMMAND ----------

import json  # noqa: E402

from trazia.lote import procesar_carpeta  # noqa: E402

resultados = {}
for estrategia in ("b_reglas", "d_hibrido"):
    salida = TRABAJO / estrategia
    inicio = time.perf_counter()
    filas = procesar_carpeta(
        RAIZ / "examples" / "documents",
        salida,
        estrategia=estrategia,
        dataset="synthetic",
        trabajo=TRABAJO / "cache",
    )
    resultados[estrategia] = filas
    print(f"\n{estrategia}: {time.perf_counter() - inicio:.1f} s")
    for fila in filas:
        print(
            f"  {fila.tag} rev{fila.revision}: {fila.estado}"
            f" · {fila.familia} LOD {fila.lod} · {fila.boquillas} boquillas"
            f" · {fila.pendientes} campos pendientes · {fila.avisos} avisos"
            + (f" · {fila.cambios} cambios" if fila.cambios is not None else "")
            + (f" · ERROR {fila.error}" if fila.error else "")
        )
    cambios = json.loads((salida / "V-101" / "cambios_revA_revB.json").read_text("utf-8"))
    assert [f.estado for f in filas] == ["ok", "ok"], filas
    assert cambios["changes"], "La comparación A→B debería encontrar cambios"
print("\nEntorno listo: el motor lee, modela, valida el IFC y compara revisiones.")
