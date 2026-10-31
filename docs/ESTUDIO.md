# Estudio comparativo de estrategias A · B · C · D

Protocolo para responder a la pág. 13 del reto («justificad vuestros trade-offs») con datos.
Decisiones de fondo en [DECISIONES.md](DECISIONES.md) (DEC-01, 02, 21 y 22).

## Pregunta

¿Qué estrategia de lectura da el mejor modelo y los mejores datos, con qué coste y con qué
incertidumbre? ¿Cómo cambia la respuesta según el tipo de documento?

## Hipótesis (se publican antes de medir)

| # | Hipótesis | Cómo se confirma o refuta |
| --- | --- | --- |
| H1 | B gana en planos vectoriales de un proveedor conocido y pierde en estilos no vistos | Acierto de B en estilos reservados frente a vistos |
| H2 | A (visión + geometría) generaliza mejor que B, pero alucina más y cuesta más | Tasa de alucinación, coste por equipo y acierto en estilos reservados |
| H3 | C solo sirve si hay un caso parecido en la biblioteca; con la exclusión de uno real cae | Acierto de C según la similitud con el caso recuperado más cercano |
| H4 | D supera a todas en la Puntuación GA2MODEL, con coste cercano a B | Comparación pareada e intervalos bootstrap |
| H5 | La memoria de la revisión anterior es el canal que más sube el F1 de cambios | Ablación de D sin memoria |
| H6 | La verificación geométrica es el canal que más baja el ECE | Ablación de D sin geometría |

## Variantes

| Id | Descripción |
| --- | --- |
| `a_vision` | A con modelo local (Qwen3-VL) |
| `a_vision@gemini` | A con Gemini (solo sintéticos) |
| `a_vision@mistral` | A con Mistral OCR + Document AI (solo sintéticos) |
| `a_detector` | A con el detector propio ajustado (Florence-2) |
| `b_reglas` | B completo (texto, tablas, cotas, cajetín, hoja de datos, VESOR) |
| `b_reglas+ocr` | B sobre líneas de OCR cuando no hay capa de texto |
| `c_rag` | C con recuperación visual y adaptación de parámetros |
| `d_hibrido` | D completo con fusión aprendida (regresión logística sobre las señales de los canales, tarea 3.4; por defecto desde el 31/10) |
| `d_hibrido+heuristica` | D con la fusión heurística de antes del 31/10. En los estudios 1 a 3, `d_hibrido` era esta variante y la aprendida se llamaba `d_hibrido+fusion` |
| `d_hibrido−geometria`, `−memoria`, `−rag`, `−vision`, `−detector` | Ablaciones de D, quitando un canal cada vez |

Todas pasan por el mismo postproceso: normalización, contrato 0.3, familia e IFC.

## Datos

| Conjunto | Contenido | Uso |
| --- | --- | --- |
| **S-dev** | Sintéticos de 6 estilos de proveedor × 3 niveles de degradación, con rev1 y rev2 | Desarrollo y entrenamiento |
| **S-reservado** | 2 estilos de proveedor nunca vistos, con los mismos niveles | **Generalización**; solo se abre para medir |
| **S-mecánico** | Bombas y compresores con bancada y boquillas de aspiración e impulsión | Nivel de detalle 1 y generalización por tipología |
| **S-adversarial** | Documentos con instrucciones incrustadas | Seguridad (DEC-32) |
| **R-ref** | Los 4 equipos de TR con IFC de referencia | Exclusión de uno: se entrena o calibra con 3 y se mide en el cuarto |
| **R-B** | Equipos de «estáticos B» con verdad manual (los que dé tiempo) | Validación real adicional |

Semillas fijas y versión del generador registradas en cada resultado.

## Métricas

- **Rúbrica:**
  - geometría (campos, mm, °, IoU, Hausdorff);
  - atributos (valor + unidad, ECE, cobertura de intervalos);
  - cambios (precisión, recall, F1, magnitud).
- **Operación:** € por equipo, segundos por revisión, segundos de GPU y llamadas a modelos.
- **Fiabilidad:**
  - tasa de alucinación (valores sin respaldo en el documento);
  - cobertura de cita;
  - curva riesgo-cobertura.
- **Puntuación GA2MODEL** (DEC-22), con dos restricciones: alucinación < 1 % y cita = 100 %.

## Estadística

