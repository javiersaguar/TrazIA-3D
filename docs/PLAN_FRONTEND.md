# Plan frontend TrazIA-3D · identidad, portada y 3D

Fecha: 30/10/2026. Entrega del reto: 27/11/2026 10:00.
Destino en el repo: `docs/PLAN_FRONTEND.md` (copia de este plan) + dos encargos listos para pegar.

## Estado de ejecución · 30/10/2026

- [x] Paso 0: contratos, dependencias y paleta compartidos.
- [x] 1.1–1.7: marca, portada, shell, gráficas, bocetos y adaptación, recibidos de feat/web-marca.
- [x] 2.1: materiales físicos, entorno y calidad adaptativa.
- [x] 2.2: cinco familias ilustrativas, partículas, selección y miniaturas.
- [x] 2.3: holograma/materialización, recortes reales y página Modelo.
- [x] 2.4: coreografía por elemento, seguimiento de cámara, cotas, scrub, A | B y presentación.
- [x] 2.5: revisión multipanel, PDF multipágina, inspector, evidencia y aprobación API.
- [x] 2.6: IFC enriquecido con procedencia y GUID; revisión A 73 productos, B 83.
- [x] Integración de ambas ramas en feat/web-3d y comprobaciones de frontend/Python/IFC.
- [x] Capturas claras/oscuras y revisión a 390, 1024 y 1600 px.
- [x] Lighthouse escritorio 100, 3D enriquecido 239 fps y Three fuera de los scripts iniciales.

El detalle visual se solicita con `build_ifc(..., details=True)` y se activa para los sintéticos
de la API/demo. No añade campos extraídos ni cambia implícitamente el LOD del núcleo o del bench.
Los patrones de brida cubren los tamaños documentados de clases 150/300; el Pset identifica
supuestos visuales y alcance de la tabla. Ver [informe 3D](agentes/INFORME_FRONTEND_3D.md) y
[verificación](agentes/verificacion_frontend.json). La fusión está preparada localmente: se conserva
la restricción del encargo de no hacer push ni PR y no se cambia main.

## Contexto

El frontend (`web/`, Next.js 16.4 + React 19 + Tailwind 4 + R3F + motion 14) funciona y tiene
siete pantallas, pero parece una demo: tema oscuro azulado, logo genérico de recipiente, botón de
copiloto morado, `/` redirige a `/proyecto`, el 3D es correcto pero sobrio y el morph de Cambios
interpola cajas en lineal durante 9 s sin coreografía. Queremos que parezca un producto industrial:
identidad propia (logo nuevo negro + azul celeste), modo oscuro negro como la app bancaria de
referencia, portada muy cuidada con login simulado, 3D realista, transición holograma → modelo real,
animaciones suaves con propósito y el boceto de todas las secciones.

Decisiones ya tomadas:
- **3D detallado por las dos vías** (respuesta del usuario): modelos procedurales detallados con la
  etiqueta «Ilustrativo» en portada y demos, y además enriquecer el IFC generado para que el visor
  real (Revisión, Cambios) muestre el mismo detalle. El visor nunca dibuja una segunda geometría
  (regla de `AGENTS.md`).
- **Sin Spline ni framer-motion.** Las escenas de Spline son externas y pesadas y no son de nuestro
  dominio. `motion/react` 14 ya está instalado y es la misma API que framer-motion. El estilo de los
  prompts de referencia (nube de partículas que se puede arrastrar, HUD en las esquinas, titular con
  frase rotatoria y desenfoque, botones con corchetes, diálogo de demo con pasos en vivo, foco que
  sigue al cursor) se reimplementa con R3F y motion, adaptado a recipientes y planos.
- **Sin shadcn.** El repo tiene primitivas propias en `src/components/ui/` (Panel, Button, Badge…) y
  `cn` en `src/lib/cn.ts`. El `Card` de los prompts se sustituye por `Panel`.
- **Login simulado:** usuario y contraseña visibles; «Iniciar» entra siempre, sin validar ni guardar
  credenciales. Solo se guarda `sessionStorage["trazia.sesion"]="demo"`. Las rutas de la app no
  quedan bloqueadas (los e2e y los enlaces directos siguen funcionando). «Salir» vuelve a `/`.
- **Las 5 mejoras propuestas por la otra IA entran en el plan**, repartidas entre los dos agentes.
  También su advertencia: cada animación debe tener un propósito (orientar, confirmar o explicar un
  cambio), no adornar.

