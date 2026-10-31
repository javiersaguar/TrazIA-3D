# D aprendido + calibración v5 · medición CPU del 31/10

336 revisiones sintéticas, 64 equipos y 168 condiciones equipo/degradación. Corpus SHA
`da9ea85b70734d8ccdb0d63aef882b1d488667f08e52495a5a9b6c28a951e170`, idéntico al histórico.
[Protocolo y reproducción](protocolo.md).

| Medida | 1 worker | 4 workers |
| --- | ---: | ---: |
| Revisiones terminales | 336 | 336 |
| DRAFT generados | 174 | 174 |
| LOD 2 / LOD 1 | 134 / 40 | 134 / 40 |
| Errores | 162 | 162 |
| Timeout / cancelaciones | 0 / 0 | 0 / 0 |
| Tiempo de lote, incluida subida (s) | 1.434,2816 | 877,6943 |
| Tiempo de subida (s) | 6,7607 | 6,5851 |
| Llamadas externas / coste declarado | 0 / 0 EUR | 0 / 0 EUR |
| Aciertos caché de trabajos / observados | 0 / 336 | 0 / 336 |

**Aceleración observada: 1,6341×.** Estados, LOD y mensajes de error coinciden revisión a
revisión entre 1/4 workers. Ambos despliegues son nuevos, sin resultados heredados. Es una
medición de host compartido, sin repetición aislada ni intervalo de incertidumbre.
El coste declarado es solo de proveedores: no mide electricidad, amortización ni trabajo humano.

[Un worker](d-workers-1.json), [cuatro workers](d-workers-4.json),
[comparación y tiempos por equipo](comparacion.json), [tabla por equipo](por-equipo.csv).
Los tiempos de pipeline, ejecutor y espera observada se conservan separados. La suma de
latencias por equipo no equivale a tiempo de pared debido a esperas concurrentes.

## Errores y comparación histórica

| Entrada | done | error |
| --- | ---: | ---: |
| Vectorial | 126 | 2 |
| Escaneado limpio | 43 | 61 |
| Escaneado pobre | 5 | 99 |

84 errores de boquillas incompletas, 63 de campos ausentes y 15 de incoherencia geométrica.
[Inventario de los 162 casos](revisiones-pendientes.jsonl). Los dos fallos vectoriales siguen
siendo D-712/1 y D-712/2 en S-reservado. No se ajusta el lector con esos casos.

Frente al D heurístico anterior (173/163), se mantienen 173 éxitos y 162 fallos; C-201,
S-dev/escaneado_limpio/1, pasa de error de posición de N1 a DRAFT LOD 2. D-220, misma
degradación/revisión, continúa con error, ahora referido a N2 en lugar de N1. Son las únicas
dos filas con cambio de estado/LOD/mensaje. También cambiaron código y calibración:
**no se atribuye causalidad aislada a la fusión ni se mide precisión contra el plano**.

## Incrementalidad comprobada

OCR real RapidOCR/ONNX en CPU, contenedor sin red y dos páginas sintéticas. La primera
página es idéntica entre A/B; solo cambia la segunda. [Registro completo](incremental.json).

| Fase | Llamadas al reconocedor | Tiempo OCR con render/caché (s) |
| --- | ---: | ---: |
| A en frío | 2 | 2,4175 |
| B con una página cambiada | 1 | 0,6758 |
| B repetida | 0 | 0,2477 |
| B en frío, control separado | 2 | 1,6364 |

Carga inicial del modelo: 0,7777 s, separada. Diferencia B/control: 0,9606 s en esta única
secuencia. Confirma reutilización de inferencia OCR por página. **El render aún recorre todas
las páginas, y ingestión/fusión no son enteramente incrementales**. No extrapolar ese ahorro
al lote ni marcar el requisito de extremo a extremo como resuelto.

## Contención y escenario de proyecto

[Traza de mayor precisión](host-precision.jsonl), [traza inicial redondeada](host.jsonl) y
[límites de observación](contencion.json). En 14 de las 68 muestras de mayor precisión se
detectó la CLI de comparación de Lectura; la última fue a las 16:30:11 UTC. No detectar ese
PID en las siguientes no acredita ausencia de otras tareas, cargas WSL o GPU. No se realizó
una repetición con host aislado. No se ejecutan inferencias GPU ni se usan claves de API.

Extrapolar la tasa de cuatro workers a 400 × 4 da **69,66 min para 1.600 terminaciones**,
incluidos errores; con uno, 113,83 min. No es tiempo para 1.600 IFC válidos. A la tarifa
**supuesta** de 0,25 EUR/worker-h, solo cómputo de terminaciones sería 1,1610 EUR; proveedores,
0 EUR. Revisión humana, infraestructura fija y total del proyecto siguen sin medir (`null`).
[Escenario paramétrico](pitch-400x4.json). `scale_pitch.py --exigir-todos` escribe el informe
y devuelve código 2, como corresponde a una cobertura incompleta. El diagrama reutilizable
está en [PITCH_ESCALA.md](../../../PITCH_ESCALA.md).

3.7/H.7 permanecen abiertas: no hay cobertura para todos los DRAFT, presupuesto de modelos
válidos ni pipeline incremental por página de extremo a extremo. No se usan datos privados.