- Comparación **pareada** sobre los mismos documentos.
- Intervalos **bootstrap del 95 %** por métrica (1.000 remuestreos por equipo).
- **McNemar** para el acierto por campo entre la estrategia ganadora y la segunda.
- Se informa de todo, también de lo que no sale bien. Nada de elegir la semilla que conviene.

## Salidas

- `generated/estudio/estudio.json` y `estudio.md` (tablas, intervalos y Pareto).
- Pantalla **Estudio** en la web (DEC-28).
- Diapositiva «Elegimos con datos» del pitch.
- Recomendación del selector: estrategia por tipo de documento.

## Calendario

| Fecha | Hito |
| --- | --- |
| 4 nov | Interfaz `Strategy`, generador v2 (estilos + reservados) y arnés del estudio con B |
| 14 nov | A, C y D v1; primer estudio en S-dev |
| 21 nov | Estudio completo con S-reservado, ablaciones y estadística; selector elegido |
| 25 nov (día 1) | Estudio sobre R-ref con exclusión de uno; ajuste del selector con datos reales |
| 26 nov | Cifras finales para el pitch |

## Cómo se ejecuta

```bash
uv run python -m synthetic --conjunto todos     # S-dev, S-reservado, S-mecánico, S-adversarial
uv run python -m bench.estudio                  # generated/estudio/estudio.json y estudio.md
```

Cada variante pasa por `trazia.pipeline.process`, el mismo camino que el producto; la rev2 recibe
la rev1 como `previous`. Definiciones operativas de cada métrica: cabecera de `bench/estudio.py`.

- **Geometría** = campos geométricos correctos (±1 mm, ±0,5°) × min(1, IoU/0,95) del IFC. Si la
  revisión no llega a IFC, vale 0: sin modelo no se entrega geometría. La fracción sin penalizar
  se publica al lado.
- **Alucinación** = valores emitidos cuya región citada no contiene el número o el texto
  (`bench/support.py`, con tolerancia de formato). Un error de unidad sobre un número que sí está
  en la cita cuenta como error, no como alucinación.
- **Escala** = 1 − (0,5·min(1, s/60) + 0,5·min(1, €/0,50)). **Innovación** = 1 para todas: no
  cambia el orden. Por eso una variante que no lee nada puntúa 0,20, no 0.
- La puntuación principal se calcula sobre S-dev + S-reservado. S-adversarial se informa aparte
  (tasa de envenenamiento) y S-mecánico queda sin medir hasta que el contrato tenga envolvente.

## Resultados

### Estudio 1 · solo B y sus ablaciones (26/10/2026)

Generador v2, conjuntos con las semillas de la tabla de `docs/BENCH.md`, 1.000 remuestreos por
equipo. 120 equipos-degradación puntuables (240 revisiones). **Datos sintéticos.**

| Variante | Puntuación | IC 95 % | Geometría | Atributos | ECE | F1 cambios | Alucinación | Cita |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `b_reglas` | 0,370 | [0,335; 0,408] | 3,3 % | 70,2 % | 0,191 | 8,0 % | 0,0 % | 100 % |
| `b_reglas-tablas` | 0,327 | [0,311; 0,342] | 0,0 % | 67,5 % | 0,250 | 0,0 % | 0,0 % | 100 % |
| `b_reglas-hdm` | 0,255 | [0,224; 0,293] | 3,3 % | 12,5 % | 0,125 | 8,0 % | 0,0 % | 100 % |

| Ablación | Δ puntuación | IC 95 % |
| --- | --- | --- |
| B sin tablas ni cotas | −0,043 | [−0,076; −0,016] |
| B sin hoja de datos | −0,115 | [−0,130; −0,099] |

Lo que dice, a favor y en contra:

- **H1 se confirma en su primera mitad, y con fuerza.** B solo construye modelo en el proveedor
  `atlas` en vectorial (el estilo para el que se escribió): 5,6 % de modelos en S-dev, 0 % en
  S-reservado. En escaneados no lee geometría (no hay capa de texto).
- **Los atributos dependen de la hoja de datos**, no del plano: sin ella B cae del 70 % al 12,5 %.
  Con proveedores en psig/°F/lb o en español, B no lee los datos de diseño del plano.
- **Alucinación 0 % y cita 100 %**: B nunca inventa; cuando falla, falta el dato. Es la base que
  las estrategias con modelos tienen que igualar.
