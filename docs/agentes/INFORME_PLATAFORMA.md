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



## Fase 3 · Cola intercambiable y contabilidad

Interfaz compartida para cola en proceso y Redis/arq, worker configurable, migración 0002 con
leases y reclamación atómica. Reintentos con backoff y plazo total; cancelación que descarta los
resultados tardíos. Avisos de Lectura visibles en GET /jobs/{id}.

RunInfo añade accounting_complete opcional. El consumo conocido se suma entre intentos;
cuando falta un intento, coste/tokens/GPU quedan null. El contador de llamadas es parcial y se
marca como tal. La revisión conserva el RunInfo de Lectura y el trabajo mide la orquestación.
No se modifica la huella del IFC almacenado al cerrar la contabilidad del trabajo.

La batería completa pasa 61/61 pruebas Python; lint y formato Python correctos.
Nueve pruebas nuevas cubren errores transitorios, límite de intentos, errores definitivos,
timeout, cancelación, lease activa, suma de coste, concurrencia local y contrato del adaptador Redis.
Redis se ha probado con un doble del cliente; no se presenta como prueba con un servidor real.
Docker no está instalado en este equipo; se registrará esa limitación al preparar los perfiles.


## Fase 4 · Contenedores y perfiles

Dockerfile.api y Dockerfile.web, perfiles local/gpu/escala, Postgres, Redis persistente,
workers replicables, healthchecks y usuarios sin privilegios. Contextos de build acotados;
los originales privados y .env no entran en las imágenes.
Ambos YAML se han validado contra el esquema oficial de Compose (hash en API.md).
No hay Docker instalado: construcción, arranque de contenedores, GPU, Redis y Postgres reales
quedan sin verificar. No se atribuyen cifras de rendimiento a esos perfiles.
Los pesos de Ollama no se incluyen en el repositorio ni en la imagen.


### Excepciones al reparto autorizadas

Javier autorizó excluir Markdown del formateador de Ruff en pyproject.toml. La comprobación
`uv run ruff format --check .` vuelve a pasar sin editar el documento de coordinación.
También autorizó integrar Pipeline en features/pipeline, stores/pipeline y sus pruebas/configuración
Playwright. El 3D permanece fuera del alcance y sin cambios.


## Fase 5 · Web conectada

Cliente con tipos OpenAPI, transporte conmutado por NEXT_PUBLIC_API_URL, ediciones con
ETag/If-Match e idempotencia y sincronización de consultas. La URL del IFC cambia al editar
para recargar la versión actual sin modificar el visor. La píldora identifica API local,
dataset y errores de conexión. Un error de API no devuelve mocks como si fueran datos reales.

Pipeline permite documentos propios de V-101 o los originales de la demo, crea revisiones
nuevas y consume eventos SSE persistidos, con reanudación nativa y deduplicación. Las 16
etapas del contrato están en el grafo. Solo los eventos recibidos activan sus tarjetas; las
etapas no ejecutadas no se presentan como disponibles. El modo offline conserva su guion.
El trabajo presenta segundos medidos, coste conocido y avisos/contabilidad parcial.

Endpoints usados: documentos, equipo/revisiones, campos, IFC/documentos originales,
trabajos/cancelación/eventos, diff y bench. Instrucciones de conexión y generación en API.md.
Se conserva la revisión del documento al reprocesarlo, independiente de la revisión del modelo.

### Límites y necesidades

El selector de revisión de la pantalla de revisión sigue mostrando A/B. Los resultados de
nuevos trabajos se acceden por ID desde la API; falta generalizar ese selector. Las estrategias
A/C/D necesitan process de Lectura: el adaptador solo implementa B y devuelve un error explícito
para las otras. No hay nuevos resultados de precisión ni coste GPU en esta fase.
La autorización adicional sobre la pantalla de revisión está pendiente; no se ha editado.

### Comprobaciones de cierre

61/61 pruebas Python; Ruff check y format globales correctos. Typecheck, lint (sin errores,
un aviso previo de TanStack Table), 13/13 pruebas unitarias y build pasan en ambos modos.
Playwright: 9/9 con API real y 6/6 offline (las tres pruebas exclusivas de API se omiten).
Inspección visual de Pipeline offline a 1600 px: grafo de 16 etapas, tarjetas y tabla cargan;
captura local en generated/qa/pipeline-offline.png. No se modifica código del visor ni de Lectura.


