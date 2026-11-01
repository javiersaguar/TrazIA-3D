# F.5 · Cruce de marcas y cambios

La capa Plataforma consume el detector vectorial de Lectura sin modificarlo. La comparación
recibe los originales, verifica sus SHA y añade `layers.revision_marks`. Revisión consulta el
modo ligero de `/diff`, muestra las discrepancias y permite enfocar el PDF, documento y página
correspondientes. Seleccionar un campo devuelve el foco a su propia evidencia.

Cada campo se contrasta con sus lecturas de B, incluidas alternativas; un campo de boquilla
puede compartir ubicación con otro de la misma boquilla. Cada original tiene su propio sistema
de páginas: no se mezclan dos páginas 1 de documentos diferentes. Las cajas de A no se trasladan
a B cuando el campo ha desaparecido. Estas modificaciones no cambian el contrato de datos 0.3.

Las marcas son candidatas, no evidencia de aprobación ni garantía de que un cambio exista.
El modo API `marks=true` no crea IFC ni ejecuta ECC. La UI conserva el aviso en modo mock y
ofrece reintento cuando falla la API. El cruce se renueva tras cambiar campos.

## Cobertura y límites

- PDF vectorial: Δ/nubes según el detector ya implementado; se cruzan con cambios localizados.
- PDF raster o página dominada por imagen: sin lectura de marcas; no se acusa falta de marca.
- PDF mixto: solo se cruzan páginas legibles; las no legibles se enumeran.
- Máximo 100 páginas por original; truncamiento explícito.
- Original no disponible, SHA incorrecto o error PDF: estado explícito, sin discrepancias inventadas.
- Cambios sin localización en B: separados de los cambios sin marca próxima.
- No cambia fuentes, valores, GUID, aprobación ni ETag.

## Verificación

`uv run pytest -q tests/test_plataforma_revision_marks.py tests/test_api_revision_marks.py`:
diez pruebas, incluidas dos fuentes con página 1, hash incorrecto, raster con cabecera vectorial,
página 101, eliminación sin caja nueva, ubicación compartida por una boquilla y originales
ausentes o no verificables en la API sin error de servidor.
Los PDF de esas pruebas son sintéticos generados en memoria.

El caso de `web/tests/e2e/3d.spec.ts` «Revisión cruza marcas por documento…» usa un informe
sintético interceptado para verificar navegación a otro PDF/página y retorno al campo. No es una
medición de precisión del detector. Sus medidas previas pertenecen al estudio de Lectura citado
en el ROADMAP; esta integración no las reestima ni las convierte en precisión sobre planos TR.

F.5 permanece parcial por el detector de escaneados. C.4 y D.5 requieren un IFC de referencia de
TR; 3.8/E.6 requiere correcciones humanas representativas. Javier confirma que aún no se han
aportado esas evidencias. E.5 sigue pospuesta y no se inicia una sesión manual.