- **ECE 0,19**: las confianzas fijas de B no están calibradas (tarea de DEC-12).
- **Adversarial**: 2,8 % de envenenamiento. B no obedece instrucciones, pero sí lee el texto en
  blanco sobre blanco de la capa de texto cuando cae en una fila de «datos de diseño». La
  comprobación visual de D (DEC-10) tiene que cerrar este hueco.
- McNemar: B completo acierta 374 campos más que sin tablas (p < 10⁻⁶) y 554 más que sin hoja de
  datos (p < 10⁻⁶), de 7.452 campos pareados.

### Estudio 2 · B, C, D, ablaciones y selector (30/10/2026)

Generador v2, S-dev (24 casos, semilla 2026), S-reservado (16, semilla 7919) y S-adversarial (12,
semilla 6666), con 3 degradaciones y rev1 + rev2: 132 equipos-degradación y 264 revisiones por
variante. 1.000 remuestreos por equipo. La rev2 recibe como `previous` la rev1 aprobada por el
oráculo (la memoria solo usa revisiones aprobadas, tarea 3.2). Calibración ajustada solo en S-dev,
sha256 `a8e2977b7a5c…`. **Datos sintéticos.**

| Variante | Puntuación | IC 95 % | Geometría | Atributos | ECE | F1 cambios | Cobertura 90 % | Alucinación | Cita | s/revisión |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `d_hibrido` | **0,642** | [0,607; 0,678] | 42,4 % | 90,3 % | 0,101 | 45,9 % | 96,5 % | 0,0 % | 100 % | 1,55 |
| `c_rag` | 0,558 | [0,502; 0,611] | 28,2 % | 82,6 % | 0,132 | 40,1 % | 92,0 % | 0,0 % | 100 % | 0,30 |
| `b_reglas` | 0,536 | [0,493; 0,579] | 19,9 % | 80,8 % | 0,007 | 32,8 % | 100 % | 0,0 % | 100 % | 0,03 |
| `b_reglas-hdm` | 0,393 | [0,349; 0,435] | 19,9 % | 23,3 % | 0,009 | 32,8 % | 100 % | 0,0 % | 100 % | 0,02 |
| `b_reglas-tablas` | 0,388 | [0,356; 0,419] | 0,0 % | 75,0 % | 0,000 | 0,0 % | 100 % | 0,0 % | 100 % | 0,02 |

Por conjunto (puntuación):

| Variante | S-dev | S-reservado | S-adversarial | Envenenamiento |
| --- | --- | --- | --- | --- |
| `d_hibrido` | 0,717 | **0,525** | 0,942 | 13,9 % |
| `c_rag` | 0,671 | 0,350 | 0,758 | 13,9 % |
| `b_reglas` | 0,625 | 0,386 | 0,904 | 30,6 % |

D por degradación: vectorial 0,893 · escaneado limpio 0,556 · escaneado pobre 0,418.

| Ablación de D | Δ puntuación | IC 95 % | Lectura |
| --- | --- | --- | --- |
| sin RAG | −0,076 | [−0,113; −0,042] | El canal que más aporta |
| sin geometría | −0,045 | [−0,075; −0,016] | Aporta; sin él D no construye ningún modelo en S-reservado |
| sin detector propio | −0,011 | [−0,023; −0,001] | Aporta poco, pero el intervalo no cruza 0 |
| sin memoria | +0,009 | [−0,002; 0,020] | Sin efecto medible |

McNemar sobre 7.452 campos pareados: D acierta 1.206 campos que C falla y C 79 que D falla
(p < 10⁻²⁵⁰); frente a B, 3.039 contra 25 (p ≈ 0). C supera a B: 1.949 contra 62 (p ≈ 0).

**Selector por tipo de documento.** La regla se fija en S-dev: vectorial → `b_reglas` (0,998 en
S-dev), escaneado limpio y pobre → `d_hibrido`. En S-reservado esa regla puntúa **0,372**, frente a
**0,525** de D solo. B resuelve el vectorial de los 6 proveedores vistos y ninguno de los 2 no
vistos (0 % de modelos en S-reservado). **Decisión: D para todos los tipos de documento.** El
selector por tipo sobreajusta a los proveedores de desarrollo. `estudio.json` publica la regla de
S-dev y su resultado en S-reservado (`recommendation.selector`).

Hipótesis:

- **H1 · se confirma.** B pasa de 0,625 en S-dev a 0,386 en S-reservado, con 0 % de modelos IFC en
  los proveedores no vistos. En S-dev vectorial puntúa 0,998.
