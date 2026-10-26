# Decisiones técnicas razonadas

Análisis punto por punto del [roadmap](ROADMAP.md). En cada punto se comparan las opciones reales y
se elige una. El criterio es **ganar el reto con un proyecto que se pueda defender con datos**; si hay
duda, se prefiere la opción más ambiciosa que suba el techo, aunque cueste más horas.

Cada decisión responde a cinco preguntas:

1. Cuánto suma en la rúbrica: 35 % geometría, 25 % atributos, 20 % cambios, 10 % escala y 10 %
   innovación.
2. Si se puede **demostrar con números**, porque TR pide justificar los trade-offs (pág. 13).
3. Si aguanta planos reales que todavía no hemos visto.
4. Si es legal y ético: licencias compatibles con MIT y confidencialidad del dataset.
5. Si cabe en el calendario, contando con dos agentes y cuatro personas.

> Investigación consultada el 26/10/2026, con fuentes al final. Precios y modelos cambian: se
> vuelven a comprobar la semana del evento.

---

## Resumen de las decisiones

| # | Tema | Decisión |
| --- | --- | --- |
| DEC-01 | Enfoque (pág. 13) | **Desarrollar las cuatro estrategias (A, B, C, D) y elegir por datos** con un estudio comparativo |
| DEC-02 | Qué es cada estrategia | Definición operativa cerrada para que la comparación sea justa |
| DEC-03 | Proveedores de visión | Matriz: modelo local, plataforma IndesIA, Gemini, Mistral OCR. **Datos de TR solo en local o plataforma**, salvo autorización escrita |
| DEC-04 | Modelo local en 8 GB | Qwen3-VL 4B (8B cuantizado si cabe) con Ollama; Florence-2 con `transformers` |
| DEC-05 | Detector propio | **Florence-2 ajustado con planos sintéticos** (MIT), con aleatorización de dominio y unas 20 páginas reales etiquetadas el día 1 |
| DEC-06 | OCR | RapidOCR por defecto, PaddleOCR-VL de calidad y Mistral OCR solo con sintéticos. Gana el que diga el estudio |
| DEC-07 | Geometría desde vistas | Trazos vectoriales con `pdfplumber` (no PyMuPDF, que es AGPL) y OpenCV para raster |
| DEC-08 | RAG | Recuperación visual (ColQwen2/ColSmol) + texto, más **memoria de la revisión anterior** |
| DEC-09 | Híbrido | Cascada barata → cara, verificación cruzada entre canales y fusión aprendida |
| DEC-10 | Anti-alucinación | Comprobación de cita en todos los valores de modelos; sin cita no hay valor |
| DEC-11 | Reconciliación | Búsqueda exacta de lecturas + mínimos cuadrados ponderados con restricciones de ingeniería |
| DEC-12 | Incertidumbre | Calibración isotónica + **intervalos conformes** + abstención con curva riesgo-cobertura |
| DEC-13 | Contrato 0.3 | Estados, alternativas, intervalos, nivel de detalle y metadatos de ejecución |
| DEC-14 | Unidades | `pint` + reglas de formato es/en; unidad original conservada |
| DEC-15 | Convenios | Referencia y azimut configurables por proyecto; se confirman contra el IFC de TR |
| DEC-16 | Familias | Paramétricas + **familia envolvente de reserva** + niveles de detalle 1/2/3 |
| DEC-17 | IFC | IFC4 como esquema principal; exportación IFC4X3 e IFC2X3; puertos, documentos y aprobación |
| DEC-18 | Validación IFC | `ifcopenshell.validate` + IoU y Hausdorff contra referencia |
| DEC-19 | Cambios | Tres capas: diferencia visual de páginas, campos emparejados y geometría por GUID |
| DEC-20 | BCF | BCF 2.1 (más compatible) + 3.0 opcional |
| DEC-21 | Bench | Ocho o más estilos de "proveedor", estilos reservados, mecánicos, real con exclusión de uno, intervalos estadísticos |
| DEC-22 | Métrica para elegir | **Puntuación GA2MODEL** ponderada como la rúbrica, con penalización por alucinación |
| DEC-23 | API | FastAPI + SQLModel + Alembic; trabajos en proceso **y** perfil Redis |
| DEC-24 | Despliegue | `docker compose` con perfiles: local, GPU y escala |
| DEC-25 | Coste | Contabilidad por trabajo: tokens, € por proveedor y segundos de GPU |
| DEC-26 | Copiloto | De reglas a **modelo local con herramientas y citas**, solo lectura |
| DEC-27 | Revisión humana | Cola por riesgo + aprendizaje activo + tiempo de revisión medido |
| DEC-28 | Pantalla «Estudio» | Comparativa A/B/C/D en la web: la pieza central de innovación |
| DEC-29 | Pitch | La diapositiva de trade-offs se hace con la tabla del estudio |
| DEC-30 | Licencias | Todo compatible con MIT: sin AGPL; `THIRD_PARTY.md` |
| DEC-31 | Confidencialidad | Registro de qué documento se envió a qué proveedor |
| DEC-32 | Seguridad | Documentos adversariales (inyección de instrucciones) dentro del bench |
| DEC-33 | Organización | Dos agentes de backend: **Lectura** y **Plataforma**, con contrato 0.3 cerrado de antemano |

