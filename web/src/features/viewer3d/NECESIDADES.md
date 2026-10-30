# Integración del 3D

- Las dependencias 3D de A cubren la implementación. El WASM 0.0.78 se sirve localmente en `/wasm/`.
- Falta Vitest y un script de tests unitarios en `package.json`. Se solicita añadir `vitest` como
  devDependency y `test:unit: vitest run`. Mientras tanto se ejecutan con
  `npm exec --yes --package=vitest@3.2.4 -- vitest run src/features/delta3d/morph.test.mjs`.
  `corepack pnpm dlx` falló al resolver su caché en este equipo; no se ha cambiado el manifiesto.
- El contrato original se mantiene; cualquier prop añadido es opcional.
- El laboratorio y la firma viven en `/lab/3d` y `/lab/firma`; A puede enlazarlos desde sus pantallas.
- Los estados del núcleo no incluyen supuestos/conflictos en IFC. Se admite un mapa opcional de
  estados por ID semántico; sin él se muestra el estado DRAFT leído del IFC, sin inferir aprobación.
- drei incorpora tipos transitivos de `three-mesh-bvh` 0.8 junto al 0.9 directo de A. El visor
  usa el árbol y el raycast 0.9; conviene unificar esa dependencia al actualizar el manifiesto.
- La narración interna del morph se oculta al recibir `progress` controlado: la pantalla Cambios
  ya dibuja la suya. `showNarration` opcional permite activarla explícitamente en otros contextos.
- En Cambios, A mantiene su propio temporizador. El callback `onProgress` debería pausar
  también ese temporizador (`setPlaying(false)`) al arrastrar el scrub del visor. B pausa su
  reproductor interno, pero no puede detener el de la pantalla sin ampliar el contrato.
- `Como el plano` ofrece un alzado ortográfico canónico. La alineación automática con un
  plano arbitrario requerirá la transformación del plano/calibración aportada por el núcleo.

## Plan frontend · 30/10/2026

- Paso 0 disponible en main (`976d8dd`) e incorporado por fast-forward al worktree de 3D.
- La API 8010 rechaza CORS desde localhost:3300. También se necesitarán localhost/127.0.0.1
  en 3310/3311 para la verificación indicada. Se solicita a Javier una excepción limitada a
  api/app.py; no se modifica sin respuesta ni se reinicia la API 8010. El laboratorio 3D
  puede probar geometría IFC local sin depender de este cambio.
