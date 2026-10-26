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
No se aplica todavía equivalencia entre 1 bar y 100 kPa.

Los JSON sintéticos de la fase 0.1 eran un borrador local sin publicar. La versión 0.2
añade unidades por campo, tag trazable, fondos, faldón y aprobación; no es compatible con
ese contrato anterior. Los ejemplos del repositorio ya usan 0.3.
