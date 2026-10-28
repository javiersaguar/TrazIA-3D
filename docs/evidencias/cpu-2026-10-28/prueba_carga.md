# Prueba de carga del banco y estudio sobre sintéticos

Copia del informe cerrado antes de autorizar commit/push. Su estado de publicación se refiere a ese momento; las evidencias se publican después del cierre.

Fecha del informe: 2026-10-28T13:05:20+01:00 (Europe/Madrid).

Código evaluado: `10f649d`; worktree `TrazIA-3D-prueba-carga`. Sin commit ni push. La reanudación usa la rama `chore/roadmap-cpu`, con cambios locales de exportación y metadatos de impacto; estrategias, generador y fórmulas del banco permanecen iguales. Los artefactos de medición viven en `generated/`.

## Alcance y método

Datos exclusivamente sintéticos, generador v1, 40 equipos con semilla 2026, estilos rotulado/plano/escaneado y revisiones 1/2: 120 condiciones, 240 PDF y 240 HDM Excel. Hay 155 cambios verdaderos por conjunto de 40 equipos, repetidos en cada estilo. No se ha leído `data/private/`.

SHA-256 agregado de rutas y contenido del conjunto: `1b5f432648c6aee99b913eb33abc3ae4325b0fc467d6ec5de86c958854fd9393`. Las fechas internas de PDF/Excel pueden cambiar sus bytes al regenerar.

El arnés del estudio espera conjuntos v2. `estudio_v1.py` llama al mismo `run_study` con el conjunto v1 original y adapta en memoria solo la etiqueta/población puntuada (`synthetic-v1`) y el nombre del estilo escaneado. Usa 1.000 remuestreos bootstrap agrupados por equipo, semilla 2026. No transforma documentos, verdades, estrategias ni fórmulas. El informe corrige el indicador del generador a v1. No son S-dev ni S-reservado v2; no mide generalización a proveedores nuevos. La columna por proveedor carece de significado en v1 (vendor desconocido); se utiliza el desglose por estilo/degradación. La recomendación vectorial nativa puede quedar vacía porque el arnés busca el nombre v2 vectorial y este banco llama plano al estilo equivalente; no se presenta como un selector validado.

La biblioteca de C se construye con campos verificados de rev1/plano de estos mismos 40 equipos, usando `build_entry`; C excluye el mismo equipo al recuperar plantillas. Es una evaluación de proveedores conocidos, sin biblioteca externa ni datos reales. Su preparación se cronometra por separado. D se mide sin proveedor de visión, como establece el estudio predeterminado.

Se conserva la selección predeterminada del estudio por indicación del usuario: A con visión local se omite por su coste temporal; Gemini/Mistral requieren credenciales; detector y su ablación se omiten si no están implementados; D sin visión es redundante en esta configuración. Los motivos exactos figuran más abajo.

Las etapas de medición se ejecutan secuencialmente. La sesión se interrumpió el 27/10 y se reanudó el 28/10, reutilizando condiciones completas. Durante la reanudación hubo comprobaciones dirigidas y edición local en el mismo equipo; no es una prueba de rendimiento aislada. Los tiempos de pared incluyen arranque del proceso y escritura; el tiempo interno por revisión del estudio mide el pipeline y excluye su evaluación geométrica/estadística. Los tiempos del banco promedian solo las revisiones ensambladas. No hay equivalencia directa entre ese promedio y el del estudio. B inicial puede crear caché OCR para verificar citas en escaneados; las variantes posteriores reutilizan esa caché. No es una comparación controlada de latencia en frío. No se ha parado el stack ni otros procesos del equipo.

