# Plataforma y recursos de cómputo

## Plataforma IndesIA

Pendiente de la formación (ROADMAP 0.2): qué es, recursos, modelos de visión que ofrece, límites,
salida a internet, Docker y si sus modelos pueden procesar el dataset de TR.

## Medidas en local (RTX 5070 Laptop, 8 GB)

Medido por Lectura el 27/10/2026 con `uv run python -m trazia.vision.medir` sobre páginas GA A3
de S-dev (sintéticas), caché vacía.

| Modelo | Cuantización | Página | Mosaicos | Segundos por página | VRAM de pico | Textos leídos |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen3-VL 4B Instruct (Ollama 0.40.11) | Q4_K_M | A3 escaneado limpio, 150 ppp | 6 de 1.280 px | 118 s (104 s de modelo) | 5,7 GB (0,4 GB antes) | 135 |
| Qwen3-VL 4B (variante con razonamiento) | Q4_K_M | Un mosaico | 1 | No responde: agota los 4.096 tokens razonando y no devuelve el JSON | — | — |
| RapidOCR 3.10 (PP-OCRv6 small) | ONNX, CPU | A3 escaneado limpio, 200 ppp | página entera | 2,8 s | — (CPU) | 82 |

Notas:

- La variante útil para extraer es `qwen3-vl:4b-instruct`. La etiqueta `qwen3-vl:4b` razona antes
  de responder e ignora `think: false` en esta versión de Ollama.
- En un mosaico con la tabla de boquillas, Qwen3-VL leyó bien los 35 valores y los cuatro datos de
  diseño, con cajas correctas (convención 0–1000).
- **PaddleOCR-VL: medido el 30/10/2026 y descartado como lector de página.** Ver la sección
  «Tarea 2.2» más abajo.
- Con estos tiempos, el modelo de visión no puede leer cada página: D lo reserva para los campos
  obligatorios que falten tras B, OCR, C y la geometría (DEC-09).

### Tarea 0.10 · Modelos de visión en mosaicos sobre páginas A3 (27/10/2026)

10 páginas A3 apaisadas a 150 ppp (2.481 × 1.754 px), 6 mosaicos de 1.280 px con solape del 15 %:
los dos GA de `examples/documents`, cuatro del generador v1 (`generated/synthetic`, plano y
escaneado) y cuatro de S-dev v2 (vectorial, escaneado limpio y escaneado pobre). Ollama 0.40.11,
caché vacía, VRAM muestreada con nvidia-smi cada 0,25 s (0,4 GB ocupados antes de empezar).

| Modelo | Páginas medidas | Reparto en Ollama | VRAM de pico | Segundos por página (media · mín–máx) | Textos por página | Páginas con un mosaico fallido |
| --- | --- | --- | --- | --- | --- | --- |
| `qwen3-vl:4b-instruct` (Q4_K_M, 4,3 GB cargado) | 10 / 10 | 100 % GPU | 5,8 GB | 129 s · 79–247 s | 102 | 2 (JSON truncado en un mosaico) |
| `qwen3-vl:8b-instruct` (Q4_K_M, 6,9 GB cargado) | 5 / 10 | **22 % CPU / 78 % GPU** | 7,1 GB | 339 s · 215–446 s | 101 | 0 |

- **El 8B no cabe entero en los 8 GB**: Ollama descarga el 22 % del modelo a la CPU y la página
  tarda 2,6 veces más que con el 4B. No se ha forzado a GPU. La medición se cortó tras 5 páginas
  (fin de la sesión); en esas 5 páginas no lee más textos que el 4B.
- Decisión que se desprende: `qwen3-vl:4b-instruct` es el modelo local por defecto; el 8B solo
  tendría sentido con otra GPU o con mosaicos más pequeños.
- Los dos fallos del 4B son respuestas JSON cortadas en mosaicos muy densos; el lector conserva
  el resto de la página y anota el mosaico fallido.
- Datos crudos por página en `generated/estudio/vision_010.jsonl` (fuera de Git).

### Tarea 2.2 · PaddleOCR-VL en la RTX 5070 (30/10/2026)

`uv run python -m training.paddle_vl` con el extra `train`: PyTorch 2.11 cu128 y bf16. Mismas
páginas y mosaicos que la tabla 0.10: S-dev escaneado limpio, 150 ppp, 6 mosaicos de 1.280 px.

| Carga | Resultado |
| --- | --- |
| Código remoto del repositorio con transformers 4.55 o 4.57 | No arranca: `create_causal_mask()` cambió de firma. Con un parche de nombres en 4.57, 1,5 s por token, la VRAM pasa de 8 GB (desborda a memoria compartida) y la salida entra en bucle («N1, N2, … N63») |
| Clase nativa de transformers 5.22 | Carga en 2,7 GB. En el primer mosaico responde en 3 s, pero solo con un texto («13575»). En otros mosaicos la generación no se corta: llena la GPU (7,7 GB) y no acaba una página de 6 mosaicos en 25 minutos, ni con un tope de 512 tokens |

- Transformers avisa al cargar de que ignora `mrope_section` en la configuración del modelo. Puede
  que la versión nativa no lea bien este checkpoint. Las cifras valen para esta combinación, no
  para el modelo en su entorno oficial (PaddlePaddle con PP-DocLayout delante).
- **Decisión:** no se integra en `trazia.ocr`. PaddleOCR-VL espera regiones ya recortadas por el
  detector de maquetación; sobre mosaicos de plano no sirve como lector de página. Para leer
  escaneados se queda RapidOCR (CPU) y el detector propio (abajo).

### Tarea 2.4 · Detector propio Florence-2 (30/10/2026)

`python -m training.dataset` (mosaicos de S-dev), después `training.florence entrenar`, `evaluar`
y `leer`. Base `florence-community/Florence-2-base` (0,23 B, MIT), con la torre de visión
congelada.

| Paso | Datos | Resultado |
| --- | --- | --- |
| Entrenamiento | 1.410 mosaicos de 768 px de S-dev, 3 épocas, lote 4, lr 1e-5 | 525 s, pico de 4,9 GB, pérdida 0,67 → 0,47 |
| Evaluación | 200 mosaicos de S-reservado: proveedores no vistos | Detección con IoU ≥ 0,5: precisión 0,985, cobertura 0,980, F1 0,982. Texto exacto: 90,2 %. 0,19 s por mosaico |
| Lectura de escaneados | 296 páginas (S-dev y S-reservado, limpio y pobre), 12 mosaicos por página | 2,8–3,5 s por página, 15.650 regiones en la caché `generated/cache/detector` |

- Primer intento: F1 = 0. La clase nativa vuelve a desplazar las etiquetas al calcular la pérdida,
  y el modelo aprendió a saltarse un token. Ahora la pérdida se calcula en el script, con la
  entrada del decodificador explícita.
- El canal `detector` de D solo lee la caché, así que el producto no necesita PyTorch. Su aporte
  medido está en `docs/ESTUDIO.md`.
