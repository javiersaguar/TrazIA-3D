# Revisión visual y limitaciones (borrador 2)

## Entregables

| Archivo | Contenido |
|---|---|
| `out/trazia-ga2model-draft.mp4` | Versión con BGM. 1920×1080, 30 fps, H.264 + AAC, 45 s (1350 f) |
| `out/trazia-ga2model-no-bgm.mp4` | Misma línea de tiempo, sin las capas BGM; se mantienen los SFX |
| `storyboard.md`, `design-spec.md` | Brief, dirección, mapeo de tarjetas y guion por fotogramas |
| `src/` | Proyecto Remotion. La única fuente de tiempos es `src/timeline.ts`; el manifiesto del workbench está en `src/workbench.ts` |
| `public/` | Capturas reales, geometría IFC, texturas GA, logo, fuentes y audio con su manifiesto |
| `scripts/` | Exportación IFC, rasterizado PDF, capturas con Playwright, stills de QA y hoja de contacto |
| `out/qa/` | Stills y hojas de contacto de cada iteración |

Comandos (PowerShell o bash, desde esta carpeta):

```
npm install
npm run studio          # previsualizar
npm run render          # versión con BGM
npm run render:nobgm    # versión sin BGM
node scripts/stills.mjs 120 760 1300   # stills de QA
```

## Fidelidad

- **Geometría.** Es el IFC rev A/B del repositorio (`web/public/demo/ifc/rev_{a,b}.ifc`), teselado con ifcopenshell. No se ha inventado ninguna pieza.
  - El morph A→B se hace por vértice en las piezas con la misma topología.
  - La virola y el faldón cambian de teselado entre revisiones. Se estiran en vertical (son prismas) y al terminar el morph se muestra la malla B real.
- **Coreografía 2D→3D.** Reproduce los números de `signature.tsx`: posición tumbada, escalas, q, alambre/acero y evidencias en el primer 32 %.
- **Cifras en pantalla.** Son valores de ingeniería del caso sintético, sacados de `changes.json`, del GA y de las capturas: 2.000, 6.000 y 1.200 mm; +500, +200 y +150 mm; N4 nueva.
- **Sin métricas.** No hay métricas de precisión, tiempo ni porcentajes.
- **Aviso sintético.** «Demostración · datos sintéticos» aparece en todos los fotogramas. Las propias capturas muestran además el aviso de la app («Datos sintéticos · no son del dataset de TR»).

## Sincronía de audio

- El desfase de la pista de salida se midió el 03/11/2026 en el render sin BGM (Remotion 4.0.484, H.264 + AAC 48 kHz, mp4).
- Método: correlación cruzada de cinco cues contra su archivo fuente (impacto, tres clics y arpa).
- Resultado: +1,27 a +1,29 fotogramas (unos 43 ms), igual en todo el vídeo. Coincide con `OUTPUT_AUDIO_OFFSET_F = 1.28` de `src/audio.tsx`, así que los picos caen en su fotograma objetivo.
- Script de medición reproducible: correlación con numpy sobre la pista decodificada con ffmpeg.

## Revisión independiente (03/11/2026)

Un revisor con contexto limpio comprobó el vídeo final con el checklist de la skill. Tenía los keyframes, el storyboard, la design-spec, las tarjetas, las demos y `signature.tsx`, y midió el audio.

Veredicto: **apto como borrador**, sin bloqueantes.

Confirmó estos puntos:
- No hay métricas ni porcentajes.
- Las piezas 3D salen de los IFC rev A/B por GlobalId, con deltas iguales a `changes.json`.
- La coordenada de la subida coincide con `signature.tsx`.
- Los 13 audios son CC0 y los hashes coinciden.
- Los rótulos son literales y el render es determinista.

