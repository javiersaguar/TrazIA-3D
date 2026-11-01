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


## Fase 8 · Cambios y BCF

Campos con equivalencias Pint, tolerancias y emparejamiento húngaro de boquillas nuevas.
Identidad estable opcional, propagada en trabajos con revisión previa aprobada. Los casos
ambiguos no se asignan. Diferencia por GUID en mallas IFC; comparación visual ECC con
originales verificados, marco de coordenadas común, regiones y marcadores candidatos.
Cruces señalan discrepancias para revisión. Todas las operaciones conservan datos DRAFT.

GET /diff admite layers=true; el modo rápido permite que la pantalla de cambios muestre
campos sin esperar al contraste de todas las capas. Rutas nuevas /diff/visual (PNG) y
/diff/bcf (BCF 2.1), y comandos diff --geometry y bcf. El comparador no escribe ni aprueba.
El visor 3D permanece intacto. Contrato/types actualizados para stable_id y operación renamed.

14 pruebas específicas pasan: equivalencias, unidades incompatibles, tolerancias sin alterar
huella, renombrados/GUID, ambigüedad, desplazamiento de página, nubes/triángulos candidatos,
transformación de evidencia, rechazo de hash y geometría de las revisiones de la demo.
El BCF de A→B tiene ocho topics; sus 18 documentos XML pasan los XSD oficiales v2.1.
Hashes de esquemas usados: markup 15e9af22065870d93ad45431147748adc5b32ef830d6dfe7b4eb10cf5e6c4441;
visinfo c46100eeab8211ecd62b888fdb41d1c0c47b74fa210e35da18259ddf6156e7b9;
version bb1d108e349423fef4a69ecc1648797e7e73a18ee994bcdf98f978a6a3adf899;
project a1b45e394cadf076209f22ec9f2225039932f580a50cd898c14c4cb9b1c9d5d2.

Límites: umbrales heurísticos por validar con datos TR; diez páginas por PDF y 200 regiones
por página. Nubes/Δ no son detecciones certificadas; el resultado puede ser un aviso falso.
La UI de Cambios existente consume campos/IFC; las nuevas capas se consultan por API/PNG/BCF.
No se editan pantallas protegidas para incorporar nuevos controles fuera del reparto.

Cierre: 119/119 pruebas Python, Ruff global correcto. Typecheck, lint (aviso TanStack previo),
13 pruebas unitarias y build correctos. Playwright 10/10 conectado y 7/7 offline (3 exclusivas
omitidas), incluido el laboratorio 3D. gen:api exporta ahora el esquema desde FastAPI con uv
antes de generar tipos, para no dejar un JSON de OpenAPI desactualizado. Sin push.


## Integración del 27/10/2026 y fase 9

Merge diario de main, fast-forward hasta b9f943e. La pantalla Estudio ya está incorporada
por 653412e; no se duplica su implementación. Se integra también el pipeline real de Lectura,
los proveedores visuales, el generador v2 y su ejecutor de estudio. La siguiente tarea propia
en el orden acordado es la fase 10, Copiloto (ROADMAP I.4.9 y DEC-26).

## Fase 10 · Copiloto local con citas

POST /copiloto sustituye el endpoint pendiente. Qwen3-VL-4B-Instruct con Ollama local usa
cuatro herramientas: campos, evidencia, cambios y reglas. Se verifican originales por SHA-256
antes de extraer texto de su región PDF o celda/rango Excel. Las revisiones son copias y las
herramientas no reciben sesiones SQL, funciones de escritura ni rutas arbitrarias.
Toda respuesta y propuesta lleva IDs de fuentes emitidos por estas lecturas; una referencia
inventada o una salida inválida produce abstención. No se acepta/corrige ni aprueba nada.

El panel conserva el lenguaje visual del shell: pregunta, sugerencias, espera/cancelación,
respuesta, comprobaciones propuestas y fuentes desplegables con fragmento, página/celda,
bbox y SHA. Las consultas no invalidan IFC como si fueran ediciones. Un 409 por revisión
cambiada refresca las consultas; un error de Ollama se muestra sin sustituirlo por reglas.
Offline conserva el panel de reglas y su identificación explícita.

El plan usa herramientas nativas y la respuesta final JSON Schema. No se combina format
con tools en la petición de planificación: el modelo instalado no emitía llamadas nativas
al combinarlos. Se acotan contexto, herramientas, duración y concurrencia; detalles en API.md.
Las pruebas reales detectaron que el modelo atribuía certeza al score y negaba incorrectamente
la verificación del original. Se añade reformulación para el primer caso y rechazo conservador
de contradicciones conocidas y declaraciones de escritura. No es un verificador semántico
completo: una cita válida no garantiza que toda conclusión se deduzca de ella.

Modelo instalado reutilizado: qwen3-vl:4b-instruct, ID 84f7ed8042fa, GGUF Q4_K_M, Ollama
0.40.11. Sin descarga de pesos ni nuevas dependencias. Modelo Apache-2.0 documentado en
THIRD_PARTY; configuración y tipos OpenAPI regenerados. Sin cambios en Lectura o en el visor.

### Comprobaciones y cifras

22 pruebas específicas del backend: llamadas nativas, citas de originales PDF/Excel y hashes,
ninguna escritura en seis tablas SQL, herramientas prohibidas, referencias inventadas,
salida inválida, modelo ausente/remoto, falta de calibración, contabilidad de reformulación,
JSON de proveedor ilegible, original ausente y cambios concurrentes. Se rechazan afirmaciones
de escritura y negaciones observadas de un hash verificado. No dependen de Ollama en CI.

