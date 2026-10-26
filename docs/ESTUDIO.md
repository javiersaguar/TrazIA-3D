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
| `d_hibrido` | D completo con el selector |
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
