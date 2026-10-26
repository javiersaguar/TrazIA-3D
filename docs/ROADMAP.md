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
   - [B. Extracción IA](#b-extracción-ia-el-corazón-del-25--parte-del-35)
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
4. Núcleo Python (`src/trazia`, IfcOpenShell) se mantiene. Encima: **API FastAPI** + **frontend React/Next.js con 3D real**.
5. Extracción **híbrida (enfoque D)**: tablas vectoriales + OCR + LLM multimodal con cita obligatoria + reglas de ingeniería + reconciliación entre GA, HDM y VESOR.
6. **Cada valor cita página y región**, y un "grounding check" verifica que la cita contiene el valor. Si no, no hay valor: se abstiene.
7. **Confianza calibrada de verdad** (diagrama de fiabilidad, ECE) — es literalmente un criterio del 25 %.
8. **GA2MODEL Bench:** medimos nosotros mismos contra los 4 IFC de referencia con las mismas métricas que usará el jurado (35/25/20/10/10).
9. IFC "rico": `IfcTank`, boquillas como `IfcDistributionPort`, `IfcDocumentReference` al plano, `IfcApproval` para la firma humana. IFC4 + exportación IFC4X3 / IFC2X3.
10. Delta rev1→rev2 con **animación 3D de morph por GUID**, nubes de revisión, impacto por disciplina en un grafo **React Flow** y exportación **BCF**.
11. Frontend **0 AI slop** con el estilo de la casa (PIDS, Albertitos, Ciberconciencia — capturas en `docs/referencias-estilo/`): lenguaje visual del plano de ingeniería (líneas de cota, nubes de revisión, triángulos Δ), 3D como protagonista, animaciones con propósito.
12. Momento firma: **el plano 2D se levanta y se extruye en el modelo 3D** delante del jurado.
13. Demo **offline-capable** (resultados cacheados) + vídeo de respaldo + `.pptx` (obligatorio por bases).
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
| 35 % geometría | Reconciliación de vistas + restricciones de ingeniería (suma de cotas, fondos 2:1, DN normalizados) + familias por tipología | Tabla y **mapa de calor 3D de error** (mm) contra el IFC de TR; error medio de dimensiones y boquillas |
| 25 % atributos | Extracción multi-fuente (GA + HDM + VESOR) con cita verificada + **calibración** | Exactitud valor+unidad y **diagrama de fiabilidad** con ECE |
| 20 % delta | Emparejamiento semántico de boquillas, tolerancias, cambios de evidencia y de geometría por GUID | Precisión/recall de cambios + morph 3D rev1→rev2 + log accionable + BCF |
| 10 % escalado | Pipeline asíncrono, caché por SHA-256, idempotencia, coste/latencia medidos | Procesamos **todo el dataset** en lote en directo: N equipos, X s/equipo, Y €/equipo |
| 10 % innovación | Grounding check anti-alucinación, cola de revisión priorizada por riesgo, aprendizaje de correcciones, aprobación dentro del IFC | Dato corregido → la siguiente extracción lo usa; `IfcApproval` visible en un visor IFC externo |
| Ético (general) | Humano en el bucle, DRAFT por defecto, abstención en vez de invención, documentos tratados como datos (anti prompt-injection) | Intento de inyección dentro de un PDF que el sistema ignora y señala |
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

Base construida por el agente que trabaja en `src/trazia` (Python 3.11–3.13, uv, IfcOpenShell,
pdfplumber, openpyxl, Pydantic, Streamlit + Plotly). Versión `0.2.0`, **aún sin commits**.

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

Hoy hay un agente trabajando en `src/trazia`. A partir de ahora trabajarán 4 personas y varios agentes.

1. **Mapa de propiedad por carpeta** (un único dueño por carpeta; los demás proponen por PR):

   | Carpeta | Dueño | Contenido |
   | --- | --- | --- |
   | `src/trazia/` (ingest, extraction, model, review, revisions, ifc) | Núcleo (agente actual + responsable de B/D) | Lógica Python |
   | `src/trazia/extractors/` | Responsable B | Adaptadores OCR/LLM/tablas |
   | `src/trazia/families/` | Responsable D | Familias paramétricas |
   | `src/trazia/api/` | Responsable H | FastAPI, jobs, persistencia |
   | `bench/` | Responsable G | Métricas, GT, informes |
   | `web/` | Responsable I | Frontend Next.js |
   | `synthetic/` | Responsable G | Generador de planos sintéticos |
   | `docs/` | Todos; `ROADMAP.md` lo mantiene el líder | Documentación |
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
┌──────────────────────────────── src/trazia (núcleo, ya existe) ──────────────────────────────────────────────────┐
│ ingest → classify → extractors/{vector_tables, ocr, vlm, hdm_excel, vesor} → reconcile → normalize (model.py)    │
│ → families/{vertical_vessel, horizontal_vessel, column, tank, pump} → ifc.py → review.py → revisions.py → bcf.py │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                ▲
        bench/ (GT del IFC de referencia + GT manual + sintéticos) → métricas por criterio del jurado
```

### Decisiones y trade-offs (para defender ante el jurado)

| Decisión | Elegido | Alternativa descartada | Por qué |
| --- | --- | --- | --- |
| Enfoque (pág. 13) | **D híbrido**: datos + reglas como esqueleto, visión/LLM para leer, RAG solo como "prior" | A puro visión | Robusto y explicable; la visión sola es frágil ante ambigüedad |
| Geometría | Familias **paramétricas** por tipología | Reconstrucción libre de malla | IFC limpio, editable, comparable por parámetro, GUID estables |
| Núcleo | Python + IfcOpenShell (existe) | Reescribir en TS | Estándar de facto IFC; reutiliza la base |
| Frontend | Next.js (App Router) + R3F | Seguir con Streamlit | Streamlit no da el nivel de 3D, animación y UX necesario |
| Visor | **web-ifc** en Worker → mallas Three.js | Generar geometría en cliente | Regla del proyecto: el visor lee el IFC, no una segunda geometría |
| LLM | Adaptador intercambiable (servicios GenAI de la plataforma IndesIA o API externa, p. ej. Claude con visión) | Un proveedor fijo | Coste, confidencialidad y lo que permita la plataforma; se decide con muestras reales |
| Confianza | Fusión de señales + calibración isotónica | Score fijo del LLM | El criterio del 25 % pide **calibración** |
| Persistencia | SQLite + almacén por hash (local); Postgres en el discurso de escala | Solo memoria | Auditoría, reproducibilidad, idempotencia |
| Tiempo real | SSE | WebSockets | Más simple; solo servidor → cliente |

---

## 7. Calendario por fases

Hoy: **lunes 26/10/2026**. Quedan 4 semanas hasta el evento.

| Fase | Fechas | Objetivo | Hito de salida |
| --- | --- | --- | --- |
| 0. Arranque | 26–28 oct | Equipo, reglas, repo, inscripción | Commit inicial, hooks, roles, inscritos |
| 1. Cimientos | 29 oct – 4 nov | Contrato v1, API, monorepo web, generador sintético, bench v0 | `docker compose up` levanta API + web vacía; bench mide la demo sintética |
| 2. Capacidades | 5 – 14 nov | Extracción real, familias + IFC rico, revisión UX, visor 3D | Flujo completo en web con planos sintéticos **dibujados** |
| 3. Diferenciales | 15 – 21 nov | Delta pro, impacto, BCF, calibración, momento firma 3D, escala | Demo de 6 min completa con datos sintéticos |
| 4. Endurecer | 22 – 24 nov | Congelar alcance, ensayo, modo offline, `.pptx` v1, `PREVIOUS_WORK.md` | 2 ensayos cronometrados; todo reproducible en un portátil limpio |
| 5. Hackatón | 25 – 27 nov | Dataset real → métricas reales → pulido → pitch | Entrega 27/11 10:00 |
| 6. Gala | dic | Versión pulida, vídeo, narrativa del gran premio | Presentación para el premio general |

### Fase 0 · Arranque (26–28 oct)

- [ ] **0.1** Los 4 se inscriben en `indesiahack.org/registro` y eligen el reto de Técnicas Reunidas. *Hecho:* 4 confirmaciones.
- [ ] **0.2** Hacer la formación en la plataforma IndesIA y anotar en `docs/PLATAFORMA.md`: qué es (¿JupyterHub, VS Code web, nube?), recursos (CPU/GPU/RAM), **qué modelos de IA generativa ofrece**, límites, si hay salida a internet, si se puede usar Docker. *Hecho:* documento con respuestas.
- [ ] **0.3** Comprobar si con la inscripción ya se accede al dataset o a muestras. Si sí: copiar a `data/private/` (fuera de Git) y priorizar la fase de GT. *Hecho:* respuesta registrada.
- [ ] **0.4** Reunión 0 (1 h): leer este roadmap, confirmar roles (5.5), canales, horario semanal. *Hecho:* roles en este documento.
- [ ] **0.5** Commit inicial de la base (Javier), push a `main`, protección de rama (PR + CI obligatorio). *Hecho:* `main` con CI verde.
- [ ] **0.6** Reglas de autoría: `.githooks/commit-msg`, `core.hooksPath`, workflow `authors.yml`, `.claude/settings.json`, regla en `AGENTS.md` y `CLAUDE.md`. *Hecho:* un commit de prueba con coautor es rechazado localmente y en CI.
- [ ] **0.7** `LICENSE` MIT con los 4 nombres; `CONTRIBUTING.md` con flujo de ramas y convención de commits (anexo 12.4).
- [ ] **0.8** Instalar las skills de frontend en el repo (anexo 12.1) para que todos los agentes las usen.
- [ ] **0.9** Pedir al mentor de TR (si hay canal): formato real de los GA (¿vectorial o escaneado?), unidades habituales, si las boquillas vienen en tabla, qué consideran "dimensiones principales" y con qué tolerancia comparan. *Hecho:* respuestas o pregunta enviada.

### Fase 1 · Cimientos (29 oct – 4 nov)

- [ ] **1.1 (C)** Contrato **0.3**: estados de campo (`candidate`, `conflict`, `abstained`, `accepted`, `corrected`), alternativas con su evidencia, confianza calibrada y bruta, `impact` por campo, `family`, `schema_version`. Migrador 0.2 → 0.3. *Hecho:* esquema publicado + ejemplos validados.
- [ ] **1.2 (H)** `src/trazia/api` con FastAPI: endpoints de la sección H, OpenAPI, SSE de progreso, SQLite + almacén por hash. *Hecho:* tests de API y `uv run trazia api`.
- [ ] **1.3 (I)** `web/` con Next.js + TS + Tailwind v4 + tokens de diseño; tipos generados del OpenAPI (`openapi-typescript`); TanStack Query; shell con barra lateral, barra superior y tarjeta de demostración **como en las referencias (I.2b)**; `tokens.css` con la tabla de tokens medidos, modo oscuro y claro. *Hecho:* `pnpm dev` muestra el shell con datos reales de la API y, puesto al lado de las capturas, parece del mismo producto.
- [ ] **1.4 (G)** Generador sintético v1 (`synthetic/`): recipientes aleatorios → PDF tipo GA **dibujado** (alzado + planta con líneas de cota, tabla de boquillas, notas) + HDM Excel + rev2 con mutaciones conocidas. Variante "escaneada" (raster + ruido + rotación leve). *Hecho:* 200 equipos sintéticos con GT.
- [ ] **1.5 (G)** Bench v0: métricas de la sección G sobre la demo sintética, informe JSON + Markdown. *Hecho:* `uv run trazia bench synthetic/` imprime la tabla 35/25/20.
- [ ] **1.6 (H)** `docker-compose.yml` (api + web; redis opcional). *Hecho:* portátil limpio → `docker compose up` → app funcionando.
- [ ] **1.7 (I)** Spike de visor: cargar `generated/rev_a.ifc` con web-ifc en un Worker y pintarlo en R3F a 60 fps. *Hecho:* captura y medida de fps.

### Fase 2 · Capacidades (5 – 14 nov)

- [ ] **2.1 (B)** Extractores: tablas vectoriales, OCR, LLM multimodal con cita, HDM Excel robusto, VESOR (orientaciones). Ver B.
- [ ] **2.2 (B)** Reconciliación y grounding check. Ver B.4–B.6.
- [ ] **2.3 (D)** Familias: recipiente vertical (mejorar), **horizontal con silletas**, columna (con plataformas de VESOR si hay tiempo), tanque atmosférico y bomba simplificada. Ver D.
- [ ] **2.4 (D)** IFC rico: puertos, Psets de trazabilidad, `IfcDocumentReference`, `IfcApproval`, exportación IFC4X3 e IFC2X3. Ver D.
- [ ] **2.5 (E/I)** Espacio de revisión completo: PDF + 3D + campos enlazados, cola por riesgo, atajos, deshacer. Ver E e I.
- [ ] **2.6 (I)** Visor 3D de producto: selección, aislar, corte, vista explosionada, cotas 3D, rosa de orientación. Ver I.
- [ ] **2.7 (G)** Bench v1 sobre 200 sintéticos limpios + 50 "escaneados". *Hecho:* primera tabla de errores y lista de modos de fallo.

### Fase 3 · Diferenciales (15 – 21 nov)

- [ ] **3.1 (F)** Delta pro: emparejamiento de boquillas, tolerancias, cambios de evidencia, impacto por disciplina, BCF. Ver F.
- [ ] **3.2 (I)** Vista Delta: morph 3D por GUID, fantasma rev1, nubes de revisión, grafo de impacto en React Flow.
- [ ] **3.3 (B/G)** Calibración: isotónica sobre sintéticos; diagrama de fiabilidad en la web.
- [ ] **3.4 (I)** **Momento firma**: el plano se levanta y se extruye en el 3D (I.6).
- [ ] **3.5 (H/I)** Escala: procesamiento por lotes, vista de planta (plot plan) con todos los equipos, coste y latencia por equipo.
- [ ] **3.6 (E)** Aprendizaje de correcciones: las correcciones aprobadas se guardan como ejemplos y se usan como few-shot en la siguiente extracción.
- [ ] **3.7 (J)** Guion de 6 min v1 + `.pptx` v0 + calculadora de ROI en la app.

### Fase 4 · Endurecer (22 – 24 nov)

- [ ] **4.1** Congelar alcance el 22/11 a las 20:00: solo bugs, rendimiento y pulido.
- [ ] **4.2** **Modo offline:** variable `TRAZIA_OFFLINE=1` que sirve resultados LLM cacheados por hash. Si cae la red el viernes, la demo funciona igual.
- [ ] **4.3** Dos ensayos cronometrados del pitch (6:00 exactos) con alguien externo haciendo de jurado de TR.
- [ ] **4.4** `PREVIOUS_WORK.md` redactado; tag preparado.
- [ ] **4.5** Instalación en limpio en **los 4 portátiles** (Windows y Linux) siguiendo solo el README.
- [ ] **4.6** Vídeo de respaldo de la demo (1080p, 60 fps, sin cortes raros).
- [ ] **4.7** Lista de preguntas difíciles y respuestas (J.5).
- [ ] **4.8** Kit físico: cargadores, regleta, adaptador HDMI/USB-C, ratón (orbitar 3D con trackpad sale mal), hotspot móvil.

### Fase 5 · Hackatón (25 – 27 nov) — plan por horas

**Miércoles 25**
- 09:30 llegada (plaza por orden de llegada). 11:00 presentación de retos.
- Al empezar: tag `pre-hackathon-baseline` + entregar `PREVIOUS_WORK.md` a la organización.
- Primeras 2 h: descargar el dataset a `data/private/`, inventario automático (`trazia ingest` de todo),
  clasificar por tipología y calidad (vectorial/escaneado).
- Hasta la cena: **GT de los 4 equipos con IFC de referencia** (extraer automáticamente del IFC con
  IfcOpenShell + completar a mano atributos del HDM). Ejecutar bench v-real-0. **Análisis de errores.**
- Noche: priorizar los 3 modos de fallo con más peso en la rúbrica (35 % primero).

**Jueves 26**
- Mañana: arreglar modos de fallo; adaptar familias a la geometría real (p. ej. tipo de fondo, faldón vs patas, boquillas no radiales/inclinadas).
- Mediodía: delta sobre todos los pares rev1/rev2 reales; revisar a mano y medir precisión/recall.
- Tarde: probar en **estáticos B** (sin IFC) y **un mecánico** para demostrar generalización; calibrar con datos reales (validación cruzada dejando uno fuera para no sobreajustar a 4 equipos).
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

### B. Extracción IA (el corazón del 25 % y parte del 35 %)

**Principio:** el LLM *lee*; las reglas *deciden*; el humano *aprueba*. Ningún valor sin evidencia.

**B.1 Extractores (cada uno devuelve `Candidate` con valor, unidad, página, bbox, extractor, score bruto):**

| Extractor | Para qué | Técnica |
| --- | --- | --- |
| `vector_tables` | Tablas de boquillas, listas de datos de diseño en GA vectorial | pdfplumber (palabras + líneas), reconstrucción de celdas |
| `vector_dims` | Cotas en planos vectoriales | Texto numérico + proximidad a líneas de cota y flechas (geometría vectorial del PDF) |
| `ocr` | Escaneos e imágenes | PaddleOCR o docTR (local) con cajas; Tesseract como fallback |
| `vlm` | Comprensión de vistas, notas, cotas ambiguas, orientaciones | LLM multimodal con salida JSON por esquema; recibe página + recortes + texto OCR; **debe citar bbox** |
| `hdm_excel` | Atributos de diseño (presión, temperatura, material, código, pesos) | openpyxl, búsqueda de etiquetas multilingüe, celdas combinadas, unidades en celda contigua |
| `vesor` | Orientación de boquillas (azimut) y plataformas | Tabla + vista en planta; ángulos respecto al Norte de planta |

**B.2 Qué extraer como mínimo (CAP-02) y qué extra:**
- Tag; diámetro interior/exterior; longitud entre tangentes; tipo y altura de fondos; altura total;
  soporte (faldón: altura, diámetro, espesor / patas / silletas: posición y número).
- Por boquilla: marca (N1…), servicio, DN/tamaño, rating, elevación o distancia desde referencia,
  proyección, azimut/orientación, tipo (radial, tangencial, superior, inferior).
- Extra para "valor no previsto": pesos (vacío, operación, prueba), centro de gravedad, material, presión
  y temperatura de diseño, código (ASME VIII…), corrosión admisible.

**B.3 Prompting del VLM (plantilla en `src/trazia/extractors/prompts/`):**
- Instrucción de sistema fija; el contenido del documento va como **dato delimitado**. Cualquier texto
  del documento que parezca una instrucción se ignora y se registra como alerta (anti prompt-injection).
- Salida estricta con esquema JSON (structured outputs / tool use). Campos: `value`, `unit_as_written`,
  `page`, `bbox`, `quote` (texto literal leído), `reasoning_short`, `self_confidence`.
- Unidades: devolver la unidad **tal como aparece**; la normalización la hace el código, no el LLM.
- Pasos: 1) identificar vistas (alzado, planta, detalles) y su escala; 2) leer tabla de boquillas;
  3) leer cotas generales; 4) asociar boquillas a posiciones en alzado/planta; 5) listar dudas.
- **Autoconsistencia:** N muestras (3–5) con temperatura > 0 o dos modelos distintos; el acuerdo entre
  muestras es una señal de confianza.
- Few-shot dinámico: ejemplos recuperados de equipos ya aprobados de la misma tipología (B.7).

**B.4 Grounding check (anti-alucinación, innovación clave):**
Para cada candidato del VLM: recortar la bbox citada → OCR del recorte → ¿aparece el número (con
tolerancia de formato: `2.000`, `2000`, `2,000`)? Si sí: confianza ↑ y estado `grounded`. Si no:
reintento de localización; si sigue sin aparecer: **se descarta** o queda `abstained` con aviso. En la
demo esto se enseña en directo: "el modelo dijo 2.150, pero en la región citada pone 2.105 → corregido".

**B.5 Reconciliación ("razonar", pág. 6):**
- Agrupar candidatos por campo; resolver por prioridad de fuente configurable (p. ej. tabla de boquillas
  > cota en alzado > nota) y por acuerdo entre extractores.
- **Restricciones de ingeniería** como sistema de ecuaciones: altura total = faldón + virola + fondo;
  fondo 2:1 semielíptico → altura ≈ D/4; boquillas dentro de la virola; DN en serie normalizada;
  azimut en [0, 360). Un pequeño solver (mínimos cuadrados con pesos = confianza) detecta qué valor
  es el inconsistente y lo marca `conflict` con explicación legible.
- Reconciliar GA vs HDM vs VESOR: si difieren → `conflict` con ambas evidencias, nunca "elegir en silencio".
- Desconocidos explícitos: si falta un dato, `abstained`. La geometría puede usar un **valor por defecto
  de familia marcado como supuesto** (color distinto en 3D) solo en DRAFT.

**B.6 Confianza calibrada:**
- Señales: acuerdo entre extractores, acuerdo entre muestras, grounding, calidad OCR, cumplimiento de
  restricciones, tipo de fuente, `self_confidence` del LLM (peso bajo).
- Modelo: regresión logística sobre señales → **calibración isotónica** sobre sintéticos y validación
  cruzada sobre reales. Publicar el **diagrama de fiabilidad** y el **ECE** (meta: < 0,05).
- Interpretación para el usuario: alta (≥ 0,9) verde, media naranja, baja roja; umbral de revisión
  obligatoria configurable.

**B.7 RAG como "prior", nunca como fuente:**
Índice de equipos aprobados (embeddings de página + parámetros). Se usa para: elegir familia, sugerir
qué campos buscar, few-shot. Un valor recuperado **nunca** entra al JSON sin evidencia en el documento actual.

**B.8 Coste y latencia:** registrar tokens, llamadas y segundos por equipo; caché por (hash de página,
versión de prompt, modelo). Objetivo: < 60 s y < 0,50 € por equipo (ajustar con datos reales).

*Hecho:* en sintéticos limpios ≥ 98 % de campos correctos; en escaneados ≥ 90 %; en reales, lo que diga
el bench, con análisis de errores documentado.

### C. Normalización y contrato de datos

- [ ] **C.1** Unidades con `pint`: mm, cm, m, in, ft-in (`5'-6"`), bar(g), barg/bara, kPa, MPa, psi,
  kg/cm², °C, °F, kg, t, lb. Separadores de miles y decimales en español e inglés (`2.000,5` / `2,000.5`)
  decididos por contexto del documento y marcados si son ambiguos.
- [ ] **C.2** Unidad canónica por magnitud y **unidad original conservada** en la evidencia.
- [ ] **C.3** Equivalencias en el delta: 10 bar = 1 MPa no es un cambio; 10 bar → 10 MPa sí.
- [ ] **C.4** Sistema de referencia documentado: origen, eje Z vertical, azimut (Norte de planta =
  0°, sentido horario como en VESOR **o** el convenio que use TR — confirmar con el IFC de referencia).
- [ ] **C.5** Versionado del esquema + migradores + ejemplos válidos en CI.
- [ ] **C.6** JSON exportable "para humanos": también CSV/Excel de campos con evidencia para el ingeniero.

### D. Geometría paramétrica e IFC (35 %)

**D.1 Familias** (`src/trazia/families/`), cada una con: parámetros, validaciones, defaults marcados,
generador de geometría IFC y prueba de ida y vuelta (parámetros → IFC → parámetros).

| Familia | Componentes | Prioridad |
| --- | --- | --- |
| Recipiente vertical | Virola, fondos (2:1 SE, toriesférico, hemisférico, plano), faldón / patas, boquillas radiales, superiores e inferiores | P0 (existe, mejorar) |
| Recipiente horizontal | Virola, 2 fondos, 2 silletas, boquillas en generatrices | P0 |
| Columna | Virola por tramos (diámetros distintos, conos de transición), faldón, plataformas y escaleras simplificadas (VESOR) | P1 |
| Tanque atmosférico | Virola, techo cónico/domo, fondo plano | P1 |
| Bomba / compresor | Bancada, carcasa y motor como volúmenes simplificados, boquillas de aspiración/impulsión | P2 (demostrar generalización) |

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

**D.4 Validación IFC:** `ifcopenshell.validate` (esquema + reglas) en CI; abrir en ≥ 3 visores
(Bonsai/BlenderBIM, el visor web propio basado en web-ifc, y uno de escritorio tipo xBIM/Solibri
Anywhere/BIMvision) y guardar capturas en `docs/ifc-checks/`. El validador online de buildingSMART
solo con sintéticos.

**D.5 Fidelidad contra referencia:** función que alinea nuestro IFC con el de TR (por bounding box del
equipo y eje) y calcula error por componente (ver G). Iterar familias hasta que el error de forma
dependa solo de la extracción, no de la familia.

### E. Validación y humano en el bucle

- [ ] **E.1** Reglas de validación con mensajes claros y accionables (qué pasa y cómo arreglarlo):
  geométricas (boquillas fuera de la virola, solapes entre boquillas, fondos imposibles), de unidades,
  de coherencia entre documentos.
- [ ] **E.2** **Cola de revisión priorizada** por `impacto × (1 − confianza)`: primero lo que más daño
  haría si estuviera mal (diámetro, elevaciones de boquillas) y menos seguro está.
- [ ] **E.3** Acciones por campo: aceptar, corregir (con nueva evidencia opcional), marcar como
  supuesto, rechazar. Todo con **deshacer** y registro de auditoría (quién, cuándo, antes/después).
- [ ] **E.4** Aprobación ligada a la huella (existe) + idempotencia + bloqueo si hay `conflict` sin resolver.
- [ ] **E.5** Medir **tiempo de revisión por equipo** con el propio log → cifra de impacto del pitch.
- [ ] **E.6** Aprendizaje de correcciones (3.6): corrección aprobada → ejemplo few-shot + ajuste de prioridad de fuentes.

### F. Revisiones y delta (20 %)

- [ ] **F.1** Emparejamiento de entidades rev1↔rev2: boquillas por marca; si cambia la marca, por
  servicio + DN + posición (algoritmo húngaro con coste combinado); detectar **renombrados**, altas y bajas.
- [ ] **F.2** Tolerancias por magnitud (p. ej. ±1 mm, ±0,5°) para no reportar ruido de extracción como cambio;
  distinguir "cambio de diseño" de "cambio de lectura" (misma cota, distinta evidencia/confianza).
- [ ] **F.3** Clasificar: geométrico, atributo, documental (solo evidencia), de identidad (tag).
- [ ] **F.4** **Impacto por disciplina** con reglas explicables (pág. 3 del reto): boquilla movida →
  Piping; faldón/peso → Civil (cimentación) y Estructuras; nueva boquilla → Piping + I&C si es de
  instrumento; cambio de presión/temperatura → Mecánica + Procesos. Severidad y acción sugerida.
- [ ] **F.5** Detectar **nubes de revisión y triángulos Δ** en el GA rev2 (muy comunes en planos reales):
  si la rev2 marca zonas revisadas, se usan como pista y para comprobar que no se nos escapa nada
  (un cambio detectado fuera de una nube, o una nube sin cambio detectado, se señala).
- [ ] **F.6** Salidas: `changes.json`, informe legible (Markdown/PDF), **BCF 2.1/3.0** con un topic por
  cambio (vista de cámara, GUID del elemento, descripción) → abre en herramientas BIM de coordinación.
- [ ] **F.7** El IFC rev2 conserva GUID; la rev1 se conserva intacta (pág. 11: "conservación de la versión anterior").

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
- [ ] **G.6** El bench corre en CI sobre sintéticos (regresiones = PR rojo).

### H. Backend, API y escalado (10 %)

- [ ] **H.1 Endpoints:**
  - `POST /documents` (multipart, cabecera `Idempotency-Key`, dedupe por SHA-256)
  - `POST /equipment/{tag}/jobs` → `job_id`; `GET /jobs/{id}/events` (SSE: etapa, progreso, logs)
  - `GET /equipment`, `GET /equipment/{tag}/revisions/{rev}`
  - `PATCH /revisions/{id}/fields/{path}` (con `If-Match` / versión para concurrencia optimista)
  - `POST /revisions/{id}/approve` (`Idempotency-Key`)
  - `GET /revisions/{id}/ifc?schema=IFC4|IFC4X3|IFC2X3&draft=`
  - `GET /diff?from=&to=`, `GET /diff/bcf`, `GET /bench`, `GET /plant`
- [ ] **H.2 Idempotency keys** en todo POST con efecto (subida, jobs, aprobación): repetir la petición
  devuelve el mismo resultado, sin duplicar. Clave guardada 24 h con hash del cuerpo.
- [ ] **H.3 Trabajos asíncronos:** `arq` + Redis (o `BackgroundTasks` en modo local), reintentos con
  backoff para el LLM, timeouts, cancelación.
- [ ] **H.4 Persistencia:** SQLModel sobre SQLite (local) con migraciones Alembic; Postgres en
  `docker-compose.prod.yml` para el discurso de escala. Almacén de archivos direccionado por contenido.
- [ ] **H.5 Observabilidad:** logs estructurados (JSON), traza por job, métricas de coste y latencia.
- [ ] **H.6 Seguridad básica:** CORS restringido, límites de tamaño, sin claves en el repo (`.env.example`),
  documentos tratados como datos.
- [ ] **H.7 Escala (para el pitch):** diagrama con cola, workers horizontales, caché por hash (una
  revisión que solo cambia una página solo reprocesa esa página), coste estimado de un proyecto de
  400 equipos × 4 revisiones.

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

#### I.5 3D: todo lo que debe poder hacer el visor

- [ ] Carga del IFC en Worker con barra/skeleton; nunca congela la UI.
- [ ] Órbita, paneo y zoom suaves e **interrumpibles**; "fly-to" a un elemento con muelle; doble clic = encuadrar.
- [ ] Selección con resaltado (outline) y **hit slop**: zona de picking ampliada para boquillas pequeñas.
- [ ] Aislar / ocultar / transparentar componentes; árbol IFC (proyecto → equipo → componentes → puertos).
- [ ] **Plano de corte** animado (ver interior, espesores) con relleno de sección rayado (hatch).
- [ ] **Vista explosionada** animada (virola, fondos, faldón y boquillas se separan a lo largo de su eje).
- [ ] **Cotas 3D** generadas a partir de los parámetros y ancladas a la geometría IFC, con la misma
  estética que el plano; al pasar el ratón muestran valor, unidad, confianza y fuente.
- [ ] **Rosa de orientación** (anillo de azimut 0–360° en planta) con las boquillas proyectadas: cruza
  con el VESOR.
- [ ] Vistas guardadas: isométrica, alzado, planta, "como el plano" (cámara ortográfica alineada con la
  vista del GA para poder superponer plano y modelo).
- [ ] Supuestos (valores por defecto de familia) dibujados con material distinto (rayado o translúcido).
- [ ] Rendimiento: `frameloop="demand"`, instancing para elementos repetidos, BVH, ≤ 200 k triángulos a
  60 fps en un portátil normal; DPR adaptativo.
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
| 1:30–2:30 | Extracción | Espacio de revisión: valor → recorte del plano → confianza | Grounding check y confianza calibrada (diagrama) |
| 2:30–3:45 | 3D | Momento firma: el plano se convierte en modelo; IFC abierto también en un visor externo | IFC4 con puertos, trazabilidad y aprobación dentro |
| 3:45–5:00 | Cambio | Morph rev1→rev2, nubes Δ, grafo de impacto, BCF | "Qué cambió, cuánto, dónde y a quién afecta" |
| 5:00–6:00 | Impacto y escala | Bench contra el IFC de TR + lote de todo el dataset + ROI | Números medidos, límites honestos, siguientes pasos |

**J.2 `.pptx`** (obligatorio por bases): 8–10 diapositivas con el mismo lenguaje visual que la app;
capturas y números **reales del dataset**; una diapositiva de arquitectura; una de "qué hicimos antes y
durante el evento"; una de límites y siguientes pasos. Guardado en `pitch/` del repo antes de las 10:00.

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
- **CI** (GitHub Actions): Windows + Linux para Python (existe), job web, job de autoría (anexo 12.3),
  job de bench sintético, artefactos (IFC, BCF, informe del bench).
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
