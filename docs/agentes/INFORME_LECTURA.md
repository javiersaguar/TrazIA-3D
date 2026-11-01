# Informe del agente Lectura · sesión del 30/10/2026

Cierre de la sesión de [SESION_LECTURA.md](SESION_LECTURA.md). Rama `feat/lectura`. Todo lo
medido usa **datos sintéticos**: ninguna cifra es precisión sobre planos de TR.

## Resumen

| # | Tarea | Estado | Cifra principal |
| --- | --- | --- | --- |
| 1 | **3.2** Memoria solo con revisión aprobada | Hecha | D omite la memoria (con aviso) si la anterior es DRAFT o su huella no cuadra |
| 2 | **3.3** Calibración, intervalos conformes y abstención | Hecha; D cumple la ECE desde la v6 (1/11) | Estudio 7: ECE de D 0,027 en S-reservado (antes 0,279) y cobertura del intervalo al 90 % del 91,4 % |
| 3 | **2.11** Estudio A/B/C/D | Hecho sin A | D 0,642 [0,607; 0,678], C 0,558, B 0,536 |
| 4 | **3.4** Selector y ablaciones | Hecho; sin fusión aprendida | El selector por tipo pierde en S-reservado (0,372 frente a 0,525 de D solo) |
| 5 | **2.2 / 0.10** PaddleOCR-VL | Medido y descartado | No acaba una página A3 en 25 min en la RTX 5070 |
| 6 | **2.4** Detector propio Florence-2 | Hecho | F1 0,982 en S-reservado; aporte a D +0,011 [0,001; 0,023] |
| 7 | **2.1** VESOR y **2.5** ColQwen2/ColSmol | Hechas el 1/11 (ver «Sesión del 1/11/2026») | B lee el VESOR completo; ColQwen2 baja C de 0,600 a 0,562 y queda apagado |

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
- **2.1 y 2.5** hechas el 1/11: ver «Sesión del 1/11/2026».
- **S-reservado se ha abierto más de una vez:** ver la nota del final de «Estudio 2».
- **Lectura de `correcciones.jsonl` (3.8)** para recalibrar: pendiente.

## Sesión del 31/10/2026

Rama `feat/lectura`, rehecha desde `main` (a4dd9a7). Todo sobre **datos sintéticos**.

### E.7 · Intervalo y abstención en la revisión

- La cola de revisión (`web/src/features/review/field-queue.tsx`) muestra el intervalo conforme de
  cada campo pendiente, por ejemplo «± 0,5° · 90 %».
- Un campo `abstained` lleva la marca «Confírmelo» en lugar de la barra de confianza. Su
  explicación sale al seleccionarlo.
- La cola pone lo abstenido primero. La aprobación ya estaba bloqueada mientras queden campos sin
  revisar.
- La barra de confianza dice si la confianza está calibrada.
- **Comprobado** con la API del worktree y D sobre la demo V-101 en `localhost:3125/revision`.
- **Pruebas:** `web/src/lib/mock/fields.test.ts`.
- **La demo sin conexión no cambia:** sus JSON de `web/public/demo` no traen intervalos.

### 3.3 · Calibración (revisión)

- **Fallo corregido.** En la API, D devolvía «2.000 mm, de −770.001 a 774.001 mm» como candidato
  normal.
- **Ahora:**
  - un intervalo que no informa (más del 5 % del valor o 5°) no se da y el campo se abstiene;
  - curva sí o no por estrategia, eligiendo dejando fuera un proveedor de S-dev: C va sin curva;
  - cuantiles conformes por estrategia.
- **Cifras:** en `docs/BENCH.md`, «Revisión del 31/10/2026».
- **Objetivo cumplido por:**
  - B: ECE y cobertura;
  - C: solo ECE (0,023);
  - D con fusión aprendida: solo cobertura (96,4 %), con una ECE de 0,072 (antes 0,270).

### 3.4 · Fusión aprendida