Se mantienen sin cambios, tras revisarlas: Next.js + R3F en el frontend, el visor `web-ifc` propio
(medido: 239 fps en ventana completa), SSE para tiempo real y SQLite + almacén por hash en local.

---

## 1. Estrategia de lectura (pág. 13 del reto)

### DEC-01 · Desarrollar las cuatro estrategias y elegir por datos

**Contexto.** TR ofrece cuatro enfoques y dice que «premia la decisión técnica, no una tecnología
concreta». Las preguntas clave son robustez, incertidumbre, coste, nivel de detalle y generalización.

| Opción | A favor | En contra |
| --- | --- | --- |
| Elegir D a priori | Menos trabajo | Es una opinión: no se puede defender con números |
| **Desarrollar A, B, C y D y medirlas igual** | La decisión se demuestra; ninguna otra respuesta es tan sólida ante «justificad vuestros trade-offs». El estudio además encuentra la mejor combinación | Unas tres veces más trabajo en lectura |

**Decisión.** Las cuatro estrategias se implementan detrás de la misma interfaz (`Strategy`) y se
miden con el mismo bench, los mismos documentos y las mismas métricas. La estrategia final del
producto es la que gana el estudio. Lo esperado es D, pero lo decide el dato. El estudio es un
entregable del pitch y una pantalla de la web (DEC-28).

**Cómo se valida.**
- Estudio en sintéticos de varios "proveedores" antes del evento.
- Repetición el día 1 con el dataset real, dejando fuera un IFC de referencia cada vez.

### DEC-02 · Definición operativa de cada estrategia

Para comparar con justicia, cada estrategia tiene límites claros. El postproceso es el mismo para
todas: normalización, contrato, familia e IFC.

| Estrategia | Qué hace | Qué **no** usa |
| --- | --- | --- |
| **A · Visión + 3D** | Segmenta vistas (alzado, planta, detalles) y reconstruye la geometría desde los trazos: contorno de la virola, fondos, faldón y muñones de boquilla. La escala sale de las cotas leídas por un **modelo de visión** (local o nube) o por el detector propio. Las boquillas se cruzan entre alzado (elevación) y planta (azimut) | Tablas ni reglas de texto del GA, ni la hoja de datos para geometría |
| **B · Datos + reglas** | Texto vectorial, tablas por cabecera, cotas comprobadas por cadena, cajetín, hoja de datos y VESOR, con reglas de ingeniería e instanciación de familias. Es lo que existe hoy, generalizado | Modelos de aprendizaje |
| **C · RAG** | Recupera el GA más parecido de una biblioteca de equipos aprobados (búsqueda visual + texto) y adapta sus parámetros: hereda la plantilla de lectura (dónde está cada dato) y corrige solo lo que lee en las regiones equivalentes | Lectura de toda la página; parte del caso parecido |
| **D · Híbrido** | Cascada B → OCR → detector → modelo de visión solo en lo que falta o duda. Añade la geometría de A como verificación, C como plantilla y prior, la memoria de la revisión anterior y una fusión aprendida | Nada excluido; el selector decide por tipo de documento |

