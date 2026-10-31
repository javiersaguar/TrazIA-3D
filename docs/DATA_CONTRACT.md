# Contrato 0.3 y compatibilidad con 0.2

Emitir esquema con `uv run trazia schema -o generated/revision.schema.json`.
Ejemplo completo en `examples/vessel_rev_a.json`.

Cada campo contiene `value`, `unit` y `source`. `source` incluye documento, página o
hoja/celda, localizador, región PDF opcional normalizada `[x0,y0,x1,y1]`, score y revisión.
El origen de coordenadas de la región PDF es la esquina superior izquierda.

La revisión incluye proyecto, revisión, tipo de dataset, catálogo documental y un equipo.
Los IDs de proyecto/equipo/boquilla son estables y solo admiten letras, números, `_` y `-`.
El tag tiene su propia evidencia; no se usa para calcular GUID porque puede cambiar.


## Contrato 0.3

La especificación compartida está en [COORDINACION-BACKEND.md](COORDINACION-BACKEND.md).
Se conservan los nombres de todos los campos de 0.2. Se añaden:

- `state`: candidate, conflict, abstained, accepted, corrected o assumed en cada valor trazable.
- `interval`: low, high, level (entre 0 y 1) y method=conformal; solo se informa si se ha calculado.
- `alternatives`: valores/unidades con su propia evidencia; `explanation` explica la incertidumbre.
- `Source`: confidence_raw, channel, strategy, model, prompt_sha256, grounded,
  text_original y unit_original. Son opcionales: ausencia significa desconocido.
- `Equipment`: siete tipologías, lod 1/2/3, support y envelope. Las cinco dimensiones y las
  tres boquillas siguen siendo obligatorias para vertical_vessel con lod >= 2.
- `Envelope`: origin y size con componentes x/y/z en mm y evidencia por componente. El origen
  puede ser cero o negativo; las dimensiones físicas y los tamaños deben ser positivos.
- `Nozzle`: service, rating y nozzle_type opcionales.
- `Revision.run`: estrategia, proveedores, segundos totales/GPU, tokens, coste y llamadas externas.
  Un coste desconocido es null; no se transforma en cero.

`source.reviewed` se sincroniza con `state in (accepted, corrected)`; un supuesto no equivale a
aceptación. No se aprueba una revisión con conflictos, abstenciones o supuestos pendientes.
Las alternativas también se validan contra el catálogo documental y los límites de página.

### Migrar

```bash
uv run trazia migrate antiguo.json -o revision-0.3.json
uv run trazia schema -o generated/revision.schema.json
cd web
corepack pnpm gen:types
```

`migrate_revision(dict)` no modifica la entrada y es idempotente. `load_revision` acepta 0.2 para
mantener operativo el extractor actual; devuelve siempre 0.3. reviewed=true migra a accepted;
el resto, a candidate. La confianza original también se guarda en confidence_raw. **Migrar no
calibra el score 0,75 del baseline**: Lectura debe aportar la calibración medida antes de usarlo
como probabilidad de acierto. No se inventan canales, modelos, intervalos ni metadatos de coste.

Una migración retira la aprobación porque cambia la huella. Los datos y la evidencia siguen
revisables; la nueva revisión necesita una aprobación nueva. El identificador estable del equipo
y de cada boquilla no cambia, y por tanto tampoco cambia el algoritmo de GUID del IFC.

## Formato acotado que reconoce el baseline

En texto PDF, una etiqueta por región o fila:

```text
TAG = V-101
DIAMETER = 2000 mm
HEIGHT = 6000 mm
HEAD_DEPTH = 500 mm
SKIRT_HEIGHT = 1200 mm
SKIRT_THICKNESS = 20 mm
NOZZLE N1: DIAMETER=200 mm; PROJECTION=400 mm; ELEVATION=2500 mm; AZIMUTH=0 deg
```

La familia vertical de nivel 2/3 necesita al menos tres boquillas completas. Se normalizan longitudes `mm`, `cm`, `m`
e `in` a milímetros. Solo se reconocen decimales con punto; no se interpretan separadores
de miles, unidades implícitas, cotas gráficas o ángulos sin referencia.

