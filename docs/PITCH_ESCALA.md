# Escala de TrazIA-3D · material para el pitch (02/11)

## Afirmación defendible

Un lote de **336 revisiones sintéticas** con D aprendido/v6 y sin proveedores de visión produjo **251 IFC DRAFT y 85 errores**. Cuatro workers terminaron en **1.242,72 s**, frente a **1.828,75 s** con uno: **1,4716× observado** en el mismo portátil compartido. Estados, valores/unidades y calidad coinciden por revisión. Los DRAFT son 211 LOD 2 y 40 envolventes LOD 1.

El contraste con la verdad sintética encuentra 185 DRAFT con geometría principal correcta y 96 con todos los campos evaluados correctos. **95 DRAFT tienen boquillas sin colocar; solo 81 cumplen además todos los campos evaluados correctos y ninguna boquilla pendiente.** El contador se ha corregido para leer el nivel correcto del contrato; las cifras se reconstruyen desde los modelos archivados. Estas condiciones no acreditan atributos HDM, aprobación ni ingeniería real.

[Resultados, calidad y reproducción del 02/11](evidencias/fase3/02nov/README.md). La medición previa del 01/11 fue 1,8647× con v5 y carecía de este contraste de calidad: se conserva como [histórico](evidencias/fase3/01nov/resumen.md). No se atribuyen diferencias de tiempo causalmente a una sola mejora.

## Arquitectura para la diapositiva

[SVG vectorial](evidencias/fase3/01nov/arquitectura-escala.svg) / [PNG](evidencias/fase3/01nov/arquitectura-escala.png).

```mermaid
flowchart LR
    D["PDF / HDM sintéticos<br/>SHA-256"] --> A["API<br/>idempotencia + SSE + ETag"]
    A --> C{"Caché de trabajo<br/>documentos + parámetros<br/>calibración + fusión + feedback"}
    C -->|acierto| M["Contrato 0.3 + IFC DRAFT<br/>errores y ausencias conservados"]
    C -->|fallo online| Q["Redis / arq"]
    C -->|fallo offline| E["Error explícito"]
    Q --> W["Workers CPU<br/>concurrencia 1"]
    W --> PC["Etapas por página<br/>texto / raster / OCR / geometría"]
    PC --> M
    M --> R["Revisión humana<br/>E.5 pospuesta"]
    R --> P["Aprobación vigente<br/>originales verificables"]
    R --> L["Auditoría SQL + JSONL"]
    P --> X["Sesión humana finalizada<br/>equipo y documentos destino excluidos"]
    X --> O["≤3 ejemplos en extracción<br/>prioridad acotada con mínimos"]
    O --> W
    L --> K["Propuesta de recalibración CPU<br/>sin activación automática"]
```

## Reutilización por página, medida

[Secuencia real en CPU y sin red](evidencias/fase3/01nov/incremental-etapas.json): A fría, B con solo página 2 cambiada, B repetida y control B frío. Render, extracción de texto, OCR y análisis geométrico vectorial/raster procesaron **2 / 1 / 0 / 2 páginas**. B caliente: 0,86 s; B fría: 3,25 s. Una secuencia, no ahorro generalizable. Se lee la estructura PDF para las huellas; reconciliación global e IFC siguen completos.

## Proyecto 400 equipos × 4 revisiones: escenario

| Componente | Resultado | Naturaleza |
| --- | ---: | --- |
| 1.600 terminaciones con cuatro workers | 98,63 min | Extrapolación, incluye fallos |
| 1.600 terminaciones con un worker | 145,14 min | Extrapolación, incluye fallos |
| Cómputo con cuatro workers | 0,6575 € | Hipótesis 0,10 €/worker-h |
| Cómputo con un worker | 0,2419 € | Misma hipótesis |
| Proveedores en las 336 revisiones | 0 € / 0 llamadas | Registrado en este lote |
| Revisión humana / infraestructura fija | Sin medir | E.5 pospuesta |
| Total / coste de 1.600 IFC correctos | Sin medir | No se deduce de este lote |

No es una tarifa contratada ni gasto cloud medido. El modelo permite cambiar las hipótesis y mantiene null si falta un componente. [Escenario JSON](evidencias/fase3/02nov/comparacion-redis.json):

```powershell
uv run python scripts/scale_pitch.py --entrada docs/evidencias/fase3/02nov/d-workers-4.json --salida generated/pitch-400x4.json --pendientes generated/revisiones-pendientes.jsonl --eur-worker-hora 0.10 --exigir-todos
```

Escribe las evidencias y sale con código 2 porque faltan DRAFT. Ese control no certifica precisión de ingeniería.

## Qué falta para cerrar 3.7 / H.7

[85 revisiones pendientes, reproducidas el 02/11](evidencias/fase3/02nov/fallos-d-85.json): **63 con campos ausentes y 22 con incoherencia geométrica**. No se han rellenado cifras para forzar modelos. Cada fila conserva dataset, tag, degradación, revisión, error y huella del conjunto; puede reproducirse con --tags y --degradaciones en measure_scale.py/run_scale.py contra una API propia. S-reservado no debe usarse para ajustar el lector.

Además faltan validación de precisión de ingeniería y datos humanos para presupuestar revisión. La ampliación de extracción desde correcciones ya está conectada, con condiciones conservadoras, pero no tiene aún muestra humana ni mejora validada: [límites](APRENDIZAJE_APROBADO.md). No se cuenta una exportación adversarial como resolución correcta de su conflicto.