**Ablaciones de D:** se quita cada canal (geometría, memoria de revisión, RAG, modelo de visión) para
medir cuánto aporta cada uno. Esa tabla convierte el "híbrido" en una decisión demostrada.

### DEC-03 · Proveedores de visión

| Proveedor | Fortalezas | Debilidades | Uso |
| --- | --- | --- | --- |
| **Local**: Qwen3-VL 4B/8B (Apache 2.0) en la RTX 5070 Laptop | Confidencial, coste cero y funciona sin red | 8 GB de VRAM: imágenes A3 grandes hay que trocearlas; más lento | **Por defecto con datos reales** |
| **Plataforma IndesIA** (por confirmar en la formación) | Autorizado por la organización para sus datos | Modelo y límites desconocidos | Con datos reales si existe |
| **Gemini Flash** (Google) | Detecta objetos y devuelve cajas `box_2d` normalizadas de 0 a 1000; salida JSON con esquema; barato | Tercero externo: datos de TR solo con autorización | Sintéticos; reales solo con permiso escrito |
| **Mistral OCR 4.1** + Document AI | OCR con cajas y confianza por bloque; unos 4 $ cada 1.000 páginas (2 $ en lote); opción autoalojada | Tercero externo | Sintéticos; reales solo con permiso |
| Otros (Claude, OpenAI) | Buen razonamiento visual | Coste; tercero | Solo como referencia en sintéticos, si sobra tiempo |

**Decisión.**
- Un adaptador `VisionProvider` común con salida JSON por esquema, cajas normalizadas, caché por
  (hash de página, versión de prompt, modelo) y modo offline.
- Se miden todos en sintéticos: acierto, coste por equipo y segundos.
- **Con datos de TR solo se usan el local y el de la plataforma**, salvo autorización escrita
  (DEC-31). El primer día se pregunta al mentor si se pueden usar APIs externas.

### DEC-04 · Cómo servir el modelo local en 8 GB

| Opción | A favor | En contra |
| --- | --- | --- |
| **Ollama** (ya instalado, 0.40) | Funciona en Windows; sirve modelos de visión cuantizados; API HTTP sencilla | Menos control de la resolución de imagen |
| vLLM | El más rápido en lote | En Windows solo vía WSL2; la RTX 5070 (Blackwell) requiere CUDA reciente |
| `transformers` directo | Control total; necesario para ajustar Florence-2 | Más memoria; más código |

**Decisión.**
- **Ollama para inferencia** del modelo de visión general: `qwen3-vl:4b` asegurado y `qwen3-vl:8b`
  cuantizado si deja margen.
- **`transformers` para entrenar y servir Florence-2**.
- Las páginas A3 se trocean en mosaicos con solape y las coordenadas se reproyectan.
- Se mide la VRAM real el primer día de trabajo.

### DEC-05 · Detector y lector propios entrenados con nuestro generador

**Contexto.** La literatura reciente muestra dos cosas:
- Un modelo pequeño ajustado con unos 400 planos anotados supera a GPT-4o y Claude sin ajuste en
  extracción de cotas (Florence-2: +52 % de F1, −43 % de alucinación).
- Los mejores sistemas son híbridos: un detector de anotaciones seguido de un lector.

Nosotros tenemos un generador que produce **planos anotados ilimitados**, con caja exacta de cada cota.