El IoU utilizado por este banco es de cajas envolventes de los componentes IFC, no IoU volumétrico de mallas ni Hausdorff. La geometría del estudio combina acierto de campos con ese IoU y penaliza las revisiones sin IFC; no equivale al acierto de campos del banco v1. Un IFC construido no implica que todos sus campos sean correctos. La elegibilidad solo comprueba respaldo verificable y cobertura de citas: no garantiza un IFC correcto. El F1 del estudio cuenta como no vistos los cambios de pares sin dos modelos. El campo equipment de los detalles del arnés cuenta condiciones (120), mientras que hay 40 equipos únicos. Innovación aporta un 10 % constante por convención, no por medición. Coste monetario local = 0 según RunInfo; no incluye electricidad, hardware ni coste amortizado.

## Entorno

Windows-11-10.0.26300-SP0; Python 3.12.9; CPU AMD Ryzen 9 8940HX, 16 núcleos/32 hilos. Extras instalados: dev, api (incluye geo) y ocr mediante `uv sync --frozen`. Sin límites de hilos impuestos por esta prueba.

pytest 9.1.1, ifcopenshell 0.8.5, rapidocr 3.10.0, onnxruntime 1.31.1, pydantic 2.14.1, pdfplumber 0.11.10, numpy 2.5.4, scipy 1.18.1.

## Tiempos por etapa

| Etapa | Comando | Segundos de pared | Salida |
| --- | --- | --- | --- |
| generación | `uv run python -m synthetic --casos 40 --semilla 2026` | 18.86 | 0 |
| bench | `uv run python -m bench --detalle` | 148.59 | 0 |
| estudio_b | `uv run python generated/bench/estudio_v1.py b` | 543.17 | 0 |
| biblioteca | `uv run python generated/bench/estudio_v1.py biblioteca` | 5.51 | 0 |
| estudio_variantes | `uv run python generated/bench/estudio_v1.py variantes` | No recuperada: interrupción | Interrumpido |
| estudio_variantes_reanudacion | `uv run python generated/bench/estudio_v1.py variantes` | 1280.52 | 0 |
| pytest_1 | `uv run pytest -q` | 195.33 | 0 |
| pytest_2 | `uv run pytest -q` | 157.40 | 0 |
| pytest_3 | `uv run pytest -q` | 155.00 | 0 |

## Banco: extractor de etiquetas

| Estilo | IFC/revisiones | Geometría (campos) | Atributos | F1 cambios | ECE | s/rev con IFC | IoU cajas |
| --- | --- | --- | --- | --- | --- | --- | --- |
| rotulado | 80/80 | 100.00 % | 100.00 % | 100.00 % | 0.2500 | 0.0870 | 1.0000 |
| plano | 0/80 | 0.00 % | 100.00 % | Sin medir | 0.2500 | Sin medir | Sin medir |
| escaneado | 0/80 | 0.00 % | 100.00 % | Sin medir | 0.2500 | Sin medir | Sin medir |

El banco solo puntúa cambios en pares con dos IFC; un F1 ausente en plano/escaneado significa sin pares evaluables, no 0 ni 100 %. Los atributos provienen de los Excel presentes en todos los casos.

Resumen versionado del banco: [bench-v1.json](bench-v1.json). El detalle por caso y los logs quedan en el directorio local generated/bench.

## Estudio B inicial

| Variante | Puntuación | IC 95 % | Geometría ponderada | Atributos | F1 cambios | ECE | Sin respaldo verificable | Cobertura cita | IFC/rev | Rev. con error | s/rev interno | €/equipo | Elegible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| b_reglas | 0.7982 | [0.7981, 0.7982] | 66.67 % | 100.00 % | 80.00 % | 0.1804 | 0.00 % | 100.00 % | 160/240 | 80 | 0.0804 | 0.0000 | Sí |

### Tiempo de evaluación por variante

Suma de pared de las condiciones (pipeline, comprobación de evidencias e IFC de referencia), antes del bootstrap y la comparación estadística. No es solo inferencia ni incluye el arranque del proceso.

| Variante | Condiciones | Segundos | Llamadas externas | Campos no verificables |
| --- | --- | --- | --- | --- |
| b_reglas | 120 | 474.36 | 0 | 0 |

