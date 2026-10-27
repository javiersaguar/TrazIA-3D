# Lectura visual real de un GA sintético

Original: `examples/documents/GAD_V-101_revA.pdf`, página 1 a 100 dpi.
SHA-256 del PDF: `468bb29a7c64e8a9e391e648250328f6e20ab7b44c004e10db4ebb9f2fa0a1b1`.
SHA-256 del PNG: `b5b616537860534d55dcdaf703de1af7c279a8c658f166d65ac742cedb651970`.
Modelo: qwen3-vl:4b-instruct (Q4_K_M), Ollama 0.40.11, 27/10/2026.
Se conserva la respuesta real validada en el formato normalizado de caché; no es un mock.
27 fragmentos; 2059 tokens de entrada / 1263 de salida; 34,266 s reportados por Ollama.
La lectura y su repetición offline se comprobaron con el adaptador del producto.
No representa precisión medida en datos de Técnicas Reunidas.

Reproducir la prueba sin modelo ni red:
`uv run pytest tests/test_lectura_vision.py -k versioned -q`.
