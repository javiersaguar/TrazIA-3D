# TrazIA-3D · GA2MODEL — storyboard (borrador 45 s)

Pieza audiovisual de demostración para IndesIAhack 2026 (reto GA2MODEL).
Modo: video-shotcraft, creación libre autónoma (sin plantilla Ink Press).
1920×1080 · 30 fps · 1350 fotogramas · H.264.

Todo el material sale del propio repositorio y es **sintético**:

- El plano GA es `web/public/demo/docs/GAD_V-101_rev{A,B}.pdf`, que lleva el sello «SYNTHETIC FIXTURE – Not a vendor document».
- Los planos de banco son `web/public/demo/bench/*.webp`.
- La geometría es el IFC real que genera TrazIA-3D (`web/public/demo/ifc/rev_{a,b}.ifc`), exportado a malla con ifcopenshell.
- Las capturas son de la app local (`next dev`) con los datos de demostración.

Ningún fotograma usa documentos de Técnicas Reunidas. La etiqueta «Demostración · datos sintéticos» está siempre visible en la esquina inferior derecha.

## 0 · Brief de producto

**Qué es.** TrazIA-3D lee el plano GA y la hoja de datos de un recipiente y extrae cada parámetro con su evidencia: página, bbox, celda y confianza. Una persona revisa los valores dudosos. Con eso genera un IFC4 y compara revisiones A/B campo a campo, mostrando el impacto en 3D.

**Público.** Jurado técnico de la hackatón y equipo de ingeniería de TR. Valoran trazabilidad, rigor y que el modelo sea el caso real.

**Una idea.** Del plano al modelo, con cada cambio trazado.

**Qué no se dice.** No se dan métricas de precisión, ahorros de tiempo ni porcentajes. No se presenta como evaluado sobre documentos industriales reales. No se muestra ninguna función que no exista en la app.

### Necesidades y su ejecución

| Necesidad del brief | Ejecución |
|---|---|
| Evolución 2D → datos → 3D IFC → cambios | Cuatro actos visuales sobre una sola paleta: papel → panel → acero → naranja revisión |
| Logo real, UI real | Logo vectorizado por caras (`logo-geometry.ts`, el mismo de la web) y capturas reales de `/documentos`, `/modelo?vista=revision` y `/modelo?vista=cambios` |
| «Cada dato tiene un origen» | Un campo real de Revisión, «Diámetro 2.000 mm» (fuente GA p.1 con su bbox), unido por una línea al recorte del plano donde aparece |
| WOW 2D→3D con geometría real | Malla del IFC rev A sobre el plano GA: el plano se levanta, pasa de alambre a acero y la cámara orbita hasta un plano heroico |
| Rev A/B con cambios reales | Morph por GlobalId de A a B: virola 6.000→6.500, faldón 1.200→1.350, N3 +200 mm y N4 nueva. Cifras sacadas de `changes.json` |
| Cierre | El modelo se recoge y el logo se monta encima. Lema y línea «TrazIA-3D · GA2MODEL», con más de 1 s de quietud |
| Etiqueta sintética | «Demostración · datos sintéticos» siempre visible, discreta |
| Música y SFX con licencia | Freesound CC0 (o CC BY con atribución en `public/audio/CREDITS.md`). Dos renders: con y sin BGM |

## 1 · Dirección visual (resumen; detalle en `design-spec.md`)

