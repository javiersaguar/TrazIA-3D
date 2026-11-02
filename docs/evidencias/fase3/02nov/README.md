# 3.7 / H.7 · extracción CPU y escala · 02/11/2026

## Contraste completo contra verdad sintética

Se repiten **336 revisiones por estrategia**, 672 predicciones en total. Corpus público:
S-dev 24 equipos, S-reservado 16, S-mecánico 12 y S-adversarial 12. Los tres primeros tienen
tres degradaciones y dos revisiones; el adversarial tiene una degradación y dos revisiones.
Son 64 equipos y 168 condiciones, no 336 equipos independientes.

La huella de los originales es `da9ea85b70734d8ccdb0d63aef882b1d488667f08e52495a5a9b6c28a951e170`.
La calibración v6 tiene huella semántica
`5496cf49cbe426d15ad807a662ce0aa26cb3454540b2b4b047ce3c8d3f0d66ec`, y la fusión
`a7d09074255ee78af4af3dd1cb7dd8f592e795c5000ebad560cc2a0415486d55`. Fuente y scripts se
congelan antes de ejecutar; no se añaden credenciales, red, proveedores ni dispositivos GPU.

La verdad se consulta después de predecir, nunca para reparar un dato ausente. La rúbrica
abarca tag, dimensiones principales/envolvente y boquillas, con tolerancias de 0,5 mm,
0,5 grados circulares y 1e-6 para direcciones. El tag se compara normalizando mayúsculas y
espacios extremos. Los atributos técnicos de HDM quedan fuera de esta rúbrica. Las boquillas
extra penalizan precisión y los campos ausentes penalizan recall; en la evaluación del pipeline
se conservan los candidatos parciales de las revisiones que no generan un modelo.

El diagnóstico conserva también la confianza original del extractor. Cuando difiere de la
entrada de calibración tras fusionar canales, la evaluación de aprendizaje utiliza la
`Source.confidence_raw` trazada, conservada dentro de cada fuente, y no el `raw` histórico de
la fila de diagnóstico. Las cifras de precisión/recall de valores no dependen de esa confianza.

| Estrategia | DRAFT | Error | Campos devueltos / esperados | Campos correctos | Precisión devueltos | Recall correcto | DRAFT con geometría principal correcta | DRAFT con todos los campos evaluados correctos |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| D aprendido | 251 | 85 | 4.803 / 7.932 | 4.337 | 90,30 % | 54,68 % | 185 | 96 |
| B+OCR | 220 | 116 | 4.032 / 7.932 | 3.714 | 92,11 % | 46,82 % | 138 | 65 |

Estos últimos contadores solo acreditan los campos evaluados de los sintéticos. Un DRAFT
requiere revisión, puede tener campos abstendidos o boquillas sin colocar, y no equivale a un
IFC completo aprobado. La coherencia IFC contra su JSON se audita por separado en
[D.4](../../../ifc-checks/02nov/README.md).

Los 85 errores de D persisten: **63 con campos obligatorios ausentes y 22 con dimensiones
incoherentes**. Están en escaneados: 27 limpios y 58 pobres. B+OCR solo recupera un error de D,
con geometría principal incorrecta, y pierde 32 DRAFT de D. No se activa una cadena de fallback.
El sondeo previo de los 34 fallos de S-dev incluye D sin geometría y D heurístico: tampoco
justifica activar un sustituto. No se ajustan lectores con el resultado de S-reservado.

## Tiempos del contraste

El arnés por particiones tarda **763,06 s** para ambas estrategias. La suma de tiempos de
pipeline es 1.892,08 s para D y 835,51 s para B+OCR. Se utilizan cuatro procesos y la caché de
páginas compartida ya utilizada por el sondeo de desarrollo. Los tiempos de las estrategias
se solapan y no constituyen una comparación causal de latencia ni un benchmark de Redis.
Cero llamadas externas registradas. Las duraciones de las ablaciones de aprendizaje, con
caché caliente, tampoco se atribuyen a una aceleración causada por el feedback.

## Redis real: uno y cuatro workers

Se ejecutan dos despliegues nuevos de API, Redis/arq, Postgres y almacén SHA, con concurrencia
uno por worker, puerto local 8044 y cachés de aplicación nuevas. No coinciden con las pruebas
ni con las ablaciones CPU de esta sesión. El portátil sigue siendo un host compartido; no se
controlan caché del sistema operativo, temperatura ni otros procesos del usuario.

| Workers | Revisiones | IFC DRAFT / error | Tiempo de lote | Turnaround p95 | Caché de trabajo | Llamadas externas |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 336 | 251 / 85 | 1.828,75 s | 254,78 s | 0 / 336 | 0 |
| 4 | 336 | 251 / 85 | 1.242,72 s | 195,68 s | 0 / 336 | 0 |

**1,4716× observado.** Los estados, LOD, errores y todos los valores/unidades de los 251
modelos coinciden revisión por revisión; también coincide su calidad contra GT. Cada trabajo
`done` ha construido y validado su IFC4 DRAFT antes de guardar el resultado. Los DRAFT son
211 LOD 2 y 40 LOD 1. Ambos despliegues y sus volúmenes de prueba se retiran al terminar.