| Opción | Licencia | Valoración |
| --- | --- | --- |
| YOLO11 (Ultralytics) | **AGPL-3.0** | Descartado: incompatible con publicar en MIT |
| RT-DETR (`transformers`) | Apache-2.0 | Detector válido si Florence-2 no localiza bien |
| **Florence-2 base/large** | MIT | Detección + lectura de región en un solo modelo; 0,23B/0,77B parámetros, cabe en 8 GB |
| Donut | MIT | Bueno para lectura sin OCR; no localiza |

**Decisión.**
- Ajustar **Florence-2** con planos sintéticos de varios proveedores, con aleatorización de dominio:
  fuentes, grosor de línea, ruido, rotación, idioma y unidades.
- El día 1, ajuste fino con unas **20 páginas reales etiquetadas a mano** con Label Studio (Apache-2.0).
- Es la pieza "valor no previsto": se entrena con datos generados por nosotros mismos.

**Cómo se valida.**
- F1 de detección de cotas y acierto de lectura en estilos de proveedor **no vistos en el
  entrenamiento**.
- En real, con exclusión de uno.

### DEC-06 · OCR

| Opción | Licencia | A favor | En contra |
| --- | --- | --- | --- |
| **RapidOCR** (ONNX) | Apache-2.0 | Rápido, sin red, fácil en Windows/Linux | Menos preciso con textos girados pequeños |
| PaddleOCR-VL | Apache-2.0 | Muy alto en benchmarks de documentos (OmniDocBench) | Más pesado |
| Tesseract | Apache-2.0 | Universal | Peor en planos |
| Mistral OCR 4.1 | Comercial | Cajas y confianza; muy bueno en páginas densas | Tercero externo |

**Decisión.** Las cuatro, detrás del mismo adaptador. RapidOCR por defecto (velocidad), PaddleOCR-VL
como opción de calidad y Mistral solo en sintéticos. El estudio elige el valor por defecto.

### DEC-07 · Geometría desde las vistas (núcleo de A, verificación en D)

| Opción | Licencia | Valoración |
| --- | --- | --- |
| **`pdfplumber`** (`lines`, `curves`, `rects`) | MIT | Ya es dependencia; da trazos con coordenadas |
| PyMuPDF (`get_drawings`) | **AGPL-3.0** | Descartado por licencia |
| OpenCV (LSD, Hough, contornos) para escaneos | Apache-2.0 | Necesario cuando no hay vector |

**Decisión.**
1. Segmentar vistas por agrupación espacial de trazos.
2. Detectar la virola como rectángulo dominante y la planta como círculo.
3. Detectar los muñones de boquilla como segmentos cortos perpendiculares.
4. Sacar la escala de las cotas leídas.

En A da la geometría. En D verifica la de B: si la proporción alto/ancho dibujada no cuadra con las
cotas leídas, se marca conflicto. Es un canal **independiente del texto**, que es lo que más sube la
fiabilidad.

### DEC-08 · RAG

| Opción | A favor | En contra |
| --- | --- | --- |
| Embeddings de texto | Simple | Pierde la disposición visual |
| **ColQwen2 / ColSmol** (multivector sobre la imagen de página) | Recupera por aspecto visual: proveedor, plantilla, tipología; corre en local | Integración multivector propia |
| **Memoria de la revisión anterior** | La rev1 aprobada es el mejor prior posible para leer la rev2 | Solo sirve para revisiones |

**Decisión.**
- C usa recuperación visual (ColSmol si la memoria aprieta) más texto, sobre una biblioteca de
  equipos aprobados: sintéticos de todos los estilos y, el día 1, los reales con exclusión de uno.
- La **memoria de revisión** es un canal aparte que usa D (DEC-19).
- Regla fija: un valor recuperado nunca entra en el JSON sin evidencia en el documento actual.

### DEC-09 · Composición del híbrido

**Decisión.**
1. **Cascada:** B primero (coste 0). Después OCR si no hay capa de texto. Después el detector propio.
   El modelo de visión solo para los campos ausentes o de baja confianza.
