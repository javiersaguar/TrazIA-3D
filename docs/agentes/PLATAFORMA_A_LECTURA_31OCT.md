# Pendientes para coordinar con Lectura · 31/10

No se han editado sus carpetas. Base usada: main `8713f7a`.

## Escala: cobertura antes de extrapolar IFC válidos

El lote anterior conserva 173 DRAFT / 336 revisiones y 163 errores. El inventario está en
`docs/evidencias/fase3/31oct/revisiones-pendientes.jsonl`: 84 boquillas incompletas,
63 campos ausentes, 16 incoherencias geométricas. Son 161 escaneados y dos vectoriales.

Se reprodujeron D-712/1 y D-712/2 con D sin proveedores de visión. Ambos fallan todavía por
menos de tres boquillas completas. Los eventos geometry2d declaran dos en alzado y tres/cuatro
muñones en planta, respectivamente. Resultado: `docs/evidencias/fase3/31oct/triage-d712.json`.
Es un diagnóstico de S-reservado; no ajustar con estos casos ni usar su verdad como entrada.
Localizar un análogo en S-dev y reevaluar después con el lector congelado.

`scripts/measure_scale.py` y `scripts/run_scale.py` admiten `--tags` y `--exigir-todos`.
El segundo flag conserva informes y devuelve 2 si falta algún DRAFT; no convierte una
terminación con error en producción válida. El artefacto `generated/fusion/fusion.json` no
estaba en el checkout principal al comprobarlo; no se midió D+fusión sin sus pesos.

## Few-shot y prioridades

La API ofrece `GET /learning/few-shot?path=...&strategy=...&target_revision_id=...&limit=3`:
pares user/assistant aprobados, huellas, recorte PDF y política de uso. Excluye el equipo y
documentos consultados y retira ejemplos al revocar la aprobación. Actualmente los utiliza
el contexto del Copiloto; `applied_to_extraction=false` evita afirmar que los lectores ya
los consumen. Pendiente conectar sus prompts y evaluar el ajuste de prioridades de fuentes
con separación por equipo/conjunto. Mantener ejemplos como datos, sin trasplantar sus valores
ni sus citas a la extracción actual.

La caché de trabajos v3 incorpora SHA de fusión/calibración y no guarda si cambian durante
la ejecución. La recalibración CPU existente sigue siendo una propuesta sin activar.

## Muestra humana

`generated/piloto-manual-31/` contiene A/B generadas por B/CPU (22/26 campos con score bruto).
Está preparado en la web 3120 y API 8022 offline, sin simulación de acciones humanas.
El revisor inicia/finaliza una sesión; la API distingue pruebas y agrupa por equipo/dataset.
La muestra humana representativa sigue vacía. Protocolo: `docs/MUESTRA_REVISION_MANUAL.md`.
