# Entrega a Lectura · diagnóstico CPU del 02/11/2026

No se han editado los lectores, estrategias, calibración, `bench/`, `synthetic/`, `training/`
ni `model.py`. Se han utilizado sus interfaces existentes, con GPU deshabilitada, sin
proveedores y sin datos de `data/private/`. No hay un chat activo de Lectura identificado
en esta sesión; esta entrega deja los casos y la reproducción preparados.

## 1. Los 85 errores de D persisten

Repetido el corpus completo de 336 revisiones con la fuente congelada de main d6b7e9e más
el guard de feedback verificado de Plataforma, calibración v6 y fusión empaquetada:
**251 DRAFT y 85 errores**. Los errores son 27 escaneados limpios y 58 pobres; no hay
errores vectoriales. No se ha usado la verdad para construir los modelos.

| Diagnóstico | Revisiones |
| --- | ---: |
| Faltan las cinco dimensiones obligatorias | 34 |
| Falta `skirt_thickness` | 11 |
| Falta `diameter` | 7 |
| Faltan `height`, `head_depth`, `skirt_height` | 6 |
| Faltan `diameter`, `skirt_thickness` | 4 |
| Falta `head_depth` | 1 |
| El fondo inferior queda por debajo del suelo | 20 |
| Profundidad de fondo mayor que el radio | 2 |

Los dos últimos grupos deben seguir bloqueados: no se intercambian dimensiones ni se
rellenan campos desde GT para aumentar el contador de exportaciones. Los errores no
demuestran un defecto del validador de Plataforma.

### Comparación de estrategias existentes

- D: 251 DRAFT, 85 errores; precisión de campos devueltos 90,30 %, recall correcto 54,68 %.
- B+OCR: 220 DRAFT, 116 errores; precisión 92,11 %, recall correcto 46,82 %.
- B+OCR recupera un error de D con geometría principal incorrecta y pierde 32 DRAFT de D.
  Se descarta activar ese fallback automático.
- En los 34 errores históricos de S-dev se probaron también D sin geometría y D heurístico:
  D sin geometría comparte la recuperación incorrecta de B+OCR; D heurístico no recupera
  ninguno. Es un sondeo de desarrollo, no un ajuste sobre S-reservado.

Entre los 251 DRAFT de D, 185 tienen correctas todas las dimensiones principales evaluadas
y **96** tienen correctos todos los campos de la rúbrica utilizada (tag, geometría y
boquillas). Es una comparación sintética con tolerancias explícitas, sin atributos de HDM;
no acredita fidelidad de ingeniería real ni 1.600 IFC correctos. En los JSON reales de la API,
95 DRAFT conservan boquillas sin colocar; solo 81 tienen todos los campos evaluados correctos
y ninguna boquilla pendiente. El contador de Plataforma se ha corregido y reconstruido.

Los errores de valor más frecuentes en D son altura (86), altura de faldón (66) y profundidad
de fondo (57). Pueden coexistir en una misma revisión. El inventario anterior ya contiene
candidatos, texto, página/caja y GT consultada después de extraer:
[inventario previo](../evidencias/fase3/01nov-triage/triage-v6.json). La repetición de esta sesión
queda en [85 errores de D del 02/11](../evidencias/fase3/02nov/fallos-d-85.json) y
[calidad de las 672 predicciones](../evidencias/fase3/02nov/calidad-por-revision.json).

Reproducción: `scripts/triage_scale.py --report <d-workers-4.json> --data <synthetic_v2>
--sets s-dev s-reservado s-mecanico s-adversarial --strategy d_hibrido --output <dir>`.
`--all-cases` incluye también los 251 exportados; `scripts/measure_cpu_quality.py` orquesta
las variantes por partición. Requiere calibración v6, `CUDA_VISIBLE_DEVICES=-1` y los extras
OCR/geo del entorno CPU utilizado. No tocar corpus ni pesos durante la comparación.