Negro de la app (#09090b) como escenario de estudio. Una sola luz cenital fría (celeste del logo) y acero cepillado. El papel del plano es el único blanco.

La revisión B entra en el naranja de revisión de la app (#f5a35c). Los textos usan Archivo estrecho (el display de la landing) en grande, e Inter y JetBrains Mono para los datos.

Sin styleframe aparte. Las texturas y la paleta salen de la app y del plano, y el primer still de QA de cada escena hace de styleframe (`out/qa/`).

## 2 · Funciones → tarjetas de gallery

| Función | Tarjeta (validada en `gallery/api/library.json`) | Demo de referencia | Uso |
|---|---|---|---|
| Planos como objetos 2.5D | `depth-layer-moves · multiplane` y `space-camera-moves · exploded-view` | `demos/camera/space-camera-moves/ExplodedView.tsx` | Pila axonométrica de hojas con parallax por capas (sin la parte de «炸开/合体», que no aplica) |
| Lectura del documento | `scan-bracket-sweep` | `demos/effects/scan-bracket-sweep/ScanBracketSweep.tsx` | Corchetes L + barrido de 5 pasadas sobre el GA, que no se mueve |
| Campo ↔ origen | `glow-flyline-moves · flyline-arc` | `demos/effects/glow-flyline-moves/FlylineArc.tsx` | Línea con cabeza luminosa del campo al recorte; pulso al llegar |
| Plano → modelo | `wall-reveal-moves · wireframe-draw-on` + iluminación de `spotlight-hero-card` | `demos/ui-entrance/wall-reveal-moves/WireframeDrawOn.tsx` | Alambre → acero sobre el IFC real, con un foco cenital |
| Brillo de héroe | `light-play-moves · sheen-sweep` | `demos/effects/light-play-moves/SheenSweepRetry.tsx` | Un único barrido de brillo sobre el logo final (Q4) |
| Modelo → marca | `ui-to-brand-morph · input-morph-assemble` | `demos/outro/ui-to-brand-morph/InputMorphsIntoLogo.tsx` | El volumen se recoge en un punto y las caras del logo encajan en sus huecos |

`text-as-mask` se valoró para la apertura y se descartó: tapar el plano con letras gigantes ocultaba lo único que hay que leer en la escena 1.

## 3 · Storyboard por fotogramas

Las secuencias usan fotogramas absolutos. La única fuente de verdad es `src/timeline.ts`.

| # | Fotogramas | Tiempo | Imagen | Rótulo | SFX |
|---|---|---|---|---|---|
| 1 | 0–180 | 0–6 s | Negro. Aparecen en profundidad cuatro hojas: los tres planos de banco C-101 (limpio, escaneado, rotulado) y el GA V-101 rev A. Forman una pila axonométrica que deriva despacio en parallax. La cámara se acerca hasta que el GA V-101 llena el centro | «La ingeniería empieza en un plano.» (f 42) | Drone grave, roce de papel (f 12) |
| 2a | 180–270 | 6–9 s | El logo TrazIA 3D se monta por caras (vista explosionada, como en la web) y luego el wordmark. Quieto ≥ 1 s | — | Click suave en el encaje, brillo |
| 2b | 270–390 | 9–13 s | Captura real de **Documentos** inclinada en 2.5D. Corchetes y barrido sobre la miniatura del GA. Dos líneas salen hacia los campos extraídos | «Transformamos documentos en conocimiento.» (f 285) | Pasadas de escáner muy bajas |
| 3 | 390–600 | 13–20 s | Captura real de **Revisión** con «Diámetro 2.000 mm» seleccionado. Una flyline sale del valor y llega al recorte ampliado del GA donde está la cota, con pulso al llegar. Etiqueta «GA-V101 · p.1» | «Cada dato tiene un origen.» (f 430) | Tick al conectar |
| 4 | 600–930 | 20–31 s | El GA V-101 queda plano en un estudio negro y sus zonas de evidencia se encienden. El recipiente sale del papel en alambre celeste, pasa a acero y la cámara orbita hasta la vista heroica. Notas breves: virola, cabezales, faldón, toberas | «Del plano al modelo.» (f 790) | Riser 600–760, impacto f 762 |
| 5 | 930–1170 | 31–39 s | El mismo modelo hace el morph A→B. Lo que cambia se tiñe de naranja: virola +500 mm, faldón +150, N3 +200 y N4 nueva. Entra un panel recortado de **Cambios** (captura real) | «Cada cambio, bajo control.» (f 960) | Woosh suave, ticks de cambio |
| 6 | 1170–1350 | 39–45 s | El modelo se recoge en un punto de luz y el logo encaja en su lugar. Barrido de brillo único. Quietud final de ~1,7 s | «Del plano al modelo, con cada cambio trazado.» / «TrazIA-3D · GA2MODEL» | Swell final y cola limpia |

### Arco de energía

- 0–6 s, bajo: misterio.
- 6–13 s, sube algo: identidad y lectura.
- 13–20 s, medio: precisión.
- 20–31 s, crece hasta el pico en f 762: transformación.
- 31–39 s, medio-alto: control.
- 39–45 s, se resuelve: firma.

## 4 · Rótulos

Todos en español y en sentence case, sin cifras inventadas.

- «La ingeniería empieza en un plano.»
- «Transformamos documentos en conocimiento.»
- «Cada dato tiene un origen.»
- «Del plano al modelo.»
- «Cada cambio, bajo control.»
- «Del plano al modelo, con cada cambio trazado.» / «TrazIA-3D · GA2MODEL»

En el morph de la escena 5 aparecen etiquetas de dato tomadas de `web/public/demo/json/changes.json`:

- Altura 6.000 → 6.500 mm
- Faldón 1.200 → 1.350 mm
- N3 elevación 3.500 → 3.700 mm
- N4 añadida