El cliente archiva la respuesta JSON real de cada modelo mediante `--guardar-modelos`, y
`scripts/score_scale_quality.py` evalúa después esos archivos, verificando la huella de los
originales. Las revisiones fallidas cuentan como campos ausentes en esta rúbrica de **salida
exportada**: 4.242 campos devueltos de 7.932 esperados, 3.959 correctos, precisión 93,33 % y
recall 49,91 %. Es un denominador distinto del contraste del pipeline anterior, que conserva
candidatos parciales de errores.

Se detectó y corrigió un error de Plataforma: el contador consultaba
`Equipment.unplaced_nozzles`, cuando el contrato lo guarda en `Revision.unplaced_nozzles`.
La corrección se hace después de terminar ambas pasadas. El informe original queda intacto y
la cifra se reconstruye desde los JSON archivados: **95 DRAFT con boquillas sin colocar**, en
lugar del cero original. Hay 96 DRAFT con todos los campos evaluados correctos, pero **solo 81**
cumplen además que no haya boquillas sin colocar. Esa condición todavía no certifica atributos
HDM, ingeniería real ni aprobación humana. Se añade una prueba del cliente contra una respuesta
de API con el campo en el nivel correcto.

El tiempo acumulado de trabajos es 1.715,59 / 4.824,58 s; los segundos se solapan en paralelo
y no son segundos de CPU consumida. Una [muestra puntual Docker](resource-sample.jsonl) registra
95 hilos y 1,34–1,40 GiB por worker. No es un promedio ni prueba causal de la contención.
[Versiones del entorno ejecutado](runtime-versions.json).

### Proyecto 400 × 4: escenario, no factura

| Hipótesis / resultado | 1 worker | 4 workers |
| --- | ---: | ---: |
| Extrapolación de 1.600 terminaciones, incluidas fallidas | 145,14 min | 98,63 min |
| Cómputo si se supone 0,10 €/worker-h | 0,2419 € | 0,6575 € |
| Gasto de proveedores registrado en este lote | 0 € | 0 € |
| Tiempo/coste total de 1.600 IFC correctos | Sin medir | Sin medir |

Los workers comparten el mismo portátil: no son cuatro máquinas cloud de precio contratado.
Energía, infraestructura fija, almacenamiento, revisión humana y reparación no están medidos.
No se extrapola una tasa de los 81 casos sintéticos para prometer IFC reales correctos.

Reproducción del lote medido:

```powershell
uv run python scripts/run_scale.py --wsl Ubuntu --workers 1 4 --estrategia d_hibrido --image trazia-plataforma:20261102-cpu-v1 --data ../TrazIA-3D/generated/synthetic_v2 --output generated/02nov-scale --api-port 8044 --calibration docs/evidencias/fase3/01nov-triage/calibracion-v6.json --expected-calibration 5496cf49cbe426d15ad807a662ce0aa26cb3454540b2b4b047ce3c8d3f0d66ec --expected-fusion a7d09074255ee78af4af3dd1cb7dd8f592e795c5000ebad560cc2a0415486d55 --eur-worker-hora 0.10 --guardar-modelos
```

La imagen CPU es una instantánea local identificada por digest en los informes, con fuente y
pesos congelados; no es una referencia a una imagen publicada. El cliente actual ya incluye la
corrección del contador, por lo que una nueva ejecución mostrará la cifra correcta directamente.

- [Comparación exacta, presupuesto y corrección de observaciones](comparacion-redis.json).
- [Pasada original de un worker](d-workers-1.json) / [cuatro workers](d-workers-4.json).
- [Calidad de los modelos exportados: un worker](calidad-exportada-workers-1.json) /
  [cuatro workers](calidad-exportada-workers-4.json).

## Artefactos y reproducción

- [Resumen por estrategia y conjunto](comparacion-cpu.json).
- [672 predicciones: estados y calidad por revisión](calidad-por-revision.json).
- [85 errores de D: valores, evidencias y verdad consultada después](fallos-d-85.json).
- [Sondeo de desarrollo, identificado por separado](sondeo-s-dev.json).
- [Entrega concreta a Lectura](../../../agentes/ENTREGA_LECTURA_02NOV.md).
- [Ablación sintética de aprendizaje](../02nov-aprendizaje/README.md).

El entorno CPU utilizado contiene los extras OCR existentes y sus pesos empaquetados; no se
descargan pesos durante el experimento. `scripts/measure_cpu_quality.py` ejecuta
`scripts/triage_scale.py` por conjunto, verificando los originales y registrando fuente,
parámetros, proveedor y SHA de verdad. Para reproducir, suministrar `--report` con el inventario
de 336 revisiones, `--data` con el corpus sintético y `--output` con un directorio vacío; elegir
`--strategies d_hibrido b_reglas+ocr --scope all --workers 4`. Montar fuente/scripts congelados
y calibración v6 en lectura, fijar `CUDA_VISIBLE_DEVICES=-1` y bloquear la red.

El coste de generar **1.600 IFC correctos de ingeniería** sigue desconocido. La extrapolación
de terminaciones del lote debe incluir los errores y declarar cualquier tarifa como hipótesis;
no se transforma la tasa de DRAFT en precisión medida de un proyecto real.