## Sistema visual (referencia para ambos agentes)

Paleta oscura (negro tipo app bancaria, acento celeste del logo). Sustituye los valores azulados de
`src/styles/tokens.css`. Los nombres de token se mantienen para no romper clases.

| Token | Oscuro | Claro |
| --- | --- | --- |
| `--bg` | `#09090b` | `#f6f7f9` |
| `--sidebar` | `#0c0c0e` | `#ffffff` |
| `--surface` | `#111113` | `#ffffff` |
| `--surface-raised` | `#18181b` | `#f9fafb` |
| `--surface-sunken` | `#060607` | `#eef0f3` |
| `--border` / `--border-strong` | `#222226` / `#303036` | `#e4e6ea` / `#cfd3da` |
| `--text` / `--text-muted` / `--text-faint` | `#f4f4f5` / `#a1a1aa` / `#6b6b74` | `#0b0b0d` / `#52525b` / `#8a8a94` |
| `--accent-strong` (celeste logo) | `#2aa8f2` | `#0a84d6` |
| `--accent` / `--accent-text` | `#5cc4ff` / `#7fd0ff` | `#0a84d6` / `#0870b8` |
| `--accent-soft` | `rgb(42 168 242/.14)` | `#e6f4fd` |
| `--grid-line` | `rgb(255 255 255/.04)` | `rgb(0 0 0/.05)` |
| `--assistant` | `= --accent-strong` | `= --accent-strong` |

- Se eliminan `--chip-violet*` y la clase `violet`; sus usos pasan a `sky`/`accent`
  (`primitives.tsx:76`, `bench-workspace.tsx:182`, cabecera del copiloto).
- Los semánticos se conservan: `live`, `danger`, `warning`, `revision` (naranja de cambios) y
  `approved`.
- Superficies al estilo Ember: borde de 1 px, brillo superior sutil
  (`linear-gradient(180deg, rgb(255 255 255/.035), transparent 40%)`), sombra profunda y radio de
  14/12 px. El ítem activo del menú es una píldora elevada con borde (ya existe
  `layoutId="nav-active"`). Las etiquetas de sección van en mono pequeño (Inter + JetBrains Mono ya
  cargadas).
- Movimiento: 120/180/240 ms para UI y 400–700 ms para entradas y gráficas, con
  `--ease-out cubic-bezier(.22,1,.36,1)`. Solo se animan `transform`/`opacity` (y `pathLength` en
  SVG). Las gráficas se animan una vez al montarse, no en cada refetch. `MotionConfig
  reducedMotion="user"` ya existe y todo tiene un estado final estático.
- 3D: fondo negro con viñeta radial, celeste para holograma y selección, naranja `revision` para
  cambios. `src/lib/brand.ts` exporta estos colores en hex para three.js.

## Paso 0 · Común, en `main` antes de repartir (hecho el 30/10/2026)

Fija contratos y dependencias para que los dos agentes no se pisen en `package.json`, tokens ni
navegación.

1. Logo original en `web/public/brand/trazia-3d-logo.png` y `docs/marca/trazia-3d-logo.png`.
   Referencias visuales en `docs/referencias-estilo/05-banca-oscuro.png` (modo oscuro) y
   `06-holograma-a-real.png` (realismo y transición). La vectorización y la animación del logo son
   del Agente 1 (1.3).
2. Paleta de la tabla anterior en `src/styles/tokens.css`, sin violet (tokens, `@theme inline` y
   `Tone`). `src/lib/brand.ts` con los colores en hex para el 3D.
3. Dependencias MIT fijadas: `react-resizable-panels` 4.15.2 (Revisión) y `three-bvh-csg` 0.0.18
   (aberturas y taladros en los modelos ilustrativos). Registradas en `THIRD_PARTY.md`.
4. `src/lib/nav.ts` con todas las secciones (ver 1.6) y sus rutas con `SketchPage`
   (`components/shell/sketch-page.tsx`, «Boceto en curso»). `/proyecto` pasa a llamarse «Resumen».
   e2e: las secciones en boceto cargan sin errores.
5. Stubs de los contratos 3D en `features/showcase3d/` y `features/hologram/` (`index.ts` reexporta
   el `.tsx`).