La espera de finalización de trabajos en test_api_queue pasa de 10 a 30 s: el pipeline real
integrado y la validación EXPRESS superaban ocasionalmente diez segundos bajo carga. Se
conservan las aserciones y los límites de producción; no se simula el trabajo.

Web: typecheck, lint (aviso previo TanStack), 13 unitarias y build pasan con/sin API.
Playwright conectado: 12 pasan, una exclusiva offline omitida. Offline: ocho pasan y cinco
exclusivas API omitidas. Las pruebas de interfaz usan una respuesta explícitamente marcada
como fixture, verifican citas/error 503 y que escribir preguntas no activa atajos de revisión.
Comprobación adicional de navegador contra Ollama real y revisión visual en claro/oscuro
1600×940 y móvil 390×844; panel contenido en los 366 px disponibles, con scroll propio.
Capturas locales en generated/qa/copilot-{dark,light,mobile}.png.

| Consulta real sobre la demo sintética | Tiempo pared | Tokens entrada/salida | Resultado |
| --- | --- | --- | --- |
| Fuente del diámetro | 4.997 s | 6596/366 | Respuesta con citas |
| Significado del score | 5.137 s | 6561/396 | Respuesta con citas |
| Cambio N3 A→B | 2.619 s | 4399/168 | Respuesta con citas |
| Petición de aprobar | 3.669 s | 3891/270 | Abstención: contradicción del modelo rechazada |

Las cuatro consultas reales conservaron sin cambios todas las tablas SQL comparadas.
Las tres consultas de lectura responden: diámetro 2000 mm, score 0,75 sin calibración aportada
y elevación N3 3500→3700 mm. Evidencia local y contabilidad en generated/copilot/; son pruebas
funcionales sobre originales sintéticos, no precisión medida con el dataset de TR.
Sin llamadas a proveedor externo ni tarifa facturada; no se mide energía ni segundos GPU.
Los tokens incluyen planificación/respuesta/reformulación y se dejan null si falta contabilidad.

### Límites y siguiente fase

Sin OCR en esta herramienta, sin historial conversacional y sin comprobación semántica general.
Cancelar aborta la espera web, sin garantizar que Ollama detenga una generación en marcha.
Una lectura/hash correcto no certifica ingeniería. Revisión y aprobación siguen siendo humanas.
No se necesita un cambio adicional de interfaz de Lectura para esta fase; futuros resultados
de calibración necesitarán exponerse para explicar intervalos medidos.

Propuesta para el responsable del ROADMAP: marcar DEC-26 / I.4.9 / tarea 3.6 como implementado
con estos límites. El ROADMAP protegido permanece intacto. Próxima fase propia: 11, revisión
humana (DEC-27), seguida de CI y cálculo de escala. La excepción para editar features/review
sigue pendiente; no se ha usado ni interpretado como aprobada.


Cierre de la fase: Ruff check y format globales correctos (90 archivos); batería Python
169 pruebas correctas y una omitida. Avisos existentes: deprecación HTTPX de TestClient y
TanStack Table en lint, sin fallos. Las verificaciones web de ambos modos y la inspección
visual anterior completan la validación. Cambios preparados en commits separados de API
y panel web, sin push ni PR.


## Petición de completar y actualizar la Fase 1 · 27/10/2026

El encargo actual autoriza actualizar ROADMAP y cerrar sus tareas de Fase 1. Se comprueban
contrato/migración, API y motor compartido ya integrados; tipos regenerados sin diferencias.
Se corrige la dependencia de ejecución pytest para la validación EXPRESS en la imagen API,
se ubican cachés de visión bajo /data y se comprueban contenedores con el script aislado
scripts/check_compose.py. Local, Redis/arq/Postgres y GPU pasan; la GPU es visible desde
Ollama. El chequeo no descarga pesos ni mide inferencia dentro de ese contenedor.

Dentro del alcance 1.9 se corrigen bloques Mistral, modo offline sin claves, identidad de
caché y coherencia de variables Ollama con Compose. Registro/política aplican también a
un Ollama remoto; se rechazan modelos cloud antes de transmitir una imagen. Se añade el
comparador real de proveedores, una lectura real de Qwen versionada y pruebas de adaptadores.
El comparador deja un informe parcial y código 2 cuando falta un proveedor.

Dentro de 1.11, el bootstrap y la ablación pareada agrupan las degradaciones por equipo;
una prueba con dos equipos/cuatro condiciones impide volver a contar condiciones como
equipos independientes. El informe ya no atribuye medición a S-reservado si solo usa S-dev.
La prueba API de estudio vacío se aísla de los informes locales y comprueba también carga real.

Generados S-dev, S-reservado, S-mecánico y S-adversarial con sus semillas: 64 equipos,
336 PDF y 162 Excel. B y ablación sin HDM medidos en 24 equipos de S-dev × tres condiciones
× dos revisiones; resultados sintéticos completos en docs/evidencias/fase1. Sin ajuste con
los estilos reservados ni afirmaciones sobre datos de TR.

Cierre de comprobaciones: Ruff global y 177 pruebas Python pasan; no queda la omisión de
visión offline. Web: typecheck/lint/13 unitarias/build pasan en ambos modos, Playwright
12 conectado y ocho offline, con una/cinco omisiones por transporte respectivamente.
Los tres perfiles Compose pasan API/trabajo/SSE/IFC/idempotencia/HTTP web/persistencia.
Ningún archivo del visor 3D se modifica. No hay nuevas llamadas externas.

