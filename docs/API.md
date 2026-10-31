# API local de TrazIA-3D

## Arranque

```bash
uv sync --extra dev --extra api
uv run --extra api python -m trazia.api
```

Escucha en `127.0.0.1:8000`. Documentación interactiva: `/docs`; contrato: `/openapi.json`.
La primera ejecución aplica la migración Alembic 0001 y carga las revisiones sintéticas A/B.
Los reinicios conservan los cambios humanos: el seed no sobrescribe revisiones existentes.
`TRAZIA_DATA` cambia la carpeta de datos; `TRAZIA_DATABASE_URL` permite Postgres.
Las credenciales se configuran por entorno y no se guardan en Git.

## Endpoints de la base

| Método y ruta | Resultado |
| --- | --- |
| GET /health | Estado de API y versión del contrato |
| POST /documents | Multipart file + document_id/revision opcionales; registro y SHA-256 |
| GET /equipment | Equipos con revisiones persistidas; sin equipos de relleno |
| GET /equipment/{tag}/revisions/{rev} | Contrato 0.3 y ETag; query project_id |
| GET /revisions/{id}/fields | Campos trazables por ruta y ETag |
| PATCH /revisions/{id}/fields/{path} | Estado/corrección, nueva versión y auditoría |
| POST /revisions/{id}/approve | Aprobación si todos los campos están aceptados/corregidos y los originales coinciden |
| GET /revisions/{id}/audit | Antes/después, actor, fecha y tiempo declarado por acción |
| GET /revisions/{id}/documents/{document_id} | Original comprobado por SHA-256 |
| GET /revisions/{id}/ifc?draft=true | IFC4 DRAFT; sin draft requiere aprobación |
| POST /equipment/{tag}/jobs | Procesamiento asíncrono; 202 y job_id |
| GET /jobs/{id} | Estado, intentos, error y RunInfo |
| GET /jobs/{id}/events | SSE persistente; eventos stage y complete; admite Last-Event-ID |
| POST /jobs/{id}/cancel | Cancelación; no se publica un resultado después de cancelar |
| GET /diff?from=A&to=B | Diferencias actuales de campos/evidencia/documentos |
| GET /bench?extractor=etiquetas | Informe sintético existente, sin inventar mediciones |
| GET /plant | Equipos; layout=null hasta disponer de posición real |
| GET /estudio | Último trabajo terminado, informe de Lectura o estado vacío explícito |
| POST /estudio | StudyInput, Idempotency-Key, trabajo asíncrono 202 |
| GET /learning/corrections | Correcciones sintéticas vigentes y aprobadas, con cursor |

El id completo de revisión es `proyecto:equipo:revisión`; A/B son alias de la demo V-101.
BCF y exportación multiesquema están implementados (ver secciones posteriores).
POST /copiloto usa Ollama local y herramientas de lectura, o una respuesta cacheada.
POST /estudio ejecuta el arnés mediante la cola común y publica el resultado por trabajo.

## Concurrencia e idempotencia

Todos los POST con efecto y PATCH requieren `Idempotency-Key` (1–128 caracteres). Se conserva
24 horas, con hash del cuerpo y la respuesta en la misma transacción que el efecto.
Repetir clave/cuerpo devuelve la respuesta original. Reutilizarla con otro cuerpo devuelve 409.
Una clave se limita a su operación y recurso.

PATCH y aprobación requieren `If-Match` con el ETag devuelto al leer la revisión. Si falta: 428;
si ya cambió: 412. El update compara la versión también en SQL. La idempotencia se comprueba
antes del ETag: un reintento de una operación ya confirmada puede usar el ETag anterior.
Una edición retira la aprobación. Ni los trabajos ni el seed sobrescriben una revisión existente.

```bash
curl -i http://127.0.0.1:8000/equipment/V-101/revisions/A
curl -X PATCH http://127.0.0.1:8000/revisions/A/fields/diameter \
  -H 'Content-Type: application/json' -H 'Idempotency-Key: ejemplo-aceptar-1' \
  -H 'If-Match: "1"' -d '{"state":"accepted","actor":"Javier Saguar Antona"}'
curl -N http://127.0.0.1:8000/jobs/JOB_ID/events
```

En PowerShell, usar `curl.exe` para evitar el alias de Invoke-WebRequest.

