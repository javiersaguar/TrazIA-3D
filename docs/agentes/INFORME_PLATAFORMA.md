# Informe de Plataforma

Rama `feat/plataforma`. Inicio: 26/10/2026. Sin push ni PR.

## Fase 1 · Contrato 0.3

Implementados el contrato de coordinación, migración 0.2 → 0.3 no destructiva,
comando `trazia migrate`, ejemplos y esquema/tipos web regenerados.
Los JSON de 0.2 se siguen cargando para que el baseline de Lectura no se rompa.
La migración retira la aprobación; una edición también invalida la huella.
Los estados accepted/corrected sincronizan reviewed; los supuestos y conflictos bloquean aprobar.

Se ha ajustado el aplanado web para admitir las dimensiones opcionales de otras familias.
No se han tocado estrategias, proveedores, generador, bench ni el 3D.
El origen de una envolvente admite coordenadas negativas o cero; sus tamaños y los parámetros
físicos siguen siendo positivos. Los nombres y tipos de Vector3 son los del contrato compartido.

### Dependencias e interfaces

- Grupo `api` vacío, preparado para las comprobaciones `uv run --extra api pytest` antes de la API.
- Sin dependencias nuevas en esta fase.
- Lectura puede importar FieldState, Channel, Interval, Alternative, Vector3, Envelope y RunInfo.
- `confidence_raw` conserva el score heredado; no se presenta la migración como calibración.

### Comprobaciones

- `uv run --extra api pytest -q`: 40/40, incluidas cinco pruebas nuevas del contrato.
- `uv run ruff check .`: correcto. Formato de todos los archivos Python: correcto.
- `pnpm gen:types`, typecheck y build: correctos.
- Lint web: cero errores, un aviso previo de TanStack Table en Proyecto.
- `pnpm test:unit`: 9/9.
- `pnpm test:e2e`: 6/6 sin variable de API y 6/6 con NEXT_PUBLIC_API_URL definido.
  En esta fase la variable todavía no cambia el transporte: ambos recorridos son offline.
- Comprobado que no hay cambios en las carpetas de Lectura ni en el 3D.

### Incidencia previa en el formateador

`uv run ruff format --check .` con Ruff 0.17.2 revisa también los bloques Python de Markdown y
rechaza el formato de `docs/COORDINACION-BACKEND.md`, que está protegido por el reparto.
No se modifica ese documento. La comprobación de los archivos Python se ejecuta por separado.
Se propone al propietario excluir Markdown del formato del código o formatear el documento.

## Fase 2 · API base

API FastAPI con SQLModel, migración Alembic 0001, SQLite/Postgres configurable y almacén SHA-256.
Seed idempotente de A/B; documentos, revisiones, campos, auditoría, aprobación, trabajos,
cancelación y SSE persistente. Endpoints y ejemplos en [API.md](../API.md).
ETag/If-Match y claves idempotentes de 24 horas protegen las escrituras.
El multipart tiene límite también sin Content-Length. Solo se permite CORS local.

El adaptador usa la firma pactada de process. Hasta que Lectura publique trazia.pipeline,
solo ejecuta b_reglas; rechaza explícitamente estrategias/proveedores inexistentes.
No modifica las carpetas de Lectura. Los resultados siguen siendo DRAFT.

Comprobación completa: 52/52 pruebas Python pasan; lint y formato Python correctos.
Pruebas de API: 12 casos (persistencia tras reiniciar, dedupe, idempotencia, concurrencia,
aprobación/invalidez, SSE/reanudación, trabajos y límites). Costes y GPU no medidos permanecen null;
el baseline registra cero llamadas externas y cero coste de proveedor.
Las nuevas dependencias están inventariadas en THIRD_PARTY.md.

### Necesidades de Lectura y límites de esta fase

- process e InputDocument/StageEvent/PipelineResult según el contrato compartido.
- Ejecutable/interfaz del estudio para conectar POST /estudio; GET ya sirve su archivo si existe.
- BCF/multiesquema y copiloto tienen rutas explícitas pendientes (501/503) hasta sus fases.
- La cancelación impide publicar tras cancelación; un parseo nativo en curso es cooperativo.
- No hay autenticación multiusuario: el actor es una declaración del revisor local.
- La web todavía usa mocks: el transporte real se conectará en la fase 5.

