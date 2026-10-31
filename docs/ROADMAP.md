# ROADMAP — TrazIA-3D · Reto GA2MODEL (Técnicas Reunidas) · IndesIAhack 2026

> **Objetivo:** ganar el premio del reto GA2MODEL (1.000 €) y el Premio IndesIAhack general (2.000 €)
> con un producto que parezca hecho por un equipo de producto de ingeniería, no por un equipo de
> hackatón: geometría fiel, datos trazables, cambios entendibles, métricas propias medidas contra
> el IFC de referencia y una interfaz 3D que deje al jurado con la boca abierta.

**Equipo (únicos autores del repositorio):**
Javier Saguar Antona · Iria Lozano Carrasco · Miguel Vera del Castillo · Alejandro Cuevas Cid

**Repositorio:** `github.com/javiersaguar/TrazIA-3D` (antes `javiersaguar/IndesiaHack`).
**Documento vivo:** se actualiza al cerrar cada fase. Cada tarea tiene casilla `[ ]`, responsable y
criterio de "hecho". Si una tarea no tiene criterio de "hecho", no está bien definida.

**Documentos que lo acompañan:**
- [DECISIONES.md](DECISIONES.md): análisis punto por punto de cada decisión técnica (DEC-01 a DEC-33).
- [ESTUDIO.md](ESTUDIO.md): protocolo del estudio comparativo de las cuatro estrategias de la pág. 13.
- [COORDINACION-BACKEND.md](COORDINACION-BACKEND.md): contrato 0.3 y reparto entre los agentes
  Lectura y Plataforma.

---

## Índice

