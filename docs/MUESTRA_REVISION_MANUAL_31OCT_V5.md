# Sesión manual E.5 · V-101 sintético · 31/10

Kit para una persona del equipo. No es una prueba automatizada ni una revisión con la verdad
sintética. No consultar YAML de verdad ni aprobar por defecto: contrastar los originales en
la web. La preparación genera candidatos B/CPU; no acepta ni aprueba campos.

## Muestra y alcance

Un equipo, V-101, revisiones A y B: 22 y 26 campos respectivamente. Documentos GAD y HDM
sintéticos de la demo pública. La geometría del visor procede del IFC; no representa un
equipo industrial validado. Una persona y un equipo permiten comprobar el recorrido y medir
su tiempo de uso; no demuestran representatividad para 400 equipos ni ahorro causal.

Originales servidos desde el almacén del piloto: [GAD A](http://127.0.0.1:8030/revisions/A/documents/GA-V101),
[HDM A](http://127.0.0.1:8030/revisions/A/documents/HDM-V101),
[GAD B](http://127.0.0.1:8030/revisions/B/documents/GA-V101) y
[HDM B](http://127.0.0.1:8030/revisions/B/documents/HDM-V101).
Al descargar las HDM, guardarlas con extensión `.xlsx`. La cola muestra hoja/celda de su
procedencia; no confundir los valores de la HDM con las cajas del PDF GAD.

La API del piloto usa un almacén nuevo, `generated/piloto-manual-v5-31oct/`, separado de la
medición de escala y de las demos anteriores. Está en modo offline para impedir inferencias
nuevas. El Copiloto sin respuesta cacheada explicará su indisponibilidad. Edición, deshacer,
auditoría y aprobación conservan su funcionamiento.

## Guion para Javier

1. Abre [Revisión del piloto](http://127.0.0.1:3130/revision) en tu Chrome/Edge habitual,
   sin un navegador de pruebas automatizadas. Confirma la etiqueta de datos
   sintéticos y selecciona revisión A. Deja el navegador en primer plano.
2. En «Sesión manual», escribe tu nombre y pulsa «Iniciar sesión manual».
3. Selecciona un campo pendiente y contrástalo con su documento y elemento IFC. Acepta si
   coincide; corrige con nota/evidencia si hace falta. Puedes marcar un supuesto o rechazar
   una lectura que no logres confirmar. Rechazar deja pendiente la revisión; no inventes datos
   ni hagas correcciones innecesarias para completar la muestra.
4. Para interpretar el tiempo por campo, registra su acción antes de pasar al siguiente.
   El reloj atribuye el tiempo activo desde la acción anterior a la acción que guardas; no
   rastrea qué campo estabas mirando. Si saltas entre campos, anótalo al comunicar el resultado.
5. Si te equivocas, «Deshacer» o Ctrl+Z conserva una acción auditable. Su tiempo es trabajo
   de revisión; no se cuenta como un segundo campo distinto.
6. Cuando todos los campos estén aceptados/corregidos y las validaciones lo permitan, pulsa
   «Aprobar revisión» e indica tu nombre. Si no puedes aprobar, conserva los pendientes: el
   resultado será una muestra parcial, no una revisión completa.
7. Pulsa «Finalizar sesión» y espera «Sesión guardada: … s activos» **antes de cambiar de
   revisión, recargar o cerrar**. Si falla el guardado, reintenta sin salir.
8. Repite desde el paso 2 para revisión B. Al terminar ambas, avisa en el chat. Indica si hubo
   interrupciones, saltos entre campos o información insuficiente; no hace falta copiar los
   tiempos, se extraerán del registro.

Si acabas solo una parte, finaliza y avisa igualmente. No se tratará como un equipo completo.
Una sesión abierta o sin acciones no aporta un tiempo medido al resumen.

## Qué se cronometra

Tiempo activo monotónico comunicado por el navegador, por sesión y acción. Pausa al perder
foco/visibilidad, durante el guardado y tras 60 s sin interacción. Los clics, teclas y scroll
reactivan la actividad. Leer sin interactuar más de 60 s deja de contar; declarar esta
limitación al interpretar el resultado. No es una medición de atención cognitiva.
Consultar la HDM en Excel o en otra pestaña también pausa el tiempo activo de la web.
Por eso se exporta además la duración total entre inicio y fin según el reloj del servidor,
**incluidas interrupciones**. Ninguna de esas dos cifras se etiqueta como tiempo neto de
revisión completa sin contrastar cómo se hizo la sesión.

Se conservan identidad de revisión/equipo, actor, acciones, deshacer, tiempos, estados y
aprobación. El servidor limita los tiempos a la duración real de la sesión y valida la
concurrencia con ETag/If-Match. Una edición posterior invalida la aprobación. Las sesiones
automatizadas son `test`; las humanas son autodeclaradas, no autenticadas.

El tiempo por equipo sumará A/B y se indicará cuántas revisiones tienen muestra. Por campo
se suman acciones y deshacer, sin duplicar el campo. El tiempo activo sin acción atribuida
se presenta aparte. Ausencia de medición es `null`, nunca cero.

## Exportación después de la sesión

Desde el worktree Plataforma, con la API del piloto en marcha:

```powershell
uv run python scripts/export_review_session.py --api http://127.0.0.1:8030 --revisiones A B --salida generated/sesion-manual-v5-exportacion
```

Usar un destino nuevo: no sobrescribe una exportación existente. Es una consulta de solo
lectura: no acepta campos, no finaliza sesiones y no fabrica tiempos. Devuelve código 2
si no hay sesiones humanas finalizadas con acciones.

Produce `registro-original.json` (métricas, campos y auditoría), `tiempos.json` (equipo,
revisión y campo) y `tiempos.md`. Solo admite revisiones sintéticas. Excluye sesiones `test`,
abiertas y sin acciones de campo. Conserva acciones sin tiempo como desconocidas. La marca
`sample_complete_for_review_time` exige A/B aprobadas, sin pendientes, con muestra humana
y acciones cronometradas en todos sus campos. No declara impacto causal ni representatividad.

Antes de publicar cifras, contrastar el registro con la confirmación de la persona, declarar
número de participantes/equipos/revisiones, tiempos parciales y límites. No extrapolar dos
revisiones de un equipo a una revisión industrial de cuatro revisiones por equipo.

## Reproducir la preparación

```powershell
uv run --extra api python scripts/prepare_review_pilot.py --salida generated/piloto-manual-nuevo
```

El directorio tiene que ser nuevo y estar bajo `generated/`. No ejecutar ensayos que escriban
sobre el almacén reservado a Javier. No se usan datos privados ni proveedores de visión.

Para servir ese nuevo almacén, desde la raíz del worktree en una terminal propia:

```powershell
$env:TRAZIA_ROOT=(Get-Location).Path
$env:TRAZIA_DATA=(Resolve-Path generated/piloto-manual-nuevo).Path
$env:TRAZIA_DATABASE_URL=''
$env:TRAZIA_QUEUE='process'
$env:TRAZIA_OFFLINE='1'
$env:TRAZIA_CORRECTIONS_FILE=Join-Path $env:TRAZIA_DATA 'generated/correcciones/correcciones.jsonl'
$env:TRAZIA_CORS_ORIGINS='http://127.0.0.1:3130,http://localhost:3130'
uv run --extra api uvicorn trazia.api:create_app --factory --host 127.0.0.1 --port 8030
```

En otra terminal, desde `web/` del mismo worktree:

```powershell
$env:NEXT_PUBLIC_API_URL='http://127.0.0.1:8030'
$env:NEXT_TELEMETRY_DISABLED='1'
corepack pnpm@10.18.0 build
corepack pnpm@10.18.0 exec next start --hostname 127.0.0.1 --port 3130
```

Los puertos deben estar libres; no detener servicios ajenos para reutilizarlos. El kit en
ejecución usa `piloto-manual-v5-31oct`; el nombre `piloto-manual-nuevo` es solo para reproducir
en un almacén distinto, preservando cualquier sesión anterior.

Estado al entregar: API del piloto disponible en 8030, web compilada con esa URL. El arranque
automático del frontend en 3130 fue rechazado por revisión de aprobación (`blocked by policy`).
No se ha verificado la pantalla en esta entrega ni se ha creado una sesión humana. Para usar
el kit, iniciar la web compilada desde su carpeta `web/` con el comando `next start` de arriba;
la API existente no necesita reiniciarse. La comprobación de exportación sin muestra conserva
tiempos `null` y devuelve código 2.
