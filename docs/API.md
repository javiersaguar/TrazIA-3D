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