0. [TL;DR en 15 líneas](#0-tldr-en-15-líneas)
1. [Datos del evento que condicionan todo](#1-datos-del-evento-que-condicionan-todo)
2. [Cómo se gana: criterios → estrategia → prueba](#2-cómo-se-gana-criterios--estrategia--prueba)
3. [Visión del producto](#3-visión-del-producto)
4. [Punto de partida: qué existe hoy](#4-punto-de-partida-qué-existe-hoy)
5. [Reglas del equipo (no negociables)](#5-reglas-del-equipo-no-negociables)
6. [Arquitectura objetivo y decisiones técnicas](#6-arquitectura-objetivo-y-decisiones-técnicas)
7. [Calendario por fases](#7-calendario-por-fases)
8. [Workstreams en detalle](#8-workstreams-en-detalle)
   - [A. Ingesta](#a-ingesta)
   - [B. Lectura: cuatro estrategias comparadas](#b-lectura-cuatro-estrategias-comparadas-25--y-gran-parte-del-35-)
   - [C. Normalización y contrato de datos](#c-normalización-y-contrato-de-datos)
   - [D. Geometría paramétrica e IFC](#d-geometría-paramétrica-e-ifc-35)
   - [E. Validación y humano en el bucle](#e-validación-y-humano-en-el-bucle)
   - [F. Revisiones y delta](#f-revisiones-y-delta-20)
   - [G. Banco de evaluación (GA2MODEL Bench)](#g-banco-de-evaluación-ga2model-bench)
   - [H. Backend, API y escalado](#h-backend-api-y-escalado-10)
   - [I. Frontend: diseño, 3D y animación](#i-frontend-diseño-3d-y-animación)
   - [J. Pitch, presentación y negocio](#j-pitch-presentación-y-negocio)
9. [Calidad, pruebas y CI](#9-calidad-pruebas-y-ci)
10. [Riesgos y planes B](#10-riesgos-y-planes-b)
11. [Checklists de entrega](#11-checklists-de-entrega)
12. [Anexos](#12-anexos)

---

## 0. TL;DR en 15 líneas

1. Inscribirse los **4** antes del **23/11 23:59**; hacer la formación obligatoria en la plataforma IndesIA.
2. El código previo **está permitido si se declara al inicio del hackatón** → etiqueta `pre-hackathon-baseline` + `PREVIOUS_WORK.md`.
3. Commits **solo** de los 4 miembros. Cero `Co-authored-by`, cero firmas de IA. Hook local + check en CI.
4. Núcleo Python (`src/trazia`, IfcOpenShell). Encima: **API FastAPI** + **frontend Next.js con 3D real** (hecho: 239 fps en ventana completa).
5. **Las cuatro estrategias de la pág. 13 (A visión + 3D, B datos + reglas, C RAG, D híbrido) se desarrollan y se comparan** con el mismo bench ([ESTUDIO.md](ESTUDIO.md)). Gana la que diga el dato; la tabla del estudio es la diapositiva de trade-offs.
6. **Cada valor cita página y región**; la cita se comprueba con OCR del recorte. Sin cita no hay valor: se abstiene.
7. **Incertidumbre de verdad:** confianza calibrada (ECE < 0,05) + **intervalos conformes** por valor + curva riesgo-cobertura.
8. **GA2MODEL Bench:** sintéticos de 8 o más estilos de proveedor (2 reservados para generalización) + los 4 IFC de TR con exclusión de uno, intervalos estadísticos y **Puntuación GA2MODEL** con la rúbrica 35/25/20/10.
9. IFC "rico": `IfcTank`, boquillas como `IfcDistributionPort`, `IfcDocumentReference` al plano, `IfcApproval` para la firma humana. IFC4 + exportación IFC4X3 / IFC2X3.
10. Delta rev1→rev2 con **animación 3D de morph por GUID**, nubes de revisión, impacto por disciplina en un grafo **React Flow** y exportación **BCF**.
11. Frontend **0 AI slop** con el estilo de la casa (PIDS, Albertitos, Ciberconciencia — capturas en `docs/referencias-estilo/`): lenguaje visual del plano de ingeniería (líneas de cota, nubes de revisión, triángulos Δ), 3D como protagonista, animaciones con propósito.
12. Momento firma: **el plano 2D se levanta y se extruye en el modelo 3D** delante del jurado.
13. Demo **offline-capable** (resultados cacheados) + vídeo de respaldo + `.pptx` (obligatorio por bases). **Visión local** en la RTX 5070 Laptop (8 GB) para datos de TR; Gemini y Mistral solo con sintéticos salvo autorización escrita.
14. Día 3: **congelación a las 08:00**, entrega a las **10:00**, pitch a las 11:00 y gala de clausura a las 13:00.
15. El gran premio se decide en una **gala en diciembre**: preparar versión pulida y vídeo para ella.

---

## 1. Datos del evento que condicionan todo

Fuentes: PDF del reto (17 págs.), `indesiahack.org`, `/bases-legales` y `/preguntas-respuestas` (consultadas el 26/10/2026).

| Dato | Valor | Implicación para nosotros |
| --- | --- | --- |
| Fechas | 25, 26 y 27 nov 2026 · ETSIT-UPM, Edificio A, Av. Complutense 30 | 100 % presencial los 3 días; es requisito para optar a premio |
| Inicio | Miércoles 25, 11:00 (presentación de retos, formación de equipos) | Llegar **antes de las 10:00**: plaza por orden de llegada |
| Inscripción | 26 oct – 23 nov, 23:59 | Los 4 inscritos **esta semana** |
| Compromiso previo | Formarse en la plataforma de desarrollo de IndesIA antes del evento | La plataforma ofrece servicios de IA generativa → averiguar qué modelos y límites hay |
| Equipos | 3–5 personas; se puede ir con equipo formado | Vamos los 4 juntos |
| Entrega | Viernes 27, **10:00**: código y presentación en el repositorio | Congelamos a las 08:00 |
| Formato presentación | **.pptx** ante jurado (bases) + documentación fácil de entender | El pitch es un `.pptx`, no solo una demo |
| Exposiciones | Viernes 11:00, sala por reto; 13:00 gala de clausura con los ganadores (Aula Magna, Edif. C) | Si ganamos el reto, presentamos otra vez a las 13:00 |
| Premio reto | 1.000 € (lo decide el mentor y TR) | Rúbrica específica del PDF (pág. 14) |
| Premio general | 2.000 € entre los ganadores de reto, **en una gala en diciembre** | Hay margen para pulir producto, vídeo y narrativa tras el 27 |
| Código previo | **Permitido si se declara explícitamente al inicio** y queda claro qué existía | `PREVIOUS_WORK.md` + tag Git |
| Licencia | Lo creado en el evento: **MIT** (salvo bases específicas) | `LICENSE` MIT en la raíz |
| Datos | Confidenciales; dejar de acceder tras el evento; sin datos personales | Dataset de TR **nunca** al repo; `data/private/` en `.gitignore` |
| Descalificación | Anomalía, fraude, envenenamiento de datos, uso indebido de plataformas | Transparencia total sobre qué es sintético y qué es real |

**Criterios generales de IndesIA** (FAQ + bases): innovación en el enfoque, **uso ético de la IA**, calidad
técnica, creatividad en la presentación, impacto potencial real en la industria; y en técnico: calidad de
software, ciclo de vida del dato, **reproducibilidad** y **escalabilidad**, más experiencia de usuario y
potencial de negocio.

**Criterios específicos del reto** (PDF, pág. 14) — *la demo pesa más que las diapositivas*:

| Peso | Criterio | Qué mide TR |
| --- | --- | --- |
| **35 %** | Fidelidad geométrica | Dimensiones principales y boquillas frente al IFC de referencia |
| **25 %** | Extracción de atributos | Acierto valor + unidad **y calibración de la confianza** |
| **20 %** | Actualización incremental | Detección precisa de cambios rev1 → rev2 |
| **10 %** | Arquitectura y escalado | Viable para cientos de equipos y revisiones |
| **10 %** | Innovación técnica | Decisiones sólidas y valor no previsto |

**MVP obligatorio** (pág. 9–10): CAP-01 ingesta (GA en PDF o imagen alta resolución + Excel/PDF),
CAP-02 extracción (dimensiones externas, tag, soporte y **≥3 boquillas con posición y orientación**),
CAP-03 IFC cargable (IFC4/IFC4.3/IFC2x3: carcasa + tapas + boquillas + soporte, sin errores),
CAP-04 actualización incremental. Salidas: IFC (obl.), JSON con valor+unidad+fuente+score (obl.),
visor con checkpoint humano (obl.), delta (bonus pero vale un 20 %).

**Dataset** (pág. 12): mecánicos (bombas/compresores, solo GA con varias revisiones); estáticos A
(recipientes, columnas, tanque: GA rev1/rev2, HDM, VESOR, estructura y **IFC de referencia en 4 equipos**);
estáticos B (igual sin IFC). Nombres: `GAD_<TAG>_rev1/rev2`, `HDM_<TAG>`, `VESOR_<TAG>`,
`ESTRUCTURA_<TAG>`, `<TAG>.ifc`. Anonimizado sin cajetines.

---

## 2. Cómo se gana: criterios → estrategia → prueba

La mayoría de equipos enseñará "subo un PDF, sale un cilindro". Ganamos si el jurado **ve números
medidos**, **ve la evidencia de cada número** y **ve el cambio** de forma espectacular y útil.

| Criterio | Qué haremos que nadie más hará | Prueba que enseñamos en la demo |
| --- | --- | --- |
| 35 % geometría | Reconciliación de vistas + restricciones de ingeniería + **verificación con la geometría vectorial del dibujo** (canal independiente del texto) + familias con niveles de detalle y envolvente de reserva | Tabla y **mapa de calor 3D de error** (mm, Hausdorff) contra el IFC de TR |
| 25 % atributos | Lectura en cascada (reglas → OCR → detector propio → modelo de visión) con cita verificada + **calibración e intervalos conformes** | Exactitud valor + unidad, **diagrama de fiabilidad**, ECE y cobertura de intervalos |
| 20 % delta | **Tres capas**: diferencia visual de páginas, campos emparejados y geometría por GUID; **la rev1 aprobada como memoria** para leer la rev2 | Precisión/recall de cambios + morph 3D rev1→rev2 + log accionable + BCF |
| 10 % escalado | Cascada barata → cara, caché por SHA-256, cola intercambiable (en proceso o Redis), coste y latencia medidos por trabajo | Procesamos **todo el dataset** en lote en directo: N equipos, X s/equipo, Y €/equipo |
| 10 % innovación | **Estudio comparativo A/B/C/D** con ablaciones y estadística; detector **entrenado con nuestro propio generador**; intervalos conformes; aprobación dentro del IFC | Pantalla «Estudio» y diapositiva «Elegimos con datos» con frontera de Pareto coste-acierto |
| Ético (general) | Humano en el bucle, DRAFT por defecto, abstención en vez de invención, **datos de TR solo en local o plataforma**, registro de envíos, corpus adversarial de inyección | «Nada de vuestros planos salió del portátil» + intento de inyección que el sistema ignora y señala |
| Reproducibilidad (general) | `docker compose up` / `uv run` + semillas + datasets sintéticos versionados | Un comando reproduce el bench |
| Presentación (general) | Narrativa plano → dato → modelo → cambio → decisión; 3D cinematográfico | `.pptx` cuidado + demo en vivo + vídeo de respaldo |

**Regla de oro de producto (de TR):** el agente genera DRAFT; un ingeniero valida antes de producción.
Todo el producto gira alrededor de que esa validación sea **rápida, segura y agradable**.

---

## 3. Visión del producto

**TrazIA-3D — del plano al modelo, con cada cambio trazado.**

Un espacio de trabajo donde un ingeniero de TR:
1. Suelta el paquete documental de un equipo (GA, HDM, VESOR…).
2. Ve el pipeline trabajar en vivo y en segundos obtiene un **modelo 3D DRAFT**.
3. Revisa en una cola ordenada por riesgo: cada valor enseña su recorte del plano, su confianza y su
   impacto. Acepta con una tecla, corrige con dos.
4. Aprueba: el IFC se publica con la aprobación y la trazabilidad **dentro del propio IFC**.
5. Llega la rev2: el sistema le dice **qué cambió, cuánto, dónde y a quién afecta** (piping, civil,
   estructuras…), con un morph 3D y un BCF listo para coordinación.
6. A escala: un plot plan con todos los equipos del proyecto, su estado y su salud de datos.

Frase del pitch: *"Hoy la geometría viaja como documento. Con TrazIA-3D viaja como dato, con su
evidencia y su historia."*

---

## 4. Punto de partida: qué existe hoy

**Estado a 26/10/2026 (en `main` y en GitHub):**
- Núcleo Python 0.2.
- Frontend Next.js con las 6 pantallas y el 3D real: visor IFC, planta, comparación de revisiones y
  «del plano al modelo».
- Generador sintético v1 (3 estilos), bench v0 con la rúbrica y lector de GA dibujados (estrategia B
  inicial).
- Reglas de autoría y licencia MIT.

Detalle en [BENCH.md](BENCH.md), `web/docs/INFORME_A.md` y `web/docs/INFORME_B.md`. La tabla de abajo
es la foto inicial de la base.

Base inicial (Python 3.11–3.13, uv, IfcOpenShell, pdfplumber, openpyxl, Pydantic, Streamlit + Plotly).

| Ya existe | Falta para ganar |
| --- | --- |
| Ingesta PDF/Excel con SHA-256, páginas, regiones y celdas | OCR, clasificación de páginas, paquetes vendor, imágenes |
| Extractor de **etiquetas explícitas** (`DIAMETER = 2000 mm`) | Extractor real de planos: tablas de boquillas, cotas gráficas, vistas, LLM multimodal |
| Contrato JSON 0.2: valor, unidad, fuente, bbox, score, revisado | Score **calibrado**, estados (conflicto/abstención), alternativas, campos de impacto |
| IFC4: `IfcTank` PRESSUREVESSEL, virola, 2 fondos, faldón, ≥3 boquillas radiales, GUID estables | Puertos, Psets de trazabilidad, documento y aprobación en IFC; más familias; IFC4X3/2X3 |
| Visor Plotly que tesela el IFC | Visor 3D web de nivel producto (Three.js + web-ifc) |
| Aprobación humana ligada a huella de datos | UX de revisión rápida, priorización, auditoría |
| Delta exacto valor/unidad, GUID estables | Tolerancias, emparejamiento, impacto, morph 3D, BCF |
| CI Windows/Linux, ruff, pytest | Bench contra IFC de referencia, e2e, rendimiento |
| Demo sintética V-101 rev A/B | Generador sintético realista (planos dibujados, escaneos) |

**Decisión:** no se tira nada. `src/trazia` sigue siendo el núcleo. Streamlit queda como **fallback de
demo** hasta que el frontend nuevo lo supere; después se mantiene solo como herramienta interna.

---

## 5. Reglas del equipo (no negociables)

### 5.1 Autoría: solo los 4 miembros

En el repositorio **solo** aparecen como autores:

| Nombre | Correo Git (rellenar) |
| --- | --- |
| Javier Saguar Antona | `javisaguarantona@gmail.com` |
| Iria Lozano Carrasco | `____________` |
| Miguel Vera del Castillo | `____________` |
| Alejandro Cuevas Cid | `____________` |

- **Prohibido:** líneas `Co-authored-by:` de cualquier tipo, "Generated with…", firmas de herramientas o
  agentes de IA en commits, PR, código, comentarios o documentación. Los agentes son herramientas: la
  autoría es de quien hace el commit.
- Cada miembro configura su identidad **en este repo**:
  ```bash
  git config user.name "Nombre Apellido Apellido"
  git config user.email "correo@ejemplo.com"
  ```
- Configurar los agentes para que no añadan atribución:
  - **Claude Code** — `.claude/settings.json` del repo: `{"attribution": {"commit": "", "pr": ""}, "includeCoAuthoredBy": false}`
    (la segunda clave es la antigua; se dejan las dos).
  - **Codex** — añadir la regla a `AGENTS.md` (tarea 0.6).
  - Cualquier otro asistente: misma regla en su archivo de instrucciones.
- **Hook local** `commit-msg` que rechaza coautores (anexo 12.2) y `git config core.hooksPath .githooks`.
- **Check en CI** que falla si algún commit del PR tiene coautores o un autor fuera de la lista (anexo 12.3).
- Si se cuela un commit con coautor: se reescribe **antes** de hacer push (`git commit --amend`); si ya
  se ha subido a una rama propia, se reescribe y se avisa al equipo. Nunca reescribir `main` sin acuerdo.

### 5.2 Código previo declarado

- La mañana del 25/11, antes de empezar: `git tag -a pre-hackathon-baseline -m "Trabajo previo al evento"` y push.
- `PREVIOUS_WORK.md` en la raíz: qué existía (módulos, funcionalidades, datos sintéticos) y fecha. Se
  enseña a la organización al inicio. Todo lo posterior al tag es trabajo del evento (MIT).
- En el pitch se dice con naturalidad: "llegamos con la plataforma; aquí la hemos enfrentado al dataset
  real y estas son las métricas". Esto es una fortaleza, no una debilidad.

### 5.3 Licencia y datos

- `LICENSE` MIT con copyright de los 4 miembros.
- `data/private/` y cualquier archivo del dataset de TR **fuera de Git** (ya en `.gitignore`). Ni PDF,
  ni recortes, ni IFC de referencia, ni JSON derivados con contenido real en el repo público.
- Las métricas y capturas del dataset real van en la presentación (permitido) pero no se publican los
  documentos. Revisar con el mentor qué se puede enseñar en la gala de diciembre.
- No subir documentos del dataset a servicios externos no autorizados (incluido el validador web de
  buildingSMART). Para servicios externos, solo datos sintéticos.

### 5.4 Coordinación humanos + agentes: no pisarse

Trabajan 4 personas y varios agentes. El backend se reparte entre dos agentes, **Lectura** y
**Plataforma**; el detalle está en [COORDINACION-BACKEND.md](COORDINACION-BACKEND.md).

1. **Mapa de propiedad por carpeta** (un único dueño por carpeta; los demás proponen por PR):

   | Carpeta | Dueño | Contenido |
   | --- | --- | --- |
   | `src/trazia/{pipeline,ingest,extraction}.py`, `src/trazia/{strategies,extractors,vision,ocr,geometry2d,reconcile,calibration}/` | Lectura (responsable B: Javier) | Las cuatro estrategias, proveedores de visión, OCR, geometría desde vistas, reconciliación e incertidumbre |
   | `training/` | Lectura | Entrenamiento del detector propio con sintéticos |
   | `bench/`, `synthetic/` | Lectura (responsable G: Alejandro) | Generador, bench y estudio comparativo |
   | `src/trazia/{model,ifc,revisions,review,cli,app,viewer,bcf}.py`, `src/trazia/families/` | Plataforma (responsable D: Miguel) | Contrato, familias, IFC, cambios y BCF |
   | `src/trazia/{api,store,queue}/` | Plataforma (responsable H: Javier) | FastAPI, trabajos, persistencia |
   | `web/` | Frontend (responsable I: Iria); Plataforma conecta la API y la pantalla Estudio | Next.js; el 3D (`viewer3d`, `plant`, `delta3d`) es del responsable 3D |
   | `docs/` | Todos; `ROADMAP.md`, `DECISIONES.md` y `ESTUDIO.md` los mantiene el líder | Documentación |
   | `pitch/` | Responsable J | `.pptx`, guion, vídeo |

2. **Contrato primero.** El JSON (`docs/DATA_CONTRACT.md` + `revision.schema.json`) y el OpenAPI son
   la frontera entre equipos. Cambiar el contrato = PR con revisión de al menos otro dueño afectado.
   Los tipos TypeScript se **generan** del OpenAPI, nunca se escriben a mano.
3. **Una rama por tarea**, PR pequeño a `main`, CI en verde para fusionar. `main` siempre demostrable.
4. **Un agente = un worktree** (`git worktree add ../TrazIA-3D-web feat/web`). Nunca dos agentes en el
   mismo directorio de trabajo a la vez.
5. Antes de crear un archivo nuevo en una carpeta ajena, preguntar al dueño.
6. **Primer commit ya:** cuando el agente actual cierre su paso, Javier hace el commit inicial de la base
   y push a `main` (autor Javier, sin coautores). Sin ese commit no se puede trabajar en paralelo.
7. Opcional: el plugin `hackathon-kit` (orquestador + workers en worktrees + revisor) encaja con este
   esquema si se quiere repartir encargos entre agentes de forma sistemática.

### 5.5 Reparto de roles (propuesta — confirmar en la reunión 0)

| Persona | Rol principal | Workstreams | Apoyo |
| --- | --- | --- | --- |
| Javier | Líder técnico, integración, extracción IA | B, C, H (contrato) | G |
| Iria | Frontend, diseño y 3D | I | J (visual del `.pptx`) |
| Miguel | Geometría, IFC y familias | D, F (geometría del delta) | E |
| Alejandro | Evaluación, delta, negocio y pitch | G, F, J | A |

Cada persona es **dueña** de su carpeta y **revisora** de la de al lado.

---

## 6. Arquitectura objetivo y decisiones técnicas

```text
                         ┌──────────────────────────── web/ (Next.js, React 19, TS) ─────────────────────────────┐
                         │  Ingesta · Pipeline (React Flow) · Revisión (PDF + 3D + campos) · Delta · Bench · Planta │
                         │  three.js / R3F / drei · web-ifc en Web Worker · pdf.js · TanStack Query · Zustand      │
                         └───────────────▲─────────────── REST + SSE (OpenAPI → tipos TS) ─────────────────────────┘
                                         │
┌──────────────────────────────── src/trazia/api (FastAPI) ────────────────────────────────────────────────────────┐
│ /documents (subida idempotente, SHA-256) · /jobs (extracción asíncrona + progreso SSE) · /revisions (PATCH campos) │
│ /approve (clave de idempotencia) · /ifc · /diff · /bcf · /bench · /plant                                         │
└───────────────▲───────────────────────────────▲──────────────────────────────────▲──────────────────────────────┘
                │                               │                                  │
     Cola de trabajos (arq/Redis o         Almacén de contenido              SQLite → Postgres
     BackgroundTasks en local)             por SHA-256 (originales,          (equipos, revisiones,
                │                          recortes, IFC)                    campos, auditoría)
                ▼
┌──────────────────────────────── src/trazia · pipeline.process(documentos, strategy=…) ──────────────────────────┐
│ ingest → classify ─┬─ A · vision/ (local Qwen3-VL · plataforma · Gemini · Mistral) + geometry2d/ (trazos, vistas) │
│                    ├─ B · extractors/ (texto, tablas, cotas, cajetín, HDM, VESOR) + ocr/                          │
│                    ├─ C · rag/ (ColQwen2/ColSmol + biblioteca aprobada) · memoria de la revisión anterior        │
│                    └─ D · cascada + verificación cruzada + fusión aprendida + selector por tipo de documento      │
│ → reconcile/ (restricciones) → calibration/ (isotónica + conformal) → model.py (contrato 0.3)                     │
│ → families/ (nivel 1 envolvente · nivel 2 paramétrica · nivel 3 detalle) → ifc.py → revisions.py → bcf.py        │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                ▲                                              ▲
        bench/ + estudio (A/B/C/D, ablaciones,          training/ (Florence-2 ajustado con
        estadística, Puntuación GA2MODEL)               planos sintéticos, RTX 5070 8 GB)
```

### Decisiones y trade-offs (para defender ante el jurado)

Resumen. El análisis completo, con las opciones descartadas y cómo se valida cada una, está en
[DECISIONES.md](DECISIONES.md).

| Decisión | Elegido | Alternativas | Por qué |
| --- | --- | --- | --- |
| Enfoque (pág. 13) | **Las cuatro (A, B, C, D) implementadas y medidas**; el producto usa la ganadora y su selector por tipo de documento | Elegir una a priori | Es la única forma de *demostrar* el trade-off que pide TR (DEC-01) |
| Visión | Adaptador con modelo local (Qwen3-VL en la RTX 5070, Ollama), plataforma, Gemini y Mistral OCR | Un proveedor fijo | Confidencialidad, coste y acierto medidos; datos de TR solo en local o plataforma (DEC-03, 31) |
| Detector propio | **Florence-2 (MIT) ajustado con nuestros sintéticos** + ~20 páginas reales | YOLO (AGPL), solo modelos generales | La literatura muestra que el ajuste supera a modelos generales; licencia compatible (DEC-05, 30) |
| Geometría desde vistas | Trazos con `pdfplumber` + OpenCV en raster | PyMuPDF (AGPL) | Canal independiente del texto: verifica y, en A, construye (DEC-07) |
| Incertidumbre | Calibración isotónica + **intervalos conformes** + abstención | Score fijo del modelo | Responde a «gestionar incertidumbre» con garantía estadística (DEC-12) |
| Geometría IFC | Familias paramétricas + **envolvente de reserva** + niveles de detalle 1/2/3 | Malla libre | IFC editable y comparable, sin huecos ante tipologías nuevas (DEC-16) |
| Cambios | Diferencia visual + campos emparejados + geometría por GUID, con la rev1 como memoria | Solo diferencia de campos | Detecta lo que no está en nubes y explica el cambio (DEC-19) |
| Núcleo | Python + IfcOpenShell (existe) | Reescribir en TS | Estándar de facto IFC; reutiliza la base |
| Frontend | Next.js (App Router) + R3F (hecho) | Streamlit | Nivel de 3D, animación y UX |
| Visor | **web-ifc** en Worker → mallas Three.js (hecho) | Geometría en cliente | El visor lee el IFC, no una segunda geometría |
| Cola | Interfaz con dos implementaciones: en proceso y Redis (`arq`) | Solo `BackgroundTasks` | Demo sin dependencias y escala demostrable (DEC-23) |
| Persistencia | SQLite + almacén por hash; Postgres en el perfil de escala | Solo memoria | Auditoría, reproducibilidad, idempotencia |
| Tiempo real | SSE | WebSockets | Solo servidor → cliente |

---

## 7. Calendario por fases

Inicio del plan: **lunes 26/10/2026**. Revisión de estado: **28/10/2026**; actualizada el
**31/10/2026** con lo que cerraron los agentes Lectura, Plataforma y 3D el 30/10
([Lectura](agentes/INFORME_LECTURA.md), [Plataforma](agentes/INFORME_PLATAFORMA.md),
[3D](agentes/INFORME_FRONTEND_3D.md)). Las casillas se cierran por evidencia, no por fecha prevista. Las tareas parciales permanecen abiertas; detalle en [REVISION_ROADMAP_2026-10-28.md](REVISION_ROADMAP_2026-10-28.md).

| Fase | Fechas | Objetivo | Hito de salida |
| --- | --- | --- | --- |
| 0. Arranque | 26–28 oct | Equipo, reglas, repo, inscripción, plataforma | Inscritos; plataforma documentada; reglas de autoría activas |
| 1. Cimientos | 29 oct – 4 nov | Contrato 0.3, `pipeline` + interfaz `Strategy`, proveedores de visión, generador v2, arnés del estudio, API base | El estudio corre con B sobre S-dev; la API sirve la demo |
| 2. Estrategias | 5 – 14 nov | A, C y D v1; OCR; modelo local; detector propio entrenado; familias + IFC rico | Primer estudio A/B/C/D en S-dev |
| 3. Diferenciales | 15 – 21 nov | Cambios en tres capas, calibración + conformal, ablaciones, selector, pantalla Estudio, copiloto local, escala | Estudio completo con S-reservado; demo de 6 min con la estrategia ganadora |
| 4. Endurecer | 22 – 24 nov | Congelar alcance, ensayo, modo offline, `.pptx` v1, `PREVIOUS_WORK.md` | 2 ensayos cronometrados; todo reproducible en un portátil limpio |
| 5. Hackatón | 25 – 27 nov | Dataset real → estudio real con exclusión de uno → pulido → pitch | Entrega 27/11 10:00 |
| 6. Gala | dic | Versión pulida, vídeo, narrativa del gran premio | Presentación para el premio general |

### Fase 0 · Arranque (26–28 oct)

- [ ] **0.1** Los 4 se inscriben en `indesiahack.org/registro` y eligen el reto de Técnicas Reunidas. *Hecho:* 4 confirmaciones.
- [ ] **0.2** Hacer la formación en la plataforma IndesIA y anotar en `docs/PLATAFORMA.md`: qué es (¿JupyterHub, VS Code web, nube?), recursos (CPU/GPU/RAM), **qué modelos de IA generativa y de visión ofrece**, límites, si hay salida a internet, si se puede usar Docker, y **si sus modelos pueden procesar el dataset de TR**. *Hecho:* documento con respuestas.
- [ ] **0.3** Comprobar si con la inscripción ya se accede al dataset o a muestras. Si sí: copiar a `data/private/` (fuera de Git) y priorizar la verdad de referencia. *Hecho:* respuesta registrada.
- [ ] **0.4** Reunión 0 (1 h): leer este roadmap y [DECISIONES.md](DECISIONES.md), confirmar roles (5.5), canales y horario semanal. *Hecho:* roles en este documento.
- [x] **0.5** Commit inicial de la base y push a `main`. *Pendiente:* protección de rama (PR + CI obligatorio).
- [x] **0.6** Reglas de autoría: `.githooks/commit-msg`, `core.hooksPath`, workflow `authors.yml`, `.claude/settings.json`, regla en `AGENTS.md`. *Pendiente:* correos de Iria, Miguel y Alejandro en `.github/autores.txt`.
- [x] **0.7** `LICENSE` MIT con los 4 nombres; `CONTRIBUTING.md`.
- [x] **0.8** Skills de frontend instaladas en el repo.
- [ ] **0.9** Pedir al mentor de TR (si hay canal): formato real de los GA (¿vectorial o escaneado?), unidades habituales, si las boquillas vienen en tabla, qué consideran "dimensiones principales" y con qué tolerancia comparan, y **si autorizan procesar el dataset con APIs externas** (DEC-31). *Hecho:* respuestas o pregunta enviada.
- [x] **0.10** Medir en la RTX 5070 Laptop (8 GB) qué modelos de visión caben con imágenes A3 en mosaico: `qwen3-vl:4b`, `qwen3-vl:8b` cuantizado y PaddleOCR-VL. Anotar VRAM y segundos por página en `docs/PLATAFORMA.md`. *Hecho:* tabla medida. *Medido:* 4B al 100 % en GPU (5,8 GB, 129 s/página); 8B no cabe (22 % CPU, 339 s/página); PaddleOCR-VL medido el 30/10: carga en 2,7 GB, pero no acaba una página A3 en 25 min, y se descarta. [Tabla](PLATAFORMA.md).

### Fase 1 · Cimientos (29 oct – 4 nov)

**Revisión 27/10/2026:** implementación y pruebas en `feat/plataforma`.
Evidencias y comandos: [cierre de Fase 1](FASE1.md). **10 de 11 tareas cerradas.** La tarea 1.9 sigue abierta hasta
comprobar un segundo proveedor real; no se cuentan mocks como mediciones.

- [x] **1.1 (Plataforma)** Contrato **0.3** según [COORDINACION-BACKEND.md](COORDINACION-BACKEND.md): estados, alternativas, intervalos, nivel de detalle, metadatos de ejecución; migrador 0.2 → 0.3; tipos de la web regenerados. *Hecho:* esquema publicado por CLI, ejemplos raíz validados y tipos regenerados; checks y e2e web en ambos modos.
- [x] **1.2 (Plataforma)** API base (sección H) sirviendo la demo y con la cola en proceso. *Hecho:* pruebas de API + la web funciona con `NEXT_PUBLIC_API_URL`.
- [x] **1.3 (I)** `web/` con Next.js, tokens y estilo de la casa.
- [x] **1.4 (G)** Generador sintético v1: tres estilos (rotulado, plano, escaneado) con verdad conocida.
- [x] **1.5 (G)** Bench v0 con la rúbrica.
- [x] **1.6 (Plataforma)** `docker compose` con perfiles `local`, `gpu` y `escala` (DEC-24). *Hecho:* imágenes construidas y tres perfiles comprobados en Docker/WSL con API, SSE, IFC, idempotencia y persistencia; Redis/Postgres reales y GPU visible. [Resultados](evidencias/fase1/compose-results.json).
- [x] **1.7 (I)** Visor `web-ifc` en Worker a 239 fps en ventana completa.
- [x] **1.8 (Lectura)** `trazia.pipeline` + interfaz `Strategy` (DEC-02) con B como primera estrategia. *Hecho:* `process(..., strategy="b_reglas")` en verde.
- [ ] **1.9 (Lectura)** Adaptador `VisionProvider` con caché y modo offline: Ollama local, Gemini, Mistral y plataforma (cuando se sepa). Registro de envíos (DEC-31). *Pendiente de cierre:* Ollama real y su caché offline comprobados; Gemini/Mistral tienen adaptador y pruebas de contrato, pero falta una credencial para leer la misma página con un segundo proveedor real. Plataforma sigue pendiente de conocer su API. Véase [evidencia 1.9](FASE1.md#visión-caché-y-offline-19-parcial). *31/10, tarde:* adaptador común para Groq, OpenRouter, NVIDIA NIM y Cloudflare Workers AI (API de chat de OpenAI) con reintentos ante límites de tasa. Con las claves de Gemini, Groq, OpenRouter, NVIDIA y Cloudflare, seis modelos leen la misma tesela sintética. Comparación como lector de A en curso (`python -m bench.proveedores`).
- [x] **1.10 (Lectura)** Generador **v2**: 8 estilos de proveedor (2 reservados), niveles de degradación, multipágina, paquetes de proveedor, mecánicos y corpus adversarial (DEC-21). *Hecho:* cuatro conjuntos generados: 64 equipos, 336 PDF y 162 Excel, ocho estilos/dos reservados; [semillas y huellas](evidencias/fase1/conjuntos.json).
- [x] **1.11 (Lectura)** Arnés del estudio (`python -m bench.estudio`): variantes, estadística (bootstrap, McNemar), Puntuación GA2MODEL y Pareto (DEC-22). *Hecho:* B y ablación sin HDM medidos en los 24 equipos de S-dev y sus tres degradaciones, bootstrap por equipo y Pareto; [informe](evidencias/fase1/estudio.md).

### Fase 2 · Estrategias (5 – 14 nov)

- [ ] **2.1 (Lectura)** **B completo**: tablas por cabecera con sinónimos es/en, cotas en cualquier orientación, cajetín, hoja de datos, VESOR; sobre texto vectorial o líneas de OCR. *Parcial:* B y OCR están implementados y probados; falta verificar explícitamente el alcance VESOR antes de cerrar toda la tarea.
- [ ] **2.2 (Lectura)** **OCR** (RapidOCR, PaddleOCR-VL; Mistral solo sintéticos) y comprobación de cita (DEC-06, 10). *Parcial:* RapidOCR en CPU y comprobación de cita implementados. PaddleOCR-VL medido el 30/10 y descartado: no acaba una página A3 en 25 min en la RTX 5070 ([tarea 2.2](PLATAFORMA.md)). Falta Mistral, que depende de la credencial de 1.9. *31/10:* adaptador de chat de Mistral con visión y `python -m bench.mistral` listos y probados sin red. Falta la clave: la cuenta está en el plan Gratis, sin acceso a la API.
- [x] **2.3 (Lectura)** **A · visión + 3D**: segmentación de vistas, geometría desde trazos (`pdfplumber`/OpenCV), escala desde cotas leídas por el modelo de visión, cruce alzado ↔ planta (DEC-07). *Verificado 28/10:* Implementación A con lector de texto/OCR o visión, trazos y cruce alzado/planta; pruebas CPU en `test_lectura_estrategia_a.py`. Su calidad en el banco no se da por garantizada.
- [x] **2.4 (Lectura)** **Detector propio**: Florence-2 ajustado con S-dev en la RTX 5070 (`training/`), aleatorización de dominio; medido en S-reservado (DEC-05). *Hecho 30/10:* Florence-2 base ajustado con 1.410 mosaicos de S-dev (525 s, 4,9 GB). En 200 mosaicos de S-reservado: F1 0,982 y texto exacto 90,2 %. Conectado como canal `detector` de D; su ablación vale −0,011 [−0,023; −0,001]. [Tarea 2.4](PLATAFORMA.md).
- [ ] **2.5 (Lectura)** **C · RAG**: biblioteca aprobada, recuperación visual ColQwen2/ColSmol + texto, adaptación de plantilla y parámetros (DEC-08). *Parcial:* C v1 con huella visual ligera + vocabulario, exclusión del mismo equipo y lectura de la región actual; ColQwen2/ColSmol no está integrado.
- [x] **2.6 (Lectura)** **D v1**: cascada, verificación cruzada, reconciliación con restricciones (DEC-09, 11). *Verificado 28/10:* D v1 implementado con B/OCR, C, memoria, geometría y fusión heurística; `test_lectura_estrategia_d.py`. No equivale a fusión aprendida ni al estudio completo de 3.4.
- [x] **2.7 (Plataforma)** Familias: vertical (mejorar), horizontal con silletas, columna por tramos, tanque, envolvente de reserva (nivel 1) para mecánicos (DEC-16). *Verificado 28/10:* Familias paramétricas y envolventes LOD 1 verificadas en `test_plataforma_families.py`.
- [x] **2.8 (Plataforma)** IFC rico: puertos, Psets de trazabilidad, `IfcDocumentReference`, `IfcApproval`, exportación IFC4X3 e IFC2X3, validación en CI (DEC-17, 18). *Verificado 28/10:* IFC4/IFC4X3/IFC2X3, puertos, trazabilidad, originales y aprobación; `test_plataforma_ifc.py` y validación EXPRESS en CI.
- [x] **2.9 (E/I)** Espacio de revisión: PDF + 3D + campos enlazados, cola por riesgo, atajos, deshacer.
- [x] **2.10 (I)** Visor 3D: selección, aislar, corte, explosionado, cotas 3D, rosa de orientación.
- [x] **2.11 (Lectura)** **Primer estudio A/B/C/D** en S-dev. *Hecho:* tabla con intervalos. *Hecho 31/10:* A, B, C y D medidos con IC 95 % en S-dev, S-reservado y S-adversarial. D con fusión aprendida 0,670 [0,638; 0,702], D 0,640, C 0,567, B 0,536 y A sin modelo 0,488. A con Qwen3-VL local, en un subconjunto declarado de 6 equipos: 0,445 frente a 0,543 de A sin modelo, con un 7,3 % de alucinación y 172 s por revisión. [Estudio 3](ESTUDIO.md).

### Fase 3 · Diferenciales (15 – 21 nov)

**Avance Plataforma 27/10/2026:** [evidencias y límites](FASE3.md). Trabajo separado del
agente de Fase 2; no se editan las estrategias ni sus carpetas.

- [x] **3.1 (Plataforma)** Cambios en **tres capas** (diferencia visual, campos emparejados, geometría por GUID) + nubes Δ + BCF 2.1 (DEC-19, 20). *Verificado:* API, comparación y BCF en la batería Python; marcadores heurísticos y sin nuevas ediciones del visor.
- [x] **3.2 (Lectura)** **Memoria de revisión** en D: la rev1 aprobada guía la lectura de la rev2. *Hecho 30/10:* D solo usa la memoria si la revisión anterior está aprobada y su huella cuadra; si no, la omite con aviso. Medida con ablación: +0,009 [−0,002; 0,020], sin efecto medible (H5 rechazada).
- [ ] **3.3 (Lectura)** Calibración isotónica + **intervalos conformes** + curva riesgo-cobertura (DEC-12). *Hecho:* ECE < 0,05 y cobertura empírica ≥ nominal en S-reservado. *Parcial 30/10:* implementada y conectada como etapa `calibrate`, con abstención. En S-reservado, B cumple (ECE 0,035; cobertura 100 %). C y D no: ECE 0,210 y 0,270, y cobertura de D 94,1 %. [Detalle](BENCH.md). *Avance 31/10:*
  - Un intervalo que no informa ya no se da, y el campo se abstiene.
  - C va sin curva, elegido dejando fuera un proveedor de S-dev; con ello cumple la ECE (0,023), pero no la cobertura (53 %).
  - D con fusión aprendida cumple la cobertura (96,4 %) y baja la ECE de 0,270 a 0,072, aún por encima de 0,05. Con abstención se queda el 64 % de los campos con un riesgo del 4,7 %.
  - [Revisión 31/10](BENCH.md).
  - *Tarde 31/10:* la fusión aprendida es ya la de D, con el modelo versionado en `src/trazia/strategies/fusion_model.json`. Calibración v5 con D sin curva: ECE 0,066 y cobertura 91,5 % en S-reservado; con abstención se queda el 69 % de los campos con un riesgo del 8,3 %. Sigue sin cumplir la ECE < 0,05.
- [x] **3.4 (Lectura)** **Fusión aprendida y selector** por tipo de documento; **ablaciones** de D; estudio completo con S-reservado (H1–H6 de [ESTUDIO.md](ESTUDIO.md)). *Parcial 30/10:* selector, ablaciones y estudio con S-reservado hechos. El selector fijado en S-dev pierde frente a D solo (0,372 frente a 0,525), así que se recomienda D para todo. Ablaciones: RAG −0,076, geometría −0,045, detector −0,011 y memoria +0,009. *Hecho 31/10:* fusión aprendida (`d_hibrido+fusion`, regresión logística entrenada en S-dev con canales apagados). Dejando fuera un proveedor de S-dev, acierta el 93,2 % de los campos frente al 92,5 % de la heurística. En el estudio sube a 0,670 frente a 0,640 (McNemar p ≈ 10⁻⁷), y en S-reservado a 0,570 frente a 0,524. El selector sigue perdiendo: se recomienda la fusión aprendida para todo.
- [x] **3.5 (Plataforma)** Pantalla **Estudio** en la web (DEC-28) y conexión de la pantalla Bench al estudio. *Hecho:* misma fuente/query, variante y rúbrica con IC; bench v1 separado, errores/vacío explícitos y pruebas en ambos transportes.
- [x] **3.6 (Plataforma)** **Copiloto con modelo local**, herramientas de solo lectura y citas (DEC-26). *Verificado:* Ollama local, evidencia por hash, sin herramientas de escritura y pruebas de citas/concurrencia.
- [ ] **3.7 (Plataforma)** Escala: perfil Redis + workers, lote de todo el conjunto, coste y tiempo medidos por equipo (DEC-23, 25). *Parcial:* B dio 72 done/264 errores y 3,62× con 1/4 workers. *31/10:* D/CPU sobre las mismas 336 revisiones: 173 done (133 LOD 2 y 40 envolventes LOD 1), 163 errores; 1.823,1/1.035,2 s (1,76×) en host compartido, mismos estados por revisión. No equivale a una mejora causal frente a B. No se proyectan 1600 IFC válidos con esa cobertura. [Evidencias](FASE3.md). *Cierre de Plataforma:* inventario de los 163 fallos, reproducción por `--tags` y control `--exigir-todos` (salida 2 si falta algún DRAFT); no resuelve la lectura de escaneados. [Material de pitch](PITCH_ESCALA.md). *D aprendido/v5:* 174 DRAFT (134 LOD 2/40 LOD 1), 162 errores; 1.434,28/877,69 s (1,63×), mismos estados con 1/4 workers y 0/336 aciertos de caché de trabajos. [Comparación por revisión](evidencias/fase3/31oct-d-v5/resumen.md); sigue abierta por cobertura y presupuesto de IFC válidos.
- [ ] **3.8 (E)** Aprendizaje activo: las correcciones recalibran y se usan como few-shot (DEC-27). *31/10:* JSONL trazado y GET /correcciones; recalibración CPU implementada contra auditoría SQL y revisiones aprobadas, con separación por equipo, mínimos por estrategia y propuesta sin activar. Ensayo de nueve equipos/544 etiquetas de revisión simulada sintética. Huella de calibración en caché offline. Pares few-shot aprobados servidos por API y utilizados en el contexto del Copiloto; huella de fusión añadida a caché. Pendientes su consumo en extracción/ajuste de fuentes con Lectura y validación con correcciones de uso representativas; piloto manual preparado. [Detalle](API.md#recalibración-desde-las-correcciones-3110).
- [x] **3.9 (I)** Vista Cambios con morph 3D por GUID, fantasma rev1, marcadores Δ y grafo de impacto.
- [x] **3.10 (I)** Momento firma «del plano al modelo» (`/lab/firma`).
- [ ] **3.11 (J)** Guion de 6 min v1 + `.pptx` v0 con la diapositiva «Elegimos con datos».

### Fase 4 · Endurecer (22 – 24 nov)

- [ ] **4.1** Congelar alcance el 22/11 a las 20:00: solo bugs, rendimiento y pulido.
- [x] **4.2** **Modo offline:** `TRAZIA_OFFLINE=1` sirve resultados de modelos cacheados por hash. Si cae la red el viernes, la demo funciona igual. *Implementado 30/10:* caché de visión y copiloto, invalidación y errores recuperables; requiere preparar los cachés antes del ensayo. Además, la API guarda los trabajos validados y en offline los repite sin ejecutar el pipeline: 0,022 s frente a 3,192 s. [Alcance y pruebas](BACKEND_2026-10-30.md).
- [ ] **4.3** Dos ensayos cronometrados del pitch (6:00 exactos) con alguien externo haciendo de jurado de TR.
- [ ] **4.4** `PREVIOUS_WORK.md` redactado; tag preparado.
- [ ] **4.5** Instalación en limpio en **los 4 portátiles** (Windows y Linux) siguiendo solo el README, incluidos los modelos locales descargados de antemano.
- [ ] **4.6** Vídeo de respaldo de la demo (1080p, 60 fps).
- [ ] **4.7** Lista de preguntas difíciles y respuestas (J.5).
- [ ] **4.8** Kit físico: cargadores, regleta, adaptador HDMI/USB-C, ratón, hotspot móvil.
- [ ] **4.9** `THIRD_PARTY.md` con cada dependencia y modelo y su licencia (DEC-30).

### Fase 5 · Hackatón (25 – 27 nov) — plan por horas

**Miércoles 25**
- 09:30 llegada (plaza por orden de llegada). 11:00 presentación de retos.
- Al empezar: tag `pre-hackathon-baseline` + entregar `PREVIOUS_WORK.md` a la organización.
- **Preguntar al mentor** si se autoriza procesar el dataset con APIs externas. Sin respuesta escrita:
  solo modelo local y plataforma (DEC-31).
- Primeras 2 h: descargar el dataset a `data/private/`, inventario automático (`trazia ingest` de todo),
  clasificar por tipología y calidad (vectorial/escaneado). Confirmar convenios (origen, azimut)
  contra un IFC de referencia (DEC-15).
- Hasta la cena: **verdad de referencia de los 4 equipos con IFC** (extraída automáticamente del IFC
  con IfcOpenShell + atributos del HDM a mano). Etiquetar ~20 páginas reales para el ajuste fino del
  detector (DEC-05). Lanzar el **estudio A/B/C/D sobre R-ref con exclusión de uno**. **Análisis de errores.**
- Noche: ajuste fino del detector con las páginas reales; priorizar los 3 modos de fallo con más peso
  en la rúbrica (35 % primero); recalibrar con los datos reales.

**Jueves 26**
- Mañana: arreglar modos de fallo; adaptar familias a la geometría real (p. ej. tipo de fondo, faldón vs patas, boquillas no radiales/inclinadas).
- Mediodía: delta sobre todos los pares rev1/rev2 reales; revisar a mano y medir precisión/recall.
- Tarde: probar en **estáticos B** (sin IFC) y **un mecánico** para demostrar generalización; segunda
  pasada del estudio real; el selector queda fijado con datos reales. Las cifras del estudio pasan al `.pptx`.
- 20:00: **congelación de funcionalidades.** Solo pulido, rendimiento, textos, capturas para el `.pptx`.
- Noche: `.pptx` final con números reales; ensayo completo x2.

**Viernes 27**
- 08:00 congelación total. Bench final, `README` final, tag `entrega-final`.
- 09:00 comprobar que el repo clonado en limpio arranca. 09:30 subir `.pptx` al repo.
- **10:00 entrega.** 11:00 exposición. 13:00 gala de clausura (preparar versión de 3 min por si ganamos).

### Fase 6 · Gala de diciembre (premio general)

- [ ] Integrar feedback del jurado de TR.
- [ ] Pulido visual completo, vídeo de 90 s "cinematográfico" del producto.
- [ ] Caso de impacto con números medidos durante el hackatón (tiempo de revisión por equipo).
- [ ] Versión de pitch para un jurado no especialista: menos IFC, más impacto industrial.

---

## 8. Workstreams en detalle

### A. Ingesta

Objetivo: aceptar **cualquier** cosa que TR nos dé (CAP-01) y no perder nunca el origen.

- [ ] **A.1** Formatos: PDF vectorial, PDF escaneado, imagen (PNG/JPG/TIFF alta resolución), Excel (`.xlsx`, `.xls` vía conversión), PDF de HDM.
- [ ] **A.2** Clasificador de documento por nombre (convención `GAD_<TAG>_revN`, `HDM_<TAG>`, `VESOR_<TAG>`, `ESTRUCTURA_<TAG>`) **y** por contenido (para paquetes vendor, IN-03): página → {GA, HDM, VESOR, nota, otro} con heurística de texto + LLM visual barato.
- [ ] **A.3** Clasificador de página: vectorial con capa de texto / raster → decide extractores.
- [ ] **A.4** Render de páginas a PNG a 200–300 dpi con caché por SHA-256 + miniaturas con **BlurHash/ThumbHash** para el frontend.
- [ ] **A.5** Detección de rotación y orientación de página; deskew en escaneos.
- [ ] **A.6** Agrupación por equipo (TAG) y por revisión; detección de duplicados por hash.
- [ ] **A.7** Límites y seguridad: tamaño, páginas, tipos MIME reales, PDFs cifrados, sin ejecutar macros de Excel.

*Hecho:* todos los archivos del dataset ingeridos, catalogados y agrupados por TAG sin intervención.

### B. Lectura: cuatro estrategias comparadas (25 % y gran parte del 35 %)

**Principio:** los modelos *leen*; las reglas *deciden*; el humano *aprueba*. Ningún valor sin evidencia.
**Decisión de fondo:** las cuatro estrategias de la pág. 13 se implementan y se miden con el mismo
bench ([ESTUDIO.md](ESTUDIO.md), DEC-01/02). Gana la que diga el dato.

**B.0 Interfaz común.** `trazia.pipeline.process(documentos, strategy=…)` llama a una `Strategy`. Cada
estrategia devuelve candidatos con su evidencia (página, caja, canal, modelo y hash del prompt), un
registro de eventos por etapa y su coste (tokens, €, segundos y GPU). El postproceso es común:
reconciliación, calibración, contrato 0.3, familia e IFC.

**B.1 Las cuatro estrategias**

| Estrategia | Qué hace | Piezas | Pregunta clave que responde mejor |
| --- | --- | --- | --- |
| **A · Visión + 3D** | Segmenta vistas y reconstruye la geometría desde los trazos; la escala y las boquillas salen de un modelo de visión o del detector propio | `geometry2d/` (trazos con `pdfplumber`, OpenCV en raster), `vision/` (Qwen3-VL local, Gemini, Mistral, plataforma), detector Florence-2 | Generalización y nivel de detalle |
| **B · Datos + reglas** | Texto vectorial, tablas por cabecera, cotas comprobadas, cajetín, hoja de datos y VESOR con reglas de ingeniería | `extractors/` (existe y se generaliza) + `ocr/` cuando no hay texto | Robustez y explicabilidad |
| **C · RAG** | Recupera el GA más parecido de la biblioteca aprobada y adapta su plantilla y sus parámetros | `rag/` con ColQwen2/ColSmol (visual) + texto | Coste y aprovechamiento de históricos |
| **D · Híbrido** | Cascada B → OCR → detector → modelo de visión en lo dudoso; verificación con la geometría de A; plantilla de C; memoria de la revisión anterior; fusión aprendida y selector por tipo de documento | Todo lo anterior + `reconcile/` + `calibration/` | Incertidumbre y equilibrio coste-acierto |

Ablaciones de D: sin geometría, sin memoria, sin RAG, sin modelo de visión y sin detector.

**B.2 Qué extraer como mínimo (CAP-02) y qué extra:**
- Tag; diámetro interior/exterior; longitud entre tangentes; tipo y altura de fondos; altura total;
  soporte (faldón: altura, diámetro, espesor / patas / silletas: posición y número).
- Por boquilla: marca (N1…), servicio, DN/tamaño, rating, elevación o distancia desde referencia,
  proyección, azimut/orientación, tipo (radial, tangencial, superior, inferior).
- Extra para "valor no previsto": pesos (vacío, operación, prueba), centro de gravedad, material,
  presión y temperatura de diseño, código (ASME VIII…), corrosión admisible.
- Mecánicos (bombas y compresores): envolvente por vistas, bancada y boquillas de aspiración e
  impulsión (nivel de detalle 1, DEC-16).

**B.3 Proveedores de visión (DEC-03, 04)**
- Adaptador `VisionProvider` con salida JSON por esquema, cajas normalizadas, caché por (hash de
  página, versión de prompt, modelo) y modo offline.
- Implementaciones:
  - **Ollama local** (`qwen3-vl:4b`, `qwen3-vl:8b` cuantizado si cabe en los 8 GB);
  - **plataforma IndesIA** (si existe);
  - **Gemini** (cajas `box_2d` nativas);
  - **Mistral OCR 4.1 / Document AI**.
- Las páginas A3 se trocean en mosaicos con solape y las coordenadas se reproyectan.
- **Datos de TR solo con local o plataforma**, salvo autorización escrita (DEC-31). Cada envío queda
  registrado.
- Prompt: instrucción fija; el documento va como **dato delimitado**; se devuelve la unidad tal como
  aparece; pasos (vistas → tabla → cotas → asociación de boquillas → dudas); autoconsistencia con
  N muestras.

**B.4 Detector propio entrenado con nuestro generador (DEC-05)**
- Florence-2 (MIT) ajustado en la RTX 5070 con S-dev: detección de cotas y lectura de región.
- Aleatorización de dominio: fuentes, grosor de línea, ruido, rotación, idioma y unidades.
- El día 1, ajuste fino con ~20 páginas reales etiquetadas en Label Studio.
- **Prohibido YOLO de Ultralytics (AGPL).**

**B.5 Comprobación de cita (DEC-10).** Recortar la caja citada → OCR del recorte → ¿aparece el
número con tolerancia de formato? Si sí, `grounded`; si no, reintento y después `abstained`. El bench
mide la tasa de alucinación por estrategia y proveedor.

**B.6 Reconciliación (DEC-11)**
- Búsqueda exacta de lecturas + mínimos cuadrados ponderados.
- Restricciones:
  - cadena de cotas;
  - fondo 2:1;
  - boquillas dentro de la virola;
  - DN normalizados;
  - azimut en [0, 360);
  - GA ↔ HDM ↔ VESOR ↔ geometría dibujada.
- El valor que rompe una restricción queda `conflict` con su explicación. Nunca se elige en silencio.
- Falta un dato → `abstained`; el valor por defecto de familia se marca como supuesto y solo existe
  en DRAFT.

**B.7 Incertidumbre (DEC-12)**
- Señales: acuerdo entre canales y entre muestras, cita comprobada, calidad del OCR, restricciones
  cumplidas, tipo de fuente, similitud con el caso recuperado.
- Fusión aprendida (regresión logística) → **calibración isotónica** (ECE < 0,05) → **intervalos
  conformes** por valor numérico → curva riesgo-cobertura para fijar el umbral de revisión.

**B.8 Memoria de la revisión anterior (DEC-19).** Al leer la rev2, la rev1 aprobada es el prior: se
alinean las páginas, la lectura se concentra donde cambian y el resto se valida contra la rev1.

**B.9 Coste y latencia (DEC-25).** Registro por trabajo: tokens, llamadas, € según la tabla de
precios versionada, segundos de GPU y segundos totales. Objetivo para D: < 60 s y < 0,50 € por equipo.

*Hecho:*
- Estudio completo con intervalos.
- En S-reservado, la estrategia ganadora con ≥ 95 % de campos correctos en vectorial y ≥ 85 % en
  escaneado.
- Alucinación < 1 % y ECE < 0,05.
- En real, lo que diga la exclusión de uno, con análisis de errores documentado.

### C. Normalización y contrato de datos

- [ ] **C.1** Unidades con `pint`: mm, cm, m, in, ft-in (`5'-6"`), bar(g), barg/bara, kPa, MPa, psi,
  kg/cm², °C, °F, kg, t, lb. Separadores de miles y decimales en español e inglés (`2.000,5` / `2,000.5`)
  decididos por contexto del documento y marcados si son ambiguos.
- [ ] **C.2** Unidad canónica por magnitud y **unidad original conservada** en la evidencia.
- [x] **C.3** Equivalencias en el delta: 10 bar = 1 MPa no es un cambio; 10 bar → 10 MPa sí. *Verificado 28/10:* Equivalencias con Pint y pruebas de cambios equivalentes/incompatibles en `test_plataforma_changes.py`.
- [ ] **C.4** Sistema de referencia documentado: origen, eje Z vertical, azimut (Norte de planta =
  0°, sentido horario como en VESOR **o** el convenio que use TR — confirmar con el IFC de referencia). *31/10:* documentado y probado el convenio interno actual (+Z, 0°=+X, 90°=+Y, antihorario desde +Z; mm→m y conversión web-ifc). Norte/TR todavía sin verificar; permanece parcial. [Contrato](DATA_CONTRACT.md#sistema-de-referencia-interno-c4-3110).

- [x] **C.5** Versionado del esquema + migradores + ejemplos válidos en CI. *Verificado 28/10:* Migración 0.2→0.3 y ejemplos validados en `test_plataforma_contract.py` y `test_pipeline.py`, ejecutados en CI.
- [x] **C.6** JSON exportable "para humanos": también CSV/Excel de campos con evidencia para el ingeniero. *Hecho 28/10:* `trazia fields` exporta ambos formatos con SHA, página/celda, estado, alternativas e intervalos, sin modificar la revisión; [uso](EXPORTACION_CAMPOS.md).
- [x] **C.7** **Contrato 0.3** cerrado de antemano (DEC-13, especificación en
  [COORDINACION-BACKEND.md](COORDINACION-BACKEND.md)): estado por campo, alternativas, intervalo
  conforme, unidad original, procedencia ampliada (estrategia, canal, modelo, prompt), `kind` y `lod`
  por equipo y metadatos de ejecución por revisión. *Verificado 28/10:* Contrato 0.3 implementado y validado; coincide con 1.1.

### D. Geometría paramétrica e IFC (35 %)

**D.1 Familias** (`src/trazia/families/`), cada una con: parámetros, validaciones, defaults marcados,
generador de geometría IFC y prueba de ida y vuelta (parámetros → IFC → parámetros).

| Familia | Componentes | Prioridad |
| --- | --- | --- |
| Recipiente vertical | Virola, fondos (2:1 SE, toriesférico, hemisférico, plano), faldón / patas, boquillas radiales, superiores e inferiores | P0 (existe, mejorar) |
| Recipiente horizontal | Virola, 2 fondos, 2 silletas, boquillas en generatrices | P0 |
| Columna | Virola por tramos (diámetros distintos, conos de transición), faldón, plataformas y escaleras simplificadas (VESOR) | P1 |
| Tanque atmosférico | Virola, techo cónico/domo, fondo plano | P1 |
| Bomba / compresor | Bancada, carcasa y motor como volúmenes simplificados, boquillas de aspiración/impulsión | P1 (generalización a mecánicos) |
| **Envolvente de reserva** | Caja o cilindro envolvente leído de las vistas + puertos; para cualquier tipología no prevista | P0 (el sistema nunca se queda sin modelo) |

**D.1b Niveles de detalle (DEC-16):**
- **1:** envolvente + puertos;
- **2:** familia paramétrica;
- **3:** bridas por DN/rating y plataformas y escaleras del VESOR y de ESTRUCTURA.

Cada equipo declara su nivel en el contrato y en el IFC, y el visor lo muestra.

**D.2 Boquillas:** cuello + brida simplificada (disco con espesor y diámetro según DN/rating de tabla
ASME B16.5 simplificada) — da realismo visual y es útil a piping. Orientación por vector (radial,
tangencial con offset, inclinadas), no solo azimut.

**D.3 IFC "rico" (lo que un ingeniero de TR verá al abrirlo en su visor):**
- Equipo: `IfcTank` (`PRESSUREVESSEL` / `STORAGE` / `VESSEL` según familia), bombas `IfcPump`.
- Componentes agregados (`IfcRelAggregates`); cada boquilla además con `IfcDistributionPort` (dirección
  de flujo, DN) anidado (`IfcRelNests`) → piping puede conectarse a él.
- Psets: estándar donde existan + `TrazIA_Provenance` (documento, página, bbox, confianza, extractor,
  estado de revisión) + `TrazIA_Design` (presión, temperatura, material…).
- `IfcDocumentReference` + `IfcRelAssociatesDocument` → enlace al GA/HDM fuente con su SHA-256.
- `IfcApproval` + `IfcRelAssociatesApproval` → la aprobación humana dentro del IFC (revisor, fecha, huella).
- Estado DRAFT visible: Pset `TrazIA_Status.State = DRAFT` + nombre del archivo.
- GUID estables por ID semántico (existe) → los visores reconocen "el mismo objeto" entre revisiones.
- Exportar **IFC4** (por defecto), **IFC4X3** y **IFC2X3** (compatibilidad con SP3D/Tekla).

**D.4 Validación IFC:** `ifcopenshell.validate` (esquema + reglas) en CI; Hausdorff y Chamfer de
malla con `trimesh` contra la referencia (DEC-18); abrir en ≥ 3 visores
(Bonsai/BlenderBIM, el visor web propio basado en web-ifc, y uno de escritorio tipo xBIM/Solibri
Anywhere/BIMvision) y guardar capturas en `docs/ifc-checks/`. El validador online de buildingSMART
solo con sintéticos.

**D.5 Fidelidad contra referencia:** función que alinea nuestro IFC con el de TR (por bounding box del
equipo y eje) y calcula error por componente (ver G). Iterar familias hasta que el error de forma
dependa solo de la extracción, no de la familia.

### E. Validación y humano en el bucle

- [x] **E.1** Reglas de validación con mensajes claros y accionables (qué pasa y cómo arreglarlo):
  geométricas (boquillas fuera de la virola, solapes entre boquillas, fondos imposibles), de unidades,
  de coherencia entre documentos. *31/10:* 422 con campo/mensaje/acción, avisos de alternativas y cribado de solape radial; no certificación normativa. [Auditoría](AUDITORIA_REVISION.md).
- [x] **E.2** **Cola de revisión priorizada** por `impacto × (1 − confianza)`: primero lo que más daño
  haría si estuviera mal (diámetro, elevaciones de boquillas) y menos seguro está. *31/10:* verificada la cola existente; conflictos y abstenciones primero, todos los campos trazados y supuestos/rechazos pendientes. Impactos declarados por regla.
- [x] **E.3** Acciones por campo: aceptar, corregir (con nueva evidencia opcional), marcar como
  supuesto, rechazar. Todo con **deshacer** y registro de auditoría (quién, cuándo, antes/después). *31/10:* evidencia opcional, rechazo como abstención humana, deshacer completo por auditoría inversa, ETag/instantánea e idempotencia; errores recuperables y exportación JSONL separada. [Detalle](AUDITORIA_REVISION.md).
- [x] **E.4** Aprobación ligada a la huella (existe) + idempotencia + bloqueo si hay `conflict` sin resolver. *Verificado 28/10:* Aprobación vinculada al fingerprint, bloqueo de conflictos y cambios que invalidan aprobación; `test_pipeline.py` y `test_api_base.py`.
- [ ] **E.5** Medir **tiempo de revisión por equipo** con el propio log → cifra de impacto del pitch. *31/10:* sesiones y reloj activo conectados a acciones/auditoría, métricas por revisión y equipo y separación de pruebas. [Piloto manual preparado](MUESTRA_REVISION_MANUAL.md), todavía sin muestra humana ni cifra medida de impacto.
- [ ] **E.6** Aprendizaje activo (DEC-27): corrección aprobada → ejemplo few-shot + recalibración + ajuste de prioridad de fuentes. *31/10:* pares aprobados/recortes por API y contexto del Copiloto, retirada al revocar y exclusión del equipo/documentos consultados; recalibración CPU existente. Pendientes consumo por extractores, evaluación del ajuste de fuentes con Lectura y muestra humana representativa.
- [x] **E.7** Intervalo conforme visible por campo («2.000 mm ± 3 mm, 90 %») y umbral de revisión
  obligatoria fijado con la curva riesgo-cobertura (DEC-12). *Hecho 31/10:* la cola de revisión
  muestra el intervalo («± 0,5° · 90 %») y marca «Confírmelo» en los campos abstenidos. Estos van
  primero, y la explicación sale al seleccionarlos. El umbral es el de riesgo 5 % ajustado en S-dev.
  Comprobado con la API y D sobre la demo V-101; prueba en `web/src/lib/mock/fields.test.ts`. La
  demo sin conexión no trae intervalos.

### F. Revisiones y delta (20 %)

- [x] **F.1** Emparejamiento de entidades rev1↔rev2: boquillas por marca; si cambia la marca, por
  servicio + DN + posición (algoritmo húngaro con coste combinado); detectar **renombrados**, altas y bajas. *Verificado 28/10:* Emparejamiento húngaro, propuestas ambiguas y conservación de identidad en `test_plataforma_changes.py`.
- [x] **F.2** Tolerancias por magnitud (p. ej. ±1 mm, ±0,5°) para no reportar ruido de extracción como cambio;
  distinguir "cambio de diseño" de "cambio de lectura" (misma cota, distinta evidencia/confianza). *Verificado 28/10:* Tolerancias y equivalencias separan el cambio de valor del de procedencia; `test_plataforma_changes.py`.
- [x] **F.3** Clasificar: geométrico, atributo, documental (solo evidencia), de identidad (tag). *Hecho 28/10:* categorías explícitas en cambios, procedencia y documentos; pruebas en `test_plataforma_changes.py`.
- [x] **F.4** **Impacto por disciplina** con reglas explicables (pág. 3 del reto): boquilla movida →
  Piping; faldón/peso → Civil (cimentación) y Estructuras; nueva boquilla → Piping + I&C si es de
  instrumento; cambio de presión/temperatura → Mecánica + Procesos. Severidad y acción sugerida. *Hecho 28/10:* reglas explicadas en `revisions.change_impact`, con pruebas CPU de soporte, peso, conexiones/instrumentación y condiciones de diseño.
- [ ] **F.5** Detectar **nubes de revisión y triángulos Δ** en el GA rev2 (muy comunes en planos reales):
  si la rev2 marca zonas revisadas, se usan como pista y para comprobar que no se nos escapa nada
  (un cambio detectado fuera de una nube, o una nube sin cambio detectado, se señala).
- [x] **F.6** Salidas: `changes.json`, informe legible (Markdown/PDF), **BCF 2.1/3.0** con un topic por
  cambio (vista de cámara, GUID del elemento, descripción) → abre en herramientas BIM de coordinación. *Hecho 28/10:* JSON + Markdown (`trazia diff -o cambios.md`) y BCF 2.1, con pruebas CLI/BCF. La versión 3.0 no está implementada.
- [x] **F.7** El IFC rev2 conserva GUID; la rev1 se conserva intacta (pág. 11: "conservación de la versión anterior"). *Verificado 28/10:* GUID estables y revisión anterior inmutable; `test_pipeline.py`, `test_plataforma_changes.py` y `test_api_base.py`.
- [x] **F.8** **Diferencia visual de páginas** (DEC-19): alinear rev1 y rev2 (ECC de OpenCV) y
  localizar zonas cambiadas en píxeles o trazos. Se cruza con las nubes Δ y con la diferencia de
  campos: un cambio visual sin cambio de campo, o al revés, se señala como sospechoso. *Verificado 28/10:* ECC y cruce de regiones visuales/campos, comprobación SHA y errores de alineación explícitos; pruebas CPU en `test_plataforma_changes.py`.
- [x] **F.9** **Memoria de revisión**: la rev1 aprobada guía la lectura de la rev2 (B.8). Se mide su
  aporte al F1 con la ablación correspondiente. *Hecho 30/10:* igual que 3.2. F1 de cambios: 45,9 %
  con memoria y 51,3 % sin ella, así que no aporta en sintéticos.

*Hecho:* en sintéticos con mutaciones conocidas, F1 ≥ 0,95; en reales, precisión/recall medidos a mano.

### G. Banco de evaluación (GA2MODEL Bench)

Es nuestra arma principal: **llegamos al jurado con su propia rúbrica ya medida.**

- [ ] **G.1 GT automática desde el IFC de referencia:** con IfcOpenShell extraer del `<TAG>.ifc` de TR
  bounding boxes, ejes, radios de virola, posiciones y direcciones de boquillas (identificar elementos
  por nombre/tipo/Pset; si no, por geometría).
- [ ] **G.2 GT manual** para atributos (HDM) y para equipos sin IFC: hoja `bench/gt/<TAG>.yaml` con valor,
  unidad y evidencia. Doble revisión por dos miembros.
- [ ] **G.3 Métricas:**

  | Criterio | Métricas |
  | --- | --- |
  | Geometría 35 % | Error absoluto y relativo por dimensión principal (D, T/T, altura total, faldón); por boquilla: error de posición 3D (mm), de orientación (°), acierto de DN; precisión/recall de boquillas detectadas; IoU volumétrico y distancia de Hausdorff/Chamfer de malla (trimesh) |
  | Atributos 25 % | Exactitud valor+unidad por campo; cobertura; tasa de abstención; **ECE** y diagrama de fiabilidad; Brier score |
  | Delta 20 % | Precisión, recall y F1 de cambios; error en la magnitud del cambio; falsos cambios por ruido |
  | Escala 10 % | s/equipo, €/equipo, tokens, equipos/hora en lote, tasa de aciertos de caché |

- [ ] **G.4** Informe `bench/report.md` + JSON + página "Calidad" en la web con **mapa de calor 3D del
  error** sobre la malla (color por distancia a la referencia).
- [ ] **G.5** Anti-sobreajuste: con 4 IFC de referencia, validación **dejando uno fuera**; sintéticos
  como conjunto grande; reportar siempre por separado sintético / real.
- [x] **G.6** El bench corre en CI sobre sintéticos (regresiones = PR rojo). *Verificado 28/10:* CI ejecuta `test_bench.py`: genera sintéticos, corre el banco real y exige exactitud/IFC/F1 en los casos de referencia; una regresión falla pytest.
- [x] **G.0** Bench v0 y generador v1 hechos ([BENCH.md](BENCH.md)).
- [x] **G.7** **Generador v2** (DEC-21): 8 o más estilos de proveedor (2 reservados), niveles de
  degradación, multipágina, paquetes de proveedor, mecánicos y corpus adversarial. *Verificado 28/10:* Coincide con 1.10: generador v2/v2.1 implementado; semillas, separación de proveedores reservados y degradaciones verificadas en `test_lectura_synthetic.py`.
- [x] **G.8** **Estudio comparativo** ([ESTUDIO.md](ESTUDIO.md)): variantes A/B/C/D y ablaciones,
  bootstrap del 95 %, McNemar, **Puntuación GA2MODEL** (DEC-22), frontera de Pareto coste-acierto y
  recomendación del selector. *Hecho 31/10:* A, B, C y D, ablaciones, McNemar, Pareto y selector en el estudio 3 (ver 2.11 y 3.4).
- [x] **G.9** Métricas nuevas: tasa de alucinación, cobertura de cita, cobertura de intervalos
  conformes, curva riesgo-cobertura y coste por equipo. *Hecho 30/10:* las cinco salen en
  `estudio.json`; la curva riesgo-cobertura sale de `python -m bench.calibrar` ([BENCH.md](BENCH.md)).

### H. Backend, API y escalado (10 %)

- [x] **H.1 Endpoints:**
  - `POST /documents` (multipart, cabecera `Idempotency-Key`, dedupe por SHA-256)
  - `POST /equipment/{tag}/jobs` → `job_id`; `GET /jobs/{id}/events` (SSE: etapa, progreso, logs)
  - `GET /equipment`, `GET /equipment/{tag}/revisions/{rev}`
  - `PATCH /revisions/{id}/fields/{path}` (con `If-Match` / versión para concurrencia optimista)
  - `POST /revisions/{id}/approve` (`Idempotency-Key`)
  - `GET /revisions/{id}/ifc?schema=IFC4|IFC4X3|IFC2X3&draft=`
  - `GET /diff?from=&to=`, `GET /diff/bcf`, `GET /bench`, `GET /plant`
  - `POST /estudio` (lanza el estudio como trabajo) y `GET /estudio` (resultados para la pantalla Estudio)
  - `POST /copiloto` (preguntas con herramientas de solo lectura y citas, DEC-26)
  - *Cierre 30/10:* estudio en cola real, resultados por SHA-256 y API documentada; [pruebas y límites](BACKEND_2026-10-30.md).
- [x] **H.2 Idempotency keys** en todo POST con efecto (subida, jobs, aprobación): repetir la petición
  devuelve el mismo resultado, sin duplicar. Clave guardada 24 h con hash del cuerpo. *Verificado 28/10:* Caducidad de 24 h, huella del cuerpo y respuesta/efecto transaccionales; `Store.perform` y `test_api_base.py`.
- [x] **H.3 Trabajos asíncronos** (DEC-23): interfaz de cola con **dos implementaciones**, en
  proceso (por defecto) y Redis con `arq` y workers (perfil `escala`); reintentos con backoff para los
  modelos, timeouts y cancelación. El estudio comparativo también se lanza como trabajo.
  *Verificado 30/10:* proceso y Redis/arq/Postgres, SSE, idempotencia, timeout, cancelación y persistencia; [evidencias](BACKEND_2026-10-30.md).
- [x] **H.4 Persistencia:** SQLModel sobre SQLite (local) con migraciones Alembic; Postgres en
  `docker-compose.prod.yml` para el discurso de escala. Almacén de archivos direccionado por contenido. *Verificado 28/10:* SQLite/SQLModel/Alembic y Postgres con almacén SHA; pruebas API y los tres perfiles de Compose documentados en FASE1.md.
- [x] **H.5 Observabilidad:** logs estructurados (JSON), traza por job, métricas de coste y latencia. *Verificado 28/10:* Eventos estructurados por trabajo y RunInfo con tiempos, intentos, llamadas y coste; `api/jobs.py` y `test_api_queue.py`. Coste desconocido no se convierte en cero.
- [x] **H.6 Seguridad básica:** CORS restringido, límites de tamaño, sin claves en el repo (`.env.example`),
  documentos tratados como datos. *Verificado 28/10:* CORS, límite de subida, hashes y separación documento/instrucción verificados en las pruebas API; no se afirma una auditoría de seguridad completa.
- [ ] **H.7 Escala (para el pitch):** diagrama con cola, workers horizontales, caché por hash (una
  revisión que solo cambia una página solo reprocesa esa página), coste estimado de un proyecto de
  400 equipos × 4 revisiones. *Parcial 30/10:* diagrama, caché de trabajos por hash y extrapolación
  a 400 × 4 en [FASE3.md](FASE3.md). *31/10:* D/CPU completa 336 trabajos con 173 IFC DRAFT
  válidos y 163 errores, idénticos con 1/4 workers (1,76× en máquina compartida). Se conserva
  el desglose LOD 1/2. Todavía no hay un tiempo defendible para 1.600 IFC válidos. *D aprendido/v5:* 174/162 y 1,63×; OCR incremental comprobado por página, render/pipeline completo pendiente. [Medición nueva](evidencias/fase3/31oct-d-v5/resumen.md).
  - [x] Diagrama reutilizable y calculador de coste paramétrico para 400 × 4: [pitch](PITCH_ESCALA.md).
  - [ ] Medición del ahorro incremental de extremo a extremo por página y presupuesto de IFC válidos; cobertura y muestra humana pendientes.

### I. Frontend: diseño, 3D y animación

> **Lo que queremos:** un diseño **muy profesional**, **cero "AI slop"**, **muchas animaciones con
> propósito** y **mucho 3D**, para que sea lo más vistoso posible **sin dejar de ser una herramienta
> seria de ingeniería**. El jurado debe pensar "esto lo usaría mañana", no "esto es una plantilla".

#### I.1 Skills obligatorias para cualquier persona o agente que toque `web/`

| Skill | Para qué la usamos | Fuente |
| --- | --- | --- |
| **UI UX Pro Max** | Generar el design system inicial (estilo, paleta, tipografías, reglas UX) y consultar guías por dominio | `github.com/nextlevelbuilder/ui-ux-pro-max-skill` |
| **React Flow** | Grafo del pipeline en vivo y grafo de impacto por disciplina | `github.com/mattwoodco/skills` → `skills/react-flow` |
| **Frontend Design (Anthropic)** | Criterio anti-slop: dirección de diseño, tipografía, color, composición, movimiento | `github.com/anthropics/skills` → `skills/frontend-design` |
| **React Best Practices (Vercel)** | Rendimiento: sin cascadas de peticiones, bundle mínimo, renders, data fetching | `github.com/vercel-labs/agent-skills` → `skills/react-best-practices` |

Complementarias ya disponibles en el entorno de Javier: `emil-design-eng` y `apple-design` (pulido y
física del movimiento), `animate` / `review-animations` (construir y auditar animaciones),
`design-taste-frontend` (anti-plantilla), `ask-sonner` (toasts), `pick-ui-library`, `dataviz` (gráficas
del bench). Instalación en el anexo 12.1.

**Regla de uso:** antes de crear una pantalla, el agente abre las capturas de `docs/referencias-estilo/`
(I.2b) y carga Frontend Design + UI UX Pro Max; antes de
hacer PR, pasa React Best Practices y `review-animations` sobre lo tocado.

#### I.2 Dirección de diseño: "del plano al acero"

El vocabulario visual sale **del propio oficio**, no de una plantilla SaaS:
- **Plano:** retícula fina de delineación, líneas de cota con flechas y extensiones, rótulos de cota
  reales, sombreados (hatch) de sección, **nubes de revisión** y **triángulos Δ de revisión** para
  marcar cambios — exactamente como en un GA real.
- **Acero:** el modelo 3D con materiales PBR sobrios (acero cepillado, pintura industrial), iluminación de
  estudio con entorno HDRI suave, oclusión ambiental.
- **Paleta:** la base sale de las **referencias de estilo de la casa** (I.2b): oscuro tipo
  Ciberconciencia y claro tipo PIDS. Sobre esa base, colores con significado fijo: **naranja de
  revisión** solo para cambios, **verde de aprobado** solo para estado aprobado, rojo solo para
  conflicto, ámbar solo para avisos de honestidad ("datos sintéticos"). Cada color significa una cosa;
  nunca decorativo. Contraste AA verificado.
- **Tipografía:** la misma sans neutra de las referencias (Inter o Geist), para que el producto tenga
  continuidad con los proyectos anteriores del equipo; la mono **solo** para códigos cortos (id de
  etapa, GUID, hash, atajo `Ctrl K`). Escala tipográfica en tokens. Cifras **siempre tabulares** en
  tablas, KPI y valores.
- **Modo claro y oscuro** reales: oscuro = "sala de control" (**por defecto en la demo**, el 3D luce
  más), claro = "mesa de delineación". Botón "Modo claro/oscuro" al pie de la barra lateral, como en
  Ciberconciencia.

**Prohibido (AI slop):** degradados morado-azul, glassmorphism por defecto, "✨ AI" y destellos, iconos
emoji, héroes de "número grande + etiqueta + degradado", rejillas de tarjetas idénticas que no
aportan información distinta (las filas de KPI de las referencias **sí** valen: cada tarjeta tiene su
icono, su dato, su contexto y su micrográfica), eyebrows en mayúsculas espaciadas encima de cada título
(las mayúsculas pequeñas se reservan para grupos de la barra lateral, cabeceras de tabla y etiquetas de
KPI, como en las referencias), cerebros/robots/"redes neuronales"
decorativas, lorem ipsum, testimonios falsos, componentes shadcn sin personalizar, animar todo al
hacer scroll, sombras gigantes difusas, bordes redondeados de 24 px en todo, textos tipo "Unlock the
power of AI". Microcopy en español claro, en voz activa, con los mismos nombres de acción en todo el
flujo ("Aprobar" → "Aprobado").

#### I.2b Referencias de estilo de la casa (obligatorias)

El frontend tiene que parecer **de la misma familia** que nuestros proyectos anteriores. Las capturas
están en [`docs/referencias-estilo/`](referencias-estilo/) y **cualquier persona o agente que toque
`web/` las abre antes de diseñar una pantalla**. No se copian píxel a píxel: se reutilizan su estructura,
su densidad, su tono y sus patrones, adaptados a la ingeniería de equipos.

| Captura | Qué tomamos de ella |
| --- | --- |
| `01-pids-taxis-panel-claro.png` (PIDS · Taxis NYC) | **Modo claro**: fondo frío, tarjetas blancas, fila de KPI con icono en círculo tintado + micrográfica, píldora de estado en vivo, control segmentado `6 h / 12 h / 24 h`, tabla ordenable con id en gris (`#230`) y números alineados a la derecha, botón flotante de asistente |
| `02-albertitos-etapas-pipeline.png` (Albertitos) | **Tarjetas de etapa del pipeline**: icono en baldosa, nombre + código mono (`ingest`), insignia de estado ("Al día" / "Con errores"), **anillo de salud** 0–100 %, descripción de una línea, rejilla 2×2 de métricas (OK, reintentos, latencia, coste), botón "Ver eventos ›", carrusel horizontal con barra; KPI "Coste acumulado"; tabla "Últimos eventos" de todas las etapas |
| `03-ciberconciencia-escena-3d.png` (Ciberconciencia) | **Modo oscuro y escena 3D**: barra lateral agrupada por secciones, migas de pan, píldoras de contexto en la barra superior (dataset, "Datos simulados · sin backend", Copiloto, `Buscar Ctrl K`), escena isométrica con zonas etiquetadas, conmutador `2D / 3D`, modos de cámara ("Vista general" / "Seguir el ataque"), controles de cámara arriba a la derecha, leyenda abajo a la derecha, caja de narración con ▶ abajo a la izquierda, panel lateral de asistente, cronología en vivo debajo |
| `04-ciberconciencia-mapa-mundial.png` (Ciberconciencia) | **Página de visualización**: título + frase que explica qué se ve, aviso ámbar de "ilustrativo" con enlaces, fila de 4 KPI, barra de herramientas del lienzo (2D/3D, indicador "Demo en directo" con reloj, filtros desplegables, pausa, reiniciar), panel de detalle con **estado vacío útil** ("Sigue una ruta" + instrucción), pie con atribución de datos y leyenda de severidad |

**Tokens medidos en las capturas** (punto de partida de `web/src/styles/tokens.css`):

| Token | Oscuro (Ciberconciencia) | Claro (PIDS) | Uso |
| --- | --- | --- | --- |
| `--bg` | `#0E131A` | `#F3F6FB` | Fondo de página |
| `--surface` | `#161D26` | `#FFFFFF` | Tarjetas, paneles, escena |
| `--surface-sunken` | `#10161E` | `#F1F5F9` | Barra superior / cabecera de tabla |
| `--sidebar` | `#121820` | `#FFFFFF` | Barra lateral |
| `--border` | `#2A3441` | `#E6EDF5` | Bordes y separadores de 1 px |
| `--text` | `#F0F4F9` | `#1E293B` | Texto principal |
| `--text-strong` | `#F0F4F9` | `#1E3A8A` | Títulos (azul marino en claro) |
| `--text-muted` | `#9EABBB` | `#6A7B90` | Texto secundario, ids, ejes |
| `--accent` | `#86AEE8` | `#3B82F6` | Selección, botones activos, barras |
| `--accent-soft` | `#1F3150` | `#E8F1FF` | Fondo del ítem activo de navegación |
| `--live` | `#53A47F` | `#00BC7D` | Punto "en vivo" / "al día" |
| `--danger` | `#F07468` | `#E5484D` | Conflicto, error |
| `--warning-bg` | `#242423` + texto ámbar | `#FFF7E6` + texto ámbar | Avisos de honestidad |
| `--assistant` | `#6D4AFF` | `#6D4AFF` | Solo el botón y el panel del asistente |
| `--revision` | naranja (definir, AA) | naranja (definir, AA) | Cambios rev1→rev2, nubes Δ |
| `--approved` | verde (definir, AA) | verde (definir, AA) | Estado aprobado |

Paleta alternativa opcional: el tono cálido de Albertitos (`#F2F2E8` fondo, `#F8F8F1` superficie,
`#506C63` primario, `#B8D8CA` progreso) como tema "papel"; solo si sobra tiempo.

**Forma y densidad comunes a las 4 referencias:**
- Radios de 10–14 px en tarjetas y 8 px en botones y píldoras; bordes de 1 px en lugar de sombras grandes
  (sombra mínima o ninguna).
- Barra lateral fija de unos 235 px, plegable: logotipo en baldosa + nombre + subtítulo
  ("TrazIA-3D · Técnicas Reunidas"), navegación icono + texto, ítem activo con fondo `--accent-soft`,
  grupos con etiqueta pequeña en mayúsculas, sección "Próximamente" con la fase entre paréntesis.
- Al pie de la barra lateral: **tarjeta de demostración** ("Datos sintéticos de la demo · Ocultar · Ver
  con dataset real"), conmutador de tema y salida.
- Cabecera de página: título + **una frase que dice qué se ve y de dónde salen los datos** ("Todo sale
  del IFC generado y de la tabla de evidencias").
- Iconos de trazo fino (1,5 px) del mismo juego en toda la app, siempre dentro de una baldosa o círculo
  tintado cuando acompañan a un KPI.
- Densidad media-alta, texto de 13–14 px en tablas, mucho aire entre bloques y poco dentro de ellos.

**Patrón → dónde va en TrazIA-3D:**

| Patrón de referencia | Pantalla de TrazIA-3D |
| --- | --- |
| Píldora "Tiempo real: Spark publicó hace 36 s" | Barra superior: "Pipeline: último trabajo hace 12 s · 3 en cola" |
| Fila de KPI con micrográfica | Proyecto: equipos procesados, % campos aprobados, conflictos abiertos, coste acumulado |
| Tarjetas de etapa con anillo de salud | Pantalla **Pipeline**: Ingesta, Clasificación, Extracción, Reconciliación, Geometría, IFC, Validación — cada una con su anillo, métricas y "Ver eventos" (complementa el grafo React Flow) |
| Tabla "Últimos eventos" | Debajo de las etapas: documento, etapa, estado, latencia, detalle, cuándo |
| Escena isométrica con zonas etiquetadas | **Planta**: equipos del lote sobre el plot plan, agrupados por área, etiquetas flotantes con el tag |
| "Vista general / Seguir el ataque" | Delta: "Vista general / **Seguir el cambio**" — la cámara viaja de un cambio al siguiente |
| Caja de narración con ▶ | Delta y momento firma: "Reproducir los cambios de la rev2" con texto que acompaña cada paso |
| Panel "Asistente de respuesta" | Panel **Copiloto de revisión**: explica por qué un campo tiene baja confianza o está en conflicto, con citas |
| Leyenda abajo a la derecha | Visor 3D: aprobado / DRAFT / supuesto / cambiado / conflicto |
| Aviso ámbar "ilustrativo" | Siempre que se vean datos sintéticos: "Datos sintéticos · no son del dataset de TR" |
| Estado vacío "Sigue una ruta" | Panel de detalle sin selección: "Selecciona una boquilla o una cota para ver su evidencia" |
| Control segmentado `6 h / 12 h / 24 h` | Selección de revisión `rev1 / rev2 / Δ` y de vista `Iso / Alzado / Planta` |
| Botón flotante "TAXI AI" | Botón flotante "Copiloto" (abre el panel) |
| `Buscar Ctrl K` en la barra superior | Menú de comandos (I.8) |

Estas referencias **tienen prioridad** sobre el design system que genere UI UX Pro Max: ese skill se usa
para completar lo que las capturas no definen (estados, gráficas, escala tipográfica), no para cambiar
el estilo.

#### I.3 Stack frontend

| Necesidad | Elección |
| --- | --- |
| Framework | Next.js (App Router) + React 19 + TypeScript estricto |
| Estilos | Tailwind CSS v4 con tokens CSS propios (color, tipo, radios, sombras, duraciones, curvas) |
| Componentes base | Radix UI primitives (accesibles) estilizados a mano |
| 3D | three.js + @react-three/fiber + @react-three/drei + @react-three/postprocessing (SSAO, outline de selección, bloom muy sutil) |
| IFC | `web-ifc` en **Web Worker** → geometrías Three.js indexadas por GUID; `three-mesh-bvh` para picking rápido |
| Grafos | `@xyflow/react` (React Flow) |
| PDF | pdf.js (`react-pdf`) con capa de overlays (bboxes de evidencia) |
| Datos servidor | TanStack Query (stale-while-revalidate, optimistic updates) |
| Estado cliente | Zustand (selección compartida PDF ↔ 3D ↔ campos) |
| Animación UI | Motion (framer-motion) + View Transitions API |
| Animación 3D | Muelles (`@react-spring/three` o `maath`) + `CameraControls` de drei (interrumpible) |
| Toasts | Sonner (con "Deshacer") |
| Menú de comandos | `cmdk` |
| Tablas | TanStack Table (+ virtualización si hay muchos equipos) |
| Gráficas | visx o Recharts con el skill `dataviz` |
| Tipos API | `openapi-typescript` generado desde FastAPI |
| Tests | Vitest + Testing Library + **Playwright** (flujo de demo completo) |

#### I.4 Pantallas

1. **Proyecto / Planta.** Vista de planta 3D (plot plan, IN-04) con todos los equipos del lote como
   volúmenes; color por estado (DRAFT, en revisión, aprobado, con cambios). Tabla de equipos con salud
   de datos (% campos aprobados, conflictos). Aquí se cuenta la **escala**.
2. **Ingesta + Pipeline en vivo.** Soltar documentos; **grafo React Flow** del pipeline
   (Ingesta → Clasificación → Extractores en paralelo → Reconciliación → Familia → IFC → Validación) con
   nodos que se iluminan según los eventos SSE, contadores de campos por nodo y tiempo por etapa.
   Nodos memoizados, `nodeTypes` fuera del componente, `fitView`, sin marca de agua.
3. **Espacio de revisión (pantalla principal).** Tres paneles enlazados:
   - Izquierda: **plano PDF** con recuadros de evidencia; hover en un campo → zoom suave a su recorte.
   - Centro: **visor 3D** del IFC; el elemento del campo seleccionado se resalta con contorno y su
     **cota 3D** aparece dibujada como en el plano.
   - Derecha: **cola de campos** por riesgo: valor, unidad, barra de confianza, estado, alternativas,
     acción. Teclado: `J/K` siguiente/anterior, `A` aceptar, `E` editar, `S` marcar supuesto, `⌘Z` deshacer.
   - Selección **bidireccional**: clic en una boquilla en 3D → su fila y su recorte del plano; clic en
     una cota del PDF → el elemento 3D.
4. **Delta rev1 → rev2.** Ver I.6. Lista de cambios con nubes Δ, severidad, disciplina afectada y
   acción; **grafo de impacto React Flow** (cambio → elementos → disciplinas MEC/EST/CIV/PIP/ELE/I&C);
   botones "Exportar BCF" y "Informe".
5. **Aprobación y publicación.** Resumen, huella, revisor, pendientes; al aprobar, animación de
   "sellado" (el sello se estampa sobre el cajetín virtual) y el IFC pasa de DRAFT a aprobado.
6. **Calidad (Bench).** Tabla por criterio del jurado, diagrama de fiabilidad, **mapa de calor 3D del
   error** sobre la malla comparada con la referencia de TR (superpuesta en fantasma).
7. **Impacto.** Calculadora de ROI con los datos de TR (300–500 equipos, 3–5 revisiones, 2–4 h) y nuestro
   tiempo de revisión medido.
8. **Estudio (DEC-28).** La respuesta visual a la pág. 13:
   - tabla A/B/C/D y ablaciones de D con intervalos del 95 %;
   - **frontera de Pareto** coste-acierto;
   - resultados por estilo, proveedor de visión y nivel de degradación;
   - tasa de alucinación;
   - la recomendación del selector con su justificación.

   Mismo lenguaje visual que Bench.
9. **Copiloto con modelo local (DEC-26).** El panel actual pasa de reglas a un modelo local con
   herramientas de solo lectura. Cada respuesta cita evidencia, propone y nunca modifica.

#### I.5 3D: todo lo que debe poder hacer el visor

- [x] Carga del IFC en Worker con barra/skeleton; nunca congela la UI. *Hecho:* ver 1.7.
- [ ] Órbita, paneo y zoom suaves e **interrumpibles**; "fly-to" a un elemento con muelle; doble clic = encuadrar.
- [ ] Selección con resaltado (outline) y **hit slop**: zona de picking ampliada para boquillas pequeñas.
- [x] Aislar / ocultar / transparentar componentes; árbol IFC (proyecto → equipo → componentes → puertos).
- [ ] **Plano de corte** animado (ver interior, espesores) con relleno de sección rayado (hatch).
- [x] **Vista explosionada** animada (virola, fondos, faldón y boquillas se separan a lo largo de su eje).
- [ ] **Cotas 3D** generadas a partir de los parámetros y ancladas a la geometría IFC, con la misma
  estética que el plano; al pasar el ratón muestran valor, unidad, confianza y fuente.
- [x] **Rosa de orientación** (anillo de azimut 0–360° en planta) con las boquillas proyectadas: cruza
  con el VESOR.
- [ ] Vistas guardadas: isométrica, alzado, planta, "como el plano" (cámara ortográfica alineada con la
  vista del GA para poder superponer plano y modelo).
- [ ] Supuestos (valores por defecto de familia) dibujados con material distinto (rayado o translúcido).
- [ ] Rendimiento: `frameloop="demand"`, instancing para elementos repetidos, BVH, ≤ 200 k triángulos a
  60 fps en un portátil normal; DPR adaptativo. *31/10:* escena IFC con tres recortes en
  **157.538 triángulos y 235.3 fps** (RTX 5070, DPR 1): techo de 200 k cumplido. Render a
  demanda, instancing y BVH conservados. Falta verificarlo en otro portátil normal.
- [x] Giro automático de cámara **360°** alrededor del eje del modelo, una vuelta por minuto,
  con pausa manual, pausa por interacción, sincronización A | B y movimiento reducido.
  Comprobado: 385.7° en 64.2 s, radio estable; capturas y medidas en el informe 3D.
- [ ] Captura de pantalla del visor en PNG para el informe y el BCF.

#### I.6 Momentos firma (lo que el jurado recordará)

1. **"El plano se convierte en modelo"** (carga inicial y diapositiva 4 del pitch): la página del GA aparece
   plana en el espacio 3D; las cotas extraídas se iluminan una a una sobre el plano (orden de lectura
   del pipeline); las líneas de la vista de alzado se levantan y se **extruyen** en el recipiente real
   (leído del IFC), que pasa de alambre azul a acero. 4–6 s, una sola vez, saltable, respeta
   `prefers-reduced-motion`.
2. **Morph de revisión rev1 → rev2:** la rev1 queda como fantasma azul de alambre; los elementos se
   emparejan **por GUID** y se interpolan sus transformaciones (N3 sube 200 mm, el faldón se alarga
   150 mm) con un control deslizante de "tiempo de revisión" que el presentador arrastra. El fotograma
   final es exactamente el IFC rev2 (no inventamos geometría). Nubes de revisión naranjas aparecen en
   3D sobre lo cambiado, con su etiqueta "+200 mm".
3. **Mapa de calor del error** contra la referencia de TR: el jurado ve, en color, dónde y cuánto nos
   desviamos (y que es poco).
4. **Pipeline vivo:** el grafo React Flow encendiéndose mientras se procesa un equipo real en directo.

Ninguno es decorativo: los cuatro explican algo. Fuera de estos momentos, la interfaz es sobria.

#### I.7 Animación: reglas

- Cada animación responde a una acción o explica un cambio de estado. Nada de entradas fade+slide en
  cada sección ni hover animado en cada tarjeta.
- Duraciones de UI 120–240 ms con ease-out; salidas más rápidas que entradas; muelles para 3D y
  arrastres. Tokens de duración y curva en CSS, no números sueltos.
- **Interrumpibles:** cualquier transición (cámara, paneles, morph) se puede cortar y redirigir a mitad
  sin saltos.
- Solo `transform` y `opacity` en la UI (nada que provoque layout).
- `prefers-reduced-motion`: se sustituyen por fundidos cortos; el momento firma se reduce a un corte.
- Revisión de cada PR que toque animación con `review-animations`.

#### I.8 Detalles de calidad: qué incorporamos de la lista

| Detalle | ¿Entra? | Dónde y cómo |
| --- | --- | --- |
| 1. Skeleton loaders | **Sí** | Carga de IFC, cola de campos, tabla de equipos y miniaturas de páginas; con la forma real del contenido |
| 2. Optimistic updates | **Sí** | Aceptar/corregir campo y cambiar estado: la UI cambia al instante con TanStack Query y se revierte si la API falla |
| 3. Command menu | **Sí** | `⌘K`/`Ctrl+K` (cmdk): saltar a equipo, boquilla o campo, cambiar de vista, exportar IFC/BCF, comparar revisiones |
| 4. Shortcut hints | **Sí** | Atajos visibles en tooltips y en el menú de comandos; panel `?` con todos |
| 5. Undo toasts | **Sí** | Sonner: "Campo aceptado · Deshacer" durante 5 s; también para descartar evidencias |
| 6. Stale-while-revalidate | **Sí** | TanStack Query: listas de equipos, revisiones y bench se muestran desde caché y se revalidan |
| 7. Pre-rendering | **Parcial** | Pre-renderizar las páginas estáticas (portada, informe de impacto); en la app, **prefetch** del IFC y de la revisión siguiente al pasar el ratón |
| 8. BlurHash placeholders | **Sí** | Miniaturas y páginas de PDF (generadas en la ingesta con ThumbHash/BlurHash) |
| 9. View transitions | **Sí** | Cambio entre pantallas y paso de lista de equipos → espacio de revisión (el volumen del equipo "vuela" a su sitio) |
| 10. Swipe-to-dismiss sheets | No | Aplicación de escritorio; sin hojas móviles |
| 11. Interruptible animations | **Sí** | Cámara 3D, morph rev1→rev2, paneles; ver I.7 |
| 12. Predictive back | No | Gesto de Android; no aplica |
| 13. Hit slop | **Sí** | Picking 3D de boquillas pequeñas y asas de recuadros en el PDF; botones de icono con área ≥ 32 px |
| 14. Safe area insets | No | Sin objetivo móvil (solo tener `viewport-fit` correcto si se enseña en una tablet) |
| 15. One time code autofill | No | Sin autenticación por código |
| 16. Tabular numbers | **Sí, imprescindible** | `font-variant-numeric: tabular-nums` en todos los valores de ingeniería, tablas, deltas y métricas |
| 17. Balanced headlines | **Sí** | `text-wrap: balance` en títulos; `text-wrap: pretty` en párrafos |
| 18. Continuous corners | Opcional | Esquinas tipo squircle (`corner-shape` donde haya soporte) en paneles y diálogos; solo si queda tiempo |
| 19. Idempotency keys | **Sí** | Subidas, lanzar jobs y aprobar (H.2); el frontend genera la clave por acción |
| 20. Amazon safe triangle | **Sí** | Submenús del menú contextual del árbol IFC y de las acciones de boquilla (Radix lo resuelve; verificarlo) |

#### I.9 Accesibilidad, rendimiento y pulido

- Contraste AA, foco visible, todo operable con teclado (incluido seleccionar elementos 3D desde el árbol).
- Presupuestos: JS inicial < 250 KB gz sin el chunk 3D (que se carga en diferido); LCP < 2 s en local;
  INP < 200 ms; visor a 60 fps.
- React Best Practices: sin cascadas de `await` (paralelizar con `Promise.all`), imports directos sin
  barrels, `dynamic()` para 3D/PDF/React Flow con `ssr: false`, estado derivado en render, sin
  componentes definidos dentro de componentes.
- Estados vacíos, de error y de carga diseñados (no texto por defecto). Errores que dicen qué pasó y
  cómo arreglarlo.
- Favicon, título por pantalla, metadatos, página 404 propia.

### J. Pitch, presentación y negocio

**J.1 Estructura de 6 minutos** (sigue la pág. 15 del reto; regla narrativa: plano → dato → modelo →
cambio → decisión):

| Tiempo | Bloque | Qué se ve | Qué se dice |
| --- | --- | --- | --- |
| 0:00–0:45 | Problema | Un GA real anonimizado y la cifra 1.800–10.000 h | "La geometría viaja como documento, no como dato" |
| 0:45–1:30 | Input | Soltamos el paquete del equipo; pipeline vivo | Ingesta autónoma, hashes, clasificación |
| 1:30–2:30 | Extracción | Espacio de revisión: valor → recorte del plano → confianza e intervalo; **pantalla Estudio**: A/B/C/D y Pareto | «Probamos las cuatro estrategias que proponéis y elegimos con datos»; cita comprobada; intervalos conformes |
| 2:30–3:45 | 3D | Momento firma: el plano se convierte en modelo; IFC abierto también en un visor externo | IFC4 con puertos, trazabilidad y aprobación dentro |
| 3:45–5:00 | Cambio | Morph rev1→rev2, nubes Δ, grafo de impacto, BCF | "Qué cambió, cuánto, dónde y a quién afecta" |
| 5:00–6:00 | Impacto y escala | Bench contra el IFC de TR + lote de todo el dataset + ROI | Números medidos, límites honestos, siguientes pasos |

**J.2 `.pptx`** (obligatorio por bases): 8–10 diapositivas con el mismo lenguaje visual que la app.
- Capturas y números **reales del dataset**.
- Una diapositiva de arquitectura.
- **«Elegimos con datos»**: la tabla del estudio A/B/C/D con intervalos y la frontera de Pareto. Es
  la respuesta directa a la pág. 13 y nuestra diapositiva más diferencial.
- Una de "qué hicimos antes y durante el evento".
- Una de límites y siguientes pasos.

Se guarda en `pitch/` del repo antes de las 10:00.

**J.3 Demo:** en vivo sobre la app, con el **modo offline** activado de reserva y el vídeo listo en
otra pestaña. Ratón físico. Pantalla a 1920×1080, zoom de interfaz ajustado para el proyector, modo claro
si la sala es luminosa.

**J.4 Caso de negocio:** con datos de TR (pág. 5): 400 equipos × 4 revisiones × 3 h ≈ 4.800 h/proyecto de
modelado transcriptivo. Si nuestra revisión asistida tarda **T min medidos** por revisión, el ahorro es
4.800 h − 1.600 × T/60. Presentarlo como hipótesis con el tiempo **medido** durante el hackatón, no
inventado. Añadir valor cualitativo: menos errores tardíos (interferencias, campo), disciplinas
sincronizadas, atributos consultables.

**J.5 Preguntas difíciles (preparar respuesta de 20 s para cada una):**
- ¿Qué pasa con planos escaneados o de mala calidad? → OCR + VLM + abstención + revisión priorizada; métricas separadas.
- ¿Y si la IA se inventa una cota? → Grounding check; sin evidencia no hay valor; DRAFT + aprobación.
- ¿Escala a 500 equipos? → Lote medido, caché por hash, workers, coste por equipo.
- ¿Confidencialidad si usáis un LLM externo? → Adaptador intercambiable: modelos de la plataforma o
  locales; nada sale sin autorización; procesamiento local por defecto.
- ¿Se integra con SP3D / Tekla? → IFC2X3/IFC4 estándar con puertos y GUID estables; BCF para coordinación.
- ¿Por qué no reconstrucción geométrica libre? → Trade-off pág. 13: paramétrico = robusto y comparable.
- ¿Por qué no usar solo un modelo de visión? → Lo medimos: estrategia A frente a D. Cifra de
  alucinación, coste por equipo y acierto en estilos no vistos.
- ¿Un detector entrenado con planos sintéticos sirve con planos reales? → Aleatorización de dominio,
  medido en estilos reservados y ajuste fino con ~20 páginas reales; cifra de exclusión de uno.
- ¿Qué significa el «± 3 mm»? → Intervalo conforme: cobertura del 90 % garantizada y comprobada
  empíricamente.
- ¿Habéis mandado nuestros planos a una IA externa? → No: modelo local en el portátil (o el de la
  plataforma). Registro de envíos para demostrarlo.
- ¿Qué parte existía antes? → `PREVIOUS_WORK.md`, enseñado al inicio.
- ¿Cuánto cuesta por equipo? → Cifra medida (B.8).
- ¿Qué haríais con 3 meses más? → Más familias, entrenamiento con históricos de TR, integración con su CDE.

**J.6 Reparto en el escenario:** 2 personas hablan (problema/impacto y demo), 1 conduce la demo, 1 vigila
tiempo y tiene el vídeo listo. Todos pueden responder preguntas de su área.

---

## 9. Calidad, pruebas y CI

- **Python:** ruff (lint + formato), pytest (existente) + tests por extractor con fixtures sintéticas,
  tests de ida y vuelta de familias, validación IFC, tests de API, bench sintético con umbrales.
- **Web:** ESLint + typecheck estricto, Vitest para lógica, **Playwright** que recorre la demo entera
  (ingesta → revisión → aprobación → delta → exportación) en CI, capturas de regresión visual de las
  pantallas clave.
- **CI** (GitHub Actions): Windows + Linux para Python (existe), job web, job de autoría (existe),
  job de bench sintético y **estudio reducido** (B y D sin modelos de visión, con caché), artefactos
  (IFC, BCF, informe del bench y del estudio). Los modelos de visión no corren en CI: se usan
  respuestas cacheadas y versionadas.
- **Definition of Done de un PR:** CI verde, tests nuevos para lo nuevo, sin coautores, sin datos
  privados, documentación tocada si cambia el contrato, capturas si cambia la UI.
- **Reproducibilidad:** `uv.lock` y `pnpm-lock.yaml` comprometidos, semillas fijas en el generador
  sintético, versión de prompts y modelos registrada en cada resultado.

---

## 10. Riesgos y planes B

| Riesgo | Prob. | Impacto | Mitigación / plan B |
| --- | --- | --- | --- |
| No hay dataset hasta el día 1 | Alta | Alto | Generador sintético realista + bench listo para ejecutarse sobre reales en la primera hora |
| GA reales muy distintos a los sintéticos | Media | Alto | Arquitectura de extractores enchufables; día 1 dedicado a análisis de errores; VLM como comodín |
| La plataforma IndesIA limita qué LLM usar o la red | Media | Alto | Adaptador de proveedor; OCR y reglas locales funcionan sin LLM; modo offline cacheado |
| Wi-Fi caído en la demo | Media | Alto | Modo offline + vídeo de respaldo + hotspot móvil |
| Frontend no llega a tiempo | Media | Alto | Streamlit sigue funcionando como fallback hasta la congelación del 22/11 |
| Sobreajuste a 4 equipos | Media | Medio | Validación dejando uno fuera + sintéticos + estáticos B |
| Familias no cubren la geometría real | Media | Alto | Priorizar la familia que más aparezca en el dataset; "supuestos" visibles en lugar de inventar |
| Agentes que se pisan o rompen `main` | Media | Medio | Mapa de propiedad, worktrees, PR + CI obligatorio |
| Commit con coautor en el historial | Baja | Medio | Hook local + check en CI + revisión antes de push |
| Rendimiento 3D pobre en el proyector/portátil | Baja | Medio | Presupuesto de triángulos, DPR adaptativo, ensayo en el portátil de la demo |
| Agotamiento | Alta | Medio | Turnos de descanso el día 2; nadie programa después de las 02:00 |
| Cuatro estrategias no llegan a tiempo | Media | Alto | B y D tienen prioridad; A y C con versión mínima medible el 14/11; el estudio vale aunque una estrategia sea básica, si se dice |
| Enviar datos de TR a un tercero sin permiso | Baja | **Descalificación** | Solo modelo local o plataforma por defecto; autorización escrita para APIs externas; registro de envíos (DEC-31) |
| Licencia AGPL en una dependencia | Media | Alto | Lista negra (Ultralytics, PyMuPDF) y `THIRD_PARTY.md` revisado antes de la entrega (DEC-30) |
| El modelo local no cabe o va lento en 8 GB | Media | Medio | `qwen3-vl:4b` como mínimo; mosaicos; caché; plataforma o API como alternativa medida |
| El detector entrenado con sintéticos falla con planos reales | Media | Medio | Aleatorización de dominio, estilos reservados, ~20 páginas reales etiquetadas el día 1, D cae a B y al modelo de visión |
| Sobreajuste del estudio al generador propio | Media | Alto | Estilos reservados nunca vistos y resultados reales con exclusión de uno, siempre separados de los sintéticos |

---

## 11. Checklists de entrega

### Antes del 25/11
- [ ] 4 inscritos y formación de plataforma hecha
- [ ] `main` verde; `docker compose up` y `uv run` funcionan en los 4 portátiles
- [ ] Bench listo para apuntar a `data/private/`
- [ ] `PREVIOUS_WORK.md` redactado; tag preparado
- [ ] Modo offline probado; vídeo de respaldo grabado
- [ ] Kit físico preparado

### Entrega viernes 27/11 · 10:00
- [ ] Repo con código final, tag `entrega-final`, CI verde
- [ ] `README.md` con: qué es, cómo ejecutar en 3 comandos, arquitectura, métricas reales, límites
- [ ] `pitch/TrazIA-3D.pptx` subido
- [ ] `bench/report.md` con resultados sobre el dataset (sin incluir documentos del dataset)
- [ ] `PREVIOUS_WORK.md`, `LICENSE` (MIT), `CONTRIBUTING.md`
- [ ] Ningún archivo del dataset ni secreto en el historial (`git log --all -- data/` vacío; búsqueda de claves)
- [ ] Todos los commits de los 4 miembros, **sin coautores** (`git log --format='%an <%ae>%n%b' | grep -i co-authored` vacío)
- [ ] IFC de ejemplo (sintético) que abre sin errores en un visor externo

### Demo (antes de entrar a la sala)
- [ ] Portátil enchufado, notificaciones desactivadas, pestañas preparadas, zoom ajustado
- [ ] Estado inicial de la demo reseteado con un comando (`trazia demo reset`)
- [ ] Vídeo de respaldo abierto; modo offline listo
- [ ] Cronómetro

---

## 12. Anexos

### 12.1 Instalar las skills en el repo

Para que **todos** los agentes de los 4 miembros las tengan, se instalan dentro del repo
(Claude Code lee `.claude/skills/`; Codex lee `.agents/skills/`).

```bash
# UI UX Pro Max (CLI oficial)
npx ui-ux-pro-max-cli init --ai claude
npx ui-ux-pro-max-cli init --ai codex
```

```bash
# React Flow, Frontend Design y React Best Practices (copiar la carpeta de la skill)
npx degit mattwoodco/skills/skills/react-flow .claude/skills/react-flow
npx degit anthropics/skills/skills/frontend-design .claude/skills/frontend-design
npx degit vercel-labs/agent-skills/skills/react-best-practices .claude/skills/react-best-practices
```

```bash
# Misma copia para Codex
cp -r .claude/skills/react-flow .claude/skills/frontend-design .claude/skills/react-best-practices .agents/skills/
```

Alternativa en Claude Code para UI UX Pro Max: `/plugin marketplace add nextlevelbuilder/ui-ux-pro-max-skill`
y `/plugin install ui-ux-pro-max@ui-ux-pro-max-skill`. Generar el design system de TrazIA-3D:

```bash
python3 .claude/skills/ui-ux-pro-max/scripts/search.py "industrial engineering BIM 3D review tool" --design-system --persist -p "TrazIA-3D" -f markdown
```

El resultado (`design-system/trazia-3d/MASTER.md`) es un **punto de partida**: se revisa contra I.2 y se
descarta todo lo que suene a plantilla.

### 12.2 Hook `commit-msg` (rechaza coautores y firmas de IA)

`.githooks/commit-msg`:

```sh
#!/bin/sh
# Rechaza commits con coautores o firmas de herramientas.
msg_file="$1"
if grep -Eiq '^[[:space:]]*co-authored-by:' "$msg_file"; then
  echo "ERROR: no se permiten líneas Co-authored-by en este repositorio." >&2
  exit 1
fi
if grep -Eiq 'generated with|generated by|noreply@anthropic\.com|noreply@openai\.com|copilot@github\.com' "$msg_file"; then
  echo "ERROR: el mensaje contiene una firma de herramienta. Quítala." >&2
  exit 1
fi
exit 0
```

Activar (cada miembro, una vez): `git config core.hooksPath .githooks` (en Linux/macOS además
`chmod +x .githooks/commit-msg`).

### 12.3 Check de autoría en CI

`.github/workflows/authors.yml` (completar los correos de la tabla 5.1):

```yaml
name: Autoría
on: [push, pull_request]
jobs:
  authors:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - name: Solo miembros del equipo y sin coautores
        run: |
          allowed="javisaguarantona@gmail.com|CORREO_IRIA|CORREO_MIGUEL|CORREO_ALEJANDRO|noreply@github.com"
          bad_authors=$(git log --format='%ae%n%ce' | sort -u | grep -Ev "^($allowed)$" || true)
          if [ -n "$bad_authors" ]; then echo "Autores no permitidos:"; echo "$bad_authors"; exit 1; fi
          if git log --format='%B' | grep -Eiq '^[[:space:]]*co-authored-by:'; then
            echo "Hay commits con Co-authored-by"; exit 1
          fi
```

(Si algún miembro usa el correo `@users.noreply.github.com`, añadirlo a `allowed`.)

### 12.4 Convención de commits y ramas

- Ramas: `feat/<area>-<tema>`, `fix/<area>-<tema>`, `docs/…`, `bench/…` (p. ej. `feat/web-delta-morph`).
- Mensajes en español, imperativo, con prefijo de área: `extraction: añade grounding check por OCR del recorte`.
- Sin trailers de coautoría. Sin emojis. Un cambio lógico por commit.

### 12.5 Plantilla de encargo para un agente

```text
Contexto: TrazIA-3D (ver docs/ROADMAP.md, sección <X>). Carpeta de la que eres dueño: <carpeta>.
No toques archivos fuera de <carpeta> salvo que se indique. Trabaja en el worktree <ruta>, rama <rama>.
Tarea: <tarea concreta con id del roadmap>.
Hecho cuando: <criterio verificable + comando de comprobación>.
Reglas: commits sin coautores ni firmas; datos de data/private/ nunca al repo; contrato en
docs/DATA_CONTRACT.md (si necesitas cambiarlo, para y avisa); skills de frontend obligatorias si tocas web/.
```

### 12.6 Glosario rápido

- **GA (General Arrangement):** plano de disposición general del equipo; referencia geométrica.
- **HDM:** hoja de datos mecánicos (presión, temperatura, material, código, pesos).
- **VESOR:** plano de orientación de boquillas y plataformas.
- **T/T:** longitud entre tangentes de la virola.
- **Faldón (skirt):** soporte cilíndrico de recipientes verticales.
- **DN / rating:** diámetro nominal y clase de presión de una boquilla/brida.
- **IFC:** formato abierto BIM (buildingSMART). **BCF:** formato abierto de incidencias de coordinación BIM.
- **HITL:** humano en el bucle. **ECE:** error de calibración esperado.
- **DRAFT:** modelo generado automáticamente, no apto para producción hasta su aprobación.