### Por estilo

| Variante | Estilo | Geometría | Atributos | F1 cambios | s/rev interno |
| --- | --- | --- | --- | --- | --- |
| b_reglas | rotulado | 100.00 % | 100.00 % | 100.00 % | 0.1424 |
| b_reglas | plano | 100.00 % | 100.00 % | 100.00 % | 0.0868 |
| b_reglas | escaneado | 0.00 % | 100.00 % | 0.00 % | 0.0121 |

### Fallos observados

| Variante | Revisiones | Primer renglón del error |
| --- | --- | --- |
| b_reglas | 80 | Faltan datos explícitos: tag, diameter, height, head_depth, skirt_height, skirt_thickness |

### Sin medir

Ninguna.

Evidencias: [estudio-b.json](estudio-b.json), generated/bench/estudio_b/estudio.md y generated/bench/estudio_b/casos.jsonl (locales). El detalle JSONL conserva los errores y tiempos de todas las condiciones, incluidas las fallidas.

## Estudio comparativo predeterminado

| Variante | Puntuación | IC 95 % | Geometría ponderada | Atributos | F1 cambios | ECE | Sin respaldo verificable | Cobertura cita | IFC/rev | Rev. con error | s/rev interno | €/equipo | Elegible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| a_geometria | 0.3980 | [0.3941, 0.4018] | 0.00 % | 100.00 % | 0.00 % | 0.2043 | 0.00 % | 100.00 % | 0/240 | 240 | 1.1598 | 0.0000 | Sí |
| b_reglas | 0.7982 | [0.7981, 0.7983] | 66.67 % | 100.00 % | 80.00 % | 0.1804 | 0.00 % | 100.00 % | 160/240 | 80 | 0.0501 | 0.0000 | Sí |
| b_reglas+ocr | 0.8047 | [0.8004, 0.8091] | 68.49 % | 98.85 % | 78.49 % | 0.1577 | 0.00 % | 100.00 % | 167/240 | 73 | 0.1810 | 0.0000 | Sí |
| c_rag | 0.6261 | [0.6055, 0.6432] | 35.02 % | 98.75 % | 43.98 % | 0.1261 | 0.00 % | 100.00 % | 92/240 | 148 | 0.1793 | 0.0000 | Sí |
| d_hibrido | 0.7145 | [0.7035, 0.7253] | 45.66 % | 98.75 % | 68.76 % | 0.1150 | 0.00 % | 100.00 % | 174/240 | 66 | 1.5288 | 0.0000 | Sí |
| b_reglas-tablas | 0.6041 | [0.6041, 0.6041] | 33.33 % | 100.00 % | 50.00 % | 0.2500 | 0.00 % | 100.00 % | 80/240 | 160 | 0.1040 | 0.0000 | Sí |
| b_reglas-hdm | 0.6554 | [0.6523, 0.6578] | 66.67 % | 33.33 % | 76.49 % | 0.1706 | 0.00 % | 100.00 % | 160/240 | 80 | 0.0822 | 0.0000 | Sí |
| d_hibrido-geometria | 0.8123 | [0.8012, 0.8229] | 71.88 % | 98.75 % | 72.62 % | 0.1263 | 0.00 % | 100.00 % | 181/240 | 59 | 0.2126 | 0.0000 | Sí |
| d_hibrido-memoria | 0.7208 | [0.7108, 0.7305] | 45.72 % | 98.75 % | 72.46 % | 0.1224 | 0.00 % | 100.00 % | 175/240 | 65 | 0.9982 | 0.0000 | Sí |
| d_hibrido-rag | 0.7100 | [0.6992, 0.7198] | 44.02 % | 98.85 % | 68.99 % | 0.1155 | 0.00 % | 100.00 % | 167/240 | 73 | 0.7187 | 0.0000 | Sí |

