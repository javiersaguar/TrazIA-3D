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
