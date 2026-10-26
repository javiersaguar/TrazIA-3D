# TrazIA-3D · web

Frontend de TrazIA-3D (Next.js App Router, React 19, TypeScript, Tailwind CSS v4).
Diseño: `docs/ROADMAP.md`, secciones I e I.2b, y las capturas de `docs/referencias-estilo/`.

## Arrancar

```bash
corepack enable   # o usar "corepack pnpm" en lugar de "pnpm"
pnpm install
pnpm dev          # http://localhost:3000
```

## Comprobaciones

```bash
pnpm typecheck
pnpm lint
pnpm build
pnpm test:e2e     # Playwright con Microsoft Edge instalado en el sistema
```

## Datos

No hay API todavía. `src/lib/mock/api.ts` imita los endpoints de la sección H del roadmap y lee
los archivos **sintéticos** de `public/demo/` (copiados de `examples/` y `generated/`).
Los tipos del contrato se generan, no se escriben a mano:

```bash
uv run trazia schema -o generated/revision.schema.json   # desde la raíz del repo
pnpm gen:types                                           # desde web/
```

## Propiedad de carpetas

| Carpeta | Responsable |
| --- | --- |
| `src/features/viewer3d/`, `plant/`, `delta3d/`, `src/workers/`, `src/app/lab/`, `public/demo/ifc/` | 3D |
| Resto de `web/` | Shell, diseño y pantallas 2D |

El 3D se consume siempre desde `@/features/viewer3d` con `next/dynamic` y `ssr: false`.
Contrato de props en `src/features/viewer3d/types.ts`; selección compartida en `src/stores/selection.ts`.