- **Código:** `trazia/strategies/fusion.py` (señales y modelo en JSON, sin pickle) y
  `bench/fusion.py` (ajuste).
- **Variante del estudio:** `d_hibrido+fusion`. Sin `generated/fusion/fusion.json` usa la
  heurística y lo avisa.
- **Validación** dejando fuera un proveedor de S-dev:

  | | Elección acertada | ECE |
  | --- | ---: | ---: |
  | Aprendida | 93,2 % | 0,023 |
  | Heurística | 92,5 % | 0,068 |

### 2.11 y G.8 · Estudio 3

Resultados en `docs/ESTUDIO.md`, «Estudio 3». Puntuación GA2MODEL con IC 95 %:

| Variante | Puntuación | IC 95 % | Comentario |
| --- | ---: | --- | --- |
| D con fusión aprendida | 0,670 | [0,638; 0,702] | 0,570 en S-reservado |
| D | 0,640 | | 0,524 en S-reservado |
| C | 0,567 | | |
| B | 0,536 | | |
| A sin modelo | 0,488 | | |
| A con detector | 0,489 | | 4 % sin anclar: no elegible |

- **A con Qwen3-VL local** (subconjunto de 6 equipos): 0,445 frente a 0,543 de A sin modelo, con un
  7,3 % de alucinación y 172 s por revisión.
- **Recomendación:** `d_hibrido+fusion` para todo.

### 2.4 · `a_detector`

- A usa el detector propio como lector en escaneados (desde su caché).
- Entra en el estudio como variante.

### Lo que necesito de Plataforma (31/10)

- **Clave de la caché de trabajos.** Además del sha256 de la calibración, debe incluir el de la
  fusión aprendida: `trazia.strategies.fusion.load_fusion().sha256`, o `None` si no hay. Ahora es
  más urgente: D usa la fusión aprendida por defecto, y si se reentrena, la caché serviría
  resultados del modelo anterior.
- **`.env.example`.** Añadir, vacías, las claves nuevas de visión: `GROQ_API_KEY`,
  `OPENROUTER_API_KEY`, `NVIDIA_API_KEY`, `CLOUDFLARE_API_TOKEN` y `CLOUDFLARE_ACCOUNT_ID`.
- **Calibración en un clon limpio.** Sigue en `generated/calibration/`, fuera de Git. La v5 es la
  que corresponde a D con fusión aprendida (sha256 `dd2f98c238da…`).

### D con fusión aprendida por defecto (31/10, tarde)

- Decidido con el estudio 3: la fusión aprendida gana a la heurística en puntuación (0,670 frente
  a 0,640), ECE (0,072 frente a 0,270) y tiempo (1,8 s frente a 3,2 s por revisión), con McNemar
  p ≈ 10⁻⁷ (86 campos que solo acierta la aprendida, 29 que solo acierta la heurística).
- `HybridStrategy` usa `fusion="aprendida"` por defecto. El modelo va versionado en
  `src/trazia/strategies/fusion_model.json`: 1,7 KB de coeficientes, sin datos. `bench.fusion
  --publicar` lo sustituye. `TRAZIA_FUSION=off` vuelve a la heurística.
- La heurística sigue en el estudio como `d_hibrido+heuristica`. Los informes de los estudios 1 a
  3 usan los nombres de antes: allí `d_hibrido` es la heurística y `d_hibrido+fusion` la aprendida.
- Calibración v5: D sin curva isotónica e intervalos recalculados. En S-reservado, ECE 0,066 y
  cobertura del intervalo 91,5 %; con abstención se queda el 69 % de los campos con un riesgo del
  8,3 %. Medida en el estudio 5 de `docs/ESTUDIO.md`.
- Estudio 6, sobre `main` `b3c3ebf` (fusión aprendida + PR de Alejandro): D 0,703 [0,671; 0,736],
  ECE 0,036, F1 de cambios 56,0 %, 82,3 % de modelos y 0,614 en S-reservado. La heurística queda en
  0,691 (McNemar 78/25, p ≈ 2·10⁻⁷). Son las cifras de D que hay que citar a partir de ahora;
  `generated/estudio/` ya las tiene (el estudio 5 queda en `generated/estudio-5/`).