ROADMAP actualizado a 10/11 tareas de Fase 1 cerradas, con enlaces a evidencias. 1.9 permanece
parcial: Ollama real comprobado, Gemini y Mistral sin credenciales para la segunda lectura
real exigida por el criterio de hecho. No se reemplaza esa prueba con un mock o con dos
modelos del mismo proveedor. Plataforma IndesIA sigue sin servicio conocido, como prevé
«cuando se sepa». Falta una clave configurada por el equipo para cerrar 1.9; se ha solicitado
solo la ruta del archivo local, nunca que se publique la clave. Detalle y reproducción en
[FASE1.md](../FASE1.md). Sin push ni PR.


## Fase 3 · Bench y medición de escala, 27/10/2026

Por petición del usuario se avanza en Fase 3 sin modificar el worktree/código de Lectura,
actualmente ocupado por Fase 2. Se cierra 3.5 conectando Bench al mismo informe de Estudio,
con selector de variante, rúbrica/IC/alcance y bench v1 separado. Se corrigen avisos de alcance
y la diferencia entre error y estado vacío. No se modifican los archivos del visor.

3.1 y 3.6 ya implementadas se registran como verificadas en ROADMAP. Para 3.7 se crean un
cliente de lote y un orquestador Docker aislado. Se miden 336 revisiones, 64 equipos y 168
condiciones con uno y cuatro workers Redis/arq/Postgres: 221,425 frente a 65,445 s (3,38×).
Ambos obtienen 20 done y 316 errores. done acredita IFC estructural/EXPRESS, no verdad geométrica.
Se conserva coste null y no se presenta el lote como capacidad de producir 1600 IFC válidos.
3.7 queda parcial y se indican necesidades de Lectura para repetir con Fase 2 y contabilidad.
No se altera memoria/calibración/fusión/aprendizaje activo en las carpetas del otro agente.

180 pruebas Python, Ruff global, web types/lint/15 unitarias/build pasan. Playwright 15 con API
(una omitida) y 11 offline (cinco omitidas). Inspección de Bench en ambos temas sobre API real.
La configuración permite probar el build con servidor/API aislados sin parar localhost:3000.
CI añade job web, sin eliminar pasos Python existentes. Evidencia y reproducción en
[FASE3.md](../FASE3.md), con JSON de métricas por equipo/condición bajo docs/evidencias/fase3.
No hay nuevas dependencias ni cambios de contrato con Lectura. Commit y push autorizados por
el encargo actual, a feat/plataforma; no se fusiona su trabajo sin terminar ni se hace push forzado.


## Sesión 30/10/2026 · estudio en cola, offline y correcciones

Trabajo en el worktree `TrazIA-3D-plataforma`, rama `feat/plataforma`, desde el frontend
integrado de `feat/web-3d`. Se respeta SESION_LECTURA.md; no se modifican sus carpetas
ni se ocupa la GPU. Sin push, PR, cambios en main o datos privados.

H.1/H.3: POST /estudio usa la cola común con subproceso cancelable y resultados por SHA-256.
La prueba Redis/arq/Postgres real acredita idempotencia, SSE, timeout, cancelación y
persistencia tras reinicio: 6,134 s para un equipo sintético y dos revisiones vectoriales.
4.2: modo offline de visión y caché del copiloto, invalidada por datos/modelo/código y
con originales comprobados de nuevo. 3.8: exportación de correcciones aprobadas; la
recalibración y uso few-shot esperan la interfaz pública de Lectura y siguen abiertos.

[Informe, reproducción, límites y evidencia](../BACKEND_2026-10-30.md). El ROADMAP marca
H.1/H.3/4.2 con sus comprobaciones y mantiene 3.7/H.7 y 3.8 parciales.


## Sesión 30/10 · backend independiente y publicación de feat/plataforma

Encargo actual: cinco tareas, sin editar Lectura, web ni el contrato model.py.
Se reutiliza el worktree ya existente, se fusiona main `a75e8ef` y se instala con
`uv sync --frozen --extra dev --extra api --extra geo`. Base verde: Ruff y
239 pruebas Python correctas, una omitida, 166,42 s. La omisión corresponde al extra
OCR opcional no incluido en la instalación requerida. No se usa la GPU.

### 1 · H.1/H.3: CLI estable del estudio

Sustituido el adaptador que importaba run_study por la invocación de la CLI estable
como subproceso. Se mantienen cola, idempotencia, leases, SSE, timeout, cancelación
y resultado por SHA-256. Se elimina study_worker.py. Las pruebas comprueban el
argv sin shell, un estudio real de un caso y 20 remuestreos, ausencia de informe,
error, timeout, cancelación, persistencia y replay. No cambia ninguna interfaz de
Lectura ni se esperan funciones nuevas suyas.

Cierre tarea 1: Ruff check y format globales correctos; 241 pruebas correctas y una
omitida en 251,74 s. Seis pruebas específicas del estudio correctas.

### 2 · 4.2: caché persistida de resultados de trabajos

La API comprueba hashes de documentos + estrategia + proveedores y contexto documental.
Con OFFLINE, el acierto restaura un DRAFT sin ejecutar el pipeline; el fallo responde
409 en español antes de encolar. Se verifica la integridad del resultado y originales,
se conserva idempotencia y se indican cache_hit y contabilidad marginal sin inferencia.
La migración 0004 sirve en SQLite y Postgres. No se cachean fallos ni aprobaciones.
Las pruebas no presuponen confianza o intervalos vacíos. No se cambia model.py, web
ni vision/cache.py. Trece pruebas específicas de caché/cola correctas.

