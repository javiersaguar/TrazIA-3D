# Edición asistida del modelo · contrato, API y estado

Workstream K. Plan: [PLAN_EDICION_ASISTIDA.md](PLAN_EDICION_ASISTIDA.md). Fecha: 08/11/2026.

**Estado:** K.0–K.6 implementados en la rama `feat/edicion-asistida`, con pruebas escritas en
`tests/test_edicion_asistida.py` y `web/src/features/design-edit/form.test.ts`. La suite **no se
ha ejecutado en el portátil de desarrollo** porque le falta memoria. Debe pasar en CI antes
de integrar en `main`. K.7 queda abierto hasta tener esa ejecución y una sesión de uso. K.8 no
se ha empezado. Todos los ejemplos son sintéticos (V-101) y no hay datos de TR.

## 1. Orden de diseño frente a corrección de lectura (K.0)

| | Corrección de extracción | Cambio de diseño |
| --- | --- | --- |
| Pregunta | ¿Qué dice el plano? | ¿Qué queremos que sea? |
| Vía | `PATCH /revisions/{id}/fields/{path}` (Revisión) | Propuesta → previsualizar → confirmar (Proponer cambios) |
| Revisión | Edita la misma revisión e invalida su aprobación | Crea una revisión DRAFT nueva; la base no cambia |
| `Source.channel` | `humano` | `diseno` |
| Documento citado | El original (página y región) | Su propio documento de orden (`role: orden_diseno`) |
| Confianza | La de la lectura; se conserva la bruta | `1`, sin `confidence_raw` ni intervalo: valor declarado, no estimación |
| Aprendizaje | Puede entrar si se aprueba con originales verificados | Excluido siempre |

Una orden de diseño nunca se atribuye al plano original: el validador rechaza un campo
`diseno` que cite un original y un campo de lectura que cite una orden. Tampoco tiene
página, celda, región, estrategia, modelo ni `grounded`. `PATCH` no puede corregir ni
rechazar un valor de diseño, ni enviar una fuente `diseno`. Sí puede aceptarlo como parte de
la revisión técnica.

### Ampliación aditiva del contrato 0.3

Solo se añaden campos opcionales. Si están ausentes **no se serializan** (`exclude_if`), así
que los JSON existentes y sus huellas de aprobación no cambian. Las huellas de los ejemplos A
y B se han comprobado idénticas antes y después del cambio.

- `Channel` admite `diseno`.
- `Source.design = {kind: "cambio_diseno", proposal_id, operation_id}`.
- `Document.role = "orden_diseno"`. Ausente significa original aportado.
- `Revision.derived_from = {kind: "cambio_diseno"|"reversion", revision_id, input_sha256,
  proposal_id, order_document_id}`.

Hay que actualizar los consumidores de tipos: `uv run trazia schema -o generated/revision.schema.json`
y `pnpm gen:types`. La web nueva usa tipos propios en `features/design-edit/api.ts` y no
depende de esa regeneración.

El documento de orden es un JSON canónico guardado por SHA-256 con actor, motivo, origen
(formulario, chat o deshacer), texto pedido, revisión base con su huella, y valores y fuentes
anteriores de cada operación. Es la evidencia de la orden y nunca una lectura.

### Matriz familia × operación (MVP)

| Familia | Operaciones admitidas |
| --- | --- |
| `vertical_vessel` LOD 2/3 | `diameter`, `height` (longitud entre tangentes), `total_height` (derivada), `head_depth`, `skirt_height`, `skirt_thickness`; por boquilla radial existente: `diameter`, `projection`, `elevation`, `azimuth`; `service`/`rating` si existen; atributos |
| `vertical_vessel` LOD 1 | Solo atributos; la envolvente no se edita |
| `horizontal_vessel`, `column`, `tank` | Solo atributos hasta probar cada familia (K.8) |
| `pump`, `compressor`, `generic` | Solo atributos |

Restricciones que se validan sobre el **lote completo**, no campo a campo:

- **Altura total y longitud entre tangentes son magnitudes distintas.** `height` es la
  longitud de la virola. `total_height` se resuelve explícitamente como
  `height = total − faldón − fondo superior` y no puede ir junto a `height` en el mismo lote.
- **Elevación sobre el suelo local** (z = 0 en la base del faldón). También se admite sobre la
  tangente inferior: se convierte con el faldón del candidato y se muestra la conversión.
- **Azimut en el convenio interno**: 0° = +X, antihorario. El Norte de planta no está
  verificado (C.4), así que una petición «respecto al Norte» se rechaza en lugar de suponerlo.
