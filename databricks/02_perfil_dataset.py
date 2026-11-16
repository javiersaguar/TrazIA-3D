# Databricks notebook source
# MAGIC %md
# MAGIC # TrazIA-3D · 02 · Perfil del dataset
# MAGIC
# MAGIC Lo primero que se ejecuta el día 25, antes del lote: recorre la carpeta de documentos y
# MAGIC cuenta lo que decide la estrategia, sin abrir nada a mano.
# MAGIC
# MAGIC - Equipos, revisiones y tipos de documento (GA, HDM, VESOR, ESTRUCTURA).
# MAGIC - PDF vectoriales, escaneados, mixtos o con el texto en curvas.
# MAGIC - Formato, giro y número de páginas.
# MAGIC - Unidades, notación de boquillas (DN, NPS, clase de brida) e idioma.
# MAGIC - Hojas de los XLSX, resolución de las imágenes e IFC de referencia.
# MAGIC
# MAGIC La salida son recuentos y formas de nombre (`GAD_A-9_revA.pdf`). No lleva nombres de
# MAGIC archivo, tags ni textos, así que se puede pegar al asistente de código después de leerla
# MAGIC (`docs/FLUJO_IA.md`).
# MAGIC
# MAGIC Parámetros:
# MAGIC - **entrada**: carpeta de documentos. Vacía = `examples/documents` del repo (sintéticos).
# MAGIC - **max_paginas**: páginas leídas por PDF (30 basta para el perfil; más es más lento).
# MAGIC - **salida**: carpeta donde guardar `perfil.json` (opcional).

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
if str(RAIZ / "src") not in sys.path:
    sys.path.insert(0, str(RAIZ / "src"))

ENTRADA = parametro("entrada", "", "Entrada (/Volumes/...)")
MAX_PAGINAS = int(parametro("max_paginas", "30", "Páginas por PDF") or 30)
SALIDA = parametro("salida", "", "Guardar perfil.json en (opcional)")
if not ENTRADA:
    ENTRADA = str(RAIZ / "examples" / "documents")
    print("Sin entrada: se usan los ejemplos sintéticos del repo.")
ENTRADA = Path(ENTRADA)
if not ENTRADA.is_dir():
    raise FileNotFoundError(f"No existe la carpeta de entrada {ENTRADA}")
print(f"Entrada {ENTRADA} · hasta {MAX_PAGINAS} páginas por PDF")

# COMMAND ----------

from trazia.perfil import avisos, perfilar  # noqa: E402

perfil = perfilar(ENTRADA, max_paginas=MAX_PAGINAS)
lecturas = avisos(perfil)
print(
    f"Perfil en {perfil['segundos']} s: {perfil['archivos']['total']} archivos, "
    f"{perfil['equipos']['total']} equipos, {perfil['pdf']['documentos']} PDF."
)
print("\nQué mirar primero:")
for linea in lecturas or ["Nada llamativo: lanzar 01_procesar_lote con uno o dos equipos."]:
    print(f"  - {linea}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Perfil completo (para el equipo y para el asistente)
# MAGIC
# MAGIC Recuentos agregados. Léelo antes de pegarlo: si alguna forma de nombre fuera de la
# MAGIC convención resultara reconocible, se describe con palabras en lugar de pegarla.

# COMMAND ----------

texto = json.dumps({**perfil, "avisos": lecturas}, ensure_ascii=False, indent=1, default=str)
print(texto)
if SALIDA:
    destino = Path(SALIDA)
    if destino.resolve().is_relative_to(RAIZ.resolve()):
        raise ValueError("La salida no puede estar dentro del repositorio: usa un volumen o /tmp")
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "perfil.json").write_text(texto, encoding="utf-8")
    print(f"Guardado en {destino / 'perfil.json'}")