### Tiempo de evaluación por variante

Suma de pared de las condiciones (pipeline, comprobación de evidencias e IFC de referencia), antes del bootstrap y la comparación estadística. No es solo inferencia ni incluye el arranque del proceso.

| Variante | Condiciones | Segundos | Llamadas externas | Campos no verificables |
| --- | --- | --- | --- | --- |
| a_geometria | 120 | 304.81 | 0 | 859 |
| b_reglas | 120 | 219.25 | 0 | 0 |
| b_reglas+ocr | 120 | 349.37 | 0 | 0 |
| c_rag | 120 | 208.01 | 0 | 0 |
| d_hibrido | 120 | 661.25 | 0 | 512 |
| b_reglas-tablas | 120 | 293.20 | 0 | 0 |
| b_reglas-hdm | 120 | 342.87 | 0 | 0 |
| d_hibrido-geometria | 120 | 277.13 | 0 | 0 |
| d_hibrido-memoria | 120 | 424.15 | 0 | 512 |
| d_hibrido-rag | 120 | 334.56 | 0 | 556 |

### Por estilo

| Variante | Estilo | Geometría | Atributos | F1 cambios | s/rev interno |
| --- | --- | --- | --- | --- | --- |
| a_geometria | rotulado | 0.00 % | 100.00 % | 0.00 % | 0.0484 |
| a_geometria | plano | 0.00 % | 100.00 % | 0.00 % | 0.0798 |
| a_geometria | escaneado | 0.00 % | 100.00 % | 0.00 % | 3.3513 |
| b_reglas | rotulado | 100.00 % | 100.00 % | 100.00 % | 0.0675 |
| b_reglas | plano | 100.00 % | 100.00 % | 100.00 % | 0.0790 |
| b_reglas | escaneado | 0.00 % | 100.00 % | 0.00 % | 0.0038 |
| b_reglas+ocr | rotulado | 100.00 % | 100.00 % | 100.00 % | 0.1039 |
| b_reglas+ocr | plano | 100.00 % | 100.00 % | 100.00 % | 0.1428 |
| b_reglas+ocr | escaneado | 5.46 % | 96.56 % | 2.29 % | 0.2962 |
| c_rag | rotulado | 0.00 % | 100.00 % | 0.00 % | 0.0744 |
| c_rag | plano | 92.19 % | 100.00 % | 90.03 % | 0.1539 |
| c_rag | escaneado | 12.86 % | 96.25 % | 6.78 % | 0.3096 |
| d_hibrido | rotulado | 100.00 % | 100.00 % | 100.00 % | 0.1688 |
| d_hibrido | plano | 27.85 % | 100.00 % | 71.93 % | 0.1973 |
| d_hibrido | escaneado | 9.12 % | 96.25 % | 8.84 % | 4.2201 |
| b_reglas-tablas | rotulado | 100.00 % | 100.00 % | 100.00 % | 0.2053 |
| b_reglas-tablas | plano | 0.00 % | 100.00 % | 0.00 % | 0.0942 |
| b_reglas-tablas | escaneado | 0.00 % | 100.00 % | 0.00 % | 0.0124 |
| b_reglas-hdm | rotulado | 100.00 % | 0.00 % | 92.36 % | 0.1079 |
| b_reglas-hdm | plano | 100.00 % | 100.00 % | 100.00 % | 0.1325 |
| b_reglas-hdm | escaneado | 0.00 % | 0.00 % | 0.00 % | 0.0061 |
| d_hibrido-geometria | rotulado | 100.00 % | 100.00 % | 100.00 % | 0.0915 |
| d_hibrido-geometria | plano | 100.00 % | 100.00 % | 86.18 % | 0.1079 |
| d_hibrido-geometria | escaneado | 15.63 % | 96.25 % | 10.78 % | 0.4385 |
| d_hibrido-memoria | rotulado | 100.00 % | 100.00 % | 100.00 % | 0.0950 |
| d_hibrido-memoria | plano | 28.29 % | 100.00 % | 81.05 % | 0.1332 |
| d_hibrido-memoria | escaneado | 8.88 % | 96.25 % | 8.65 % | 2.7664 |
| d_hibrido-rag | rotulado | 100.00 % | 100.00 % | 100.00 % | 0.0657 |
| d_hibrido-rag | plano | 27.85 % | 100.00 % | 71.93 % | 0.0848 |
| d_hibrido-rag | escaneado | 4.21 % | 96.56 % | 0.00 % | 2.0056 |