Cierre tarea 2: Ruff y formato global correctos; 245 pruebas correctas y una omitida
en 271,05 s. API HTTP 8020, mismo almacén tras reinicio: trabajo original 3,192 s y
recuperación cacheada 0,022 s registrados por el job (no latencia HTTP total), con
pipeline omitido y fallo explícito al cambiar la estrategia. Solo sintéticos.

### 3 · CORS configurable

TRAZIA_CORS_ORIGINS sustituye la lista por orígenes explícitos separados por comas.
Vacío conserva exactamente los puertos actuales; configuración para 3120 documentada
en .env.example y API.md y propagada por Compose. Nueve comprobaciones específicas
pasan: defaults, reemplazo, normalización, rechazo de otros sitios y configuración
inválida. No se cambia web ni se usan los puertos de otros equipos.

Cierre tarea 3: Ruff y formato globales correctos; 253 pruebas correctas y una omitida
en 301,02 s. API real 8020: preflight desde localhost:3120 devuelve 200 con el origen
permitido; un origen ajeno devuelve 400 sin cabecera de autorización CORS.

### 4 · 3.8 (datos): JSONL y GET /correcciones

Registro de cada cambio de valor/unidad/estado, con el formato solicitado y los
metadatos de la predicción antes de intervenir. Fecha UTC y huella de los datos
resultantes; null para ausentes. GET /correcciones filtra desde ISO inclusivo.
El JSONL se publica desde una bandeja transaccional, con cursor bloqueado y recuperación
tras fallo de escritura, reintento idempotente o archivo truncado. Las ediciones
rechazadas y peticiones sin cambios no añaden líneas. La migración 0005 no modifica
model.py. No se llama a calibración ni se escribe en carpetas de Lectura.
Siete pruebas específicas correctas: con/sin calibración, idempotencia, estado, rechazo,
fallo tras escribir, concurrencia, filtro de fecha, recuperación y aprobación existente.

Cierre tarea 4: Ruff y formato globales correctos; 258 pruebas correctas y una omitida
en 290,06 s. Prueba HTTP 8020: la fila devuelta por GET coincide exactamente con la
última línea UTF-8 del JSONL. Evidencia sintética en evidencias/fase3/correccion-api-30oct.json.

### 5 · 3.7/H.7: escala en CPU

Sonda D completa: 4 done y 16 errores en 20 revisiones, 169,256 s. Se elige el fallback
B indicado en el encargo. Lote completo: 64 equipos, 168 condiciones y 336 revisiones;
72 done y 264 errores con uno y con cuatro workers Redis/arq/Postgres. Tiempos medidos:
352,475 y 97,285 s, mejora observada 3.62×. Mismo hash de entrada, imagen y estado
para cada revisión. Visión bloqueada, providers vacío y sin dispositivos GPU. Se usan
solo las estrategias presentes en main a75e8ef y la base 3D autorizada.

Diagrama, latencias, resultados completos, desglose por conjunto y extrapolación de
400×4 en [FASE3.md](../FASE3.md), con evidencia bajo evidencias/fase3/30oct. El coste de
proveedores declarado es 0 EUR y no incluye energía ni revisión humana. La estimación
de cómputo usa 0,25 EUR/worker-h como hipótesis explícita. Con 264 errores no se calcula
un tiempo defendible para 1600 IFC válidos; done tampoco acredita fidelidad geométrica.
Los ensayos se hacen mientras Lectura trabaja en paralelo, sin CPU dedicada.

Cierre tarea 5: Ruff y formato globales correctos, 264 pruebas correctas y una omitida
en 327,83 s. No hubo pruebas propias activas durante los lotes completos B. Todos los
contenedores y volúmenes exclusivos del ensayo se eliminan al terminar; no se para
ningún stack ajeno. Se preservan costes desconocidos como null cuando aparezcan.

### Estado final del encargo

Las cinco tareas están implementadas y medidas en su alcance: CLI estable del estudio,
caché de trabajos offline, CORS configurable, registro JSONL/GET de correcciones y lote
CPU con proyección explícita. No se llama a calibración, no se integran cambios de
feat/lectura y no se editan sus carpetas, model.py, web ni ROADMAP. No hay dependencias
nuevas ni cambios de uv.lock. Interfaces nuevas: GET /correcciones?desde, cache_hit en
GET /jobs, y configuración CORS/ruta JSONL. No se regeneran tipos web por la separación
de esta sesión. Los datos generados siguen en el worktree de Plataforma.

Publicación autorizada exclusivamente de feat/plataforma, sin fusión a main ni PR.
El hito amplio de cobertura/IFC correctos y la recalibración automática de 3.8 no se
declaran terminados; no forman parte de la porción de datos/medición cerrada aquí.


## Sesión 31/10 · escala CPU y recalibración

Trabajo en `feat/cierre-plataforma-visor`, desde main a4dd9a7. Se conservan sin tocar los
cambios en curso de Lectura (fusión, estrategias, calibración base y UI de abstención).
No se detiene su API 8020 ni la API 8010/web 3100. Pruebas/preview propias en 8022/3120.
No se usan datos privados ni GPU para extracción, calibración o escala.

### Hecho

- El ensamblador admite las coordenadas trazadas de una envolvente LOD 1. El nuevo lector
  de bombas obtiene cotas exteriores de alzado/planta; el origen local es un supuesto
  declarado. No inventa conexiones. Las validaciones de recipientes detallados permanecen.
- Lectura de un tag aislado y único cuando el rótulo de proveedor es desconocido, sin
  recurrir al nombre del fichero ni elegir entre identificadores contradictorios.
