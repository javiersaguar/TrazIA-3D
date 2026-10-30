# Informe del agente Lectura · sesión del 30/10/2026

Cierre de la sesión de [SESION_LECTURA.md](SESION_LECTURA.md). Rama `feat/lectura`. Todo lo
medido usa **datos sintéticos**: ninguna cifra es precisión sobre planos de TR.

## Resumen

| # | Tarea | Estado | Cifra principal |
| --- | --- | --- | --- |
| 1 | **3.2** Memoria solo con revisión aprobada | Hecha | D omite la memoria (con aviso) si la anterior es DRAFT o su huella no cuadra |
| 2 | **3.3** Calibración, intervalos conformes y abstención | Hecha; el criterio de ECE no se cumple en S-reservado | D: ECE 0,017 en S-dev y 0,279 en S-reservado; cobertura del intervalo al 90 %: 94,1 % |
| 3 | **2.11** Estudio A/B/C/D | Hecho sin A | D 0,642 [0,607; 0,678], C 0,558, B 0,536 |
| 4 | **3.4** Selector y ablaciones | Hecho; sin fusión aprendida | El selector por tipo pierde en S-reservado (0,372 frente a 0,525 de D solo) |
| 5 | **2.2 / 0.10** PaddleOCR-VL | Medido y descartado | No acaba una página A3 en 25 min en la RTX 5070 |
| 6 | **2.4** Detector propio Florence-2 | Hecho | F1 0,982 en S-reservado; aporte a D +0,011 [0,001; 0,023] |
| 7 | **2.1** VESOR y **2.5** ColQwen2/ColSmol | No empezadas | — |

## Qué se ha hecho

### 3.2 · Memoria de revisión

- El canal `memoria` de D solo se usa si `previous.approval` existe y su huella coincide con los
  datos. Usa `Revision.fingerprint()` de `model.py`, sin reimplementarla.
- Si no: evento `memory` «omitido» y aviso en español.
- El estudio pasa como `previous` la rev1 aprobada por el oráculo (`bench.estudio.reviewed_by_oracle`).
- Pruebas: `tests/test_lectura_estrategia_d.py`.

### 3.3 · Calibración (`src/trazia/calibration/`)

- **Confianza:** curva isotónica por (estrategia, canal, escaneado/vectorial), con respaldos hasta
  una curva global.
- **Intervalos:** conformal partido al 90 % para campos numéricos, por clase (°, mm, número) y
  franja de confianza.
- **Abstención:** umbral por estrategia para un riesgo objetivo del 5 %. El campo queda
  `abstained` con una explicación; el valor se conserva para la revisión.
- **Etapa `calibrate`** en `pipeline.process`, entre la reconciliación y el contrato.
  - Parámetros en `generated/calibration/calibracion.json`.
  - Otra ruta con `TRAZIA_CALIBRATION`; `off` la desactiva.
  - Sin parámetros, la etapa sale «omitido» y la confianza no cambia.
- **Ajuste:** `uv run python -m bench.calibrar`.
  - Curvas con la mitad de S-dev; cuantiles y umbrales con la otra mitad.
  - C y D usan bibliotecas RAG que excluyen al proveedor medido.
- **Resultado en S-reservado:**

  | Estrategia | ECE sin calibrar | ECE calibrado | Cobertura del intervalo | Abstención: se queda · riesgo |
  | --- | --- | --- | --- | --- |
  | B | 0,191 | 0,035 | 100 % | 85,5 % · 0 % |
  | C | 0,023 | 0,210 | 77,0 % | 24,3 % · 0 % |
  | D | 0,126 | 0,270 | 94,1 % | 58,4 % · 10,2 % |

- **El criterio del ROADMAP (ECE < 0,05 en S-reservado) solo se cumple con B.** En C y D la
  calibración empeora el ECE. Causa: la geometría rellena muy pocos campos en S-dev y casi 600 en
  S-reservado. Está explicado en `docs/BENCH.md` y no se ha forzado.

### 2.11 y 3.4 · Estudio

Resultados completos en `docs/ESTUDIO.md`, «Estudio 2».

- **D gana en los tres conjuntos.** McNemar frente a C y a B con p ≈ 0.
- **Todas las variantes:** alucinación 0 % y cita 100 %.
- **Ablaciones de D** (Δ puntuación):

  | Sin | Δ | IC 95 % |
  | --- | --- | --- |
  | RAG | −0,076 | [−0,113; −0,042] |
  | Geometría | −0,045 | [−0,075; −0,016] |
  | Detector propio | −0,011 | [−0,023; −0,001] |
  | Memoria | +0,009 | [−0,002; 0,020] |