### Fallos observados

| Variante | Revisiones | Primer renglón del error |
| --- | --- | --- |
| a_geometria | 84 | Faltan datos explícitos: tag, diameter, height, head_depth, skirt_height, skirt_thickness |
| a_geometria | 156 | El recipiente vertical de nivel 2/3 necesita al menos tres boquillas |
| b_reglas | 80 | Faltan datos explícitos: tag, diameter, height, head_depth, skirt_height, skirt_thickness |
| b_reglas+ocr | 1 | Boquilla N3: debe quedar dentro de la virola |
| b_reglas+ocr | 49 | El recipiente vertical de nivel 2/3 necesita al menos tres boquillas |
| b_reglas+ocr | 14 | Faltan datos explícitos: height, head_depth, skirt_height |
| b_reglas+ocr | 5 | Boquilla N1: debe quedar dentro de la virola |
| b_reglas+ocr | 2 | El fondo inferior debe quedar por encima del suelo |
| b_reglas+ocr | 2 | Boquilla N2: debe quedar dentro de la virola |
| c_rag | 80 | Faltan datos explícitos: tag, diameter, height, head_depth, skirt_height, skirt_thickness |
| c_rag | 2 | Boquilla N3: debe quedar dentro de la virola |
| c_rag | 16 | Boquilla N1: debe quedar dentro de la virola |
| c_rag | 38 | El recipiente vertical de nivel 2/3 necesita al menos tres boquillas |
| c_rag | 8 | Faltan datos explícitos: head_depth |
| c_rag | 1 | Boquilla N5: debe quedar dentro de la virola |
| c_rag | 2 | Boquilla N2: debe quedar dentro de la virola |
| c_rag | 1 | El fondo inferior debe quedar por encima del suelo |
| d_hibrido | 2 | Boquilla N3: debe quedar dentro de la virola |
| d_hibrido | 4 | Boquilla N2: debe quedar dentro de la virola |
| d_hibrido | 14 | Boquilla N1: debe quedar dentro de la virola |
| d_hibrido | 35 | El recipiente vertical de nivel 2/3 necesita al menos tres boquillas |
| d_hibrido | 2 | Esta familia admite fondos con profundidad hasta el radio |
| d_hibrido | 6 | El fondo inferior debe quedar por encima del suelo |
| d_hibrido | 1 | Boquilla N4: debe quedar dentro de la virola |
| d_hibrido | 2 | Boquilla N5: debe quedar dentro de la virola |
| b_reglas-tablas | 160 | Faltan datos explícitos: tag, diameter, height, head_depth, skirt_height, skirt_thickness |
| b_reglas-hdm | 80 | Faltan datos explícitos: tag, diameter, height, head_depth, skirt_height, skirt_thickness |
| d_hibrido-geometria | 2 | Boquilla N3: debe quedar dentro de la virola |
| d_hibrido-geometria | 11 | Boquilla N1: debe quedar dentro de la virola |
| d_hibrido-geometria | 40 | El recipiente vertical de nivel 2/3 necesita al menos tres boquillas |
| d_hibrido-geometria | 2 | Faltan datos explícitos: head_depth |
| d_hibrido-geometria | 1 | Boquilla N5: debe quedar dentro de la virola |
| d_hibrido-geometria | 2 | Boquilla N2: debe quedar dentro de la virola |
| d_hibrido-geometria | 1 | El fondo inferior debe quedar por encima del suelo |
| d_hibrido-memoria | 2 | Boquilla N3: debe quedar dentro de la virola |
| d_hibrido-memoria | 3 | Boquilla N2: debe quedar dentro de la virola |
| d_hibrido-memoria | 14 | Boquilla N1: debe quedar dentro de la virola |
| d_hibrido-memoria | 36 | El recipiente vertical de nivel 2/3 necesita al menos tres boquillas |
| d_hibrido-memoria | 2 | Esta familia admite fondos con profundidad hasta el radio |
| d_hibrido-memoria | 5 | El fondo inferior debe quedar por encima del suelo |
| d_hibrido-memoria | 1 | Boquilla N4: debe quedar dentro de la virola |
| d_hibrido-memoria | 2 | Boquilla N5: debe quedar dentro de la virola |
| d_hibrido-rag | 2 | Boquilla N3: debe quedar dentro de la virola |
| d_hibrido-rag | 51 | El recipiente vertical de nivel 2/3 necesita al menos tres boquillas |
| d_hibrido-rag | 7 | Boquilla N1: debe quedar dentro de la virola |
| d_hibrido-rag | 4 | Boquilla N2: debe quedar dentro de la virola |
| d_hibrido-rag | 5 | El fondo inferior debe quedar por encima del suelo |
| d_hibrido-rag | 1 | Boquilla N4: debe quedar dentro de la virola |
| d_hibrido-rag | 2 | Boquilla N5: debe quedar dentro de la virola |
| d_hibrido-rag | 1 | Esta familia admite fondos con profundidad hasta el radio |

