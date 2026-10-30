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

## Interfaces

**Lo que Lectura entrega a Plataforma:**

- `bench.estudio.ejecutar(config, on_event)` se podrá llamar en proceso, para que `POST /estudio`
  (hoy devuelve 503) lo lance como trabajo de la cola.
  - `config`: datos, variantes, casos, degradaciones, remuestreos y semilla, con los mismos
    nombres que la CLI.
  - `on_event(StageEvent)` informa del progreso.
  - Devuelve la ruta de `estudio.json`.
  - La firma exacta se publicará en el informe en cuanto exista.
- `estudio.json` sigue la Interfaz 3. `interval_coverage` y `ece` pasan a estar rellenos.
- La revisión que devuelve `process` traerá `confidence` calibrada, `confidence_raw` e `interval`.
  Son campos opcionales que el contrato 0.3 ya tiene. No cambia ningún nombre.
- Etapas de `StageEvent` nuevas o activadas: `calibrate` y `extract_detector`. Ya están en el grafo
  de la web.

**Lo que Lectura necesita de Plataforma:** nada que bloquee. Si la memoria de revisión (3.2) necesita
una función pública para comprobar la huella de la aprobación, Lectura usará la que exista en
`revisions.py` o `review.py`. Si no existe, la pedirá por escrito.

## Tareas que quedan libres para Plataforma

- **H.1 / H.3:** `POST /estudio` como trabajo, usando `bench.estudio.ejecutar`.
- **3.7 / H.7:** escala con la cola Redis sobre una estrategia que cubra el conjunto, coste por
  equipo y diagrama.
- **3.8:** aprendizaje activo. Lectura expondrá cómo recalibrar desde correcciones humanas en
  `calibration/`, y Plataforma lo conecta desde la API.
- **4.2:** modo offline `TRAZIA_OFFLINE=1`. La caché de visión ya existe en `vision/cache.py`.
- CORS de la API para otros puertos locales de la web (3300 y 33xx, según `NECESIDADES.md` del 3D).
- Selector de revisión de la web para revisiones que no sean A/B.

## Aviso de solape

El 30/10 por la tarde, el agente 3D del frontend tenía trabajo **sin commit** en
`../TrazIA-3D-web-3d` sobre carpetas de Plataforma:

- `src/trazia/families/detail.py` (nuevo), `families/__init__.py`, `ifc.py` y `api/app.py`;
- los IFC públicos de `web/public/demo/ifc/`;
- `tests/test_pipeline.py`, `tests/test_plataforma_ifc.py` y `tests/test_frontend_detail_ifc.py`.

Es su tarea 2.6 (enriquecer el IFC). Antes de editar esos ficheros, Plataforma debe esperar a que se
fusione o coordinarse con Javier.