En Excel, una fila por parámetro: columna de etiqueta, valor y unidad. Atributos reconocidos:
`DESIGN_PRESSURE` (bar/kPa/MPa), `DESIGN_TEMPERATURE` (C), `OPERATING_WEIGHT` (kg)
y `MATERIAL` (sin unidad física, representada como `1`). No se evalúan fórmulas.

Se aceptan algunos alias literales en inglés/español; no son un motor general de comprensión.
La separación de columnas PDF usa una heurística de espacio. Planos densos y tablas con
saltos de línea pueden necesitar el futuro extractor de visión.

## Incertidumbre y conflictos

El score del baseline es 0,75: identifica candidatos de una regla, no una probabilidad de
acierto calibrada. No se convierte en aprobación. Todos los candidatos empiezan sin revisar.
Dos valores o unidades diferentes para el mismo campo bloquean `assemble`; la interfaz
permite desmarcar evidencias contradictorias. Si faltan parámetros se informa del error y
no se completa la geometría con valores inventados.

La interfaz `Extractor.extract(bundles) -> list[Candidate]` es el punto de extensión.
Un adaptador IA deberá conservar páginas/celdas/regiones y devolver campos desconocidos
fuera del contrato geométrico hasta su resolución. El texto de documentos es dato, nunca
instrucciones para ejecutar acciones o cambiar las reglas del sistema.

## Aprobación y revisiones

`approve` verifica hashes de originales, registra una declaración de revisión humana y
crea la huella de los datos incluyendo unidades, fuentes y documentos. El validador rechaza
una aprobación cuyo hash no coincide. No autentica al revisor ni verifica la verdad técnica
del contenido. Modificar datos requiere una nueva revisión.

La comparación separa cambios semánticos (valor/unidad), de evidencia y de catálogo.
La unidad de un atributo es parte del significado: el mismo número en bar y MPa cambia.
Con el extra geo/API se reconocen equivalencias físicas; 1 bar y 100 kPa se registran como cambio de procedencia, sin cambio de valor físico.

Los JSON sintéticos de la fase 0.1 eran un borrador local sin publicar. La versión 0.2
añade unidades por campo, tag trazable, fondos, faldón y aprobación; no es compatible con
ese contrato anterior. Los ejemplos del repositorio ya usan 0.3.


## Familias paramétricas y detalle (0.3, ampliación aditiva)

Todos los parámetros numéricos siguientes son campos trazados (valor, unidad mm, fuente,
estado e incertidumbre). Los tipos se publican también en `trazia.families.parameters`.

| Familia | Parámetros de nivel 2 |
| --- | --- |
| vertical_vessel | Los cinco parámetros históricos; virola en Z, fondos semielipsoidales y faldón |
| horizontal_vessel | horizontal: diameter, length, head_depth, support_height, saddle_width (axial), saddle_span (transversal) y dos saddle_positions en X |
| column | column.sections: id estable, diameter inferior, top_diameter opcional y height; una transición de diámetro necesita su tramo explícito |
| tank | tank: diameter, height, roof (flat/conical/domed) y roof_height (cero solo en flat) |
| pump, compressor, generic | Envolvente de nivel 1; no se simula una familia detallada |

La horizontal tiene su virola en X, entre 0 y length; el eje queda a support_height + D/2.
Las silletas se dibujan en sus dos posiciones trazadas, con asiento cóncavo. La columna
arranca en Z=0 y acumula alturas; no se interpolan saltos entre diámetros incompatibles.
El tanque arranca en Z=0 y su altura incluye el techo. Son envolventes geométricas de equipo,
no un modelo de espesores de fabricación. El nivel 1 usa exactamente envelope.origin/size,
incluidos los orígenes negativos; sirve para todas las tipologías.

Las boquillas conservan los cuatro campos históricos. Fuera de la familia vertical radial
requieren también position (Vector3 en mm) y direction (componentes trazadas de unidad 1,
vector no nulo). Se normaliza la dirección al generar geometría; elevation coincide con Z.
En vertical se admiten también estas colocaciones explícitas para boquillas superiores,
inferiores, tangenciales o inclinadas. Una dirección ausente no se adivina.

Nivel 3 requiere al menos un detalle trazado: flange en boquilla (outer_diameter, thickness
más rating), platforms (id, origin, size) o ladders (id, origin, width, height, rail_diameter,
rung_spacing). Una brida representa su envolvente anular según dimensiones aportadas; no
se atribuye conformidad ASME ni se deducen dimensiones de una clase sin tabla autorizada.
Los campos de detalles también bloquean la aprobación. No se aceptan detalles con lod=1/2.