### Sin medir

- `a_vision`: unos 4 min de GPU por página: se mide aparte en un subconjunto.
- `a_vision@gemini`: sin GEMINI_API_KEY en .env: sin medir.
- `a_vision@mistral`: sin MISTRAL_API_KEY en .env: sin medir.
- `a_detector`: estrategia aún no implementada.
- `d_hibrido-detector`: estrategia aún no implementada.
- `d_hibrido-vision`: el estudio no da proveedor de visión a D: sería idéntica a d_hibrido.

Evidencias: [estudio-variantes.json](estudio-variantes.json), generated/bench/estudio_variantes/estudio.md y generated/bench/estudio_variantes/casos.jsonl (locales). El detalle JSONL conserva los errores y tiempos de todas las condiciones, incluidas las fallidas.

## Tres pasadas consecutivas de pytest

| Pasada | Segundos de pared | Código de salida | Resumen pytest |
| --- | --- | --- | --- |
| 1 | 195.33 | 0 | 225 passed, 1 warning in 193.59s (0:03:13) |
| 2 | 157.40 | 0 | 225 passed, 1 warning in 156.09s (0:02:36) |
| 3 | 155.00 | 0 | 225 passed, 1 warning in 153.68s (0:02:33) |

Tiempo de calendario desde el inicio de la generación hasta este informe (incluye interrupción nocturna, no es tiempo de proceso): 57314.25 s (incluye preparación y comprobaciones entre comandos). Suma de las etapas terminadas (excluye el tramo interrumpido): 2504.36 s.

## Estado final

Todas las etapas solicitadas han terminado; véanse códigos de salida y fallos arriba.

Sin commit ni push. Hay cambios locales de ROADMAP, documentación, exportaciones, impacto y CI en este worktree. No se han modificado estrategias, generador ni fórmulas del banco, ni datos de otros worktrees. La duración original del comparativo interrumpido no se inventa: solo se conservan los tiempos de sus condiciones y el tiempo medido de reanudación. Un intento dirigido previo fue bloqueado por Control de aplicaciones; las tres pasadas completas finales pudieron usar el comando exacto uv run pytest -q y terminaron sin fallos.
