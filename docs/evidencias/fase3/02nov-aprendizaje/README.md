# Evaluación adicional de aprendizaje · 02/11/2026

**Simulación sintética, cero sesiones humanas y ningún perfil activado.** No se escriben
correcciones ni aprobaciones en el almacén de la aplicación. E.5 continúa pospuesta.

## Protocolo

Se congelan los documentos del corpus, la fuente de ejecución, la fusión y la calibración v6.
Se ajusta exclusivamente con los **24 equipos de S-dev** y se evalúa sobre **16 equipos de
S-reservado**, con sus tres degradaciones y dos revisiones (96 entradas). No comparten equipos
ni SHA de documentos originales. La verdad se consulta después de la extracción, para simular
etiquetas de corrección; nunca se entrega al pipeline para completar datos ausentes.

La ablación ejecuta D real sin proveedores, con tres contextos experimentales: prioridades,
ejemplos y ambos. Los pesos proceden de `channel_priorities`, con los mínimos y límites de
producción; los tres ejemplos se toman de errores de S-dev. Se transportan mediante el contexto
de feedback, sin fabricar una sesión humana. Los intervalos de la diferencia se remuestrean por
equipo (2.000 muestras, semilla 2026), manteniendo juntas sus revisiones y degradaciones.

La recalibración utiliza el `propose` existente de `bench.recalibrar`: partición interna por
equipo entre curva, conformal y validación, seguida del contraste externo en S-reservado. Las
etiquetas usan la confianza de entrada de calibración (`Source.confidence_raw`), que en D puede
ser distinta de la confianza original del extractor tras la fusión. ECE e intervalos solo se
calculan sobre campos emitidos con correspondencia en la verdad; ausencias y boquillas extras
se contabilizan por separado en precisión y recall de extracción.

## Resultados medidos

| D / 96 revisiones | DRAFT / error | Campos correctos / esperados | Geometría principal correcta en DRAFT | Todos los campos evaluados correctos en DRAFT |
| --- | ---: | ---: | ---: | ---: |
| Sin perfil | 77 / 19 | 1.100 / 2.484 (44,28 %) | 47 | 23 |
| Prioridades | 77 / 19 | 1.008 / 2.484 (40,58 %) | 35 | 15 |
| Solo ejemplos | 77 / 19 | 1.100 / 2.484 (44,28 %) | 47 | 23 |
| Ejemplos + prioridades | 77 / 19 | 1.008 / 2.484 (40,58 %) | 35 | 15 |

La diferencia media de recall por equipo es **−3,72 puntos porcentuales**, IC95 por equipos
**[−6,08; −1,65]**, para prioridades y para el perfil combinado. Los pesos ajustados son tabla
1,076294; cota 1,069701; cajetín 1,055689; OCR 1,007977 y geometría 0,85. Este perfil empeora el
conjunto reservado y **no se acepta para producción**.

El prompt cambia de SHA al incluir los ejemplos. Sin llamadas a proveedores, el perfil de
ejemplos conserva exactamente los resultados de D: esta prueba verifica el transporte y el
aislamiento, y deja sin medir la eficacia few-shot de un modelo de visión.

| Recalibración | Validación externa | ECE base → propuesta | Cobertura de intervalos informativos | Decisión |
| --- | --- | ---: | ---: | --- |
| B+OCR | 564 campos emitidos en S-reservado | 0,1454 → 0,0753 | 94,58 % → 94,58 % | Propuesta aislada; objetivo ECE < 0,05 sin alcanzar |
| D | 1.328 campos emitidos en S-reservado | Base 0,0913; propuesta ausente | Base 98,82 % | El arnés existente no propone curva para D sin los datos de fusión con máscaras |

B+OCR usa 1.758 campos de ajuste y 899 de validación interna, todos de S-dev. Su ECE interna
mejora 0,0215 → 0,0064; el deterioro al proveedor reservado evidencia por qué no basta esa
validación interna. En S-reservado hay 228 campos numéricos con intervalo demasiado amplio,
excluidos de la cobertura de intervalos informativos; no se presentan como intervalos útiles.
La precisión de valores no cambia al recalibrar su confianza.

`propose` devuelve para D `insufficient`: `fit` reserva D como PASSTHROUGH y no recibe las
filas de fusión con máscaras en esta ruta. No es una demostración de que falten etiquetas:
se han recogido 2.662 campos D en S-dev. La entrega a Lectura solicita revisar esta limitación
sin eliminar la protección contra el sesgo de proveedor.

## Seguridad del circuito y tiempos

Se ha corregido el consumidor de feedback para que un contexto no verificado no altere el
prompt ni las prioridades; su huella incluye el estado de verificación. Los factores inválidos
se neutralizan y los válidos se acotan a [0,85; 1,15], conservando la fuente original. Se añaden
pruebas de aislamiento y de confianza de entrada a calibración.

Esta última evaluación tarda **19,55 s**, con la caché de páginas caliente de la medición CPU
previa. Sus tiempos no se comparan con la extracción inicial para atribuir una aceleración al
aprendizaje. Cero llamadas externas y GPU deshabilitada. El coste total de uso real sigue sin
medir; tampoco hay muestra humana representativa.

## Reproducción y artefactos

El script `scripts/evaluate_synthetic_feedback.py` recibe `--measurements` (las particiones
completas producidas por `scripts/measure_cpu_quality.py`), `--report` (inventario del lote),
`--data` y `--output`. Ejecutar en el entorno CPU con `CUDA_VISIBLE_DEVICES=-1`, calibración v6
y sin red, montando también `bench/`, `synthetic/` y la caché de páginas. El entorno utilizado
está identificado en el [registro de procedencia](provenance.json).

- [Resultados completos, riesgo-cobertura e IC95](evaluation.json).
- [Propuesta B+OCR sintética, sin activar](candidate-calibration-b_reglas+ocr.json).
- [Entrega de problemas a Lectura](../../../agentes/ENTREGA_LECTURA_02NOV.md).

3.8/E.6 conservan pendiente la evaluación con correcciones humanas representativas; no se
consideran cerradas por este ensayo sintético.
