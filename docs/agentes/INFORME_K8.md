# K8 · sesión 08/11/2026

Base: `origin/main` 46601c1; worktree propio `TrazIA-3D-k8`, rama
`feat/k8-modelado-planos`. Datos sintéticos públicos, sin GPU ni datos privados.

## Entregado

- Altas/bajas reversibles de boquillas, plataformas y escaleras, snapshots completos,
  IDs/GUID persistentes, validación de colocación, unidades explícitas y procedencia `diseno`.
  Las plataformas/escaleras exigen aceptar LOD 3; no se ocultan al deshacer otras órdenes.
- Matriz extendida a horizontal, columna, tanque y envolventes LOD 1 de las siete familias.
  Validación conjunta de soportes, continuidad, techos, direcciones y dimensiones.
- Formulario de piezas y selección de equipo/proyecto/revisión en Proponer cambios. Borradores
  estructurales desde chat determinista, con aclaraciones y sin ejecutar ni confirmar órdenes.
- GA nuevo A3, PDF vectorial y SVG, desde la geometría efectiva del IFC: tres vistas, escala,
  cotas exteriores, cajetín, manifiesto y descarga del IFC exacto. Cola CPU, SSE, idempotencia,
  ETag y bloqueo de publicación al cancelar o editar la base. Originales intactos.
- Informe K6 paginado para evitar perder operaciones largas. ReportLab añadido al extra `api`;
  ya estaba fijado en `dev`: ninguna versión nueva en `uv.lock`.
- OpenAPI y tipos HTTP regenerados. Contrato `Revision` 0.3 sin cambios.

## Correcciones previas necesarias

- Las referencias de altura total y elevación se calculan con el faldón final del lote.
- Un no-op de texto informa del caso sin lanzar una excepción de formato numérico.
- La publicación vuelve a comprobar el ETag dentro de la transacción; prueba con edición
  intercalada después de la comprobación inicial y antes de publicar.
- La web conserva/bloquea aclaraciones del chat y vuelve obsoleta la previsualización si
  cambia actor, campos, piezas o LOD. El estado terminal del trabajo se publica en la misma
  transacción que su resultado para cerrar la carrera con cancelación.
- El selector respeta `project_id` al buscar revisiones de equipos fuera de DEMO-PLANT.

## Comprobado

- Ruff check y format check completos: verdes.
- Suite Python completa en contenedor Linux CPU: **506 pruebas, 0 fallos, 262,31 s**.
  Dos avisos anteriores: deprecación Starlette/httpx y división inválida en una prueba que
  inyecta una dirección IFC corrupta. Windows bloquea el ejecutable pytest local; no se ha
  desactivado esa protección. Python ejecutado en contenedor con la imagen CPU existente.
- K8: **37 pruebas**; repetición tras ampliar la comprobación de reversión API completa y
  rechazo de GA como original: 37 correctas, 20,15 s.
- Web Windows: typecheck, lint, **53 unitarias** y build correctos. Lint conserva el aviso
  previo de React Compiler/TanStack Table en `project-workspace.tsx`.
- Playwright sobre build, API aislada 8058, puerto web de pruebas 3355 y SwiftShader CPU:
  alta de boquilla por chat → IFC cargado → confirmación → descarga GA → propuesta de deshacer;
  parámetros incompletos/LOD explícito; edición de un horizontal del proyecto FAMILY-TEST.
  Tres recorridos correctos; capturas del formulario en oscuro y claro.
- Siete GA sintéticos generados y renderizados; comprobación de A3, geometría en mm, cotas,
  márgenes y texto. Tiempos medidos y muestras en [evidencias K8](../evidencias/k8/README.md).

## Reproducir

```powershell
uv sync --frozen --extra dev --extra api --extra geo
uv run ruff check .
uv run ruff format --check .
uv run python -m pytest -q
uv run python scripts/verify_k8_drawings.py
cd web
corepack pnpm@10.18.0 typecheck
corepack pnpm@10.18.0 lint
corepack pnpm@10.18.0 test:unit
corepack pnpm@10.18.0 build
```

El test K8 corre conectado a la API con la configuración habitual de Playwright. El tercer
caso es opcional: `PW_K8_FAMILY_TAG=H-K8`, con un fixture horizontal `FAMILY-TEST` cargado
en el almacén de prueba; no modifica los equipos de la demo del usuario.

## Límites

No hay líneas ocultas ni validación de fabricación/esfuerzos. Las cotas son extensiones de la
malla completa, no dimensiones interiores. Las bombas/compresores siguen como envolventes.
Se evaluaron multiequipo/RBAC: implementación aplazada, sin atribuir permisos al nombre del actor.
Cancelar impide publicar; no termina inmediatamente un hilo nativo ya iniciado. K8 queda
marcado en el roadmap con estas condiciones; K2/K4 humanos, modelo local K5, cierre K7,
datos TR y sesiones humanas conservan sus pendientes.