- Nuevo circuito CPU JSONL → auditoría SQL → revisiones sintéticas con aprobación vigente
  → isotónica/conforme. Confianza bruta identificable, confirmaciones y correcciones,
  deduplicación por campo, exclusión de unidades cambiadas sin normalizar y separación de
  equipos entre ajuste y prueba. Mínimos por estrategia. No publica candidatos si la
  muestra es insuficiente o el ECE empeora. No activa nada ni modifica aprobaciones.
- Las estrategias no reajustadas conservan su calibración previa, incluidos intervalos
  y abstención. Huella de calibración en caché v2 y protección frente a cambio durante
  la ejecución. Compose comparte el archivo entre API y workers.
- `scripts.measure_feedback` verifica el circuito en S-dev/vectorial: nueve equipos,
  18 revisiones aprobadas de forma simulada, 544 etiquetas; 376 de ajuste y 168 de prueba.
  En 6,344 s genera una propuesta para B: ECE 0,1018 → 0 y cobertura de intervalo 100 %
  en este subconjunto. Son etiquetas de un oráculo sintético, no trabajo humano medido.
- Lote completo D/CPU: 336 revisiones; 173 done y 163 error, idénticos por revisión con
  uno/cuatro workers. 1.823,100/1.035,171 s: 1,76× observado en host compartido. 133 LOD 2
  y 40 LOD 1; sin timeouts ni cancelaciones. Proveedores declarados 0 EUR, cero llamadas
  externas. No incluye energía ni coste operativo. No se atribuye causalmente la mejora
  de cobertura frente al B anterior a una sola corrección: cambió la estrategia.

### Cómo se comprueba

Ruff check/format globales; 284 pytest correctos y una omisión en 255,11 s. Pruebas del
feedback con aprobaciones reales de la API, invalidación, deduplicación y separación
por estrategia/equipo; CLI rechaza muestra insuficiente sin dejar propuestas antiguas.
Ensayo reproducible y cada trabajo del lote en docs/evidencias/fase3/31oct. API.md y
DATA_CONTRACT.md documentan operación, semántica de LOD y clave de caché. Web validada
por separado: typecheck/lint/32 unitarias/builds y 25/30 pruebas de humo offline/API.

### Interfaces y límites

Sin cambios de modelo 0.3 ni dependencias. `bench.recalibrar --almacen --correcciones
--base --salida` es nuevo. `scripts.measure_scale` añade LOD/familia y grupos de error.
Los estados `done` son IFC DRAFT estructuralmente válidos, no exactitud frente al plano.
Quedan 161 errores de escaneados y D-712 rev1/2 vectoriales por boquillas incompletas.
3.7/H.7 no se cierran: solo se extrapolan terminaciones, no 1600 IFC válidos. La CPU no
estuvo dedicada y Lectura ejecutaba estudios paralelos. 3.8 no se cierra completo:
falta few-shot y una muestra de correcciones de uso representativa. El candidato del
ensayo sintético se conserva sin activar. El visor y el giro se describen en el informe 3D.


## Sesión 31/10 · revisión humana y material de escala

Base main 8713f7a; rama feat/cierre-plataforma-visor. Se conserva model.py 0.3 y el reparto de
COORDINACION-BACKEND.md. Sin cambios en lectores, OCR, estrategias, entrenamiento ni visor 3D.

Cerrados E.1–E.3: validación accionable, diagnóstico de coherencia/solape como cribado, cola
existente auditada y ampliada a campos trazados, rechazo explícito y deshacer completo con
concurrencia, idempotencia y auditoría inversa. La web preserva los errores recuperables, las
instantáneas vistas y la escritura SQL si falla solo exportar JSONL. Migración de almacén 0006.

E.5 instrumentado: sesión declarada por persona o prueba, tiempo activo, límites de reloj,
agrupación por proyecto/equipo/dataset y métricas desconocidas a null. Piloto A/B preparado
por pipeline B/CPU (22/26 campos con score bruto), sin simular actividad humana. API 8022 y
web 3120 sobre generated/piloto-manual-31; API en offline para evitar inferencias nuevas.
[Protocolo](../MUESTRA_REVISION_MANUAL.md), [captura](../capturas/revision-sesion-manual-31.png).

E.6/3.8 parcial: ejemplos aprobados con hash, retiro al revocar, filtro por campo/estrategia,
exclusión del equipo/documentos y recorte PDF verificado; contexto del Copiloto y su caché
con manifiesto. Caché de trabajos v3 con SHA de fusión/calibración y protección de cambios
mientras se ejecuta. No se activa una propuesta ni se afirma integración del few-shot en
extracción: esa conexión/prioridad de fuentes es de Lectura. Falta muestra humana representativa.

C.4 documentado y probado internamente: +Z, 0°=+X, 90°=+Y, mm→m, matriz web-ifc (X,Z,-Y).
Norte/TR sin verificar. [Evidencia](../evidencias/fase3/31oct/referencia-local.json).

3.7/H.7: diagrama exportable y presupuesto paramétrico; inventario de 163 fallos (84 boquillas,
63 campos ausentes, 16 geometría), --tags y --exigir-todos. Continúan 173/336 DRAFT del lote
anterior; no se reinterpreta como 1600 válidos. Reproducción D-712: 2 errores / 0,9310 s,
sin GPU ni coste de proveedores; no es una medida de escala. El coste humano/infraestructura
y total de IFC válidos siguen sin estimar. [Pitch](../PITCH_ESCALA.md).

