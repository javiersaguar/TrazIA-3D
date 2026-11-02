# OCR, escala y aprendizaje · 02/11/2026, noche

Datos exclusivamente sintéticos. Cero llamadas a proveedores, GPU deshabilitada y ninguna
sesión humana creada. E.5 sigue pospuesta. El contrato 0.3 y los validadores IFC no se relajan.

## Cobertura y precisión

Mismo corpus de 336 revisiones, semilla y originales del registro anterior. Calibración v6
5496cf49cbe426d15ad807a662ce0aa26cb3454540b2b4b047ce3c8d3f0d66ec y fusión empaquetada
sin reajustar pesos. La GT se consulta después de obtener las predicciones.

| Lectura CPU | DRAFT | Errores | Precisión de campos devueltos | Recall correcto |
| --- | ---: | ---: | ---: | ---: |
| Base del 02/11 | 251 | 85 | 90,30 % | 54,68 % |
| Resolución 2048, descartada | 248 | 88 | 87,85 % | 55,23 % |
| Cabeceras y columnas, tamaño original | 252 | 84 | 90,44 % | 54,95 % |
| Suplemento de cotas giradas | 260 | 76 | 90,69 % | 55,53 % |
| Mosaico condicionado, versión evaluada | 267 | 69 | 91,04 % | 55,31 % |

Se conservan los **251 DRAFT anteriores**, los **96 casos con todos los campos evaluados
correctos** y los **185 con geometría principal correcta**. Se recuperan 16 errores sin transición
inversa a error. La geometría principal correcta alcanza 194 (+9). Los 16 DRAFT recuperados no
son 16 modelos de ingeniería completamente correctos: el total de casos con todos los campos
correctos sigue en 96 y la rúbrica no incluye atributos HDM. Los errores y boquillas ausentes
permanecen en el denominador de calidad.

El mosaico busca dimensiones únicamente cuando faltan o son incoherentes. Solo adopta una
lectura completa y compatible con las cotas previas de alta confianza; no cambia tablas ni
atributos anteriores. El giro y los recortes devuelven sus cajas al sistema original del PDF.
Las pruebas verifican esta transformación y la reutilización de caché entre revisiones.

Quedan **53 errores por campos ausentes y 16 por incoherencia geométrica**. La lista incluye
bombas cuyo mensaje genérico menciona dimensiones de recipiente: no se interpreta ese mensaje
como identificación válida de familia. No se promete que 1.600 IFC de ingeniería queden correctos.

Los tiempos de las cuatro exploraciones no son una comparación de rendimiento: cambian el
estado de las cachés y la carga de pruebas concurrentes. Para rendimiento se usa el ensayo
separado Redis/Postgres/API/workers descrito abajo.

## Escala con Redis, Postgres, API y workers

Despliegue `docker compose` del perfil escala (Redis/arq, Postgres con almacén por SHA-256,
API y workers con concurrencia 1), imagen `sha256:7a76b476…`, CPU sin GPU, providers=[] y sin
credenciales externas en los contenedores. Mismo corpus de 336 revisiones (SHA
`da9ea85b…`), calibración v6 `5496cf49…` y fusión `a7d09074…`. Cada despliegue es nuevo, sin
resultados heredados (0/336 aciertos de caché de trabajos).

| Medida | 1 worker | 4 workers |
| --- | ---: | ---: |
| Revisiones terminales | 336 | 336 |
| DRAFT (LOD 2 / LOD 1) | 267 (221 / 46) | 267 (221 / 46) |
| Errores | 69 | 69 |
| DRAFT con boquillas sin colocar | 101 | 101 |
| Tiempo de lote, incluida subida (s) | 2.786,33 | 906,94 |
| Subida (s) | 6,34 | 4,99 |
| Revisiones terminadas por segundo | 0,121 | 0,370 |
| Espera media / p95 por revisión (s) | 260,3 / 390,3 | 84,5 / 128,4 |
| Pipeline medio por revisión (s) | 7,93 | 10,39 |
| Llamadas externas / coste de proveedores | 0 / 0 EUR | 0 / 0 EUR |

