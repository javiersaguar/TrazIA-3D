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
- **PaddleOCR-VL: sin medir.**
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