6. Commit en `main` como Javier, sin coautores.
   - Agente 1: trabaja en el checkout principal en la rama `feat/web-marca`.
   - Agente 2: worktree `../TrazIA-3D-web-3d` en la rama `feat/web-3d`.
   - Encargo completo del Agente 2: `docs/agentes/ENCARGO_FRONTEND_3D.md`.

## Agente 1 · Marca, portada, shell, secciones y animación 2D

Es dueño de `src/styles/`, `src/components/shell/`, `src/components/ui/`, `src/components/motion/`
(nuevo), `src/components/brand/` (nuevo), `src/features/landing/` (nuevo), `src/features/tour/`
(nuevo), `src/app/page.tsx`, `src/app/layout.tsx`, `src/lib/nav.ts`, las rutas nuevas de 1.6 y las
partes 2D de proyecto, pipeline, bench, estudio, study, impact y copilot. No toca
`features/viewer3d|delta3d|plant|changes|review|hologram|showcase3d`.

### 1.1 Modo oscuro negro (pide 1, mejora IA 3)
- Ajustar los componentes que dependen del azul antiguo: `drafting-grid`, skeleton, scrim, los
  overrides de React Flow en `globals.css`, el `Toaster` (pasar `theme` de next-themes en lugar de
  `"system"`) y las sombras.
- Repasar Sidebar, Topbar, Panel y KpiCard con el tratamiento Ember: buscador con `⌘K` visible,
  píldora activa elevada y contadores alineados a la derecha en mono.
- El modo claro se conserva, coherente con el logo: blanco, negro y celeste.

### 1.2 Botón del copiloto (pide 2)
- `CopilotLauncher` (`src/components/shell/copilot.tsx`) pasa a ser un círculo de 52 px solo con un
  icono propio del copiloto (`components/brand/copilot-mark.tsx`: la D celeste del logo con un punto
  de «habla»; alternativa: lucide `Bot`).
  - Fondo `surface-raised`, borde `border-strong` y aro celeste suave al pasar el ratón.
  - Respiración lenta del aro (opacidad, 3 s) solo mientras hay una respuesta pendiente.
  - `aria-label="Abrir copiloto"` y tooltip con `Kbd`.
- Cabecera del panel y burbujas: de violet a `accent-soft`/`accent-text`.

### 1.3 Logo nuevo y su animación de formación (pide 10)
- `components/brand/logo.tsx` incluye `LogoMark` (solo la marca, para sidebar y favicon) y `Logo`
  (marca + wordmark). Sustituye `shell/logo.tsx` y `app/icon.svg`. También se crea `app/apple-icon.png`.
- `components/brand/logo-assemble.tsx` es la animación de entrada de la portada (~2,4 s, se puede
  saltar con clic o Esc, una vez por sesión):
  1. Las aristas de cada cara se dibujan (`pathLength` 0→1, escalonado 40 ms).
  2. Las piezas entran deslizando por sus ejes isométricos: la barra de la T desde arriba a la
     izquierda, el fuste desde abajo, la D desde la derecha y la «flecha» interior al final.
  3. Las caras se rellenan con sus degradados: negro/grafito y celeste.
  4. Las letras de «TrazIA» entran con desenfoque escalonado y «3D» enciende un brillo celeste breve.
  5. El logo encoge hasta la cabecera de la portada (`layoutId="brand"`).
- Con movimiento reducido se muestra el logo final directamente.

### 1.4 Portada `/` con login (pide 3 y 4, mejora IA 4)
`src/app/page.tsx` deja de redirigir y renderiza `features/landing/landing-page.tsx`, fuera del
shell `(app)`. Secciones:
1. **Intro:** `LogoAssemble` a pantalla completa sobre negro con rejilla técnica tenue.
2. **Hero** en dos columnas (una en móvil), con un foco que sigue al cursor
   (`components/motion/spotlight.tsx` con springs de motion) y fondo con trama diagonal tenue.
   - Izquierda:
     - Titular en banda: «Del plano al modelo 3D». Debajo, una línea serif rotatoria con
       desenfoque: «con cada cambio trazado», «con evidencia en cada cota», «listo para revisión
       humana».
     - Entradilla.
     - **Tarjeta de acceso:** usuario, contraseña (mostrar/ocultar), «Recordarme» y botón
       «Iniciar».
       - Al pulsar: spinner de 500 ms, después `sessionStorage` y `router.push("/proyecto")` con
         view transition.
       - Nota mono: «Demo · el acceso aún no valida credenciales».
     - Botón con corchetes «Ver demo», que abre `DemoDialog`. El diálogo recorre las etapas reales
       con tiempos y un check por etapa: Ingesta PDF → Lectura A/B/C/D → Reconciliación →
       Modelo IFC → Cambios A→B.
   - Derecha:
     - `<ShowcaseVessel mode="particles">` del Agente 2: el recipiente se forma a partir de una
       nube de partículas al estilo ink-orbit. Se arrastra para girarlo y un clic cambia de equipo.
     - HUD mono en las esquinas: «N 042°», «V-101 · GA→IFC», «Arrastra para girar · Clic para
       cambiar equipo» y «rev B».
