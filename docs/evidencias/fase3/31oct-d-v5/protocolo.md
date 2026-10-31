# Protocolo · D aprendido / calibración v5 · 31/10/2026

Solo sintéticos. El origen es `../TrazIA-3D/generated/synthetic_v2`, el mismo conjunto de
336 revisiones del lote histórico. Se verifican nombres y SHA de los documentos antes de
comparar los estados por `(dataset, tag, degradación, revisión)`.

## Fijación de artefactos

- Código de producción de `main` 8717c41 y primer commit de esta sesión f5b6ae8.
- Arnés de escala instrumentado en 26019b0; la imagen no copia `scripts/` ni los datos generados.
- Imagen: `trazia-plataforma:20261031-d-v5-f5b6ae8`; su ID efectivo se archiva en cada informe.
- SHA de parámetros de fusión aprendida: `a7d09074255ee78af4af3dd1cb7dd8f592e795c5000ebad560cc2a0415486d55`.
- SHA de parámetros de calibración v5: `dd2f98c238da35d7d648b36b99317e2a991d7041d51ab03ea171428952c10636`.
- Calibración copiada de Lectura en solo lectura al worktree propio, sin editar su origen.
  Montaje de archivo read-only en API y workers; las huellas se comprueban dentro de **cada**
  contenedor antes de admitir el lote. No basta con comprobar las del proceso anfitrión.

La caché de trabajos v3 de main ya incluía SHA de calibración y fusión. El primer commit
añade una prueba que modifica pesos reales en una copia temporal y verifica el fallo de
caché; también prueba un cambio entre búsqueda y guardado. No se modifican pesos activos.

## Ejecución

```powershell
uv run python scripts/run_scale.py --wsl Ubuntu --workers 1 4 --estrategia d_hibrido --image trazia-plataforma:20261031-d-v5-f5b6ae8 --data ../TrazIA-3D/generated/synthetic_v2 --output generated/escala-d-v5/lote-principal --api-port 8030 --calibration generated/calibration/calibracion.json --expected-calibration dd2f98c238da35d7d648b36b99317e2a991d7041d51ab03ea171428952c10636 --expected-fusion a7d09074255ee78af4af3dd1cb7dd8f592e795c5000ebad560cc2a0415486d55
```

Redis/arq y Postgres reales en Docker/WSL. Concurrencia 1 por worker, ventana de 32 trabajos,
un intento, límite 180 s por trabajo y 7.200 s por lote. Cada despliegue crea proyecto y
volúmenes nuevos y elimina solo los suyos al terminar; no reutiliza resultados del lote previo.
API solo en `127.0.0.1:8030`. Se preservan los puertos y procesos ajenos.

Sin asignación de GPU, `CUDA_VISIBLE_DEVICES=-1`, `OMP_NUM_THREADS=1`,
`OPENBLAS_NUM_THREADS=1`, `TRAZIA_VISION_OFFLINE=1`, proveedores vacíos. Se aborta si un
contenedor tiene alguna de las variables conocidas de credenciales externas presentes.
No se imprimen valores ni se usa ninguna clave. OCR RapidOCR/ONNX en CPU.

Se miden tiempo del lote incluida subida, espera observada por trabajo, tiempo declarado por
pipeline y tiempo del ejecutor. La suma de latencias por equipo puede incluir esperas
simultáneas: **no equivale al tiempo de pared del lote**. Los errores conservan su estado;
un campo contable desconocido permanece `null`.

La tasa de caché de los informes es la de **trabajos completos**. No mide la caché de páginas
OCR, que se ensaya aparte. Un lote fresco con cero aciertos no prueba ausencia de ahorro OCR.

## Prueba incremental independiente

`scripts/probe_incremental.py` rasteriza un plano sintético público y crea dos revisiones
de dos páginas; cambia solo la segunda página. Ejecuta el OCR real e intercepta su llamada
al reconocedor para contar inferencias y medirlas; no modifica el módulo de Lectura. Fases:
A en frío, B con una página cambiada, B repetida y B en frío como control independiente.

Contenedor con `--network none`, modelos ONNX empaquetados, CPU y proveedores CUDA ausentes.
Se conservan SHA de PDFs, huellas de píxeles por página, número de llamadas reales y tiempos
en `incremental.json`. La carga inicial del modelo se mide por separado. Una sola secuencia,
sin intervalo de incertidumbre; no extrapolar su porcentaje de ahorro a todo el corpus.

La función OCR sigue renderizando todas las páginas para calcular huellas. Por tanto, esta
prueba distingue **inferencia OCR incremental** de un pipeline enteramente incremental.

## Contención y comparación

Host Windows 11 compartido. Lectura mantiene una comparación de proveedores principalmente
de red. No se detienen procesos ajenos ni se consume GPU. El observador registra PIDs de esa
comparación, CPU/memoria por proceso y tiempo UTC cada 30 s, sin sus argumentos ni secretos.
La primera traza redondea el porcentaje de CPU a enteros por la sobrecarga de `Math.Max`;
`host-precision.jsonl` corrige esa pérdida de precisión con doble explícito. No se interpreta
un cero redondeado como ausencia de carga. La traza tampoco mide por sí sola toda la carga
interna de WSL, la GPU ni presión de memoria.

Comparar D aprendido/v5 con D heurístico anterior no aísla el efecto de los pesos: también
cambiaron calibración y código. Son estados de generación/validación sobre sintéticos, no
precisión de extracción ni fidelidad industrial. El speedup de 1/4 workers se informa como
observado en host compartido; no como capacidad de una máquina dedicada.