2. **Verificación cruzada:** tabla, cota, hoja de datos, VESOR, geometría vectorial y revisión
   anterior.
3. **Fusión aprendida:** una regresión logística sobre las señales elige y puntúa cada valor; se
   entrena con sintéticos y se valida en real.
4. **Selector:** elige la cascada según el tipo de documento (vectorial, escaneado, paquete de
   proveedor, mecánico).

**Por qué.** Lo barato y explicable va primero; lo caro, solo donde aporta. Cada valor tiene varias
fuentes que se pueden contrastar, que es la mejor señal de confianza que existe.

### DEC-10 · Comprobación de cita (anti-alucinación)

**Decisión.**
- Todo valor que venga de un modelo cita página y caja.
- Se recorta la caja, se lee con OCR y se comprueba que contiene el valor, con tolerancia de formato.
- Si no, se reintenta la localización; si sigue fallando, queda `abstained`.

El bench mide la **tasa de alucinación** (valores sin respaldo en el documento) por estrategia y
proveedor.

### DEC-11 · Reconciliación

| Opción | Valoración |
| --- | --- |
| Prioridad fija de fuentes | Simple, pero elige en silencio |
| Solver de restricciones genérico (OR-Tools) | Potente; sobra para este tamaño |
| **Búsqueda exacta + mínimos cuadrados ponderados** | Pocas variables: se prueban las combinaciones de lecturas y se ajusta con pesos de confianza |

**Decisión.**
- Restricciones:
  - cadena de cotas;
  - fondo 2:1 → altura ≈ D/4;
  - boquillas dentro de la virola;
  - DN en serie normalizada;
  - azimut en [0, 360);
  - coherencia GA ↔ HDM ↔ VESOR.
- El valor que rompe una restricción se marca `conflict` con una frase que explica por qué.
- Dependencias: `numpy` y `scipy` (BSD).

### DEC-12 · Incertidumbre

**Decisión, en tres niveles:**
1. **Calibración isotónica** por canal, con `scikit-learn` (BSD). Objetivo: ECE < 0,05.
2. **Intervalos conformes** (conformal prediction) para valores numéricos: «2.000 mm ± 3 mm con el 90 %
   de cobertura garantizada». Es un nivel por encima de una confianza calibrada y responde
   literalmente a «gestionar incertidumbre».
3. **Abstención** con curva riesgo-cobertura: qué error se comete según el porcentaje de campos que se
   deja revisar a una persona.

**Cómo se valida.** ECE, cobertura empírica de los intervalos y curva riesgo-cobertura, en el bench y
en la pantalla Bench.

---

## 2. Contrato y datos

### DEC-13 · Contrato 0.3

**Decisión.** Se cierra ahora, antes de repartir el trabajo, para que los dos agentes construyan
contra lo mismo. Especificación en [COORDINACION-BACKEND.md](COORDINACION-BACKEND.md).

- **Por campo:**
  - `state` (`candidate`, `conflict`, `abstained`, `accepted`, `corrected`, `assumed`);
  - confianza calibrada y bruta;
  - intervalo conforme;
  - unidad original;
  - alternativas con su evidencia;
  - explicación del conflicto;
  - procedencia ampliada: estrategia, canal, modelo y hash del prompt.
- **Por equipo:** `kind` (vertical, horizontal, columna, tanque, bomba, compresor, genérico), `lod`
  (1/2/3), tipo de soporte y boquillas con servicio, rating, tipo y vector de dirección opcional.
- **Por revisión:** metadatos de ejecución (estrategia, coste, segundos y modelos).
- Migrador 0.2 → 0.3; el visor sigue funcionando porque los nombres de elemento del IFC no cambian.

### DEC-14 · Unidades

| Opción | Valoración |
| --- | --- |
| Tabla propia | Rápida, pero frágil con ft-in, psi o kg/cm² |
| **`pint`** (BSD) | Conversión robusta y equivalencias para el delta |

