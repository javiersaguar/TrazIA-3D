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
pnpm test:e2e     # Playwright con el Chrome del sistema (PW_CHANNEL=msedge para Edge)
pnpm capturas     # capturas de las 6 pantallas en oscuro y claro → docs/capturas/
```

## Datos

No hay API todavía. `src/lib/mock/api.ts` imita los endpoints de la sección H del roadmap y lee
los archivos **sintéticos** de `public/demo/` (copiados de `examples/` y `generated/`).
Los tipos del contrato se generan, no se escriben a mano:

```bash
uv run trazia schema -o generated/revision.schema.json   # desde la raíz del repo
pnpm gen:types                                           # desde web/
```

La pantalla Bench lee `public/demo/json/bench-etiquetas.json` y `bench-combinado.json`, copias de
`generated/bench*/report.json` (ver `docs/BENCH.md`). Para refrescarlas, desde la raíz:

```bash
uv run python -m synthetic --casos 20 --semilla 2026
uv run python -m bench --extractor etiquetas --salida generated/bench-etiquetas
uv run python -m bench --extractor combinado --salida generated/bench-combinado
```

y copiar los dos `report.json` a `web/public/demo/json/`.

## Propiedad de carpetas

| Carpeta | Responsable |
| --- | --- |
| `src/features/viewer3d/`, `plant/`, `delta3d/`, `src/workers/`, `src/app/lab/`, `public/demo/ifc/` | 3D |
| Resto de `web/` | Shell, diseño y pantallas 2D |

El 3D se consume siempre desde `@/features/viewer3d` con `next/dynamic` y `ssr: false`.
Contrato de props en `src/features/viewer3d/types.ts`; selección compartida en `src/stores/selection.ts`.