## Archivos, trabajos y límites actuales

- Archivos inmutables por SHA-256 en `data/store/`, fuera de Git. Lectura verifica el hash.
- Límite de archivo: 25 MiB; multipart completo: 26 MiB, incluso con transferencia por fragmentos.
- CORS solo para localhost y 127.0.0.1, puertos 3000/3100/3200; ETag expuesto al cliente.
- El actor de revisión se registra, pero no se autentica: esta base se sirve en local.
- La cola local limita a dos trabajos simultáneos. Se recuperan trabajos interrumpidos al arrancar.
- Cancelación cooperativa entre etapas: un parseo nativo ya iniciado puede terminar en su hilo;
  el estado persistido impide que publique el resultado tras cancelar o agotar el tiempo.
- El adaptador temporal mantiene la firma de process y solo ejecuta b_reglas sin proveedores.
  Cuando exista trazia.pipeline, se usa automáticamente su process sin modificar sus archivos.
- RunInfo mide segundos con reloj monotónico. En el baseline no hay tokens, llamadas externas ni
  coste de proveedor; GPU permanece null. No se calcula un coste energético sin medirlo.
- El tiempo de revisión suma únicamente acciones que aportan seconds. No se atribuye tiempo cero
  a las acciones sin cronometraje ni se presenta ese registro como atención activa demostrada.

## Fuentes de implementación