Validación final: Ruff check y format (167 archivos); pytest 303 passed / 1 skipped (298,21 s);
web typecheck, lint sin errores (aviso anterior de TanStack), 38 unitarias y build; Playwright
con API: 31 passed / 1 skipped (modo alternativo) en 2,1 min, Chrome/SwiftShader sin inferencia
GPU. Se corrigió el retorno vacío al cerrar sesión y una etiqueta accesible duplicada que
interfería con el diálogo de aprobación. En CPU se amplían las esperas, no se rebajan los
criterios de triángulos. No se añaden dependencias.

ROADMAP: E.1–E.3 marcados; E.5/E.6/3.7/3.8/C.4/H.7 conservan el trabajo pendiente explícito.
Detalle de interfaces y límites: [auditoría](../AUDITORIA_REVISION.md) y [API](../API.md).


### Integración posterior con main e46573d

Al preparar la subida, main incorporó el modelo de fusión versionado de Lectura y cambió D
para usarlo por defecto. Los resultados 173/336 y la reproducción D-712 de esta sesión siguen
correspondiendo a D heurístico sobre la base 8713f7a; no se atribuyen al nuevo D aprendido.
La variante actual para reproducir la fusión anterior es `d_hibrido+heuristica`. El modelo
empaquetado sí participa en la huella de caché v3. Se conserva el trabajo de ambos equipos.

Verificación del resultado integrado antes del push: Ruff check/format (168 archivos),
304 pruebas Python correctas y una omisión en 267,28 s; 38 unitarias web, typecheck,
lint sin errores y build correctos. Revisión cargada con 22 campos y cero errores JS,
mediante Chrome/SwiftShader y sin modificar la sesión manual.


## Sesión 31/10 · D aprendido / v5 y kit E.5

### 3.7 / H.7: medición y límites

Rama feat/plataforma desde origin/main 8717c41. La caché v3 ya incluía la huella de fusión; se añade prueba de modificación real de pesos y de cambio entre búsqueda/guardado. Variables de proveedores nuevas vacías en .env.example. Calibración v5 copiada sin editar Lectura, montada read-only y verificada en cada contenedor. Sin nuevas dependencias ni cambio de contrato/API.

Lote nuevo CPU/Redis/arq/Postgres: **336 revisiones, 64 equipos; 174 done (134 LOD 2, 40 LOD 1), 162 error**, iguales con uno/cuatro workers. **1.434,2816 / 877,6943 s; 1,6341× observado**. Cero llamadas externas, 0 EUR de proveedores, contabilidad completa; cero aciertos de caché de trabajos sobre 336 observaciones por despliegue fresco. Los JSON y CSV conservan tiempos por equipo, pipeline y ejecutor separados.

Comparación con D heurístico: 173 done→done, 1 error→done (C-201 limpio/1), 162 error→error. D-220 limpio/1 conserva el error y cambia N1 por N2 en el mensaje. Código y calibración también cambiaron; no se atribuye causalidad a pesos ni precisión industrial. [Evidencias y reproducción](../evidencias/fase3/31oct-d-v5/resumen.md).

Prueba OCR real sin red/GPU: 2/1/0/2 llamadas al reconocedor para frío/cambio/repetición/control; B cambiante 0,6758 s frente a control frío 1,6364 s. Render todavía recorre ambas páginas: no es un pipeline enteramente incremental. La traza de host tiene 68 muestras de mayor precisión, 14 con la CLI de comparación de Lectura detectada; no certifica toda la carga WSL/GPU. No se realizó otra pasada con host aislado.

Extrapolación explícita: 69,66 min para 1.600 terminaciones con cuatro workers, incluidos errores. Cómputo hipotético 1,1610 EUR a 0,25 EUR/worker-h. Total del proyecto, tiempo/coste de IFC válidos, energía y revisión humana sin medir. Control --exigir-todos devuelve 2. 3.7/H.7 siguen abiertas. Se limpiaron solo los despliegues propios; portal y servicios ajenos preservados.

### Necesidades para Lectura

Quedan 84 errores por boquillas incompletas, 63 por campos ausentes y 15 geométricos; [inventario exacto](../evidencias/fase3/31oct-d-v5/revisiones-pendientes.jsonl). D-200 limpio/1: falta skirt_thickness; D-200 limpio/2 y pobre/1: menos de tres boquillas. D-220 limpio/1: N2 fuera de virola. D-712 vectorial/1 y /2, en S-reservado: siguen faltando tres boquillas completas. Usar los reservados solo como diagnóstico y evaluar ajustes con separación por equipo. No se modifica ningún lector ni se rellena un fallo para producir IFC. La incrementalidad completa necesita coordinación con el dueño de ingestión/OCR.

Validación previa al commit de medición: Ruff check y format completos correctos; suite Python completa en verde con API, incluida la exportación E.5 que se publicará en el siguiente commit. El build conectado de la web también pasa.


### E.5: kit preparado; a la espera de Javier

[Guion de sesión y exportación](../MUESTRA_REVISION_MANUAL_31OCT_V5.md). Almacén propio nuevo generated/piloto-manual-v5-31oct: V-101 A/B obtenidas por B/CPU, 22/26 campos candidatos, cero sesiones humanas y ninguna aprobación. No se usan oráculos ni se simulan tiempos humanos. Originales GAD/HDM servidos por la API, con procedencia por campo.

Nuevo scripts/export_review_session.py: lectura de métricas, auditoría y campos; admite solo sintéticos, excluye test/abiertas/sin acciones. Agrupa por identidad de equipo/revisión/campo, suma trabajo de deshacer sin duplicar campos, distingue activo y duración total con interrupciones y conserva desconocidos a null. Tiempo por campo es el atribuido a acciones, no permanencia visual. Compleción exige todos los campos con acciones cronometradas, revisión aprobada y sin sesiones abiertas. No declara ahorro causal ni representatividad. Destino nuevo para conservar la fuente original.