- **H2 · sin medir.** A (visión) no entra en este estudio: con Qwen3-VL 4B a unos 129 s por página
  (tabla 0.10 de `docs/PLATAFORMA.md`), las 264 revisiones no caben en la sesión. Queda pendiente
  un subconjunto declarado como tal.
- **H3 · compatible, sin la prueba que pedía.** C cae de 0,671 en S-dev a 0,350 en S-reservado, con
  bibliotecas que excluyen al proveedor medido. No se ha medido el acierto frente a la similitud
  con el caso recuperado.
- **H4 · se confirma en puntuación, no en coste.** D es la mejor variante en los tres conjuntos y
  la diferencia es significativa. Coste 0 € para todas (todo local), pero D tarda 1,55 s por
  revisión frente a 0,03 s de B: 55 veces más, aunque muy lejos del límite de 60 s de la escala.
- **H5 · se rechaza.** Quitar la memoria no baja la puntuación ni el F1 de cambios (45,9 % con
  memoria, 51,3 % sin ella). Con la memoria limitada a revisiones aprobadas (3.2) el canal ya no
  aporta en estos datos.
- **H6 · se rechaza.** Sin geometría el ECE baja (0,101 → 0,041), no sube. La geometría sube la
  puntuación, pero sus campos en S-reservado no se parecen a los de S-dev (en S-dev rellena 37
  campos vectoriales; en S-reservado 593, con el 95 % de aciertos) y la curva de calibración
  ajustada en S-dev los infravalora. Detalle en `docs/BENCH.md`.

Más cosas que salen:

- **Alucinación 0 % y cita 100 % en todas las variantes**, también en D y C con canales de
  modelo: la etapa de anclaje descarta lo que no se puede verificar en el documento.
- **Envenenamiento: B sube del 2,8 % (estudio 1) al 30,6 %.** Ahora B lee más campos en
  S-adversarial (74 % de geometría) y con ellos más trampas. D lo baja al 13,9 % y D sin geometría
  vuelve al 30,6 %: la comprobación geométrica es la que frena parte de las trampas. No hay
  desglose por tipo de trampa en esta salida.
- **Calibración.** El ECE de D en S-dev es 0,017, pero en S-reservado 0,279. La cobertura del
  intervalo al 90 % sí se mantiene: 94,1 % en S-reservado. Detalle y curva riesgo-cobertura en
  `docs/BENCH.md`.
- **S-reservado se ha abierto más de una vez** en esta sesión, y dos cambios vienen de mirarlo:
  1. Tras la primera calibración (ECE de D 0,356 en S-reservado) se añadieron las bibliotecas que
     excluyen al proveedor y la distinción escaneado/vectorial.
  2. El primer estudio dio «sin detector» +0,020: la fusión elegía como representante una lectura
     del detector que luego no pasaba el anclaje. Se corrigió la fusión (prefiere un canal
     verificable) y se repitió el estudio.

  Las dos correcciones son de diseño, no de parámetros: todo lo que se ajusta (curvas, cuantiles y
  umbrales) sigue saliendo solo de S-dev. Aun así, las cifras de S-reservado de este estudio ya no
  son una medida a ciegas.

### Estudio 3 · A, fusión aprendida y calibración revisada (31/10/2026)

**Datos.**

- Mismos conjuntos, degradaciones, oráculo y remuestreos que el estudio 2. **Datos sintéticos.**
- Calibración nueva, ajustada solo en S-dev (sha256 `f7b78a0f73a1…`). Cambios en `docs/BENCH.md`,
  «Revisión del 31/10/2026»:
  - C sin curva;
  - intervalo que no informa → abstención;
  - cuantiles por estrategia.
- Fusión aprendida ajustada en S-dev con `python -m bench.fusion`.

| Variante | Puntuación | IC 95 % | Geometría | Atributos | ECE | F1 cambios | Cobertura 90 % | Alucinación | s/revisión |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `d_hibrido+fusion` | **0,670** | [0,638; 0,702] | 44,0 % | 92,5 % | **0,039** | 47,5 % | 98,4 % | 0,0 % | 1,84 |
| `d_hibrido` | 0,640 | [0,606; 0,677] | 42,4 % | 90,3 % | 0,101 | 45,9 % | 97,8 % | 0,0 % | 3,23 |
| `c_rag` | 0,567 | [0,516; 0,618] | 28,2 % | 82,6 % | 0,088 | 40,1 % | 77,7 % | 0,0 % | 0,40 |
| `b_reglas` | 0,536 | [0,493; 0,579] | 19,9 % | 80,8 % | 0,007 | 32,8 % | 100 % | 0,0 % | 0,04 |
| `a_detector` | 0,489 | [0,448; 0,533] | 19,5 % | 75,0 % | 0,139 | 30,4 % | 93,5 % | **4,0 %** | 1,52 |
| `a_geometria` | 0,488 | [0,446; 0,531] | 19,2 % | 75,0 % | 0,139 | 30,4 % | 93,7 % | 0,0 % | 1,81 |