[Sesiones SQLModel](https://sqlmodel.tiangolo.com/tutorial/fastapi/session-with-dependency/),
[Alembic programático](https://alembic.sqlalchemy.org/en/latest/api/config.html),
[cola arq](https://arq-docs.helpmanual.io/).


## Cola local y Redis

`TRAZIA_QUEUE=process` es el valor por defecto. Con `TRAZIA_QUEUE=redis`, configurar
`TRAZIA_REDIS_URL` y arrancar uno o más workers:

```bash
uv run --extra api arq trazia.queue.worker.WorkerSettings
```

Los workers comparten la base de datos y data/store con la API. La migración 0002 incorpora
leases: solo un ejecutor reclama un trabajo, incluso ante una entrega repetida de Redis.
Un trabajo interrumpido se puede recuperar al caducar su lease. Un cierre limpio deja la tarea
pendiente; el reinicio conserva sus intentos anteriores y no duplica la revisión.

JobInput admite timeout_seconds (plazo total, máximo 3.600), max_attempts (1–5) y
retry_backoff_seconds (0–30). Se reintentan errores de transporte y fallos que Lectura marque
opcionalmente retryable=true; los datos inválidos no se reintentan. El backoff es exponencial,
limitado a 30 segundos y contenido en el plazo total.

RunInfo suma consumo de los intentos que lo devuelven. El campo opcional accounting_complete=false
avisa si algún intento no devolvió contabilidad; en ese caso tokens/coste/GPU son null y
external_calls representa solo las llamadas contabilizadas, no un total garantizado.
El RunInfo de la revisión conserva la ejecución de Lectura; el del trabajo mide también la
orquestación y los reintentos. Así no se cambia la huella del IFC ya producido al cerrar el trabajo.


## Docker Compose

Usar un perfil cada vez (local/gpu/escala comparten el puerto de API):

```bash
docker compose --profile local up --build
docker compose --profile gpu up --build
docker compose --profile gpu exec ollama ollama pull qwen3-vl:4b-instruct
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile escala up --build
# Aumentar workers; todos comparten Postgres y el almacén de contenido:
docker compose --profile escala up --scale worker=4
```

Local: web 3000 y API 8000. Escala: web 3200 y API 8000, Redis y Postgres internos.
GPU: Ollama con reserva de GPU NVIDIA; descargar el modelo en su volumen antes de usarlo.
La configuración de escala añade dos workers por defecto en docker-compose.prod.yml.
Los puertos publicados se limitan a 127.0.0.1. Las credenciales de la base de datos son de demo local.
API y web se ejecutan como usuarios sin privilegios. Los contextos de build excluyen .env,
datos privados, cachés y dependencias del host mediante archivos Dockerfile.*.dockerignore.

El cliente Next recibe NEXT_PUBLIC_API_URL al compilar la imagen. Dejar el build arg vacío
produce la demo offline. Para el perfil local con Ollama en el host, usar
TRAZIA_OLLAMA_URL=http://host.docker.internal:11434; GPU usa el servicio interno ollama.
Sin Docker, las variables de .env se pueden cargar con `uv run --env-file .env --extra api ...`.

**Validación 27/10/2026:** imágenes Linux construidas y perfiles local, escala y GPU
arrancados en Docker 29.6.2 / Compose 5.3.1 dentro de Ubuntu/WSL. API, trabajo B, SSE, IFC,
idempotencia, HTTP de Next y persistencia tras reinicio pasan en los tres perfiles. Escala
usa Redis/arq/Postgres; NVIDIA visible desde el contenedor Ollama: RTX 5070 Laptop, 8151 MiB.
No se ha medido inferencia dentro del contenedor GPU ni un lote de 400 equipos.

Repetir después de construir las imágenes con
`uv run python scripts/check_compose.py --wsl Ubuntu --profiles local escala gpu` desde
PowerShell, o sin `--wsl Ubuntu` donde Docker esté en PATH. El chequeo crea y elimina solo su
proyecto temporal, sin publicar puertos. [Evidencias de Fase 1](FASE1.md).


## Web conectada y tipos

Sin `NEXT_PUBLIC_API_URL`, la web conserva la demo offline. Para conectar:

```powershell
# Terminal 1, raíz del repositorio
uv run --extra api python -m trazia.api
# Terminal 2, web/
$env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:8000"
corepack pnpm dev
```

El cliente no sustituye errores de API por datos simulados. Las ediciones envían ETag e
Idempotency-Key; se serializan por revisión y un conflicto 412 actualiza la consulta.
Los IFC llevan una versión en la URL para cargar la geometría vigente sin cambiar el visor.
Pipeline permite subir documentos de V-101 o reprocesar sus originales, crea una revisión
nueva y muestra eventos SSE persistidos. La navegación conserva la conexión del trabajo.
El selector A/B de Revisión sigue limitado a las revisiones de la demo; las revisiones de
trabajos se consultan por su identificador en la API.

`corepack pnpm gen:api` desde web/ exporta `create_app().openapi()` con uv y regenera
openapi.json y schema.ts con openapi-typescript, sin necesitar un servidor en ejecución.
`corepack pnpm gen:types` regenera el contrato de revisión desde su JSON Schema.
Para verificar ambos transportes, ejecutar los comandos web con la variable definida y
sin ella. Playwright arranca una API aislada y persistencia bajo generated/ para el modo
conectado; `PW_EXTERNAL_API=1` permite usar un servidor ya iniciado.


## IFC multiesquema y comparación geométrica

`GET /revisions/{id}/ifc?draft=true&schema=IFC4X3` admite IFC4 (por defecto), IFC4X3 e IFC2X3.
La ruta mantiene las comprobaciones de aprobación y originales del flujo de revisión.
Los trabajos validan contrato y reglas EXPRESS antes de publicar el IFC; un error no se
presenta como modelo válido. Esta validación verifica estructura IFC, no exactitud del plano.

```bash
uv run --extra api trazia export examples/vessel_rev_a.json --draft --schema IFC2X3 -o generated/rev_a_2x3.ifc
uv run --extra api trazia validate-ifc generated/rev_a_2x3.ifc
uv run --extra geo trazia compare-ifc generated/rev_a.ifc referencia.ifc --samples 1024 -o generated/geometry.json
```

La comparación empareja elementos por GlobalId y usa mallas trianguladas del IFC en metros.
Informa IoU de cajas, Chamfer simétrico no cuadrático y Hausdorff **muestreado**, con semilla
reproducible y distancias por vértice para un mapa de error. Se comparan muestras con
triángulos; el máximo observado no garantiza el máximo continuo de toda la superficie.
Un GUID sin pareja aparece añadido/eliminado, sin inventar una correspondencia.
Instalar `--extra geo` para estas métricas; Docker.api ya lo incluye.

Entidades IFC4/4X3: Tank/Pump/Compressor, componentes agregados y un DistributionPort por
boquilla en su extremo. IFC2X3 usa FlowStorageDevice/FlowMovingDevice/FlowSegment/FlowFitting
con tipos TankType/PumpType/CompressorType/PipeSegmentType/PipeFittingType: esas clases de
ocurrencia modernas no existen en 2X3. Conserva Names, GUID y geometría; los fondos usan BRep.

DocumentReference apunta a urn:sha256 del original; su asociación y TrazIA_Provenance
conservan hashes, fuentes y RunInfo. Los psets comunes añaden referencias y diámetro nominal.
IfcApproval solo se añade a una exportación aprobada, tras revisión humana; un DRAFT no crea
una aprobación automática. OwnerHistory identifica la aplicación local, sin autenticar personas.

Fuentes: [validación IfcOpenShell](https://docs.ifcopenshell.org/autoapi/ifcopenshell/validate/index.html),
[proximidad trimesh](https://trimesh.org/trimesh.proximity.html) y
[metadatos de autor IFC](https://docs.ifcopenshell.org/autoapi/ifcopenshell/api/owner/settings/index.html).

Para referencias externas con GUID distintos pero nombres coincidentes y únicos, usar
`compare-ifc ... --match name`. Este modo se elige explícitamente y rechaza nombres
ambiguos; no empareja elementos por parecido visual sin una correspondencia comprobable.


## Cambios en tres capas y BCF 2.1

- GET /diff?from=A&to=B conserva la respuesta rápida de campos para la web.
- GET /diff?from=A&to=B&layers=true añade páginas alineadas con OpenCV ECC, geometría
  por GUID y comprobaciones cruzadas de regiones/campos y marcadores de revisión.
- GET /diff/visual?from=A&to=B&document_id=GA-V101&page=1 devuelve PNG con diferencias
  resaltadas; 409 si no se puede alinear, 422 si la página no existe.
- GET /diff/bcf?from=A&to=B descarga un topic por cambio de campo, selección IFC y cámara.

```bash
uv run --extra api trazia diff examples/vessel_rev_a.json examples/vessel_rev_b.json --geometry -o generated/changes.json
uv run --extra api trazia bcf examples/vessel_rev_a.json examples/vessel_rev_b.json -o generated/changes_DRAFT.bcfzip
```

La API instala el extra geo a través de su dependencia de extras; el CLI geométrico también
puede instalarlo por separado. La diferencia visual verifica originales por SHA-256, usa
traslación/rotación ECC acotada a 3 grados y 5 % de página y transforma evidencias y marcadores
al marco de la página anterior. Si falla la alineación se informa, sin atribuir cambios.
Se procesan hasta diez páginas por PDF común y hasta 200 regiones/marcadores por página.
Los triángulos y nubes son candidatos heurísticos que hay que confirmar. Los cruces señalan
campos sin región y regiones sin campo; un cajetín modificado también puede producir avisos.

La capa geométrica usa distancias de vértices de mallas propias con discretización fija,
en metros y por GUID; compare-ifc ofrece el contraste adicional contra superficies.
No se incorpora un mapa de calor al visor protegido. BCF contiene cámaras, GUID, huellas y
referencias documentales; no incluye originales privados ni declara aprobación automática.
El formato se ha contrastado con los XSD oficiales de la etiqueta v2.1 de buildingSMART.

Fuentes: [BCF 2.1](https://github.com/buildingSMART/BCF-XML/releases/tag/v2.1),
[ECC OpenCV](https://docs.opencv.org/4.x/dc/d6b/group__video__track.html).


## Copiloto local con citas (DEC-26)

`POST /copiloto` consulta Ollama en el equipo. El servidor solo dispone de herramientas
`read_fields`, `read_evidence`, `read_changes` y `read_rules`; recibe copias de revisiones y
la capacidad de leer originales por SHA-256, sin sesiones SQL ni funciones de escritura.
No acepta/corrige campos, aprueba, crea trabajos ni registra tiempo de revisión humana.

```powershell
ollama pull qwen3-vl:4b-instruct
$env:TRAZIA_OLLAMA_URL = "http://127.0.0.1:11434"
$env:TRAZIA_OLLAMA_MODEL = "qwen3-vl:4b-instruct"
uv run --extra api python -m trazia.api
```

El `pull` solo hace falta si no están instalados los pesos. Se reutiliza el servidor Ollama;
los pesos no se incluyen en Git. La web necesita `NEXT_PUBLIC_API_URL` como se explica arriba.
En modo offline conserva sus explicaciones por reglas, identificadas como tales.
En modo API, una caída del modelo muestra el error y no se sustituye por reglas.

```json
{
  "question": "¿Qué cambia respecto a la revisión A en esta cota?",
  "revision_id": "B",
  "previous_id": "A",
  "path": "nozzles.N3.elevation"
}
```

`path` y `previous_id` son opcionales; las revisiones deben corresponder al mismo proyecto y
equipo. La respuesta contiene `statements`, `proposals` y `citations`; cada afirmación y
comprobación propuesta remite a IDs emitidos por las herramientas. Las citas distinguen
campo JSON, original, cambio y regla. Para originales incluyen documento/SHA, página y bbox
PDF o hoja/celda Excel, más el fragmento efectivamente leído. `original_verified` significa
que coincide el SHA-256, no que la interpretación técnica sea correcta.

Se devuelve `read_only: true`, modelo, versión/huella de revisión, huella de instrucciones y
herramientas, y `run` con tiempo de pared y tokens reportados por Ollama, incluidos reintentos.
`external_calls=0` y `cost_eur=0` reflejan ausencia de proveedor facturado; no miden electricidad,
amortización o coste total del equipo. `gpu_seconds` queda sin medir. Si falta contabilidad,
los tokens son null y `accounting_complete=false`, sin inventar ceros.

- 200 con `abstained=true`: evidencia insuficiente, contrato inválido o referencias rechazadas;
  no hay afirmaciones, propuestas ni citas en una abstención.
- 409: cambió una revisión durante la consulta; la web refresca sus datos.
- 422: entrada inválida, campo inexistente o revisiones incompatibles; 404 para revisión ausente.
- 503: Ollama/modelo no disponible, no local o sin capacidad de herramientas.

Se comprueba `/api/show`: modelo GGUF con herramientas, sin metadatos remotos. Se permiten
loopback, localhost y los nombres de servicio local `ollama`/`host.docker.internal`; sin proxies
de entorno, redirecciones, credenciales ni modelos cloud. La persona que despliega debe
configurar esos nombres para el servicio local. Los documentos y preguntas son datos, no
instrucciones para ampliar capacidades.

Límites: 200 rutas de contexto, seis campos por lectura, cuatro llamadas nativas de herramientas
en el plan, diez lecturas como máximo; fragmentos PDF de hasta 1800 caracteres y rangos Excel
de hasta 32 celdas. Contextos inicial/final acotados a 24k/48k caracteres, pregunta de hasta
2000 caracteres, una consulta activa por proceso API. Timeout del modelo 90 s, total de ruta
95 s. Cancelar en el navegador aborta la espera HTTP; no garantiza detener una generación ya
iniciada en Ollama. No hay memoria de conversación entre consultas.

El plan usa llamadas nativas; la salida final usa JSON Schema con las citas disponibles.
Se rechazan referencias inventadas, declaraciones de escritura y determinadas negaciones
de verificación contradictorias con el original leído. Se permite una reformulación si el score se presenta
como certeza/probabilidad sin calibración. No se garantiza que toda conclusión del modelo
se deduzca de sus citas: hay que comprobar los fragmentos. PDF escaneado o imagen sin texto
legible no recibe una cita OCR inventada; esta herramienta no implementa OCR.

Fuentes de integración: [Ollama chat](https://docs.ollama.com/api/chat),
[herramientas](https://docs.ollama.com/capabilities/tool-calling) y
[salida estructurada](https://docs.ollama.com/capabilities/structured-outputs).


## Medición del lote con workers

`scripts/run_scale.py --wsl Ubuntu --workers 1 4` levanta despliegues aislados Redis/arq/Postgres
y llama al cliente `scripts/measure_scale.py` para procesar todo el corpus sintético. Requiere
la imagen API construida y generated/synthetic_v2. Publica la API de prueba solo en localhost
18000 dentro de WSL; no sustituye el servidor de desarrollo. Los almacenes son nuevos por prueba
y se eliminan con sus contenedores al terminar. Se conserva el estado terminal de cada trabajo.

El informe separa tiempos observados, costes no informados y extrapolación a 400×4. No supone
que un trabajo fallido haya producido un IFC, ni que un IFC estructuralmente válido coincida
con el plano. Resultados y límites de la primera medición: [FASE3.md](FASE3.md).


## Estudio, modo offline y correcciones · 30/10/2026

[Contrato, ejemplos, arquitectura y verificación](BACKEND_2026-10-30.md).
`POST /estudio` exige un cuerpo StudyInput y `Idempotency-Key`. Devuelve 202 con `job_id`;
se consulta y cancela mediante `/jobs/{id}`. `GET /estudio?job_id=…` selecciona su resultado.
La ruta de conjuntos sintéticos la fija `TRAZIA_STUDY_DATA`, nunca el cliente.
`GET /learning/corrections?after=0&limit=100` no entrena ni recalibra.
Con `TRAZIA_OFFLINE=1`, visión y copiloto usan sus cachés; una consulta sin caché devuelve
un error recuperable. Los tipos OpenAPI de la web reflejan el contrato actualizado.


## Estudio mediante CLI estable · sesión Plataforma 30/10

El trabajo lanza `python -u -m bench.estudio` como subproceso con los argumentos estables
`--datos`, `--conjuntos`, `--variantes`, `--casos`, `--degradaciones`, `--remuestreos`,
`--semilla` y `--salida`. No importa funciones internas de `bench`. El directorio de
salida pertenece al trabajo; el JSON se guarda en el almacén SHA-256 al terminar.
Se conservan SSE de inicio/salida resumida/fin, timeout, cancelación del proceso e
idempotencia. Un proceso que termine sin `estudio.json` deja un error explícito; no
publica resultados ni sustituye el estado vacío. Prueba real: un caso, variante B,
vectorial, 20 remuestreos.


## Caché de trabajos en la API · 4.2

Los trabajos de lectura terminados y con IFC validado guardan su revisión DRAFT y avisos
en el almacén SHA-256. La clave combina hashes de originales, metadatos documentales
(identidad, nombre, revisión y orden), estrategia, proveedores, dataset y huella de la
memoria anterior, cuando la haya. Los IDs SQL de subida no forman parte de la clave.
No se cachean fallos, cancelaciones, timeouts ni aprobaciones humanas posteriores.

Con `TRAZIA_OFFLINE=1`, POST de trabajo comprueba la entrada antes de encolar: un fallo
devuelve HTTP 409 en español. También se verifican los originales y el blob cacheado.
En un acierto el worker restaura el resultado sin llamar al pipeline, asigna los IDs
del trabajo nuevo y mantiene approval=null. GET /jobs/{id} indica cache_hit=true y SSE
explica la reutilización. La contabilidad de esa lectura de caché tiene cero tokens,
inferencia GPU y llamadas externas nuevas; no suma el coste histórico del trabajo
original ni mide energía. El modo online sigue ejecutando el pipeline y calentando
la caché; esta es una instantánea preparada para la demo, no una evaluación de un
modelo actualizado. Al cambiar modelos/reglas se prepara una caché nueva.

Persistencia: Alembic 0004 añade job_cache y el indicador de acierto al trabajo. No cambia
el contrato 0.3 ni se modifica vision/cache.py. Las cachés de visión/copiloto existentes
se conservan, separadas de esta caché de resultados del pipeline.


## CORS configurable · sesión Plataforma

`TRAZIA_CORS_ORIGINS` acepta orígenes HTTP(S) separados por comas y sustituye la lista
predeterminada. Se recortan espacios, se normalizan puertos estándar y se eliminan
duplicados. Rutas, credenciales, comodines y puertos inválidos se rechazan al crear la API.
Ausente o vacía conserva localhost y 127.0.0.1 en 3000, 3100, 3200, 3300, 3310 y 3311.
Compose propaga la variable a API y workers. Para el frontend de esta sesión, PowerShell:

```powershell
$env:TRAZIA_CORS_ORIGINS="http://localhost:3120,http://127.0.0.1:3120"
$env:TRAZIA_PORT="8020"
uv run --extra api python -m trazia.api
```

Las cabeceras de idempotencia, If-Match y ETag y los métodos admitidos no cambian.


## Registro de correcciones humanas · 3.8 (datos)

Cada PATCH confirmado que cambia valor, unidad o estado registra una fila transaccional
y añade una línea a `generated/correcciones/correcciones.jsonl`. La ruta estándar es
relativa a la raíz del repo; `TRAZIA_CORRECTIONS_FILE` permite fijarla. Con data_root
explícito en una aplicación embebida, la salida predeterminada queda dentro de ese
almacén, para aislar datos y pruebas. Compose usa /data/correcciones/correcciones.jsonl.

Formato de cada línea: revision_id, equipment_tag, revision, path, value_before,
value_after, unit, state_before, state_after, confidence, confidence_raw, channel,
strategy, document_id, page, bbox, actor, at y data_sha256. Los opcionales ausentes
son null. La confianza, canal, estrategia y cita pertenecen a la predicción ANTERIOR
a la intervención; unit y data_sha256 corresponden al resultado. at es ISO 8601 UTC.
No se exige ni se supone que la confianza esté calibrada o que exista un intervalo.

GET /correcciones?desde=2026-10-30T00:00:00Z devuelve {correcciones:[...],count:N},
filtrado inclusivamente desde esa fecha. Se requiere zona horaria; no llama a modelos
ni a calibración. Son intervenciones históricas, incluidas revisiones aún no aprobadas.
La exportación previa /learning/corrections conserva su selección de ejemplos aprobados.

Se conserva auditoría, ETag/If-Match e idempotencia. Una petición repetida no duplica
líneas; una edición rechazada o sin cambios no crea una corrección. Alembic 0005 añade
una bandeja de salida SQL y un cursor. El bloqueo de publicación funciona en SQLite
y Postgres. Ante un fallo tras escribir, el reintento descarta solo la cola no confirmada
y vuelve a publicar; el archivo perdido o truncado se reconstruye con las filas SQL.
Usar un único almacén SQL por archivo configurado. Si falla la exportación, el PATCH
informa 503: el campo está guardado y se reintenta con la misma Idempotency-Key. Las
filas siguen accesibles por GET; al arrancar se intenta publicar lo pendiente.


## Recalibración desde las correcciones (31/10)

`uv run python -m bench.recalibrar --almacen <TRAZIA_DATA> --correcciones <JSONL> --base <calibracion.json> --salida generated/recalibracion`
propone un reajuste isotónico y conforme en CPU, sin ejecutar visión. `--base` es opcional.
El JSONL se contrasta con el registro SQL, la predicción original de la auditoría, la
aprobación vigente y los originales disponibles. Se deduplican los clics por campo;
se incluyen confirmaciones correctas y correcciones, no solo errores. Los ejemplos
reales, borradores, intervenciones sustituidas, valores ya humanos y predicciones sin
confianza bruta identificable quedan fuera. Las revisiones del mismo tag no se reparten
entre ajuste y prueba. Los cambios de unidad sin normalizar se excluyen, y los textos
se comparan sin distinguir mayúsculas.

Mínimos: seis equipos independientes por estrategia, 30 campos por grupo de ajuste
y 30 campos de validación por estrategia. Dos tercios de los equipos se dividen de nuevo entre curva y cuantil; el
tercio restante valida ECE. Solo se escribe `calibracion.json` si todas las estrategias
observadas tienen curva y el ECE de validación no empeora frente a la base. Siempre se
escribe `informe.json`, con estado `insufficient`, `rejected` o `candidate`; la propuesta
no activa nada. No se sobrescribe la base. Las estrategias sin nuevos ejemplos
conservan su calibración anterior (o confianza bruta si no tenían parámetros), también
para intervalos y abstención. El sesgo de qué campos revisa una persona
impide interpretar esta validación como precisión sobre todos los planos.

Para activar una propuesta revisada, usar su archivo como `TRAZIA_CALIBRATION`. En
Compose, API y workers comparten `/data/calibration/calibracion.json` por defecto. La
clave de caché incorpora la huella de la calibración; las entradas de la versión previa
no se reutilizan. Si los parámetros cambian mientras corre un trabajo, ese resultado
se entrega pero no se incorpora a la caché. Los valores/calibraciones no cambian las
revisiones ya aprobadas.

El lote de escala informa ahora `lod` y `equipment_kind` para cada modelo accesible y
`successful_lods`/`errors_by_message` en el resumen. Una envolvente de bomba LOD 1 no
se presenta como un recipiente detallado. Los errores de inspección por tag permanecen
explícitos y no interrumpen la contabilidad del lote.