### Proveedores de visión (31/10, tarde)

- `OpenAICompatibleProvider` para Groq, OpenRouter, NVIDIA NIM y Cloudflare Workers AI
  (`groq:<modelo>`, `openrouter:<modelo>`, `nvidia:<modelo>`, `cloudflare:<modelo>`). Pide JSON por
  esquema y, si el modelo no lo admite, pasa a JSON libre con el esquema en el prompt. Reintenta
  ante 429 y 503. Coste 0 € por defecto (cuotas gratuitas); configurable por servicio.
- Las peticiones llevan un agente de usuario propio: Groq rechaza con 403 el de urllib.
- Una tesela sintética de 1280 px por modelo:
  - responden con JSON válido `gemini-3.5-flash-lite` (5 s), Groq `qwen/qwen3.8-27b` (3 s),
    OpenRouter `nvidia/nemotron-3.5-super-vl:free` (17 s), NVIDIA
    `nemotron-3.5-super-vl-120b-a12b` (52 s) y `llama-3.2-90b-vision-instruct` (185 s), y
    Cloudflare `@cf/qwen/qwen3.8-27b` (51 s);
  - fallan `gemini-3.8-flash` y `gemini-3.1-flash-lite` (503, saturados), Gemma 4 en OpenRouter
    (429), Llama 4 Scout en Cloudflare (JSON roto) y Moondream (otro formato de entrada).
- `python -m bench.proveedores` mide cada modelo como lector de A junto a Qwen3-VL local y A sin
  visión, y cuenta las teselas fallidas por cuota: un modelo con fallos no está medido del todo.
- **Fallo encontrado y corregido en el adaptador de Gemini** (anterior a esta sesión): Gemini da
  las cajas como `[y1, x1, y2, x2]` aunque se le pidan en `[x1, y1, x2, y2]`. Comparado con otros
  cinco modelos sobre la misma tesela. Cada texto quedaba en otro sitio del plano y de ahí salía
  un 50 % de alucinación. El adaptador las gira y no reutiliza las respuestas guardadas antes.

**Primera ronda** (4 revisiones escaneadas: 1 equipo de S-dev y 1 de S-reservado, escaneado
limpio, rev1 y rev2; calibración v5; `generated/proveedores-r1b/`). **Datos sintéticos.**

| Lector de A | Puntuación | Alucinación | s/rev | Teselas fallidas |
| --- | ---: | ---: | ---: | ---: |
| OpenRouter `nvidia/nemotron-3.5-super-vl:free` | 0,363 | 9,7 % | 32 | 0 |
| NVIDIA `nvidia/nemotron-3.5-super-vl-120b-a12b` | 0,359 | 8,6 % | 25 | 0 |
| Gemini `gemini-3.5-flash-lite` | 0,355 | 11,4 % | 32 | 0 |
| *A sin visión (`a_geometria`)* | *0,352* | *0 %* | *3* | — |
| Cloudflare `@cf/qwen/qwen3.8-27b` | 0,334 | 6,7 % | 245 | 7 |
| *Qwen3-VL 4B local* | *0,295* | *3,5 %* | *103* | — |
| Groq `qwen/qwen3.8-27b` | 0,150 | 0 % | 169 | 2 |

- `gemini-3.8-flash` no está medido: sus 24 teselas fallaron (503 por saturación y luego 429 por
  cuota). Los segundos incluyen esperas por límite de tasa y, en las filas con caché, no son el
  tiempo real del modelo.
- **Conclusión.** Ningún modelo externo mejora a A sin visión y todos los que empatan alucinan
  muy por encima del 1 %. Con 4 revisiones los intervalos son anchos: es una indicación, no un
  resultado cerrado. No se hace la segunda ronda de 20 revisiones: las cuotas gratuitas de
  OpenRouter, Groq y Cloudflare no llegan y no hay señal de mejora que justifique gastarlas.