3. **«Del holograma al modelo»:** `<HologramToReal source="procedural" progress={scrollProgress}>`
   fijado mientras se hace scroll (`useScroll`), con los tres recortes circulares (boca, faldón,
   orejeta) como en la imagen de referencia.
4. **Cómo funciona:** cuatro pasos con revelado al hacer scroll y una mini ilustración animada cada
   uno: Plano → Evidencia → Modelo → Cambios.
5. **Cuatro estrategias A/B/C/D:** tarjetas con inclinación al pasar el ratón; números del estudio
   con contador animado y la etiqueta «sintético».
6. **Pie:** CTA «Iniciar», los 4 autores y «Técnicas Reunidas · GA2MODEL».
- Rendimiento: el 3D se carga con `next/dynamic({ ssr:false })` después del primer pintado y se
  pausa fuera de pantalla. Objetivo de Lighthouse en escritorio: 85 o más.
- Tras el primer login se lanza un recorrido guiado de 3 pasos (`features/tour/`): documento →
  evidencia → modelo → cambios, saltable y guardado como visto en `localStorage`.

### 1.5 Animación suave en gráficas y componentes (pide 5)
Primitivas nuevas en `src/components/motion/`: `Reveal`, `Stagger`, `CountUp` (`animate()` de
motion sobre el número, con formato `es-ES`), `DrawPath` y el hook `useInViewOnce`. Aplicación:
- `components/ui/data.tsx`:
  - `Sparkline`: el trazo se dibuja y después aparece el punto final.
  - `HealthRing`: arranca en 0 (`initial` en lugar de `false`).
  - `ConfidenceBar`: crece desde 0.
  - `KpiCard`: `CountUp` y entrada escalonada.
- Estudio:
  - Forest plot: los bigotes crecen desde el estimador.
  - Pareto: los puntos aparecen con «pop» y la frontera se dibuja.
  - Ablaciones: las barras crecen.
- Bench: `ReliabilityChart` dibuja la diagonal y después la curva; las tarjetas de estilo se
  escalonan.
- Impacto: barras con spring al mover los sliders y cifras con `CountUp`.
- Pipeline: los nodos de React Flow entran escalonados y la etapa activa respira.
- Común:
  - `Segmented` y las pestañas con indicador `layoutId`.
  - Paneles que suben con fundido al entrar en la página.
  - Elevación de 1 px al pasar el ratón por tarjetas clicables.
  - Las filas de las tablas siguen con `row-in`.

### 1.6 Boceto de todas las secciones (pide 6)
Datos de mock en `src/lib/mock/bocetos/` y un aviso «Boceto · datos de ejemplo» en cada página.
Navegación nueva (`src/lib/nav.ts`, atajos G+tecla renumerados y listados en `ShortcutsDialog`):
- **Trabajo:** Proyectos (`/proyectos`, nuevo), Resumen (`/proyecto`), Documentos (`/documentos`,
  nuevo), Pipeline, Revisión, Cambios, Modelo 3D (`/modelo`, nuevo, Agente 2).
- **Calidad:** Bench, Estudio, Impacto.
- **Gestión:** Familias (`/familias`), Lote (`/lote`), Informes (`/informes`), Auditoría
  (`/auditoria`), Ajustes (`/ajustes`).

Contenido de cada boceto (Agente 1):

| Sección | Contenido |
| --- | --- |
| Proyectos | Rejilla de proyectos con miniatura `EquipmentThumb`, avance y equipos |
| Documentos | Zona para soltar ficheros y bandeja con estado por documento (recibido → leído → revisado) |
| Familias | Catálogo de recipientes vertical y horizontal, columna, intercambiador, tanque y bomba; miniatura 3D; F2/F3 |
| Lote | Cola de trabajos con progreso, cancelación y coste (0 €, local) |
| Informes | Exportar IFC, BCF, CSV e informe PDF; historial con huella |
| Auditoría | Línea temporal de ediciones, aprobaciones e invalidaciones |
| Ajustes | Política de proveedores (deny / synthetic_only / allow), estrategia por defecto, modelo local, tema, equipo y usuarios |

