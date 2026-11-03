# TrazIA-3D · GA2MODEL — design spec

Todos los tokens salen del producto: `web/src/styles/tokens.css`, `web/src/lib/brand.ts`, la landing y el visor 3D. El vídeo no añade una «piel» propia.

## Color

| Token | Valor | Origen | Uso en el vídeo |
|---|---|---|---|
| `bg` | #09090b | `--bg` / `BRAND.black` | Escenario de todas las escenas |
| `surface` | #111113 | `BRAND.surface` | Paneles y tarjetas de rótulo |
| `border` | #222226 | `BRAND.border` | Bordes de 1 px de paneles |
| `text` | #f4f4f5 | `--logo-word` | Rótulos |
| `muted` | #a1a1aa | `--muted` | Texto auxiliar y etiqueta sintética |
| `sky` | #2aa8f2 | `BRAND.sky` | Evidencia, flylines, alambre |
| `skyLight` | #5cc4ff | `BRAND.skyLight` | Brillos, cabeza de flyline, barrido |
| `logoSky` | #4cbaf9 | `--logo-sky` | Halo del logo |
| `revision` | #f5a35c | Acento de revisión B en Cambios | Todo lo que cambia en la escena 5 |
| Acero | `BRAND.steel` con metalness 0.85 y roughness 0.34 | `SteelMaterial` | Material del recipiente |
| Papel | Blanco del PDF rasterizado | GA sintético | Único blanco grande del vídeo |

Nada de degradados decorativos. La luz la hacen los materiales y un solo foco.

## Tipografía

| Rol | Familia | Ajustes |
|---|---|---|
| Rótulo principal | Archivo, eje `wdth` 72, peso 600, tracking −0.012em | Mismo estilo que `.landing-display`. Tamaño 76–92 px (≥ 56 px, Q11) |
| Dato / etiqueta técnica | JetBrains Mono, 500 | 30–34 px (≥ 32 px salvo la etiqueta sintética, que es un aviso legal discreto a 26 px) |
| Texto auxiliar | Inter, 500 | 32–36 px |

Los rótulos van alineados a la izquierda en el tercio inferior izquierdo, con margen de 120 px. El rótulo final va centrado bajo el logo.

## Retícula y forma

- Margen de seguridad de 120 px horizontal y 96 px vertical.
- Radios: 14 px en paneles y 12 px en tarjetas, como en la app.
- Bordes de 1 px en `border`. Las sombras son solo de contacto, sin halos grises.

## Movimiento (preset «confianza técnica / precisa»)

| Token | Valor |
|---|---|
| Entrada estándar | 21–30 f, `bezier(0, 0, 0.2, 1)` |
| Movimiento en pantalla | `bezier(0.65, 0, 0.35, 1)`, el mismo `ease` que usa la Signature del producto |
| Rebote | Ninguno. Solo un aterrizaje con 4 % de sobrepaso en la escena 2a, encaje de caras |
| Cámara | Siempre en movimiento lento (dolly ≤ 4 %/s, órbita ≤ 6°/s). Sin sacudidas (Q3) |
| Quietud | Marca ≥ 30 f (R1). Rótulos ≥ 45 f legibles quietos. Fin de película con 50 f quietos |
| Brillo | Un solo barrido, recortado al logo final (Q4) |
| Tránsitos | Cortes en negro de 6–10 f o continuidad de cámara. Nada de wipes |

## Coreografía de firma (respetada del producto)

La escena 4 reproduce la `Signature` de `web/src/features/viewer3d/signature.tsx` con los mismos números:

- El plano es un `planeGeometry` de 12 de ancho, apaisado.
- Las zonas de evidencia se encienden durante el primer 32 % del progreso (como `signature.tsx`).
- El modelo gira en `rotation.x` de −π/2 a 0 con `scale.z` de 0.025 a 1.
- Pasa de alambre a acero entre 0.28 y 0.82.

La diferencia: aquí el progreso lo marca el fotograma, no el scroll.

## Material y licencias

- Texturas: PDF sintético rasterizado a 4200 px (`scripts/render_pdf.py`) y capturas a 1920×1080 @2x (`scripts/capture.mjs`).
- Geometría: `scripts/export_ifc.py` (ifcopenshell 0.8.5). Una malla por producto IFC, emparejadas por GlobalId entre A y B.
- Logo: `logo-geometry.ts` del producto, copiado a `src/brand/`.
- Audio: Freesound CC0 o CC BY. El registro está en `public/audio/sfx/manifest.json` y `public/audio/CREDITS.md`.

## Reglas de seguridad de datos

- Solo datos sintéticos del repositorio. La etiqueta «Demostración · datos sintéticos» está en todos los fotogramas.
- Sin cifras de rendimiento ni de precisión. Las únicas cifras en pantalla son valores de ingeniería del caso sintético (mm, revisiones).
