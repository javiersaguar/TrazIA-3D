# Piloto de revisión manual · preparado, sin muestra recogida todavía

La primera sesión usa V-101 de la demo y documentos **sintéticos**. Una persona debe hacer la
revisión. Su uso real de la interfaz no convierte esos planos en documentación real de TR.
Un equipo y sus revisiones permiten comprobar el recorrido; no constituyen una muestra
representativa de 400 equipos.

El almacén `generated/piloto-manual-31/` contiene A/B generadas por la estrategia B en CPU:
22 y 26 campos, todos con score bruto y procedencia de la estrategia. No se ha aceptado,
corregido ni aprobado ningún campo al prepararlo. La demo legada conserva su almacén anterior.
Reproducir con un destino nuevo: `uv run python scripts/prepare_review_pilot.py --salida generated/piloto-nuevo`.

## Recorrido

1. Abre `http://localhost:3120/revision` con la API conectada en el puerto 8022. Selecciona rev A.
   La API del piloto está en modo offline: edición y aprobación funcionan; el Copiloto sin
   respuesta cacheada no inicia una inferencia nueva.
2. En «Sesión manual», escribe tu nombre y pulsa «Iniciar sesión manual».
3. Contrasta los campos con el PDF y el IFC. La cola antepone conflictos y abstenciones y después
   ordena por impacto × (1 − confianza). El impacto es una regla declarada, no una medición.
4. Acepta lo que coincida; corrige un valor con su nota y evidencia si hace falta; marca supuestos
   o rechaza lecturas que no puedas confirmar. Rechazar conserva el candidato y bloquea aprobar.
   No hagas una corrección innecesaria para producir un ejemplo de aprendizaje.
5. «Deshacer» o Ctrl+Z restaura el campo completo. Si otra persona lo cambió después, se pide
   recargar en vez de sobrescribir su edición. Un fallo no añade una acción al historial local.
6. Cuando todos los campos estén aceptados o corregidos, puedes aprobar con tu nombre. La firma
   queda vinculada a la huella de datos y documentos; una edición posterior la invalida.
7. Pulsa «Finalizar sesión» **antes de recargar o salir**. Inicia otra sesión para rev B.

El reloj usa tiempo monotónico del navegador: pausa cuando la pestaña/ventana pierde atención,
durante el guardado y a partir de 60 segundos sin interacción. Scroll, teclado y clic reactivan
la actividad. Es tiempo activo declarado por el cliente, no una medición de atención cognitiva.
El servidor comprueba que cabe en la duración de la sesión y no duplica los tiempos al repetir
una escritura idempotente. Las sesiones sin acciones no aportan un tiempo de revisión.

Si cierras una sesión a mitad, su tiempo sigue siendo parcial aunque se haya guardado. Una sesión
abierta no se cuenta como terminada. Tras recargar no se reanuda automáticamente un reloj perdido.

## Consultar la muestra

```powershell
Invoke-RestMethod http://127.0.0.1:8022/revisions/A/review-metrics
Invoke-RestMethod 'http://127.0.0.1:8022/equipment/V-101/review-metrics?project_id=DEMO-PLANT'
Invoke-RestMethod http://127.0.0.1:8022/revisions/A/audit
Invoke-RestMethod http://127.0.0.1:8022/correcciones
Invoke-RestMethod 'http://127.0.0.1:8022/learning/few-shot?path=diameter'
```

Antes de una revisión humana, `active_seconds` es `null`, no cero. Las métricas distinguen
sesiones `human` declaradas y `test`, sesiones abiertas, sesiones con acciones, dataset, campos
pendientes y aprobación. Las pruebas de navegador se registran como `test`. Esa identificación
ayuda a separar ensayos; no autentica a una persona.

Solo las correcciones que siguen vigentes en una revisión aprobada se ofrecen como pares
few-shot. Incluyen huella de aprobación, documento y URL del recorte de evidencia. Una
revocación los retira. `target_revision_id` excluye el mismo equipo, sus revisiones y documentos.
El contenido documental se trata como datos, no como instrucciones. El Copiloto los recibe
como ejemplos de revisión; no son citas ni pruebas de los valores del equipo consultado.

La API no activa una recalibración ni cambia los extractores al producir ejemplos. El consumo
de pares en los prompts de extracción y el ajuste de prioridad de fuentes se coordinan con
Lectura y requieren su evaluación. La propuesta de recalibración CPU existente se ejecuta
contra el JSONL y la misma base SQL; no se activa por haber finalizado una sesión.

## Para una muestra representativa posterior

Definir participantes, familias y degradaciones antes de recoger datos; registrar revisiones
parciales y abandonadas; separar entrenamiento y evaluación por equipo; informar cuántos
equipos completaron la aprobación y la distribución de tiempos. No extrapolar el tiempo de
unos clics al de revisar un equipo completo. La web de demo ofrece inicialmente V-101 A/B;
la API registra métricas por identidad de revisión y agrupa por proyecto/equipo/dataset.

No se han usado datos de `data/private/`. No hay correcciones humanas nuevas ni mejora
representativa medida mientras esta sesión permanezca preparada sin ejecutar por una persona.