Los soportes implementados son faldón en vertical y silletas en horizontal. Declarar patas,
orejetas u otros soportes de nivel 2/3 falla hasta aportar una familia compatible.
`fields()` recorre todos los parámetros: IDs estables para boquillas/tramos/detalles, índices
0/1 solo para saddle_positions. Se conservan las rutas históricas y los GUID del ejemplo.
El IFC incluye LOD, Family y campos completos en TrazIA_Traceability.


## Identidad de boquillas y comparación

`nozzles[].stable_id` es opcional y administrativo: preserva el GUID si cambia el nombre `id`.
Sin él, se conserva el algoritmo histórico basado en id. Los stable_id efectivos deben ser
únicos. Con previous_id aprobado, el trabajo empareja boquillas y propaga identidades en una
copia DRAFT; no hereda una aprobación. La comparación de consulta no modifica revisiones.
El emparejamiento húngaro de nombres nuevos usa servicio, DN, posición y dirección;
los empates cercanos quedan ambiguos y no reciben identidad automáticamente. Su coste
es heurístico, no una probabilidad de acierto calibrada.

La comparación separa equivalencia física y tolerancia de la huella: ignorar una diferencia
menor de 0,1 mm para el informe no conserva una aprobación si el dato fue modificado.
Tolerancia angular por defecto: 0,01 grados con distancia circular. Los atributos numéricos
usan equivalencia de unidades con Pint; las temperaturas con C se interpretan como degC
solo en campos de temperatura. Las tolerancias se pueden pasar por ruta al comparador.


## Entrada de envolventes LOD 1 (31/10)

El ensamblador acepta candidatos trazados `envelope.origin.{x,y,z}` y
`envelope.size.{x,y,z}` en mm. Las seis componentes y el tag deben estar presentes;
no se rellenan dimensiones ausentes. Se conserva el contrato 0.3 sin renombrar campos.
`attributes.equipment_type="pump"` identifica una bomba; sin esa clasificación la
familia es `generic`, siempre LOD 1.

El lector de bombas reconoce un alzado lateral, una planta y su nota de datum, y lee
las tres cotas exteriores. La esquina inferior local de representación se declara
explícitamente `assumed`: requiere confirmar su alineación con la planta. No se modelan
el motor ni salientes de boquillas que el lector no haya determinado. El IFC contiene
la envolvente declarada; el visor representa ese IFC. Los recipientes de LOD 2/3
conservan sus validaciones, incluido el mínimo de tres boquillas completas.

La lectura alternativa de un tag aislado no utiliza el nombre del archivo ni la verdad
sintética. Solo acepta un identificador único cuando no ha encontrado uno rotulado;
si hay identificadores contradictorios, conserva la falta de datos como error.


## Sistema de referencia interno (C.4, 31/10)

El IFC usa un sistema local dextrógiro, con Z vertical positiva y origen en el centro del equipo
en planta a nivel del suelo local; no implica georreferenciación ni Norte de planta. Las longitudes
del contrato se expresan en mm y se convierten una vez a metros en el IFC.

Para las boquillas radiales del recipiente vertical, azimut 0° apunta a +X y 90° a +Y:
`(x, y, z) = (R cos(a), R sin(a), elevación)`. El giro es antihorario visto desde +Z.
Los elementos con posición/dirección explícitas usan esos vectores trazados. Cambiar este
convenio silenciosamente a Norte/horario desplazaría la geometría existente.

En la web, web-ifc incorpora `(X,Y,Z) → (X,Z,-Y)` en `flatTransformation`; el worker aplica
esa matriz una vez. Se comprobó su base con el IFC sintético, sin render ni inferencia GPU.
`GET /reference-system` declara unidades, ejes y límites. Las pruebas cardinales y de unidades
IFC están en `tests/test_plataforma_pitch.py`.

La orientación del Norte de planta y la equivalencia con el IFC de referencia TR **no están
verificadas**. C.4 permanece parcial hasta disponer de una referencia autorizada. No se ha
abierto `data/private/` ni se atribuye este convenio matemático a VESOR o a TR.
