# Databricks notebook source
# MAGIC %md
# MAGIC # TrazIA-3D · 04 · Todo de una vez
# MAGIC
# MAGIC Encadena los notebooks 02, 01 y 03 y añade el triaje y las cifras del pitch:
# MAGIC
# MAGIC 1. **perfil** del dataset (`trazia.perfil`): solo recuentos;
# MAGIC 2. **lote** con la estrategia elegida (`trazia.lote.procesar_carpeta`);
# MAGIC 3. **evaluación** contra los IFC de TR si se da la carpeta `referencias`;
# MAGIC 4. **triaje** de los fallos (`bench.triaje`): categoría, etapa y alias `E01`…;
# MAGIC 5. **cifras del evento** (`bench.cifras`): `cifras_evento.json` en la salida.
# MAGIC
# MAGIC Los widgets son los de 01 más `referencias`. Lo que se puede llevar al portátil son las
# MAGIC salidas de la última celda y `cifras_evento.json` (agregados sin tags ni rutas). En el
# MAGIC portátil: `uv run python -m bench.cifras aplicar cifras_evento.json`
# MAGIC (docs/AUTOMATIZACION.md).
# MAGIC Las tablas con tags y los mapas se quedan en Databricks.

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
for ruta in (RAIZ / "src", RAIZ):  # trazia y bench
    if str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))
os.environ.setdefault("TRAZIA_WARMUP", "0")

from trazia.strategies import STRATEGIES  # noqa: E402

ENTRADA = parametro("entrada", "", "Entrada (/Volumes/...)")
SALIDA = parametro("salida", "", "Salida (/Volumes/...)")
REFERENCIAS = parametro("referencias", "", "IFC de TR (/Volumes/...; vacío = sin evaluar)")
ESTRATEGIA = parametro("estrategia", "d_hibrido", "Estrategia", sorted(STRATEGIES))
DATASET = parametro("dataset", "real", "Dataset", ["real", "synthetic"])
TAGS = [t.strip() for t in parametro("tags", "", "Tags (coma)").split(",") if t.strip()]
PROCESOS = int(parametro("procesos", "1", "Procesos") or 1)
PROVEEDORES = [p.strip() for p in parametro("proveedores", "", "Visión (coma)").split(",")]
PROVEEDORES = [p for p in PROVEEDORES if p] or None
TRABAJO = Path(parametro("trabajo", "/tmp/trazia/trabajo", "Cachés"))
MAPAS = Path(parametro("mapas", "/tmp/trazia/mapas", "Carpeta de mapas HTML"))

if not ENTRADA:
    ENTRADA, DATASET = str(RAIZ / "examples" / "documents"), "synthetic"
    print("Sin entrada: se usan los ejemplos sintéticos del repo.")
if not SALIDA:
    SALIDA = "/tmp/trazia/salida"
    print("Sin salida: /tmp/trazia/salida es temporal y se pierde al cerrar la sesión.")
ENTRADA, SALIDA = Path(ENTRADA), Path(SALIDA)
for carpeta in (SALIDA, MAPAS):
    if carpeta.resolve().is_relative_to(RAIZ.resolve()):
        raise ValueError("Ni la salida ni los mapas pueden estar dentro del repositorio")
if not ENTRADA.is_dir():
    raise FileNotFoundError(f"No existe la carpeta de entrada {ENTRADA}")
SALIDA.mkdir(parents=True, exist_ok=True)
print(f"Entrada {ENTRADA}\nSalida  {SALIDA}\nEstrategia {ESTRATEGIA} · dataset {DATASET}")
print(f"Referencias: {REFERENCIAS or 'ninguna (sin evaluación)'}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1 · Perfil del dataset

# COMMAND ----------

from trazia.perfil import avisos, perfilar  # noqa: E402

inicio = time.perf_counter()
perfil = perfilar(ENTRADA)
(SALIDA / "perfil.json").write_text(
    json.dumps(perfil, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(f"Perfil en {time.perf_counter() - inicio:.0f} s: {perfil['equipos']['total']} equipos.")
for aviso in avisos(perfil):
    print(f"- {aviso}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2 · Lote

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
print(f"{correctas} de {len(filas)} revisiones correctas en {time.perf_counter() - inicio:.0f} s.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3 · Evaluación contra los IFC de TR
# MAGIC
# MAGIC Solo con el widget `referencias`. Sin él no se fabrica ningún ensayo: para eso está 03.

# COMMAND ----------

evaluacion = None
if REFERENCIAS:
    from bench.evaluar import evaluar  # noqa: E402

    inicio = time.perf_counter()
    evaluacion = evaluar(SALIDA, Path(REFERENCIAS), mapas=MAPAS)
    (SALIDA / "evaluacion_tr.json").write_text(
        json.dumps(evaluacion, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"{len(evaluacion['equipos'])} equipos evaluados en {time.perf_counter() - inicio:.0f} s;"
        f" sin referencia: {len(evaluacion['sin_referencia'])}. Mapas en {MAPAS}."
    )
else:
    print("Sin referencias: se salta la evaluación.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4 · Triaje de fallos

# COMMAND ----------

from bench.triaje import informe, triar  # noqa: E402

triaje = triar(SALIDA)
(SALIDA / "triaje.json").write_text(
    json.dumps(triaje, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(informe(triaje))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5 · Cifras del evento y resumen para el asistente
# MAGIC
# MAGIC Todo lo de esta celda son agregados con alias: se puede copiar al portátil. Léelo antes.

# COMMAND ----------

from bench.cifras import cifras_evento  # noqa: E402
from trazia.lote import resumen_compartible  # noqa: E402

cifras = cifras_evento(perfil, filas, evaluacion, dataset=DATASET)
(SALIDA / "cifras_evento.json").write_text(
    json.dumps(cifras, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("cifras_evento.json:")
print(json.dumps(cifras, ensure_ascii=False, indent=1))
print("\nResumen del lote:")
print(json.dumps(resumen_compartible(filas), ensure_ascii=False, indent=1))
if evaluacion:
    from bench.evaluar import resumen_compartible as resumen_evaluacion  # noqa: E402

    print("\nResumen de la evaluación:")
    print(json.dumps(resumen_evaluacion(evaluacion), ensure_ascii=False, indent=1))
print(
    f"\nDescarga {SALIDA / 'cifras_evento.json'} y aplícalo con `python -m bench.cifras aplicar`."
)