**Decisión.** `pint` + reglas propias de formato (separadores es/en, `2.000,5` frente a `2,000.5`,
según el contexto del documento). La unidad original se conserva siempre.

### DEC-15 · Sistema de referencia y convenios

**Decisión.**
- Origen, eje vertical y convenio de azimut son configurables por proyecto.
- Se detecta la flecha de Norte del VESOR si existe.
- El primer día se confirma con el IFC de referencia de TR (G.1) antes de medir nada.

---

## 3. Geometría e IFC

### DEC-16 · Familias y nivel de detalle

| Opción | Valoración |
| --- | --- |
| Solo familias paramétricas | Fallan ante una tipología no prevista |
| Reconstrucción libre de malla | IFC difícil de editar y comparar |
| **Familias + envolvente de reserva + niveles de detalle** | Nunca hay hueco y siempre se dice qué nivel tiene cada equipo |

**Decisión.**
- **Nivel 1:** envolvente con puertos, para cualquier equipo, incluidas bombas y compresores. Usa la
  geometría de A.
- **Nivel 2:** familia paramétrica: vertical, horizontal con silletas, columna por tramos, tanque.
- **Nivel 3:** bridas por DN/rating y plataformas y escaleras del VESOR y de ESTRUCTURA.

Responde a «nivel de detalle» y «generalización» de la pág. 13.

### DEC-17 · IFC

| Opción | Valoración |
| --- | --- |
| **IFC4 (ADD2 TC1)** como principal | El mejor soporte en visores y en IfcOpenShell |
| IFC4X3 como principal | Más nuevo; menos soporte en herramientas de planta |
| IFC2X3 | Compatibilidad con herramientas antiguas |

**Decisión.**
- IFC4 por defecto; exportación IFC4X3 e IFC2X3.
- Entidades: `IfcTank`/`IfcPump`/`IfcCompressor`, componentes agregados y boquillas con
  `IfcDistributionPort`.
- Psets estándar + `TrazIA_Provenance`, `IfcDocumentReference` al original con SHA-256 e `IfcApproval`.
- Los nombres `<TAG>/componente` y los GUID estables no cambian, porque el visor depende de ellos.

### DEC-18 · Validación IFC y comparación con la referencia

**Decisión.**
- `ifcopenshell.validate` en CI.
- Comparación por elemento con IoU de cajas (existe) más distancia de **Hausdorff y Chamfer** de malla
  con `trimesh` (MIT).
- **Mapa de calor del error** en la web.
- El validador web de buildingSMART se usa solo con sintéticos.

---

## 4. Cambios entre revisiones

### DEC-19 · Detección de cambios en tres capas

| Capa | Qué detecta | Técnica |
| --- | --- | --- |
| **1. Diferencia visual de páginas** | Dónde cambió el dibujo, aunque no haya nube | Alineación rev1↔rev2 (ECC de OpenCV) y diferencia de píxeles o de trazos vectoriales |
| **2. Campos emparejados** | Qué dato cambió y cuánto | Emparejamiento húngaro de boquillas (servicio + DN + posición), tolerancias, equivalencia de unidades |
| **3. Geometría por GUID** | Qué elemento 3D se movió | Diferencia de cajas o mallas entre los IFC |

**Decisión.**
- Las tres capas, cruzadas con las nubes y los triángulos Δ.
- Un cambio visual sin cambio de campo, o al revés, se señala como sospechoso.
- La **rev1 aprobada sirve de memoria**: la lectura de la rev2 se concentra en las zonas que cambian y
  el resto se valida contra la rev1.

Es lo que más sube el 20 % y además explica el cambio con evidencia.

### DEC-20 · BCF

**Decisión.** BCF 2.1 (el más compatible con herramientas de coordinación) con un topic por cambio:
vista de cámara, GUID y descripción. BCF 3.0 opcional. Librería `bcf-client` del ecosistema
IfcOpenShell (LGPL, válida como dependencia).