- **1.9:** segundo proveedor real comprobado con seis modelos sobre la misma página. Falta el de
  la plataforma IndesIA. **2.2:** Mistral sigue sin clave.

### 1.9 y 2.2 · Mistral

- **Código listo:**
  - adaptador `mistral-chat:<modelo>` para los modelos de chat con visión, con salida JSON por
    esquema, caché, coste y la misma política de solo sintéticos;
  - `python -m bench.mistral`, que lista los modelos con visión de la clave y los mide como lector
    de A en el mismo subconjunto que Qwen3-VL local.
- **Sin medir:** la cuenta de Mistral está en el plan Gratis, que ya no da acceso a la API. Hace
  falta pasar a «Pay-as-you-go» y poner `MISTRAL_API_KEY` en `.env`.

## Sesión del 1/11/2026

### 3.3 · Calibración v6: D cumple

- Filas recogidas de nuevo sobre `main` `0d4d4dc` (fusión aprendida y PR de Alejandro), en
  `generated/calibration-v6/` y promovidas a `generated/calibration/` (sha256 `5496cf49cbe4…`).
  La v5 queda en `generated/calibration-v5/`.
- Diagnóstico: en S-reservado, D da 0,79 de confianza a la medida del dibujo en vectorial y acierta
  el 95 % (589 campos). En S-dev esa medida casi no gana (36 campos, 6 % de acierto), porque las
  tablas se leen siempre. Una curva ajustada con S-dev tal cual empeora (ECE 0,28 en S-reservado).
- Arreglo, solo con S-dev: `bench.calibrar` saca la curva de D de las elecciones de su fusión con
  canales apagados (`generated/fusion/filas.json`, de `bench.fusion`), que simulan un proveedor
  cuyas tablas no se leen. Con las tablas apagadas, el dibujo acierta el 100 % en S-dev y la fusión
  le da 0,81–0,87. La curva solo se usa si baja la ECE de D en S-dev (0,018 → 0,012).
  `--fusion-filas` cambia la ruta; sin ese fichero, D vuelve a ir sin curva.
- En S-reservado:

  | Estrategia | ECE calibrada | Cobertura 90 % | Se quedan con abstención | Riesgo de lo que se queda |
  | --- | ---: | ---: | ---: | ---: |
  | B | 0,029 | 100 % | 88,0 % | 0,0 % |
  | C | 0,040 | 91,5 % | 0 % | — |
  | D | **0,036** (antes 0,068) | 91,4 % | 68,6 % | 8,5 % |

- Límites: cobertura de ángulos de D 63 %; el riesgo con abstención de D (8,5 %) sigue por encima
  del 5 % buscado; las filas de la fusión son de antes del PR de Alejandro. Miré tres variantes de
  curva en S-reservado; la elegida es también la de menor ECE en S-dev, que es la regla escrita.
- **Estudio 7** (todo el estudio con la v6, `generated/estudio/`; el 6 queda en
  `generated/estudio-6/`): D 0,708 [0,676; 0,740], ECE 0,014 (0,027 en S-reservado), 0,625 en
  S-reservado. Aciertan los mismos campos que en el estudio 6; la subida es solo de calibración.
  Son las cifras de D que hay que citar a partir de ahora. [Estudio 7](../ESTUDIO.md).
- **Para Plataforma:** la huella de calibración cambia. Hay que volver a fijarla en el contenedor
  (escala, 3.7) y la caché de trabajos la invalida sola si usa el sha de la calibración.

### A · Ingesta

- `ingest_bytes` comprueba la firma de los primeros bytes contra la extensión, rechaza un PDF con
  contraseña con su motivo, avisa de uno cifrado sin contraseña, acepta TIFF y rechaza `.xls` y
  `.xlsm` pidiendo `.xlsx`.