- **Selector:** la regla se fija en S-dev (vectorial → B, escaneado → D) y queda por debajo de D
  solo en S-reservado. **Recomendación: D para todo.**
  - `estudio.json` publica la regla y su resultado en `recommendation.selector`.
  - Las claves `vectorial` y `escaneado` siguen con la regla de S-dev, para no cambiar la
    Interfaz 3.
- **Hipótesis:** H1 se confirma, H4 se confirma en puntuación, H5 y H6 se rechazan. H2 queda sin
  medir y H3 sin la prueba que pedía.

### 2.2 · PaddleOCR-VL

- Medido con `training/paddle_vl.py`. Descartado como lector de página.
- Cifras en `docs/PLATAFORMA.md`, «Tarea 2.2».

### 2.4 · Detector propio

- Florence-2 base ajustado con 1.410 mosaicos de S-dev: 525 s, pico de 4,9 GB.
- En 200 mosaicos de S-reservado: F1 0,982 y texto exacto 90,2 %.
- `python -m training.florence leer` deja las lecturas en `generated/cache/detector`.
- **Canal `detector` de D** (`ocr/detector.py`):
  - solo lee esa caché, así que el producto no necesita PyTorch;
  - solo actúa en PDF sin capa de texto.
- Ablación `d_hibrido-detector`.

## Cambios de interfaz

Ninguno rompe la firma de `pipeline.process`, el contrato ni la CLI del estudio.

- **Contrato 0.3 relleno:** `assemble` emite `schema_version "0.3"`. Cada campo lleva:
  - `state`: `candidate` o `abstained`;
  - `interval`, `alternatives` y `explanation`;
  - en `source`: `confidence_raw`, `channel`, `strategy`, `model` y `grounded`.
- `extraction.Candidate` tiene un campo nuevo, `state`.
- **Etapas:**
  - `calibrate`: «ok» u «omitido»;
  - `extract_detector`: «ok» u «omitido»;
  - `memory`: «omitido» si la revisión anterior no está aprobada.
- **Canal `detector`** en D y variante `d_hibrido-detector` en el registro de estrategias.
- **`estudio.json`:** claves nuevas `calibration` (`fitted_on` y `sha256`) y
  `recommendation.selector`.
- **Extra `train`** en `pyproject.toml`: torch, transformers 5, accelerate, sentencepiece y
  protobuf. Licencias en `THIRD_PARTY.md`.
- **Nuevos módulos:**
  - CLI `python -m bench.calibrar`;
  - `training.florence leer`;
  - `training.paddle_vl`.

## Lo que necesito de Plataforma

- **Clave de la caché de trabajos.** Debe incluir el sha256 de la calibración en uso: el mismo
  documento cambia de confianza, intervalo y abstención al reajustarla. Se obtiene con
  `trazia.calibration.load_calibration().sha256`, o `None` si no hay.
- **Comprobar que la revisión muestra `abstained` como estado propio** («confírmelo»), no como un
  campo normal. Los tipos de la web ya lo conocen; ahora llega relleno de verdad, con el motivo en
  `explanation`.

- **`test_success_without_report_is_an_explicit_error` depende del disco.** Falla en una copia
  local con un `generated/estudio/estudio.json` válido (fuera de Git): `GET /estudio` devuelve ese
  informe en vez de `empty`. En una copia limpia pasa. Basta con que la prueba apunte la raíz del
  repositorio a `tmp_path`.

## Límites y pendientes

- **Fusión aprendida (3.4):** la regresión logística por campo no está hecha. D sigue con la fusión
  heurística, ahora con un canal verificable como representante del grupo.
- **Calibración de C y D en proveedores no vistos.** Falla el ECE; la cobertura de los intervalos
  sí aguanta. Se podría arreglar con más variedad de proveedores en S-dev o recalibrando con las
  correcciones humanas (3.8) cuando haya.
- **A (visión) sin medir** en el estudio, por coste de GPU (unos 129 s por página).
- **2.1 y 2.5** no empezadas.
- **S-reservado se ha abierto más de una vez:** ver la nota del final de «Estudio 2».
- **Lectura de `correcciones.jsonl` (3.8)** para recalibrar: pendiente.
