# Sesión del agente Lectura · desde el 30/10/2026

Qué tareas del [ROADMAP](../ROADMAP.md) toma el agente **Lectura** en esta sesión, para que el agente
**Plataforma** sepa qué no tocar. El reparto general de carpetas sigue en
[COORDINACION-BACKEND.md](../COORDINACION-BACKEND.md). Este documento solo concreta la sesión.

- Rama y worktree: `feat/lectura` en `../TrazIA-3D-lectura`, creada desde `main` 4707382.
- Push de `feat/lectura` al cerrar cada tarea. La fusión a `main` la decide Javier.
- Commits como Javier Saguar, sin coautores ni firmas.

## Tareas que toma Lectura (en este orden)

| # | Tarea | Hecho cuando |
| --- | --- | --- |
| 1 | **3.2** Memoria de revisión solo con la rev1 **aprobada** | D omite la memoria (con aviso) si la revisión anterior es DRAFT o su huella no cuadra. Lleva pruebas |
| 2 | **3.3** Calibración isotónica + intervalos conformes + curva riesgo-cobertura | Paquete `src/trazia/calibration/` y etapa `calibrate` en `pipeline.process`. ECE y cobertura medidas en S-reservado |
| 3 | **2.11** Primer estudio A/B/C/D en S-dev | Tabla con IC95 y `generated/estudio/estudio.json` según la Interfaz 3 |
| 4 | **3.4** Fusión aprendida, selector por tipo de documento y ablaciones de D | Estudio completo con S-reservado (H1–H6) y resultados en `docs/ESTUDIO.md` |
| 5 | **2.2 / 0.10** PaddleOCR-VL medido en la RTX 5070 | VRAM y segundos por página en `docs/PLATAFORMA.md`. Integrado en `ocr/` si cabe |
| 6 | **2.4** Detector propio Florence-2 ajustado con S-dev | Medido en S-reservado y conectado como canal `detector` de D, con ablación |
| 7 | Si queda tiempo: **2.1** (VESOR) y **2.5** (ColQwen2/ColSmol en `rag/`) | Pruebas y medición frente a la huella actual |

Fuera de esta sesión: **1.9**, porque falta una credencial de un segundo proveedor real.

La GPU (RTX 5070) estará ocupada durante las tareas 3, 5 y 6. Plataforma no debe lanzar mediciones
con GPU sin avisar.

## Archivos que edita Lectura

- `src/trazia/{pipeline,ingest,extraction}.py`
- `src/trazia/{strategies,extractors,vision,ocr,geometry2d,rag,reconcile,calibration}/`
  (`calibration/` es nuevo)
- `bench/`, `synthetic/`, `training/`
- `tests/test_bench.py` y `tests/test_lectura_*.py`
- `generated/estudio/` y `generated/calibration/`, que salen de los scripts
- `docs/BENCH.md`, la sección de resultados de `docs/ESTUDIO.md`, la tabla 0.10 de `docs/PLATAFORMA.md`
  y `docs/agentes/INFORME_LECTURA.md`
- `pyproject.toml`: solo los extras `vision`, `ocr`, `rag` y `train`
- `THIRD_PARTY.md`: solo se añaden líneas, para torch, transformers y PaddleOCR

## Archivos que Lectura no toca

- Plataforma:
  - `src/trazia/{model,ifc,revisions,review,cli,app,viewer,bcf}.py`
  - `src/trazia/families/`
  - `src/trazia/{api,store,queue,copilot}/`
  - pruebas `test_api*`, `test_plataforma_*`, `test_pipeline.py` y `test_app.py`
  - Docker y CI
- Toda la carpeta `web/`.
- `docs/ROADMAP.md`, `docs/DECISIONES.md`, `AGENTS.md`, `CONTRIBUTING.md` y `tests/conftest.py`. Las
  propuestas de cambio irán en el informe.

## Trabajo en paralelo, sin dependencias

Ningún agente espera al otro. Las fronteras son las que **ya existen en `main`** y no cambian en esta
sesión.

- **CLI del estudio, estable:** `python -m bench.estudio --datos --variantes --casos --degradaciones
  --remuestreos --semilla --salida`. Escribe `<salida>/estudio.json` según la Interfaz 3.
  - Lectura no renombra ni quita argumentos.
  - Plataforma lanza el estudio como subproceso desde su trabajo `POST /estudio`. No importa
    código nuevo de Lectura.
- **`pipeline.process`, misma firma.**
  - Lectura solo rellena campos opcionales que el contrato 0.3 ya tiene: `confidence` calibrada,
    `confidence_raw`, `interval` y `state="abstained"`.
  - Las pruebas de Plataforma no deben dar por hecho que esos campos vengan vacíos ni rellenos.
- **Contrato (`model.py`):** nadie lo cambia en esta sesión.
- **Correcciones humanas (3.8):** Plataforma las exporta a un JSONL con el formato del encargo de
  Plataforma. Lectura lo leerá más adelante para recalibrar. Ninguno llama al código del otro.
- **Etapas de `StageEvent`:** `calibrate` y `extract_detector` ya están en el grafo de la web. No se
  añaden ids nuevos.

Lectura no necesita nada de Plataforma. Para la memoria de revisión (3.2) usa las funciones que ya
existen en `revisions.py` y `review.py`. Si faltara alguna, la escribe dentro de sus carpetas y no
edita las de Plataforma.

## Tareas de Plataforma en esta sesión

El detalle está en su encargo.

- **H.1 / H.3:** `POST /estudio` como trabajo de la cola, lanzando la CLI del estudio.
- **4.2:** modo offline con caché de resultados de trabajos en el almacén de la API.
- **3.7 / H.7:** escala medida en CPU sobre lo que hay en `main`, y diagrama y coste de 400 × 4.
- **3.8, parte de datos:** registro y exportación de correcciones humanas.
- **CORS configurable** por variable de entorno.

## Trabajo del agente 3D en carpetas de Plataforma

El agente 3D hizo commit de su tarea 2.6 (IFC con detalle trazado) en la rama local `feat/web-3d`
(`6abac69`, sin subir). Esa rama toca `families/detail.py`, `families/__init__.py`, `ifc.py`,
`api/app.py` (puertos CORS y `details=` en el IFC) y `tests/test_frontend_detail_ifc.py`.

Plataforma crea su worktree **desde `feat/web-3d`** y así parte de esos cambios. Lectura no toca
ninguno de esos ficheros.