**Aceleración observada: 3,07×** con cuatro workers. Estados, LOD y mensajes de error coinciden
en las 336 revisiones entre ambos despliegues. El pipeline por revisión sube de 7,9 a 10,4 s con
cuatro workers porque compiten por la misma CPU; la ganancia viene de solapar exportación,
validación IFC y espera de cola. Es una sola medición en un portátil compartido, sin repetición
ni intervalo de incertidumbre. Frente al 01/11 (1,86×) cambian el lector OCR y la carga del
host, así que no se atribuye la diferencia a una sola causa.

Por estado de entrada: vectorial 128/0, escaneado limpio 86/18 y escaneado pobre 53/51
(DRAFT/error).

**Proyección, no medida:** 1.600 trabajos terminales con 4 workers tardarían unas 1 h 12 min
(4.318,8 s) a este ritmo. Son terminaciones, no 1.600 IFC válidos: con la tasa actual, una
quinta parte acabaría en error. Escenario de cómputo con 0,10 EUR por worker-hora: 0,48 EUR;
excluye energía, almacenamiento y el coste de revisar y corregir.

Artefactos: [un worker](d-workers-1.json), [cuatro workers](d-workers-4.json),
[despliegues comparados](comparacion-escala.json) y [tabla por equipo](por-equipo.csv) con
tiempos de pipeline y de espera, coste y estados de cada uno de los 64 equipos.

## Recalibración posterior a fusión

Una curva global de D, nunca por canal, ajustada con una partición de S-dev. Curva, conformal
y validación interna usan grupos disjuntos; los originales compartidos agrupan alias transitivos.
Las etiquetas se simulan a partir de la verdad sintética tras extraer; no se escriben en el
almacén de producción ni equivalen a aprobación humana. S-reservado se usa como prueba de
regresión conocida, no como muestra real ni prueba ciega nueva de generalización.

La propuesta mejora ECE interna **0,0160 → 0,0136** (917 campos de validación). En el conjunto
reservado mejora **0,0943 → 0,0753**, con cobertura de intervalos informativos
**98,83 % → 98,79 %**. La cobertura de campos tras abstención pasa de **71,13 % a 69,31 %**;
el riesgo entre retenidos es **0,43 % → 0,44 %**. El objetivo ECE < 0,05 no se alcanza.
La recalibración no cambia valores extraídos. Propuesta sintética archivada, **sin activar**.

La CLI de producción exige por defecto auditoría, aprobación y sesión humana finalizada.
`--simulacion-sintetica` marca ensayos aislados. Las prioridades quedan en `candidate_priorities`,
con `requires_independent_validation`, y no se aplican por registrar más correcciones.
Los pocos ejemplos aprobados siguen excluyendo equipo/documentos destino; su eficacia con un
lector de visión no se ha medido aquí. 3.8/E.6 siguen abiertas para la muestra humana representativa.

## Verificación

424 pruebas correctas con OCR instalado, sin omitir el caso real que fallaba al empezar;
dos avisos previos de Starlette y del caso negativo de corrupción geométrica. Ruff check y
formato correctos. Se corrige una prueba de corrupción de caché que escogía un archivo por
orden de directorio: ahora corrompe ambas entradas y exige reconstruir ambos OCR sin rerender.

## Reproducción

`measure_cpu_quality.py` sobre los cuatro conjuntos, `d_hibrido`, providers=[], CUDA_VISIBLE_DEVICES=-1,
con la calibración anterior explícita. `evaluate_recalibration.py --measurements <d_hibrido>
--data <synthetic_v2> --base <v6> --output <dir>` evalúa la propuesta sin activarla.
Los originales conservan su SHA y los resultados completos están en generated del worktree;
se archivan resúmenes, hashes, casos, errores y recuperaciones en esta carpeta.

Artefactos: comparacion-calidad.json, casos.json, pendientes-69.json, recuperadas-16.json,
evaluation.json, propuesta-d-no-activada.json y verificacion/pytest-424.txt.