- Cada boquilla radial debe quedar dentro de la virola con su radio. Si un cambio la deja fuera,
  se informa del intervalo admisible y **no se desplaza**: hay que incluir su nueva elevación en
  el lote. Por eso un lote puede ser válido aunque uno de sus cambios, aislado, no lo sea.
- Unidades explícitas para longitudes. Se normalizan con `trazia.units` y no se mezclan
  presión absoluta y manométrica.
- Se avisa de los efectos: altura total resultante, desplazamiento de la tangente inferior y
  regeneración radial de las boquillas al cambiar el diámetro. Nada se corrige en silencio.

### Exclusión del aprendizaje (amplía DEC-26 y DEC-27)

Un único predicado, `trazia.design.provenance.is_design_field`, se aplica en:

- `api/corrections.record_change`: el registro JSONL no recibe órdenes de diseño (la auditoría
  sí las guarda);
- `api/learning.approved_examples`, que alimenta los ejemplos few-shot y el feedback;
- `api/extraction_feedback`, en la prioridad de canales;
- `calibration/feedback.training_rows`, en la recalibración (contador `design_order`).

La auditoría de una revisión derivada usa la ruta `$design` (o `$reversion`), que ningún
consumidor de aprendizaje trata como campo. DEC-26 evoluciona así: el copiloto sigue siendo
de solo lectura y el modo «Proponer cambios» devuelve un borrador sin escribir nada.

## 2. API

| Método y ruta | Garantía |
| --- | --- |
| `GET /revisions/{id}/design-operations` | Catálogo de operaciones de la familia con valores actuales y referencias |
| `POST /revisions/{id}/change-proposals` | `If-Match` + `Idempotency-Key`. Valida el lote y no modifica la base |
| `GET /change-proposals/{id}` · `GET /revisions/{id}/change-proposals` | Estado, operaciones, incidencias, efectos y huellas; marca obsoleta una propuesta si la base cambió o caducó |
| `PUT /change-proposals/{id}` | Reemplaza el lote e invalida la previsualización anterior |
| `POST /change-proposals/{id}/preview` | Trabajo en cola (`/jobs/{id}` y SSE `/jobs/{id}/events`), con cancelación |
| `GET /change-proposals/{id}/preview.ifc` | IFC temporal exacto por SHA-256 |
| `POST /change-proposals/{id}/apply` | `If-Match` de la base + `Idempotency-Key` + huellas de propuesta e IFC |
| `POST /change-proposals/{id}/discard` | Descarta la propuesta y limpia el IFC temporal |
| `POST /change-proposals/{id}/revert` | Prepara una revisión compensatoria que se previsualiza y confirma igual |
| `GET /revisions/{id}/artifacts` | IFC, orden e informe publicados, con la huella de los datos |
| `GET /revisions/{id}/design-report.pdf` | Plano derivado (K.6) |
| `POST /copiloto/design-proposals` | Borrador desde texto; nunca escribe (K.5) |

Estados: `needs_clarification`, `invalid`, `ready`, `previewed`, `applied`, `discarded`, `stale`
y `draft`, que es transitorio al crear. Errores, avisos y aclaraciones se separan por
`severity`.

**Previsualización (K.2).** El trabajo calcula el candidato, genera el IFC4 DRAFT, lo valida
(esquema y, por defecto, reglas EXPRESS) y lo compara con la base. Informa del avance en cuatro
pasos fijos, que son un denominador real. Cada cambio del delta lleva sus `operation_ids` y
cada pieza su GUID estable, si está presente en el IFC y qué operaciones la afectan. El
resultado solo se publica en la propuesta si el trabajo sigue activo y la propuesta no cambió.
Cancelar o editar no publica nada. Los IFC temporales caducan
(`TRAZIA_PROPOSAL_TTL`, 2 h por defecto) y se limpian al descartar, al editar y al arrancar.

**Confirmación (K.3).** Se confirma la propuesta previsualizada con la base vigente (`If-Match`
y huella), las huellas de propuesta e IFC enviadas por el cliente y una etiqueta de destino
libre (`<raíz>-D<n>`). Los blobs (orden e IFC) se escriben por hash **antes** de la transacción
SQL. La transacción crea a la vez la revisión, el documento de orden, la auditoría `$design` y
los artefactos. Si algo falla, solo quedan blobs huérfanos inmutables y nunca una revisión a
medias. Reintentar con la misma clave devuelve la misma respuesta; otro clic con otra clave
recibe 409. La revisión nace DRAFT, no hereda aprobación y conserva los GUID de los elementos
que siguen existiendo, porque las claves dependen del ID estable y no de la revisión.
`GET /revisions/{id}/ifc?draft=true` sirve el IFC exacto validado mientras los datos no cambien.