| # | Hallazgo | Arreglo aplicado |
|---|---|---|
| I1 | El subtítulo «Técnicas Reunidas …» de la barra lateral aparecía en las capturas (f390–430) | `scripts/redact.py` lo tapa con el color de la barra en las tres capturas. Los originales quedan en `public/captures/_orig/`, solo en local (fuera de git) |
| I2 | La etiqueta sintética no se leía sobre el papel blanco (f610–720) | La etiqueta lleva una píldora oscura detrás y sube a 26 px |
| I3 | Los resaltes de Cambios no coincidían con las tarjetas | Recorte y resaltes medidos sobre la captura 2x: panel 342,5–741,5 px y tarjetas en x 355,5 con 373 px de ancho |
| I4 | El cambio A→B apenas se leía en el 3D | Fantasma en aristas de la rev A, visible a través del acero, y cotas sobre el modelo sincronizadas con cada fila. Las cotas son: longitud entre tangentes +500 mm, N3 +200 mm, N4 nueva y faldón +150 mm. El naranja intenso se aplica solo a N3 y N4 |
| I5 | El alambre de triángulos ensuciaba la subida 2D→3D | Ahora se usan aristas (`EdgesGeometry` a 20°). Al cerrar, las aristas usan la geometría B |
| M1 | Había dos barridos de brillo | Solo queda el del logo final |
| M3 | La sombra de contacto aparecía antes de tiempo | Ahora depende de q² |
| M5 | Había textos de menos de 32 px | Notas a 28 px, PDF a 30 px, origen a 32 px y etiqueta a 26 px |

**Segunda pasada del mismo revisor, sobre el vídeo re-renderizado:**
- I1–I5 y M1 están bien, con evidencia en f395/f410, f640–700 y f1020–1160.
- Las cotas coinciden con `changes.json` y con los IFC.
- Veredicto: apto como borrador, sin obligatorios pendientes.
- Nota menor: el corchete de +500 mm abarca toda la virola de la rev B, no solo el tramo añadido.

Antes de la revisión ya se habían corregido, en la revisión propia de fotogramas, el roce del faldón con el rótulo de la escena 5 y la virola con aspecto de duelas.

Pendiente, de menor prioridad:
- **M2:** el acero se ve algo claro.
- **M4:** el fundido de la escena 3 tiene tres capas.
- **M6:** 4 pasadas de escáner en vez de 5 y 3 flylines en vez de 2. Son decisiones de ritmo. La spec decía 28 % para las evidencias, pero el valor correcto es 32 %, como en el producto.
- **M7:** de f600 a f790 no hay rótulo, solo la subida.
- **M8:** la versión con BGM está a unos −23 LUFS. Para web conviene normalizar a −16 LUFS / −1 dBTP en el máster final, y algunos SFX quedan bajos bajo la BGM.

## Limitaciones conocidas

1. **Audio no escuchado.** No puedo oír audio. Los sonidos se eligieron por descripción, valoraciones y medición (pico, RMS, actividad).
   - La BGM se compone con capas CC0 en vez de una pista única: Freesound no ofrecía una pista «ambient-industrial» completa con licencia clara.
   - Hay que escucharla antes de publicar. Si no convence, se cambia la tabla `CUES` de `src/audio.tsx` o se renderiza la versión sin BGM y se añade una pista licenciada.
2. **Vistas previas MP3.** Los audios son las vistas previas MP3 de Freesound, no los WAV originales. Para un máster final conviene descargar los originales con sesión en Freesound.
3. **Capturas de la app local.** Las capturas vienen del servidor local, rama con el contenido de `main` a 03/11/2026.
   - En la captura de Revisión, el visor 3D de la app etiqueta «6000 mm» mientras el campo seleccionado es el diámetro (2.000 mm). Es la UI real tal cual. El plano del vídeo se centra en la cola y el recorte del GA.
4. **Técnicas Reunidas.** No aparece ni su logo ni su nombre. El subtítulo de la barra lateral de la app se ha tapado en las capturas (`scripts/redact.py`), sin tocar el código de la app.
5. **ffmpeg.** El analizador de Freesound necesitaba un ffmpeg completo. Se usó `imageio-ffmpeg` en un entorno temporal; el proyecto no depende de él para renderizar.
6. **Rendimiento.** El render es determinista (sin `Date.now` ni `Math.random`), pero lento por el tramo 3D: 750 fotogramas con WebGL a través de ANGLE.
7. **Motion Workbench en Windows.**
   - `workbench/scripts/open.mjs` crea enlaces simbólicos, y Windows los rechaza sin modo desarrollador (EPERM). Se sustituyeron por uniones de directorio y enlaces duros dentro de la carpeta del workbench de la skill.
   - `workbench/demosrc` venía como archivo de texto (un enlace de git mal extraído) y se cambió por una unión a `../demos`.
   - `npm install` del workbench se ejecutó a mano.
   - Arranque: desde `workbench/`, `node scripts/open.mjs` (reutiliza el proyecto enlazado) y abrir http://localhost:5198/?import=project.
   - `CaptionUnit` usa 90 f por defecto cuando el workbench lo monta sin duración; el render no cambia.
