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