**Deshacer.** Restaura cada campo de la orden tal como estaba en la base, con su valor,
evidencia original y estado, en una revisión nueva (`derived_from.kind = reversion`). No borra
historia ni recupera aprobaciones. Si un campo cambió después de aplicar, no se pisa: la
propuesta de deshacer queda inválida y explica el motivo.

## 3. Chat (K.5)

El intérprete por defecto (`reglas-es-1`) es determinista. Opcionalmente se usa el modelo local
de Ollama (`use_model`), y si no está disponible se vuelve a las reglas, avisando. Lo que
devuelve el modelo se filtra contra el catálogo: no puede proponer otras rutas ni acciones.
El intérprete solo recibe la petición y el catálogo, **nunca el texto de los documentos**, de
modo que una instrucción escrita en un PDF no llega a él. Pide aclaración cuando la altura, la
unidad, el objeto o el valor son ambiguos. Rechaza aprobar, confirmar, publicar, añadir o
eliminar piezas y desactivar reglas. El borrador rellena el mismo formulario y sigue el mismo
recorrido de validar, previsualizar y confirmar por una persona.

## 4. Plano derivado (K.6)

Es un PDF aparte, marcado como derivado y DRAFT. Incluye autor, fecha, revisión base y
destino, huellas de la orden y del IFC, y una tabla de cambios Δn. Solo se anota sobre el plano
donde la lectura anterior tenía página y región en un PDF original verificado por SHA. Lo demás
figura como «pendiente de delineación» y no se inventa ninguna región. Si cambian cotas o
posiciones, se avisa de que el dibujo deja de estar a escala, porque una anotación no redibuja
el recipiente. El original no se modifica. El PDF se registra como artefacto y la subida de
documentos lo rechaza como original de extracción. Se genera como raster con Pillow y
pypdfium2, sin dependencias nuevas.

## 5. Interfaz (K.4)

Está en Modelo → **Proponer cambios** (`/modelo?vista=editar`), a la que también se llega desde
el visor 3D con la pieza seleccionada. El formulario funciona sin modelo de lenguaje. La
selección 3D elige el grupo (equipo o boquilla) y solo se muestran las operaciones admitidas,
con su valor actual, unidad y referencia. Si una entrada cambia, la validación y la
previsualización anteriores se marcan como no vigentes. El visor alterna antes y después y en
«después» carga el IFC temporal real, con las piezas regeneradas y los conflictos resaltados.
«Corregir la lectura» queda separado y enlaza con Revisión. Requiere la API: sin ella, la vista
lo indica y no simula propuestas.

## 6. Medidas y límites

Medido el 08/11/2026 en el portátil de desarrollo (Intel de 12 hilos, Windows 11, Python 3.13),
con un caso sintético V-101 de 2 operaciones y tres repeticiones, sin cola ni API. Sin la
primera ejecución, que lleva la carga de módulos: evaluación del lote 22–28 ms; IFC4 con
detalle 1,2–1,5 s (unos 1 011 KiB); validación de esquema 1,4–1,7 s; con reglas EXPRESS
8,9–9,4 s; comparación 3–5 ms. La previsualización completa ronda los 11 s, por eso va en cola
con SSE. No se ha medido la confirmación por API ni el tiempo humano de revisión (E.5 sigue
pospuesta).

No se acredita cálculo resistente, proceso ni cumplimiento normativo. El chat con modelo local
no se ha medido (aciertos, aclaraciones, latencia): solo está probado con un proveedor inyectado.

## 7. Verificación pendiente (K.7)

- [ ] `uv run pytest -q tests/test_edicion_asistida.py` y la suite completa en CI (Ubuntu y Windows).
- [ ] `pnpm typecheck`, `pnpm lint`, `pnpm test:unit` y `pnpm build` en CI.
- [ ] Recorrido en la aplicación con capturas en claro y oscuro: cambio válido, lote relacionado,
  unidades equivalentes, boquilla fuera de límites, ambigüedad, base obsoleta, reintento,
  cancelación, descarte y deshacer.
- [ ] Reabrir en un visor externo un IFC de revisión derivada y comprobar los GUID persistentes.
- [ ] Medir el chat con el modelo local disponible.
