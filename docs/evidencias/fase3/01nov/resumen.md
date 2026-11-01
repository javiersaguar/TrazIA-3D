# Escala CPU, unidades y páginas incrementales · 01/11

El mismo lote sintético produce **251 IFC DRAFT y 85 errores** con uno y cuatro workers. Son **211 LOD 2 y 40 envolventes LOD 1**, sin DRAFT con boquillas marcadas como no ubicadas. No es validación de precisión de ingeniería.

| Medida | 1 worker | 4 workers |
| --- | ---: | ---: |
| Revisiones terminales | 336 | 336 |
| DRAFT / errores | 251 / 85 | 251 / 85 |
| Tiempo del lote | 1.714,18 s | 919,26 s |
| Aceleración observada | 1 | 1,8647× |
| Aciertos de caché de trabajo | 0 / 336 | 0 / 336 |
| Llamadas externas / coste de proveedores registrado | 0 / 0 € | 0 / 0 € |

[Comparación por revisión](comparacion.json): las 336 coinciden en estado, LOD y error entre uno y cuatro workers. Frente al 31/10, mismo conjunto SHA: 174 siguen exportando, 77 pasan de error a DRAFT y 85 siguen en error; no hay transición DRAFT→error. Esto no aísla efecto causal: cambiaron lectores, unidades y cachés. Tampoco mide si una cifra extraída coincide con el plano.

64 equipos, 168 condiciones documentales y dos revisiones por condición; total 336. S-dev 144: 110 DRAFT/34 errores; S-reservado 96: 77/19; S-mecánico 72: 40/32 (envolventes LOD 1); S-adversarial 24: 24/0. Que una entrada adversarial exporte un DRAFT no demuestra que se resuelva correctamente su conflicto: no es una medida de robustez adversarial.

## Pendientes concretos

[Inventario para Lectura](pendientes-lectura.jsonl): 63 errores de campos ausentes y 22 de incoherencia geométrica (20 fondo inferior respecto del suelo, dos profundidad de fondo). No se rellenaron datos para forzar exportaciones. S-reservado no debe usarse para ajustar el lector. Se mantiene separado el presupuesto de IFC correctos de las terminaciones técnicas.

## Escenario 400 × 4

[Calculador ejecutado](presupuesto.json): **4.377,44 s / 72,96 minutos** con cuatro workers para 1.600 terminaciones, incluidas fallidas. Con un worker: 8.162,74 s / 136,05 minutos. Son extrapolaciones de este portátil compartido, no otra medición ni capacidad industrial garantizada.

A **0,10 €/worker-h supuesto**, cómputo de cuatro workers: **0,4864 €**; uno: 0,2267 €. No es una tarifa contratada ni gasto medido. Proveedores registrados en el lote: 0 €. Revisión humana, infraestructura fija y coste/tiempo de 1.600 IFC correctos siguen null; no hay presupuesto total del proyecto. E.5 está pospuesta por Javier.

## Incremental por página

[Prueba real CPU/sin red](incremental-etapas.json): A fría, B con solo segunda página cambiada, B repetida y control B frío. Render, texto, OCR y geometría vectorial/raster: **2/1/0/2 páginas**; reconocimiento real RapidOCR. B caliente: 0,86 s; control B frío: 3,25 s. Inicialización de motor separada en el JSON. Una secuencia: no es un porcentaje generalizable ni edición incremental del IFC. Reconciliación global y generación IFC siguen completas.

Una primera ejecución del lote fue interrumpida al detectar escalares NumPy no serializables en caché; se corrigió, se añadieron pruebas de geometría positiva/disco no escribible y se repitió desde volúmenes nuevos. No se mezclan sus cifras con las anteriores.

## Reproducción y pruebas

[Protocolo](protocolo.md), [imagen/commit/huellas](procedencia.json), [parámetros de calibración](calibracion-v5.json), [filas CSV](revisiones.csv), [carga observada agregada](host.jsonl), [verificación](verificacion.json). Los registros detallados de aplicaciones del host permanecen locales.

Ruff y formato verdes; Python 348 pasadas/una omitida en 266,67 s; web typecheck/lint/build, 42 unitarias; E2E API 33/una omitida, sin API 26/ocho omitidas. Navegador SwiftShader CPU; no nueva cifra de FPS en otro portátil. Sin cambios de dependencias ni uv.lock, GPU, datos privados ni sesión humana simulada como real.