- Sidebar: «Salir» pasa a estar activo y lleva a `/`. Avatar con el usuario de la sesión demo.

### 1.7 Pulido de producto (mejora IA 5, parte 2D)
- Distinción visible entre datos sintéticos y reales: badge persistente en la Topbar con la fuente
  de datos (mock / API) y el conjunto.
- Diseño adaptable a 1280, 1024 (tablet) y 390 px: sidebar como sheet en móvil.
- Auditoría de accesibilidad: foco visible, contraste AA en negro, `aria-live` en las cifras.

## Agente 2 · 3D, Revisión, Cambios, holograma e IFC

Es dueño de `src/features/viewer3d/`, `delta3d/`, `plant/`, `changes/`, `review/`, `showcase3d/`
(nuevo) y `hologram/` (nuevo), de las rutas `/revision`, `/cambios` y `/modelo`, de `app/lab/` y
`src/workers/`. Para el IFC (fase 2.6) también `src/trazia/families/` y `src/trazia/ifc.py`; estas
carpetas son de Plataforma, así que hay que avisar a Miguel antes de tocarlas.

### 2.1 Kit de realismo (pide 8)
Referencia: la imagen del recipiente gris acero con bridas atornilladas, boca de hombre, faldón con
aberturas y orejeta.
- `viewer3d/materials.tsx`:
  - `SteelMaterial` pasa a `meshPhysicalMaterial` (metalness .85, roughness .34, clearcoat .2)
    con normal y rugosidad de cepillado procedurales (`CanvasTexture` generada una vez y cacheada).
  - Nuevos `PaintedSteel` (gris azulado, roughness .55), `MachinedFace` (caras de brida) y
    `BoltMaterial`.
  - Se mantiene la animación de opacidad y color con react-spring.
- `viewer3d/stage.tsx`:
  - Entorno de estudio más rico con `Lightformer` (anillo + 3 rectángulos) más `RoomEnvironment`
    PMREM.
  - Tone mapping AgX, `ContactShadows` bajo el equipo y suelo con rejilla que se desvanece.
  - SSAO, SMAA y `Bloom` selectivo solo para resaltados.
  - Fondo negro con viñeta.
  - Se mantienen `frameloop="demand"` y el DPR adaptativo.

### 2.2 Modelos ilustrativos detallados (pide 7 y 8, contrato para el Agente 1)
`features/showcase3d/`, generadores paramétricos (sin IFC), etiquetados «Ilustrativo · no procede
del IFC»:
- `buildVerticalVessel(spec)`:
  - Virola, fondos 2:1 (`LatheGeometry`) y cordones de soldadura en toro.
  - Boquillas weld-neck con brida y círculo de pernos instanciados.
  - Boca de hombre con tapa ciega, pescante y bisagra.
  - Orejetas de izado con taladro (CSG) y placa de identificación.
  - Faldón con aberturas de acceso (CSG), anillo base y pernos de anclaje.
  - Opcional: plataforma y escalera.
- Más familias: `horizontalDrum` (silletas), `column` (platos y plataformas), `heatExchanger`
  (carcasa, canal y tubos visibles en corte) y `tank`.
- Componentes:
  - `ShowcaseVessel` con modos `particles`, `hologram` y `real`. En `particles` los puntos se
    muestrean sobre la superficie del modelo y se ensamblan desde una nube, al estilo ink-orbit.
    Se arrastra para girar y un clic cambia de familia con morph de partículas.
  - `EquipmentThumb` para miniaturas.

### 2.3 Holograma → modelo real (pide 9)
`features/hologram/hologram-to-real.tsx`:
- `HologramMaterial` (`shaderMaterial`):
  - Fresnel celeste, scanlines en movimiento y rejilla de plano en espacio objeto.
  - Blending aditivo y ligero parpadeo al encender.
- Material de materialización: `onBeforeCompile` sobre el físico, con `discard` por encima de una
  altura de barrido y una banda emisiva celeste en el borde, que sube de abajo arriba.
