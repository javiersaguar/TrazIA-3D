# Informe del boceto de frontend: shell, diseño y pantallas 2D

Rama `feat/web-shell`. Estado a 26/10/2026.
Comprobaciones en verde:

- `pnpm typecheck`
- `pnpm lint`, sin errores; un aviso conocido, ver «Límites».
- `pnpm build`: las 6 pantallas se prerenderizan como estáticas.
- `pnpm test:e2e`: 6 de 6 pruebas.
- `pnpm capturas`: 12 capturas.

## Qué está hecho

| Parte | Detalle |
| --- | --- |
| Skills | UI UX Pro Max, React Flow, Frontend Design y React Best Practices en `.claude/skills/` y `.agents/skills/` |
| Base | Next.js 16 (App Router), React 19.3, TypeScript estricto, Tailwind CSS 4, pnpm (`corepack pnpm`) |
| Tokens | `src/styles/tokens.css` con los colores medidos en las capturas de referencia (ROADMAP I.2b). Oscuro por defecto y claro |
| Tipos | `pnpm gen:types` genera `src/lib/types/revision.ts` desde `generated/revision.schema.json` |
| Datos | `src/lib/mock/api.ts` imita los endpoints de la sección H del roadmap sobre `public/demo/` |
| Selección | `src/stores/selection.ts` con ids semánticos que enlazan el plano, el 3D y la lista de campos |
| Contrato 3D | `src/features/viewer3d/types.ts` + stub. Las pantallas lo cargan desde `src/components/three.tsx` con `next/dynamic` y `ssr: false` |
| Shell | Barra lateral plegable con grupos y tarjeta de demostración; tema claro u oscuro. Barra superior con migas, píldoras (rev, datos sintéticos, pipeline en vivo, copiloto) y `Buscar Ctrl K` |
| Proyecto | 4 KPI (la micrográfica solo aparece con acciones reales de la sesión), hueco de `PlantScene` y tabla de equipos ordenable |
| Pipeline | Grafo React Flow con los extractores en paralelo; las etapas futuras van discontinuas. Carrusel de tarjetas de etapa con anillo de salud y tabla de eventos filtrable |
| Revisión | Plano PDF con recuadros de evidencia, hueco de `IfcViewer` y cola por riesgo. Teclado J/K/A/E/S y Ctrl+Z, actualizaciones optimistas y toast «Deshacer» |
| Cambios | KPI del delta, lista con marcadores Δ y disciplinas, `RevisionMorph` con avance y caja de narración (▶ y Espacio), grafo de impacto cambio → elemento → disciplina |
| Bench | Rúbrica del jurado con pesos, cómo se mide y objetivo; «Sin medir» en todos los resultados. Diagrama de fiabilidad vacío y honesto |
| Impacto | Calculadora con las cifras del reto. El ahorro solo aparece cuando se introduce el tiempo de revisión medido |
| Global | Menú de comandos, panel de atajos `?`, `G` + número para navegar, View Transitions entre pantallas, skeletons, movimiento reducido |

### Detalles de calidad de la lista (ROADMAP I.8)

- **Incorporados:**
  - skeleton loaders;
  - optimistic updates;
  - command menu;
  - shortcut hints;
  - undo toasts;
  - stale-while-revalidate (TanStack Query);
  - pre-rendering (pantallas estáticas);
  - view transitions;
  - animaciones interrumpibles (transiciones CSS y muelles);
  - hit slop en los recuadros del plano;
  - tabular numbers;
  - balanced headlines;
  - idempotency keys en las acciones de revisión;
  - safe triangle (Radix).
- **Pendientes:**
  - BlurHash: miniaturas de páginas, cuando la ingesta las genere;
  - esquinas continuas: opcional.
- **Descartados:** los que solo tienen sentido en móvil (swipe-to-dismiss, predictive back, safe area insets y autocompletado de código de un solo uso).

## Qué es mock

- **Revisiones y cambios:** salen de los JSON sintéticos de V-101 y de `changes.json`. El estado de revisión vive en memoria y se pierde al recargar.
- **Pipeline:** es una repetición simulada. Los recuentos son reales (vienen de los archivos) y el ritmo es artificial, por eso no se muestran latencias ni costes.
- **Equipos de planta:** V-102 a V-301 son ilustrativos y se rotulan así.
- **Impacto por disciplina:** sale de reglas del roadmap (F.4) pendientes de validar con ingeniería.
- **Copiloto:** explica cada campo con reglas a partir del JSON; no usa ningún modelo de lenguaje.
- **«Aprobar revisión»:** solo muestra un aviso. La aprobación real la firma el núcleo (`trazia approve`).

## Qué falta

1. API real (sección H) y sustituir `src/lib/mock/api.ts` por llamadas `fetch` al OpenAPI generado.
2. Esquema JSON del delta en el núcleo, para generar tipos en lugar de `src/lib/mock/diff-types.ts`.
3. Miniaturas de páginas con BlurHash desde la ingesta.
4. Momento firma «el plano se convierte en modelo» integrado en la pantalla Revisión, cuando exista en el laboratorio 3D.
5. Persistencia de preferencias por proyecto y de la cola de revisión.

## Qué necesito del 3D

- Implementar `IfcViewer`, `PlantScene` y `RevisionMorph` respetando `src/features/viewer3d/types.ts`. Las pantallas ya les pasan selección, hover, anotaciones, vista, modo y avance.
- Emitir `onSelect` con ids semánticos (`shell`, `head-top`, `head-bottom`, `skirt`, `nozzle:N1`…). La correspondencia con el `Name` del IFC está en `src/lib/mock/fields.ts`.
- En `RevisionMorph`, respetar `progress` (0 = rev A, 1 = rev B) y llamar a `onProgress` si el usuario lo cambia desde el lienzo.
- Leyenda y controles de cámara dentro del lienzo, como en Ciberconciencia: las pantallas no los dibujan.
- Pedir en `src/features/viewer3d/NECESIDADES.md` cualquier dependencia o token nuevo.

## Límites conocidos

- Lint muestra un aviso: React Compiler se salta la tabla de equipos porque TanStack Table no es compatible. Es esperado.
- En el panel de navegador de la app de escritorio, si la pestaña queda oculta, las transiciones de vista esperan a que vuelva a pintarse. En un navegador normal no ocurre.
- Las pruebas usan el Chrome del sistema (`PW_CHANNEL=msedge` para Edge).