## 2. Recalibración de D sin propuesta

Con 2.662 campos D emitidos de S-dev, `bench.recalibrar.propose` devuelve `insufficient` /
«Faltan campos para ajuste y validación». El motivo reproducible es que `bench.calibrar.fit`
incluye D en PASSTHROUGH y omite sus curvas, y `propose` no le entrega `fusion_rows` con máscaras.
No se debe eliminar esa protección para ajustar una curva sesgada a las tablas de S-dev.
Se solicita una ruta explícita compatible con la fusión con máscaras o un diagnóstico que
distinga esta estrategia no soportada de una muestra pequeña.

B+OCR sí produce propuesta: ECE interna 0,0215 → 0,0064; externa 0,1454 → 0,0753 sobre
564 campos emitidos de S-reservado. Sigue por encima del objetivo 0,05, está marcada como
simulación y no se activa. La confianza para este contraste es `Source.confidence_raw`,
entrada de calibración, no la confianza original del extractor antes de la fusión.

Los pesos de prioridad ajustados con S-dev empeoran el recall medio por equipo reservado
en 3,72 puntos, IC95 [−6,08; −1,65]. No se modifica el algoritmo de ajuste con los resultados
de S-reservado. [Ablación, calibración y protocolo completos](../evidencias/fase3/02nov-aprendizaje/README.md).

## 3. Prueba OCR previa fallida en el entorno Linux con OCR

Antes de modificar el código, la suite con RapidOCR instalado terminó con **389 pruebas
correctas y un fallo** (196,06 s):

`tests/test_lectura_ocr.py::test_b_with_ocr_reads_a_scanned_drawing`, línea 96, espera al menos
26 campos de boquillas y obtiene **0**. La comprobación previa del diámetro sí pasa. Se usa
el motor/pesos de la imagen CPU existente, sin GPU y con la red deshabilitada.

Comando dentro de la imagen CPU: `.venv/bin/python -m pytest -q
tests/test_lectura_ocr.py::test_b_with_ocr_reads_a_scanned_drawing`. Deben montarse la fuente
actual y las pruebas; no cambiar el test para aceptar cero boquillas. El perfil dev+api+geo
sin el extra OCR omite esta prueba opcional. La omisión de ese perfil no cierra el fallo OCR.

## 4. Cambios de Plataforma relevantes

El consumidor de feedback ahora ignora contextos no verificados y acota/valida sus factores;
la huella distingue el estado de verificación. El arnés conserva errores, boquillas extras y
campos ausentes en la calidad. La inspección de escala archiva los JSON sintéticos que devuelve
la API para contrastarlos después de terminar el trabajo. El contador de boquillas sin colocar
debe leer `Revision.unplaced_nozzles`, no `Equipment.unplaced_nozzles`.

Siguen ausentes las correcciones humanas representativas y el IFC autorizado de TR.
No se transforma una evaluación sintética en evidencia de uso real.

## 5. Hilos OCR: dato para una prueba controlada posterior

Durante la pasada Redis con cuatro workers, una muestra Docker del 02/11 a las 14:43 CET
registra **95 hilos/PID por worker**, aproximadamente 1,34–1,40 GiB por proceso y uso conjunto
instantáneo de 23,11 CPU lógicas. Host: Ryzen 9 8940HX, 16 núcleos/32 hilos; límite de memoria
mostrado por Docker 43,11 GiB. `OMP_NUM_THREADS=1` y `OPENBLAS_NUM_THREADS=1` ya están fijados.
`trazia.ocr.engine._rapidocr` construye `RapidOCR()` con sus valores predeterminados.

Se propone contrastar, dentro del lector, límites explícitos de hilos por sesión ONNX y una
prueba controlada con el mismo corpus. Los hilos enumerados incluyen los que esperan: esta
muestra puntual no prueba saturación sostenida, consumo máximo ni una causa aislada de la
aceleración observada. No se ha cambiado la configuración del motor durante las mediciones.