---

## 5. Evaluación

### DEC-21 · Bench para un estudio creíble

**Decisión.**
- **Generador v2 con ocho o más estilos de "proveedor":**
  - cabeceras en español e inglés;
  - pulgadas y ft-in;
  - cotas horizontales;
  - tablas en otra posición;
  - varias páginas;
  - paquetes de proveedor con el GA dentro (IN-03);
  - mecánicos (bomba con bancada).
- **Dos estilos reservados** que nunca se usan para desarrollar ni entrenar: miden generalización.
- **Niveles de degradación**: vectorial, escaneado limpio, escaneado pobre.
- **Real**: exclusión de uno con los 4 IFC; verdad manual para algunos de «estáticos B».
- **Estadística**: intervalos bootstrap del 95 % y prueba de McNemar entre estrategias sobre los
  mismos campos.
- **Corpus adversarial**: documentos con instrucciones incrustadas (DEC-32).

### DEC-22 · Puntuación para elegir la estrategia

**Decisión.** Una única puntuación que imita la rúbrica, más dos restricciones:

```text
Puntuación GA2MODEL = 0,35 · geometría + 0,25 · atributos · (1 − ECE) + 0,20 · F1 de cambios
                      + 0,10 · escala (1 − coste y tiempo normalizados) + 0,10 · innovación (fija, no se mide)
```

- **Geometría**: campos geométricos correctos en ±1 mm o ±0,5°, con penalización por IoU de IFC < 0,95.
- **Restricciones**: tasa de alucinación < 1 % y cobertura de cita = 100 %. Si no se cumplen, la
  estrategia no puede ganar, aunque puntúe más.
- Se muestra con la **frontera de Pareto** coste-acierto, para que el jurado vea el trade-off.

---

## 6. Plataforma

### DEC-23 · API y trabajos

| Opción | Valoración |
| --- | --- |
| Solo `BackgroundTasks` | Suficiente para la demo; no demuestra escala |
| Celery | Pesado para este tamaño |
| **Interfaz de cola con dos implementaciones: en proceso y Redis (`arq`)** | Demo sin dependencias y escala real con un perfil |

**Decisión.** FastAPI + SQLModel + Alembic, SSE para eventos e idempotencia en toda escritura. La cola
es intercambiable: en proceso por defecto y Redis con workers en el perfil de escala. El estudio
comparativo también se lanza como trabajo.

### DEC-24 · Despliegue

**Decisión.** `docker compose` con perfiles:
- `local`: API + web;
- `gpu`: Ollama con el modelo local;
- `escala`: Redis + workers + Postgres.

Funciona sin Docker con `uv run` y `pnpm dev`.

### DEC-25 · Contabilidad de coste

**Decisión.**
- Cada trabajo registra tokens, llamadas, € según la tabla de precios de cada proveedor (versionada
  en el repo), segundos de GPU y segundos totales.
- Coste por equipo y por proyecto (400 equipos × 4 revisiones) **medido**, no estimado.

---

## 7. Producto y demo

### DEC-26 · Copiloto

| Opción | Valoración |
| --- | --- |
| Reglas (actual) | Honesto, pero limitado |
| **Modelo local con herramientas de solo lectura y citas obligatorias** | Responde preguntas del ingeniero sobre su equipo con evidencia; sin datos fuera del portátil |

**Decisión.**
- Copiloto con modelo local (o de la plataforma) que solo puede llamar a herramientas de lectura:
  campos, evidencia, cambios y reglas.
- Cada respuesta cita la evidencia; si no hay, lo dice.
- Nunca modifica datos: propone y la persona acepta.

### DEC-27 · Revisión humana

**Decisión.**
- Cola por riesgo (existe).
- Intervalos conformes visibles por campo.
- **Aprendizaje activo:** cada corrección se guarda como ejemplo, recalibra y se usa como few-shot.
- **Tiempo de revisión medido** con el registro de acciones; es la cifra del ROI.