- **Tiempos.** El estudio corrió a la vez que A con visión en la GPU: los segundos por revisión
  son más altos que en el estudio 2 (D: 3,23 s frente a 1,55 s) y no se comparan entre estudios.
- **Ablaciones de D.** Iguales al estudio 2 dentro del intervalo:

  | Canal quitado | Δ |
  | --- | ---: |
  | RAG | −0,075 |
  | Geometría | −0,043 |
  | Detector | −0,010 |
  | Memoria | +0,010 |

Por conjunto (puntuación):

| Variante | S-dev | S-reservado | S-adversarial | Envenenamiento |
| --- | --- | --- | --- | --- |
| `d_hibrido+fusion` | 0,732 | **0,570** | 0,940 | 13,9 % |
| `d_hibrido` | 0,715 | 0,524 | 0,942 | 13,9 % |
| `c_rag` | 0,672 | 0,386 | 0,757 | 13,9 % |
| `b_reglas` | 0,625 | 0,386 | 0,904 | 30,6 % |
| `a_geometria` | 0,564 | 0,361 | 0,710 | 0,0 % |

Por degradación:

| Variante | Vectorial | Escaneado limpio | Escaneado pobre |
| --- | ---: | ---: | ---: |
| `d_hibrido+fusion` | 0,919 | 0,600 | 0,432 |
| `d_hibrido` | 0,892 | 0,553 | 0,416 |

**Fusión aprendida frente a heurística.**

- **Campos pareados.** McNemar sobre 7.452 campos: la aprendida acierta 86 que la heurística falla,
  y la heurística 29 que la aprendida falla (p ≈ 10⁻⁷).
- **Puntuación.** Sube en S-dev y en S-reservado. En S-adversarial queda igual (0,940 frente a
  0,942).
- **Calibración.** Es la única variante de D con ECE por debajo de 0,05 en el conjunto puntuado
  (S-dev + S-reservado). Solo en S-reservado da 0,072 (`docs/BENCH.md`).
- **Recomendación: `d_hibrido+fusion` para todo.**
- **Selector.** Fijado en S-dev, sigue perdiendo: 0,386 en S-reservado frente a 0,570 de la
  variante sola.

**A sin modelo de visión.** Conjunto completo.

- **Puntuación.** `a_geometria` (trazos + capa de texto u OCR) puntúa 0,488. En S-reservado queda
  por debajo de B (0,361 frente a 0,386).
- **Detector propio.** Como lector de A no cambia nada: `a_detector` 0,489 frente a 0,488, McNemar
  p = 0,60. Además mete un 4,0 % de valores que no se pueden anclar, así que no es elegible.
- **Lo que aporta A sin modelo.** No aporta como estrategia sola. En D sí aporta como canal de
  geometría (−0,043 sin él).

**A con Qwen3-VL local.** Subconjunto declarado: 2 equipos por conjunto, vectorial y escaneado
limpio, 10 condiciones, 6 equipos. Salida en `generated/estudio-avision/`.

| Variante (subconjunto) | Puntuación | IC 95 % | Alucinación | s/revisión |
| --- | --- | --- | --- | --- |
| `a_geometria` | **0,543** | [0,403; 0,688] | 0,0 % | 1,3 |
| `a_vision` (Qwen3-VL 4B) | 0,445 | [0,355; 0,512] | 7,3 % | 172 |

- **McNemar.** Sobre los mismos campos: 91 frente a 21, p ≈ 10⁻¹¹.
- **Por conjunto.** El modelo de visión como lector empeora A en S-dev (0,512) y en S-reservado
  (0,355).
- **Alucinación.** Mete un 7,3 % de valores que no se pueden anclar.
- **Tiempo.** Tarda 130 veces más.
- **Mistral y Gemini.** Pendientes de clave: `python -m bench.mistral` mide los modelos de Mistral
  en este mismo subconjunto.

