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
| GET /estudio | Archivo de Lectura o estado vacío explícito |

El id completo de revisión es `proyecto:equipo:revisión`; A/B son alias de la demo V-101.
BCF y exportación multiesquema responden 501 hasta su fase. POST /estudio y POST /copiloto
responden 503 mientras falten sus ejecutores. No devuelven resultados simulados.

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
docker compose --profile gpu exec ollama ollama pull qwen3:4b
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

**Validación disponible:** ambos YAML cumplen el esquema oficial Compose, con SHA-256
`d549057ebc2925f39f62799eab0db7b9e2c18b35b6c00595199116da3ed10e64` consultado el 26/10/2026.
Docker no está instalado en el equipo de desarrollo de esta fase. No se han construido ni arrancado
las imágenes ni se ha medido GPU/Redis/Postgres en contenedores. Hay que ejecutar esos comandos
antes de presentar el perfil de escala como probado.


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
