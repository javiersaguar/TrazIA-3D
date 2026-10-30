# Encargo · Agente 2 del frontend (3D)

Prompt para el agente que hace la parte 3D de `docs/PLAN_FRONTEND.md`. El Agente 1 (marca,
portada, shell y gráficas 2D) trabaja a la vez en el checkout principal, en la rama `feat/web-marca`.

```text
Trabaja en TrazIA-3D siguiendo AGENTS.md (raíz) y web/AGENTS.md. Eres el Agente 2 · 3D del plan
docs/PLAN_FRONTEND.md. A la vez trabaja el Agente 1 (marca, portada, shell y gráficas 2D) en la rama
feat/web-marca; no toques sus carpetas.

Repo: javiersaguar/TrazIA-3D (tu checkout local; el worktree va en la carpeta hermana).
Equipo: Windows 11 (Git Bash y PowerShell), RTX 5070 Laptop 8 GB.

ANTES DE EMPEZAR
1. Comprueba que main contiene el commit «web: paso 0 del plan frontend». Deben existir:
   - web/src/lib/brand.ts
   - web/src/features/showcase3d/index.ts
   - web/src/features/hologram/index.ts
   Si falta alguno, para y avisa.
2. Crea tu worktree y trabaja solo ahí:
     git worktree add ../TrazIA-3D-web-3d -b feat/web-3d main
     cd ../TrazIA-3D-web-3d/web && corepack pnpm@10.18.0 install --frozen-lockfile
3. Lee esto antes de tocar nada:
   - docs/PLAN_FRONTEND.md: Contexto, Sistema visual, sección «Agente 2» (2.1–2.6), Contratos y
     Verificación.
   - web/src/features/viewer3d/NECESIDADES.md.
   - La guía de Next 16 en web/node_modules/next/dist/docs/. No es el Next que conoces.
4. Referencias visuales:
   - docs/referencias-estilo/06-holograma-a-real.png: recipiente holograma azul con rejilla, una
     flecha de partículas, el recipiente de acero real y tres recortes circulares naranja (brida de
     boquilla, faldón y orejeta). Es la referencia de realismo y de la transición.
   - docs/referencias-estilo/05-banca-oscuro.png: negro, superficies #111, bordes finos y acento.
5. Usa las skills del repo: frontend-design, ui-ux-pro-max y react-best-practices; para movimiento,
   emil-design-eng y animate.

TUS CARPETAS (las únicas que editas)
- web/src/features/{viewer3d,delta3d,plant,changes,review,showcase3d,hologram}/
- web/src/app/(app)/{revision,cambios,modelo}/
- web/src/app/lab/
- web/src/workers/
- web/tests/e2e/3d.spec.ts (nuevo). Para añadirlo al proyecto «humo» de playwright.config.ts basta
  un cambio de una línea.
- Solo en 2.6: web/public/demo/ifc/, src/trazia/families/ y src/trazia/ifc.py. Los dos últimos son
  de Plataforma (Miguel): pide confirmación a Javier antes de editarlos.

NO EDITES
- web/src/styles/, components/{shell,ui,brand,motion}/, lib/nav.ts, lib/brand.ts, app/page.tsx,
  app/layout.tsx y features/{landing,tour,project,pipeline,bench,estudio,study,impact,copilot}/.
- package.json. react-resizable-panels y three-bvh-csg ya están instalados; si necesitas otra
  dependencia, pídela.
- Los colores 3D salen solo de web/src/lib/brand.ts; si falta uno, pídelo.

CONTRATOS QUE IMPLEMENTAS (stubs en showcase-vessel.tsx y hologram-to-real.tsx)
Las firmas son fijas; solo puedes añadir props opcionales.
  features/showcase3d
    type EquipmentKind = "vertical" | "horizontal" | "column" | "exchanger" | "tank";
    ShowcaseVessel({ kind?, mode?: "particles" | "hologram" | "real", interactive?, onKindChange?,
      hud?, className? })
    EquipmentThumb({ kind, size? })
  features/hologram
    HologramToReal({ source: "procedural" | "ifc", layout?: "side" | "inplace", progress?,
      autoplay?, callouts?, className? })
El Agente 1 los consume con next/dynamic({ ssr:false }) en la portada (/), /proyectos y /familias.
Deben funcionar dentro de un contenedor con alto definido y sin depender de providers de la app.

TAREA, EN ESTE ORDEN (el detalle está en el plan)
2.1 Kit de realismo:
    - SteelMaterial físico con cepillado procedural, PaintedSteel, MachinedFace y BoltMaterial.
    - Entorno de estudio con Lightformers y RoomEnvironment.
    - AgX, ContactShadows, SSAO, SMAA y Bloom solo en resaltados.
    - Fondo negro con viñeta.
2.2 Modelos ilustrativos paramétricos en showcase3d:
    - Recipiente vertical completo: fondos 2:1, soldaduras, boquillas con brida y pernos
      instanciados, boca de hombre con pescante, orejetas, faldón con aberturas (CSG), anillo base y
      pernos de anclaje.
    - Familias horizontal, columna, intercambiador y tanque.
    - ShowcaseVessel en modo «particles»: la nube se ensambla en el recipiente; arrastrar para girar,
      clic para cambiar de familia con morph y HUD en mono.
    - EquipmentThumb.
    - Etiqueta visible «Ilustrativo · no procede del IFC».
2.3 HologramToReal:
    - Shader holograma (fresnel, scanlines, rejilla) y barrido de materialización con borde emisivo.
    - Flujo de partículas y los tres recortes circulares.
    - Disposición side o inplace; progress controlado o autoplay con scrub.
    - Página /modelo: transición sobre rev_b.ifc y galería de las 5 familias ilustrativas.
2.4 Cambios: coreografía por cambio en lugar del blend lineal de 9 s.
    - Cada cambio: la cámara viaja al elemento, pulso naranja con outline, fantasma A,
      transformación con rebote, la cota interpola su número y anillo de barrido.
    - Los elementos añadidos se materializan y los eliminados se disuelven.
    - useFrame con refs, sin setState por frame.
    - Scrubber con marcas por cambio y velocidad 0,5/1/2×.
    - Resaltado sincronizado entre la lista y el 3D.
    - Vista A | B con cámaras sincronizadas y modo presentación.
    - Adapta morph.test.mjs.
2.5 Revisión:
    - Paneles redimensionables (react-resizable-panels) con tamaños guardados y modos de foco.
    - PDF de varias páginas con miniaturas e inspector IFC flotante.
    - Línea animada que une el campo, su caja en el plano y su elemento 3D.
    - «Aprobar revisión» contra la API real (ETag/If-Match) con errores recuperables; en modo mock
      se mantiene el aviso.
2.6 IFC enriquecido:
    - Piezas: bridas taladradas según ASME B16.5, boca de hombre, orejetas, aberturas del faldón,
      anillo base y pernos.
    - Cada pieza lleva Pset_TrazIA.Origen="derivado_de_norma" y un GUID estable.
    - Regenerar rev_a.ifc y rev_b.ifc y actualizar semantic.ts.

REGLAS
- Con source="ifc", el visor de Revisión, Cambios y Modelo lee la geometría del IFC. Nunca dibuja
  una segunda versión aproximada; todo lo procedural lleva la etiqueta de ilustrativo.
- Cada animación tiene un propósito. Solo transform/opacity (o uniforms en shaders). Con
  useReducedMotion, mostrar directamente el estado final estático.
- Rendimiento:
  - frameloop="demand" donde se pueda, DPR adaptativo y pausa fuera de pantalla.
  - Al menos 50 fps en este portátil.
  - three no entra en el chunk inicial de /.
- Los datos sintéticos van siempre etiquetados y nunca se presentan como medidos en planos reales.
- Commits:
  - Pequeños, uno por subtarea, en feat/web-3d, con mensajes en español.
  - Autor «Javier Saguar <javisaguarantona@gmail.com>».
  - PROHIBIDO Co-authored-by o firmas de herramientas o asistentes en commits, código o docs.
- Sin push ni PR. No toques data/private/.

CÓMO PROBAR
- La API ya corre en http://127.0.0.1:8010. No la pares.
- Tu web conectada:
    NEXT_PUBLIC_API_URL=http://127.0.0.1:8010 corepack pnpm@10.18.0 dev --port 3300
  El puerto 3100 es del Agente 1. Next 16 no admite dos «next dev» en la misma carpeta.
- Hecho cuando, desde web/, pasan:
  - typecheck, lint, test:unit y build
  - PW_PORT=3310 corepack pnpm@10.18.0 test:e2e
  - NEXT_PUBLIC_API_URL=http://127.0.0.1:8011 PW_PORT=3311 corepack pnpm@10.18.0 test:e2e
    (levanta su propia API con uv en tu worktree; la primera vez uv crea el entorno).
- Si tu «next dev» sigue abierto, prueba los e2e contra un build: PW_USE_BUILD=1 tras «build».
- Con Python (2.6): uv run ruff check ., uv run ruff format --check . y uv run pytest -q.
- Guarda capturas oscuras de /revision, /cambios y /modelo en docs/capturas/.

AL TERMINAR CADA SECCIÓN
Anota en docs/agentes/INFORME_FRONTEND_3D.md qué hiciste, qué comprobaste y qué queda pendiente.
Al final, dime en una línea el resultado y la hora de fin.
```