Prueba de ausencia real de muestra contra API 8030: código 2, cero equipos con muestra, tiempos null, ninguna acción humana. [Preparación](../evidencias/fase3/31oct-d-v5/piloto-preparacion.json) y [estado sin muestra](../evidencias/fase3/31oct-d-v5/piloto-sin-muestra.json). La prueba unitaria solo usa tiempos automatizados etiquetados test para verificar su exclusión.

API del piloto en 127.0.0.1:8030, modo offline, CORS 3130, SQL/JSONL separados. Build web conectado correcto. Arranque del frontend 3130 rechazado por revisión automática de aprobación con motivo «blocked by policy»: no hay pantalla ni captura validada en esta entrega. El kit contiene el comando para que Javier arranque su web compilada; no hace falta reiniciar API. No se editaron archivos web ni el lector. 3.8/E.6 queda fuera de esta sesión.

Pendiente: que Javier inicie la web y haga la sesión real; después exportar el registro y publicar tiempos activos/totales por equipo y atribuidos por campo, tamaño de muestra e interrupciones. No hay cifra de impacto medida ni se marca E.5 terminada. Se detiene el trabajo del kit para pedir esa participación.

Validación final: Ruff check/format completos correctos (173 archivos). Dos pasadas completas con `uv run --extra api pytest -q`: **311 passed / 1 skipped**, en **278,68 s** y **238,83 s**; aviso de deprecación preexistente de Starlette/httpx. Build Next conectado en verde. Cuatro originales del piloto verificados por SHA contra la API, cero sesiones/acciones; [comprobación de solo lectura](../evidencias/fase3/31oct-d-v5/piloto-verificacion.json). Sin cambios web, dependencias nuevas, contrato model.py, extractores ni datos privados.


## Sesión 01/11 · unidades, feedback, página incremental y visor

### Implementado

C.1/C.2: Pint compartido en extracción y revisión, unidad/texto originales, separadores ambiguos y base de presión explícita, rechazo atómico 422. C.4: utilidades internas, Norte opcional explícito y Pset de referencia en IFC sin cambiar model.py; falta contrastar el convenio externo de TR. [Contrato](../NORMALIZACION.md).

3.8/E.6: feedback aprobado con sesión humana finalizada conectado a prompt real y prioridad acotada de canal; exclusión de equipo/documentos, mínimo de grupos independientes y campos, confianza bruta conservada e invalidación de caché al revocar. No hay entrenamiento ni activación con una sesión ficticia. [Diseño y límites](../APRENDIZAJE_APROBADO.md).

H.7: huella conservadora de página PDF antes de render/OCR; cachés verificadas y atómicas de texto, raster y geometría vectorial/raster. La fuente de una página reutilizada se vincula al documento actual. Si no puede obtenerse una huella segura, se procesa normalmente. Reconciliación global e IFC siguen completos. La prueba real RapidOCR en CPU/sin red dio patrón 2/1/0/2 páginas en todas las etapas, revisión B caliente 0,86 s y control B frío 3,25 s (una secuencia, no un benchmark estadístico). [Datos](../evidencias/fase3/01nov/incremental-etapas.json).