### DEC-28 · Pantalla «Estudio»

**Decisión.** Una pantalla nueva en la web con:
- tabla A/B/C/D y ablaciones de D;
- frontera de Pareto coste-acierto;
- resultados por estilo, proveedor y nivel de degradación;
- intervalos de confianza estadísticos;
- recomendación final con su justificación.

Es la respuesta visual a la pág. 13 y la diapositiva más diferencial del pitch.

### DEC-29 · Pitch

**Decisión.**
- Se añade una diapositiva «Elegimos con datos» con la tabla del estudio y la frontera de Pareto.
- La demo en vivo usa la estrategia ganadora.
- Ante «¿por qué no solo un modelo de visión?», se responde con la cifra medida de alucinación y coste.

---

## 8. Ética, legal y organización

### DEC-30 · Licencias

**Decisión.**
- Todo lo que se incluye en el repo es compatible con MIT. **Sin AGPL** (Ultralytics, PyMuPDF).
- LGPL o MPL solo como dependencia sin modificar (IfcOpenShell, web-ifc).
- Pesos de modelo con licencia permisiva (Qwen3-VL Apache-2.0, Florence-2 MIT).
- `THIRD_PARTY.md` con cada dependencia y su licencia.

### DEC-31 · Confidencialidad

**Decisión.**
- Los datos de TR solo se procesan con modelos locales o con el de la plataforma, salvo autorización
  escrita de la organización.
- Cada envío a un proveedor queda en un **registro**: documento, hash, proveedor y fecha.
- La interfaz muestra dónde se procesó cada valor.

En el pitch es un argumento ético concreto: «nada de vuestros planos salió del portátil».

### DEC-32 · Seguridad ante instrucciones incrustadas

**Decisión.**
- Corpus sintético con instrucciones escondidas en notas, cajetines y texto blanco.
- El bench mide que ninguna estrategia las obedezca y que se señalen.
- Los documentos se pasan siempre como datos delimitados.

### DEC-33 · Organización del backend

| Opción | Valoración |
| --- | --- |
| API + Motor (reparto anterior) | El Motor acumulaba lectura, geometría, IFC y cambios: demasiado |
| **Lectura + Plataforma** | Equilibrado. **Lectura:** las cuatro estrategias, proveedores, OCR, detector, calibración, generador y estudio. **Plataforma:** API, persistencia, web, contrato, familias, IFC, cambios y BCF |

**Decisión.** Lectura + Plataforma, con el contrato 0.3 y las interfaces cerradas de antemano en
[COORDINACION-BACKEND.md](COORDINACION-BACKEND.md). El contrato es de Plataforma; Lectura produce
candidatos y estados según la especificación.

---

## Fuentes

- Florence-2 ajustado para planos: [arXiv 2411.03707](https://arxiv.org/abs/2411.03707)
- Marco híbrido para vistas múltiples (detector + lectores): [arXiv 2510.21862](https://arxiv.org/abs/2510.21862)
- Detector orientado + modelo de visión para planos 2D: [arXiv 2506.17374](https://arxiv.org/abs/2506.17374)
- Gemini, cajas y salida estructurada: [ai.google.dev · image understanding](https://ai.google.dev/gemini-api/docs/image-understanding)
- Mistral OCR 4: [mistral.ai/news/ocr-4](https://mistral.ai/news/ocr-4)
- Modelos de visión locales por VRAM: [localaimaster.com](https://localaimaster.com/blog/best-local-vision-models) · [insiderllm.com](https://insiderllm.com/guides/vision-models-locally/)
- Comparativa de OCR (OmniDocBench): [docsumo.com](https://www.docsumo.com/blog/best-ocr-models)
- ColQwen2: [huggingface.co/vidore/colqwen2-v0.1](https://huggingface.co/vidore/colqwen2-v0.1)