- Flujo de partículas (`Points` con ruido) del holograma al modelo, como la flecha pixelada de la
  imagen.
- Tres recortes circulares con línea guía hacia el detalle: brida de boquilla, faldón y orejeta.
  Se renderizan con una segunda cámara (`RenderTexture`/`View` de drei) y aparecen al terminar.
- Disposición `side` (holograma a la izquierda, real a la derecha) o `inplace` (barrido sobre el
  mismo modelo).
- `source="ifc"` usa los `PreparedProduct` de `rev_b.ifc` (el visor sigue leyendo IFC) y
  `source="procedural"` usa `showcase3d`.
- `progress` controlado (scroll en la portada) o autoplay con scrub.
- Página `/modelo`:
  - Holograma → real sobre el IFC.
  - Galería de las 5 familias ilustrativas con selector.
  - Botón para ver en Revisión.

### 2.4 Cambios en tiempo real más perceptibles (pide 7, mejora IA 2)
`delta3d/revision-morph.tsx`, `delta3d/morph.ts` y `changes/changes-workspace.tsx`:
- **Coreografía por cambio** en lugar de un único blend lineal de 9 s. La línea de tiempo tiene un
  segmento por cambio, ordenado por elemento; cada segmento:
  1. La cámara viaja al elemento (`CameraControls.fitToBox`, transición suave).
  2. Pulso emisivo naranja y outline.
  3. El fantasma A en alambre se queda.
  4. Transformación con ease `(.65,0,.35,1)` y un pequeño rebote en escala.
  5. Etiqueta con la cota interpolando su número («DN 150 → 200», «H 8 200 → 8 600 mm»).
  6. Anillo de barrido en el elemento y asentado al color `revision`.
- Elementos añadidos: se construyen con el barrido de materialización de 2.3. Eliminados: se
  disuelven en partículas rojas.
- Reproducción con `useFrame` + refs, sin `setState` por frame. `morph.test.mjs` se adapta a la
  línea de tiempo segmentada.
- Scrubber con marcas por cambio clicables, velocidad 0,5/1/2× y pausa del temporizador de
  pantalla al arrastrar (pendiente de `NECESIDADES.md`).
- Sincronía lista ↔ 3D: pasar el ratón o hacer clic en un cambio lo resalta en el modelo, y al
  revés.
- Vista dividida A | B con cámaras sincronizadas, modo «solo modificados» y modo presentación:
  pantalla completa, interfaz mínima y recorrido automático por los cambios.

### 2.5 Revisión como workspace profesional (mejoras IA 1, 2 y 5)
`review/review-workspace.tsx`, `pdf-panel.tsx` y `field-queue.tsx`:
- `react-resizable-panels` sustituye la rejilla fija de tres columnas. El tamaño se guarda en
  `localStorage` y hay modos de foco (solo plano, solo modelo).
- PDF de varias páginas con miniaturas laterales y cajas de evidencia de todas las páginas; quitar
  `pageNumber={1}`.
- Inspector flotante de propiedades IFC (Psets, GUID, fuente y confianza) para el elemento
  seleccionado.
- Clic en un campo: resalta la caja en el plano y el elemento en 3D, con una línea de conexión
  animada.
- «Aprobar revisión» con confirmación real del servidor cuando hay API (endpoint de aprobación de
  Plataforma, con ETag/If-Match), errores recuperables y estado de progreso; en modo mock se
  conserva el aviso.

### 2.6 Enriquecer el IFC generado (pide 7 y 8, vía «real»)
Coordinar con Miguel, dueño de `src/trazia/families/` y `ifc.py`.
- Añadir piezas de detalle derivadas de campos existentes:
  - Bridas con taladros según DN/clase (tabla ASME B16.5).
  - Boca de hombre con tapa y pescante, orejetas de izado.
  - Aberturas de faldón, anillo base y pernos de anclaje.
- Cada pieza lleva `Pset_TrazIA.Origen = "derivado_de_norma"` para no presentarla como leída del
  plano. Mismo GUID estable por ID.
- Regenerar `web/public/demo/ifc/rev_a.ifc` y `rev_b.ifc`. `semantic.ts` reconoce las piezas nuevas.
- Comprobar con `uv run pytest -q` y `validate_ifc`.

## Contratos entre agentes (stubs del paso 0)