**Hipótesis (actualización).**

- **H2 · se rechaza en lo que pedía.** A no generaliza mejor que B: en S-reservado `a_geometria`
  saca 0,361 y B 0,386. Con lector de visión, A alucina más (7,3 %) y cuesta 130 veces más tiempo.
  Lo segundo sí se confirma.
- **H4 · se confirma con la fusión aprendida.** D con fusión aprendida es la mejor variante en
  S-dev y en S-reservado. La diferencia con la heurística es significativa.
- **H1, H3, H5 y H6.** Sin cambios frente al estudio 2.

**S-reservado se ha vuelto a abrir para este estudio.**

- **Las tres decisiones nuevas se tomaron solo con S-dev:**
  - la fusión aprendida;
  - la curva sí o no por estrategia;
  - el umbral del intervalo informativo.

  Las dos primeras se eligieron dejando fuera un proveedor de S-dev cada vez. El umbral salió de un
  fallo visto en la demo V-101.
- **Excepción.** Los canales apagados al entrenar la fusión responden al diagnóstico del 30/10, que
  salió de S-reservado.

### Estudio 5 · D con fusión aprendida por defecto (31/10/2026, tarde)

**Datos.** Mismos conjuntos, degradaciones, oráculo y remuestreos que el estudio 3, sobre `main`
`e46573d` (sin las correcciones del estudio 4). **Datos sintéticos.** Cambian dos cosas:

- `d_hibrido` es ya D con fusión aprendida (el modelo versionado en
  `src/trazia/strategies/fusion_model.json`, el mismo del estudio 3). La heurística pasa a
  `d_hibrido+heuristica`. Las ablaciones de D usan ahora la fusión aprendida.
- Calibración v5 (sha256 `dd2f98c238da…`): D sin curva isotónica. Las curvas generales, que usan
  las variantes sin curva propia (A, por ejemplo), ya no incluyen las lecturas de D. Por eso A y B
  no puntúan igual que en el estudio 3: se comparan solo dentro de este estudio.

Puntuación GA2MODEL sobre el conjunto puntuado (S-dev + S-reservado):

| Variante | Puntuación | IC95 | ECE | Cobertura del intervalo | S-reservado | s/rev |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| `d_hibrido` | **0,670** | [0,639; 0,703] | **0,038** | 96,9 % | **0,571** | 1,9 |
| `d_hibrido+heuristica` | 0,653 | [0,621; 0,686] | 0,058 | 93,7 % | 0,567 | 1,9 |
| `b_reglas+ocr` | 0,588 | [0,535; 0,642] | 0,038 | 98,7 % | 0,380 | 0,4 |
| `c_rag` | 0,567 | [0,516; 0,618] | 0,088 | 77,7 % | 0,386 | 0,4 |
| `a_geometria` | 0,563 | [0,528; 0,595] | 0,116 | 95,3 % | 0,551 | 1,5 |
| `b_reglas` | 0,536 | [0,494; 0,579] | 0,007 | 100 % | 0,386 | 0,03 |

- **Fusión aprendida frente a heurística.** McNemar sobre 7.452 campos: 83 que solo acierta la
  aprendida y 28 que solo acierta la heurística (p ≈ 2·10⁻⁷). Δ de puntuación −0,018 al volver a
  la heurística, IC95 [−0,032; −0,005].
- **Ablaciones de D con la fusión aprendida** (Δ de puntuación al quitar el canal, IC95):

  | Canal quitado | Δ | IC95 | Campos que solo acierta D / solo la ablación |
  | --- | ---: | --- | --- |
  | Geometría | −0,077 | [−0,109; −0,045] | 675 / 8 |
  | RAG | −0,017 | [−0,029; −0,007] | 259 / 3 |
  | Memoria | +0,002 | [−0,012; +0,016] | 23 / 0 |
  | Detector | +0,001 | [−0,018; +0,016] | 166 / 43 |

  Con la fusión aprendida, el RAG pesa menos que con la heurística (−0,017 frente a −0,075): la
  fusión aprende cuándo fiarse de las tablas y del dibujo sin él. Memoria y detector aciertan
  campos (23 y 166 que solo acierta D), pero su efecto en la puntuación no se distingue de cero.
- **Recomendación** (S-dev): `b_reglas` en vectorial y `d_hibrido` en escaneado. El selector
  fijado en S-dev sigue perdiendo en S-reservado: 0,388 frente a 0,571 de `d_hibrido` solo.