## Fase 6 · Familias y niveles de detalle

Registro paramétrico en families/: vertical histórica, horizontal con silletas cóncavas,
columna por tramos y transiciones, tanque con tres tipos de techo y envolvente LOD1 para
las siete tipologías. LOD3 admite envolventes anulares de bridas con rating y dimensiones
trazadas, plataformas y escaleras con peldaños. Posición/dirección explícita para boquillas
no radiales. Se rechazan familias, soportes o detalles incompletos; no se rellenan medidas.

La generación IFC consume esas familias, mantiene metros de salida, nombres históricos y
algoritmo de GUID. FieldsJSON incluye todos los nuevos campos, que cuentan para aprobar.
Contrato y tipos OpenAPI/web regenerados. Parámetros y ejes en DATA_CONTRACT.md.
Sin dependencias nuevas ni endpoints nuevos: GET IFC y los trabajos aceptan el contrato ampliado.
Lectura puede importar los tipos de families.parameters y producir estas familias.

Las formas representan envolventes de ingeniería, no despieces de fabricación. Bridas sin
certificación de norma ni tabla DN/rating implícita. Las bombas/compresores se reservan con
LOD1 hasta disponer de una familia detallada. No hay nuevos resultados de precisión real.

Comprobaciones de cierre: 80/80 pruebas Python (19 específicas de familias), Ruff global
correcto. Las familias y el LOD3 pasan ifcopenshell.validate con reglas EXPRESS y se
verifican por sus mallas IFC, dimensiones y GUID. Typecheck, lint, 13 pruebas unitarias y
build pasan con/sin API; Playwright 9/9 conectado y 6/6 offline (3 exclusivas omitidas).
Vista local revisable: generated/families/familias.html y cuatro IFC DRAFT de fixtures
sintéticos (horizontal, columna, tanque y reserva de bomba). No son métricas de extracción.


## Fase 7 · Semántica IFC, esquemas y métricas

IFC4/4X3 y conversión explícita a las clases/tipos de IFC2X3; fondos BRep en 2X3.
Componentes agregados, puertos con posición/dirección, documentos referenciados por SHA-256,
Psets comunes y TrazIA_Provenance. IfcApproval solo en exportación humana aprobada.
Names, GUID y número de productos con geometría del ejemplo permanecen estables.
No se editan archivos del visor. Exportación API/CLI con selector schema; comando validate-ifc.

Los trabajos validan IFC y reglas EXPRESS antes de publicar. Métricas opcionales con extra geo:
IoU, Chamfer y Hausdorff muestreado por GUID, semilla fija y error por vértice. No se presenta
el muestreo como máximo continuo garantizado ni como precisión contra el IFC de TR aún ausente.
CLI compare-ifc y ejemplos en API.md. Docker instala geo; no se dispone de Docker para probar imagen.
Licencias añadidas a THIRD_PARTY. Lectura puede seguir produciendo Revision sin tocar su interfaz.

Las pruebas específicas cubren tres esquemas, cinco familias/reservas, puertos y originales,
aprobación/invalidez y desplazamiento conocido de 0,2 m entre cajas. La batería específica
pasa 20/20. El desplazamiento produce Hausdorff muestreado 0,2 m e IoU 2/3; son pruebas
analíticas sintéticas, no resultados de extracción. El mapa por vértice queda disponible en JSON;
la integración de ese mapa dentro del visor requiere al responsable del 3D.

Cierre: 104/104 pruebas Python, Ruff global correcto. Se añade una prueba específica para
referencias externas con GUID distintos y nombres únicos (--match name); las pruebas
específicas de IFC son ahora 21. Typecheck, lint (aviso TanStack previo), 13 pruebas unitarias
y build correctos. Playwright: 10/10 con API y 7/7 offline (3 exclusivas omitidas), incluido
/lab/3d. La espera de pruebas para procesamiento/visor admite la validación EXPRESS real;
no se altera la lógica ni se simula su finalización. No hay push ni cambios en el 3D.