```ts
// features/showcase3d/index.ts  (Agente 2 implementa; Agente 1 consume con next/dynamic ssr:false)
type EquipmentKind = "vertical" | "horizontal" | "column" | "exchanger" | "tank";
export function ShowcaseVessel(p: { kind?: EquipmentKind; mode?: "particles" | "hologram" | "real";
  interactive?: boolean; onKindChange?(k: EquipmentKind): void; hud?: boolean; className?: string }): JSX.Element;
export function EquipmentThumb(p: { kind: EquipmentKind; size?: number }): JSX.Element;
// features/hologram/index.ts
export function HologramToReal(p: { source: "procedural" | "ifc"; layout?: "side" | "inplace";
  progress?: number; autoplay?: boolean; callouts?: boolean; className?: string }): JSX.Element;
```

Colores 3D solo desde `src/lib/brand.ts`. El Agente 2 no edita tokens CSS. Si un agente necesita
algo del otro, lo pide por escrito y no edita el archivo ajeno.

## Orden y fusión

1. Paso 0 en `main`.
2. En paralelo:
   - Agente 1: 1.1 → 1.2 → 1.3 → 1.4 → 1.5 → 1.6 → 1.7.
   - Agente 2: 2.1 → 2.2 → 2.3 → 2.4 → 2.5 → 2.6.
3. Fusión a `main` por PR con CI verde, primero Agente 2 (contratos reales) y después Agente 1.
   Captura final en claro y oscuro.

## Verificación

- En cada agente, desde `web/`:
  - `corepack pnpm@10.18.0 typecheck`
  - `corepack pnpm@10.18.0 lint`
  - `corepack pnpm@10.18.0 test:unit`
  - `corepack pnpm@10.18.0 build`
  - `corepack pnpm@10.18.0 test:e2e` (sin API y con `NEXT_PUBLIC_API_URL`)
- e2e nuevos:
  - `/` muestra el login.
  - «Iniciar» con campos vacíos navega a `/proyecto`.
  - «Salir» vuelve a `/`.
  - Todas las rutas de la navegación responden.
  - El copiloto se abre con el botón redondo.
- Visual en el navegador integrado (`localhost:3100`):
  - Capturas `capturas` en oscuro y claro.
  - Emulación de movimiento reducido.
  - Anchos de 390, 1024 y 1600 px.
- Rendimiento:
  - Lighthouse de la portada ≥ 85 en escritorio.
  - 3D a ≥ 50 fps en el portátil de la demo.
  - El chunk inicial de `/` no incluye three.
- Si se toca el IFC (2.6): `uv run ruff check .`, `uv run pytest -q` y validación del IFC.
- Reglas:
  - Commits como Javier, sin `Co-authored-by` ni firmas.
  - Nada de `data/private/`.
  - Skills de frontend obligatorias al tocar `web/`: frontend-design, ui-ux-pro-max,
    react-best-practices y emil-design-eng/animate.
  - Leer la guía de Next 16 en `node_modules/next/dist/docs/` (`web/AGENTS.md`).

## Encargos listos para pegar (formato ROADMAP 12.5)

El encargo completo del Agente 2, con carpetas, contratos, puertos y comprobaciones, está en
`docs/agentes/ENCARGO_FRONTEND_3D.md`. Resumen de ambos:

**Agente 1**: «Trabaja en TrazIA-3D siguiendo AGENTS.md y web/AGENTS.md. Checkout principal,
rama `feat/web-marca`. Tarea: secciones 1.1–1.7 de docs/PLAN_FRONTEND.md.
Solo tus carpetas (lista del plan); consume `ShowcaseVessel`, `HologramToReal` y `EquipmentThumb` por
sus contratos sin editarlos. Hecho cuando typecheck, lint, unit, build y e2e pasan y las capturas
oscuro/claro están en docs/capturas. Commits sin coautores ni firmas.»

**Agente 2**: «Trabaja en TrazIA-3D siguiendo AGENTS.md y web/AGENTS.md. Worktree
`../TrazIA-3D-web-3d`, rama `feat/web-3d`. Tarea: secciones 2.1–2.6 de docs/PLAN_FRONTEND.md.
Solo tus carpetas; respeta los contratos de showcase3d y hologram; el visor sigue leyendo IFC. Antes
de 2.6 avisa a Miguel (dueño de families/ e ifc.py). Hecho cuando typecheck, lint, unit, build, e2e
y, si tocas Python, ruff + pytest pasan. Commits sin coautores ni firmas.»
