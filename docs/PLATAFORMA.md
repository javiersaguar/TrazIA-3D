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
- **Qwen3-VL 8B: sin medir.** Pesa unos 6 GB en Q4_K_M más el proyector de visión; con 8 GB de
  VRAM y mosaicos de 1.280 px es probable que se reparta entre GPU y CPU. Queda pendiente.
- **PaddleOCR-VL: sin medir.**
- Con estos tiempos, el modelo de visión no puede leer cada página: D lo reserva para los campos
  obligatorios que falten tras B, OCR, C y la geometría (DEC-09).