- `pipeline.process` convierte PNG, JPEG y TIFF (también de varias páginas) en un PDF escaneado a
  200 ppp, así que B, C y D les pasan OCR y visión. El documento conserva el nombre y el SHA-256
  del original. Un documento idéntico a otro de la misma llamada se lee una sola vez, con aviso y
  evento `ingest` «omitido».
- ROADMAP: A.7 cerrada; A.1–A.6 y G.1–G.5 anotadas con lo que hay y lo que falta.

### 2.1 · VESOR en B

- B reconoce un VESOR por el nombre (`VESOR_…`) o el id. Lee su tabla de orientación (sin exigir
  columna de elevación y sin buscar cotas verticales) y los rótulos de planta «N3 135°». Canal
  `vesor`, que la fusión de D no ha visto: en esos campos D decide con la heurística, como ya hacía
  con cualquier canal nuevo.
- Generador `synthetic/vesor.py` (fuera de los conjuntos S-*: no cambia el estudio).

### F.5 · Marcas de revisión

- `trazia.extractors.revision_marks.find_marks(pdf)` devuelve los Δ y las nubes de un PDF vectorial
  y las páginas escaneadas que no ha podido leer; `check_changes(changes, reading)` señala los
  cambios sin marca y las marcas sin cambio.
- `python -m bench.marcas`: Δ 47/47 (S-dev) y 38/38 (S-reservado) en vectorial, sin falsos. El
  91 % (S-dev) y el 65 % (S-reservado) de los cambios localizados caen junto a una marca.
- **Necesito de Plataforma:** llamar a `check_changes` desde `revisions.compare` con las lecturas
  de la revisión nueva (página y caja de cada cambio y de sus alternativas) y mostrar el resultado
  en la revisión. `families/change_detection.py` ya cuelga marcadores heurísticos de cada cambio;
  esto los sustituye en vectorial.

### 2.2 y 2.5

- 2.2 cerrada: sin Mistral (decisión del equipo), RapidOCR con comprobación de cita y el detector
  propio. PaddleOCR-VL sigue descartado con lo medido el 30/10.
- 2.5 cerrada: ColQwen2 integrado en C y medido; queda apagado porque empeora a C.
  - **Qué hay:** `src/trazia/rag/visual.py` (vectores por página con caché por sha256 y MaxSim).
    C lo usa con `TRAZIA_RAG_RETRIEVAL=colqwen2`; sin torch, sin modelo o con una biblioteca
    antigua vuelve a la huella ligera con un evento `rag · error`. La biblioteca guarda ahora el
    sha256 y la ruta de cada PDF. La confianza sale siempre de la huella del par elegido, así que
    la curva de calibración de C no cambia.
  - **Umbral:** 0,63 de MaxSim, fijado en S-dev quitando de la biblioteca el proveedor del caso
    (índice de Youden). Separa «hay caso parecido» casi igual que la huella: AUC 0,81 frente a 0,79.
  - **Resultado de C** (`bench.rag_visual`, misma biblioteca y calibración v6):

    | Recuperación | Total | S-dev | S-reservado |
    | --- | --- | ---: | ---: |
    | Huella | 0,600 [0,556; 0,644] | 0,686 | 0,454 |
    | ColQwen2 sin umbral | 0,572 [0,512; 0,629] | 0,693 | 0,321 |
    | ColQwen2, umbral 0,63 | 0,562 [0,504; 0,616] | 0,670 | 0,349 |

  - **Por qué:** ColQwen2 elige proveedores que se parecen por idioma y estilo, pero C copia
    posiciones de campos, y eso lo mide mejor la rejilla de tinta.
  - **Coste:** 0,4 s por página y 4,6 GB de VRAM en la RTX 5070, frente a 0,05 s de la huella.
  - **Instalación:** el extra `train` con torch 2.11 cu128 (`uv pip install` desde
    download.pytorch.org). Ojo: `uv sync --frozen --extra dev` lo desinstala.
  - **Pendiente:** volver a medirlo con los GA reales (R-ref).