POST /viewer/bcf: conversión sin mutación de PNG/cámara/GUID reales a BCF; validación de tamaño, imagen y cámara. [API](../API.md#ampliaciones-0111).

### Comprobado

Ruff check y format verdes. Suite Python final tras la regresión NumPy: 348 pasadas, una omitida, 266,67 s (la pasada anterior dio 346/1 en 302,25 s). Tras ampliar el inventario de escala, 14 pruebas focalizadas verdes. Web: typecheck, lint, build y 42 unitarias. No se añadieron dependencias ni cambió uv.lock. Datos exclusivamente sintéticos, sin GPU ni proveedores externos.

### Pendientes y coordinación con Lectura

E.5 pospuesta expresamente por Javier el 01/11: no se ha iniciado ni simulado una sesión humana. Faltan muestra humana representativa y evaluación separada del feedback; C.4 requiere el convenio de referencia de TR. Los cambios del lote de escala con unidades/lectores/cachés nuevos no deben atribuirse causalmente a una sola pieza. Se conserva un inventario por revisión para entregar a Lectura sin ocultar los errores ni considerar un DRAFT como ingeniería validada. Las métricas nuevas del lote se incorporan tras ejecutarlo con imagen fijada.


Incidencia de la primera ejecución 01/11: detenida tras detectar escalares NumPy float32 no serializables en la caché de geometría. Se conservan los datos de diagnóstico en generated/mejoras-01nov/escala/; no se utilizan como medición final. Corregida serialización a números JSON nativos y persistencia opcional (un fallo de disco/codificación no invalida la computación). Regresión con geometría raster positiva y lectura posterior de caché; prueba de ruta no escribible.


### Resultado final del lote 01/11

251 DRAFT/85 errores en ambas pasadas (211 LOD 2/40 LOD 1); 1.714,18/919,26 s, 1,8647×. Mismos estados/LOD/errores en las 336 revisiones. Frente al 31/10: 77 error→DRAFT y ninguna pérdida de exportación; no valida precisión ni efecto causal de una pieza. 63 casos con campos ausentes, 22 con geometría incoherente: [inventario](../evidencias/fase3/01nov/pendientes-lectura.jsonl). Fuente/imagen fijadas y parámetros archivados, volúmenes nuevos en cada pasada, GPU oculta y proveedores vacíos. 0/336 aciertos de caché de trabajo; cero llamadas externas.

[Resumen y reproducción](../evidencias/fase3/01nov/resumen.md). Proyecto 400×4: extrapolación 72,96 min para terminaciones, también fallidas; hipótesis 0,10 €/worker-h → 0,4864 € solo de cómputo. No se da presupuesto total ni de IFC correctos. Diagrama actualizado SVG/PNG para el pitch; H.7 mantiene abiertas cobertura/precisión y presupuesto válido. ROADMAP marca C.1/C.2 y siete mejoras del visor; rendimiento en otro portátil sigue pendiente. E.5 pospuesta; 3.8/E.6 sin muestra humana representativa y C.4 externo sin verificar.

Pruebas finales: Python 348/una omitida, 266,67 s; Ruff check/format verdes. Web typecheck/lint/build, 42 unitarias, API 33/una omitida y offline 26/ocho omitidas. Sin nuevas dependencias. No se han integrado ramas ajenas ni modificado main.


## Sesión 01/11 · F.5, diagnóstico y evidencias pendientes

### Hecho

- F.5: cruce del detector vectorial de Lectura en `revisions.compare`, por documento/página y SHA.
  API `marks=true` evita ECC/IFC; Revisión enfoca marca/PDF y retorna al campo. Escaneados,
  originales no verificables, páginas truncadas y eliminaciones sin caja nueva se declaran sin lectura.
  No se cambia `model.py` ni el detector de Lectura, ni se aprueba/modifica la revisión.
- Reproducidos en CPU los 85 errores con código actual y calibración v6: 85 errores, cero recuperados,
  290,244 s acumulados. Candidatos/alternativas/fuentes y GT posterior archivados para Lectura.
  No se usan GT para predecir ni se relajan validadores. [Evidencias](../evidencias/fase3/01nov-triage/resumen.md).
- D.4: IFC4 sintético DRAFT validado con reglas EXPRESS (cero incidencias), abierto en Bonsai
  y visor web con SHA idéntico. Capturas y archivo en [ifc-checks](../ifc-checks/01nov/README.md).
  Actualización posterior: Javier abrió manualmente el IFC en BIMvision y aportó su captura;
  la apertura visual en tres visores queda documentada. La herramienta no pudo controlar esa ventana.
- Documentado el estado real de C.4/D.5 y E.6: sin referencia de TR ni muestra humana aportada,
  no se declara fidelidad externa ni mejora de extracción. E.5 permanece pospuesta.

### Comprobado

- Ruff check y format verdes, 206 archivos.
- Suite completa Python final: 389 pasadas/una omitida, 207,50 s; trece pruebas específicas
  pasan (2,15 s), incluidas originales perdidos/no verificables y GT solo posterior a extracción.
- Web: typecheck/lint/build verdes (aviso existente de TanStack); 42 unitarias.
- E2E conectado: 34 pasadas/una omitida en la pasada completa; el nuevo caso opcional D.4
  se corrigió para reconocer el ID compuesto de B y pasó después por separado (2,8 s).
  Sin API: 26 pasadas/nueve omitidas (2,2 min).
  La primera ejecución web se interrumpió por configurar mi puerto fuera de CORS; al autorizar
  el origen del test las comprobaciones de API/IFC volvieron a pasar. No se cambiaron límites de tiempo.
- No dependencias nuevas, no GPU de inferencia, no datos privados, no integración de ramas ajenas.

### Pendiente y límites

F.5 conserva el límite de detección en raster. 3.7/H.7 conserva 63 casos sin campos y 22
geometrías incoherentes; las 251 exportaciones anteriores no se han reevaluado con v6, ni se ha
medido nuevo escalado o precisión. El coste de 1.600 IFC correctos sigue desconocido. C.4/D.5
requieren el IFC autorizado de TR; E.6 requiere correcciones humanas representativas. No se
inicia E.5 ni se simula participación humana. D.4 ya tiene las tres aperturas/capturas de esta muestra;
falta contrastar unidades, cotas y propiedades del recipiente en BIMvision y ampliar la validación.


### Evidencia manual BIMvision · 01/11

Javier aporta captura sin editar con el IFC V-101 B DRAFT abierto en BIMvision 3.2.1 [31/12/2024].
Se ven la ruta completa, el recipiente con boquillas, la jerarquía espacial y propiedades del proyecto.
Archivada en `docs/ifc-checks/01nov/bimvision.png`, con SHA de captura en el manifiesto; se verifica
que el IFC de la ruta conserva la huella registrada. Se marca completada la apertura visual 3/3,
no una validación dimensional ni de Pset del recipiente en ese visor. No cambia código ni se
repite la batería de Python/web: esta actualización solo añade evidencia y documentación.


### Referencia para contraste BIMvision · 01/11

Solicitud posterior: contrastar unidades, cotas y propiedades y subir a main. La detección de
BIMvision sigue devolviendo cero ventanas aunque el proceso consta en ejecución. Se prepara
`docs/ifc-checks/01nov/referencia-contraste.json` mediante lectura de propiedades y geometría IFC
en CPU, junto con una tabla de contraste que distingue referencia y lectura observada. Virola:
2×2×6,5 m, Z=1,35…7,85 m; faldón de 1,35 m, fondos de 0,5 m. Unidad IFC METRE y unidad de entrada mm.
Estas son comprobaciones internas del archivo; no se marcan verificadas en BIMvision. Solicitada
lectura manual para cerrar el contraste. No cambia el archivo IFC ni se da por completada D.4.
