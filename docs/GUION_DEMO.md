# Guion de la demo: exposición y vídeo (6:00)

Un solo guion para dos cosas:

- **La exposición del viernes 27 a las 11:00:** voz en directo y la app en vivo. Los clips de
  vídeo (cámara, IA y promo) van intercalados.
- **El vídeo de la demo (tarea 4.6):** el mismo guion grabado entero. Sirve de plan C si falla la
  app y para enseñarlo fuera del evento.

Sigue la estructura de [ROADMAP J.1](ROADMAP.md#j-pitch-presentación-y-negocio): plano → dato →
modelo → cambio → decisión. El recorrido técnico de la app está en [DEMO.md](DEMO.md) y el
material de escala, en [PITCH_ESCALA.md](PITCH_ESCALA.md).

## Reglas que no se saltan

1. **Datos.** Hasta el día 26 todo lo que se ve es sintético y se dice. Las cifras de TR solo
   entran cuando estén medidas en Databricks, y siempre separadas de las sintéticas. En el guion
   aparecen como **[CIFRA TR]**: si no hay medida, la frase se dice sin cifra o se quita.
2. **Ningún dato de TR fuera de la plataforma.** No se meten planos, capturas ni nombres de TR en
   generadores de vídeo, en Claude, en el repo de GitHub ni en el vídeo publicado. Las tomas que
   enseñen datos de TR se graban y montan en la plataforma o en el portátil de la exposición, y
   antes de usarlas fuera se pregunta a los mentores ([FLUJO_IA.md](FLUJO_IA.md)).
3. **La IA generativa se ve como tal.** Cada clip de IA lleva el rótulo «Imagen generada con IA»
   en la esquina, y ninguno muestra la interfaz ni geometría que pase por nuestra. Cuenta en el
   criterio de ética y uso responsable.
4. **Sin marcas ni personas reales en los clips de IA:** ni logotipos de TR o de otras empresas, ni
   caras reconocibles, ni texto legible (los modelos lo deforman).
5. **Nada que la app no haga.** Lo ilustrativo (holograma, planta con equipos de relleno) se dice
   como ilustrativo, igual que en la propia app.

## Reparto de voces

Cada voz habla en su bloque y cambia de toma de cámara. Propuesta para ajustar en el primer
ensayo:

| Voz | Bloques | Persona |
| --- | --- | --- |
| V1 | Apertura, problema y cierre | Javier |
| V2 | Entrada de documentos y evidencia | Por decidir |
| V3 | Del plano al modelo y cambios | Por decidir |
| V4 | Estrategias, medida contra TR y escala | Por decidir |

En la exposición en directo, quien no habla lleva el ratón. Nadie habla mientras otra persona lee
una cifra.

## Leyenda

| Código | Qué es | Dónde está |
| --- | --- | --- |
| `APP` | La web en vivo (o grabada para el vídeo), con la ruta y los clics | [Preparación de la app](#preparación-de-la-app) |
| `CAM-A`…`CAM-E` | Tomas nuestras desde distintos ángulos | [Tomas de cámara](#tomas-de-cámara) |
| `IA-1`…`IA-5` | Clips generados con IA, con su prompt | [Clips generados con IA](#clips-generados-con-ia) |
| `PROMO` | Tramos del vídeo de 45 s de `promo/trazia-hackathon` (fotogramas a 30 fps) | `promo/trazia-hackathon/out/` |
| `DBX` | Grabación de pantalla de Databricks (notebooks 02, 01 y 03) | Solo desde el día 25 |
| `RÓTULO` | Texto sobreimpreso en el montaje | En cada fila |

## Guion

Tiempo de voz: unas 700 palabras en 6:00, a unas 140 palabras por minuto. El resto son pausas y
transiciones. Si un bloque se alarga, se recorta su voz, no la del cierre.

### 0:00–0:20 · Apertura

| Pantalla | Voz (V1, en off) |
| --- | --- |
| `IA-1` (8 s): amanecer sobre una planta de proceso, plano aéreo que avanza despacio. `IA-2` (8 s): mesa de ingeniería con planos en papel, nubes de revisión en rojo, una mano pasa hojas. `RÓTULO` esquina: «Imagen generada con IA» | «Una planta como esta tiene cientos de equipos. Cada uno llega descrito en planos: disposición general, hoja de datos, revisión uno, revisión dos, revisión tres…» |
| Corte a negro y `PROMO` f0–180 (6 s): la pila de planos sintéticos en parallax hasta que el GA V-101 llena la pantalla | «…y alguien tiene que convertir cada plano en un modelo 3D. A mano.» |

### 0:20–0:45 · El problema

| Pantalla | Voz (V1, a cámara) |
| --- | --- |
| `CAM-A` V1 de frente, plano medio | «En Técnicas Reunidas un proyecto tiene unos 400 equipos y cada uno pasa por unas cuatro revisiones de su plano. Si modelar cada revisión lleva tres horas, son 4.800 horas de trabajo de transcripción por proyecto.» |
| `RÓTULO` a pantalla completa: «400 × 4 × 3 h = 4.800 h» y, debajo, «El reto estima entre 1.800 y 10.000 h por proyecto» | «Y el problema no es solo el tiempo. Es que la geometría viaja como documento, no como dato: cuando cambia una cota, nadie sabe a quién afecta hasta que choca en campo.» |

### 0:45–1:00 · Quiénes somos

| Pantalla | Voz (V1) |
| --- | --- |
| `PROMO` f180–270 (3 s): el logo se monta por caras. Después `CAM-D`: los cuatro en plano general. `RÓTULO` con los nombres: Javier Saguar, Iria Lozano Carrasco, Miguel Vera del Castillo y Alejandro Cuevas | «Somos TrazIA-3D. Leemos los planos, generamos el modelo IFC y guardamos de qué parte del plano sale cada dato. Cuando llega una revisión, enseñamos qué ha cambiado.» |

### 1:00–1:40 · Entran los documentos

| Pantalla | Voz (V2) |
| --- | --- |
| `CAM-B` V2 en tres cuartos, 3 s, y corte a `APP` `/documentos`: arrastrar `GAD_V-101_revA.pdf` y `HDM_V-101_revA.xlsx` a la bandeja. Se ve la familia «Recipientes verticales» y el proyecto | «Empezamos por lo que tiene el ingeniero: el plano GA y la hoja de datos. Los soltamos aquí. Cada archivo queda registrado con su huella, así que sabemos exactamente qué versión hemos leído.» |
| `APP` `/pipeline`: pulsar «Reproducir explicación» a 2× con el recorrido D · Híbrido. Las cuatro fases se encienden: documentos, lectura, reconciliación, modelo | «La lectura va en cascada: texto, tablas, cotas y cajetín; el OCR entra solo si el plano está escaneado. Luego reconciliamos unidades y fuentes, y si dos fuentes se contradicen el valor se bloquea en lugar de inventarse.» |
| Desde el 25: `DBX` 4 s con el notebook `02_perfil_dataset` y su lista de avisos, en desenfoque si enseña datos. `RÓTULO`: «Dataset de TR · Azure Databricks» | «Con el dataset del reto hemos hecho lo mismo dentro de la plataforma, en lote: [CIFRA TR] equipos y [CIFRA TR] revisiones.» |

### 1:40–2:30 · Cada dato tiene un origen

| Pantalla | Voz (V2) |
| --- | --- |
| `APP` `/modelo?vista=revision`. A la izquierda el plano y a la derecha la «Cola de revisión», ordenada por riesgo. Clic en «Diámetro de la virola · 2.000 mm»: el plano salta a la región de la cota | «Este es el espacio de revisión. Cada valor tiene su unidad, su confianza y la región del plano de la que sale. Pulso el diámetro y me lleva a la cota. Si no se puede citar, no entra.» |
| `PROMO` f390–600 (7 s) como transición: la línea luminosa del campo al recorte | (pausa de un segundo, sin voz) |
| `APP`: filtro «Por revisar» y señalar la frase «Ordenada por riesgo: primero lo que hay que confirmar». Con los datos de TR, abrir un campo en abstención si lo hay; en la demo sintética todos tienen confianza 0,75 y basta con señalar la frase | «La cola no va en orden de plano, va por riesgo: primero lo que más impacta y menos confianza tiene. Si el sistema no está seguro, se abstiene y lo dice. Prefiere un hueco a un número inventado.» |
| `CAM-C` 2 s: detalle de la mano en el ratón y la pantalla desenfocada | «Al final decide una persona.» |

### 2:30–3:00 · Elegimos con datos

| Pantalla | Voz (V4) |
| --- | --- |
| `CAM-B` V4, 2 s, y corte a `APP` `/bench?vista=estudio`: tarjetas «Recomendación · Planos vectoriales» (B) y «Planos escaneados» (D), y la gráfica de puntuación con intervalos | «El reto proponía cuatro caminos: visión, reglas, RAG o híbrido. No elegimos uno a ojo: construimos los cuatro y los medimos con la misma rúbrica que vais a usar vosotros. En planos vectoriales gana el de reglas, en escaneados el híbrido. Por eso la estrategia se elige por tipo de documento.» |
| `RÓTULO` fijo abajo: «Estudio sobre 40 equipos sintéticos · intervalos del 95 %» | — |

### 3:00–3:50 · Del plano al modelo

| Pantalla | Voz (V3) |
| --- | --- |
| `IA-3` (6 s): un plano en papel sobre una mesa; sus líneas se levantan y forman un recipiente en alambre celeste. `RÓTULO` «Imagen generada con IA» | «Lo que buscábamos era este momento: que el plano se convierta en modelo.» |
| `APP` portada `/`, sección «Del plano al modelo»: bajar despacio con la rueda y ver cómo el plano GA de V-101 se levanta hasta el IFC | «Y en la app ese momento no es una animación sin más: es el IFC que acabamos de generar.» |
| `APP` `/modelo?vista=revision`: vista Iso, después «Rayos X» y «Explosionado». Clic en la boquilla N2: el «Inspector IFC» muestra sus propiedades. Leer el pie «IFC4 · 22.706 triángulos · sintético» | «Lo que veis es el IFC, no un dibujo aparte: IFC4 con virola, fondos, faldón y boquillas con su orientación y elevación. Cada elemento lleva dentro de qué plano viene y su estado de aprobación. Se abre en cualquier visor del mercado.» |
| Alternativa al clic en vivo: `PROMO` f600–930 (11 s), alambre → acero con órbita | — |

### 3:50–4:50 · Llega la revisión B

| Pantalla | Voz (V3) |
| --- | --- |
| `APP` `/modelo?vista=cambios`: las cuatro tarjetas de arriba (8 cambios de campos, 7 afectan a la geometría, 2 documentos nuevos y la huella de datos). Pulsar **Espacio** para reproducir: la cámara sigue cada cambio de A a B | «Ahora llega la revisión B del plano. Esto es lo que más tiempo cuesta hoy, y aquí está en segundos: ocho cambios de campo, siete afectan a la geometría.» |
| `APP` lista de cambios: clic en «Longitud entre tangentes +500 mm», después en «N3 · elevación +200 mm» y en «N4 · boquilla nueva». En el 3D se iluminan en naranja | «La virola crece 500 milímetros, la boquilla N3 sube 200 y aparece una boquilla nueva, la N4. Y cada elemento conserva su identificador: el modelo B es el mismo objeto que el A, actualizado, no uno nuevo.» |
| `APP` bajar a «Impacto por disciplina»: las etiquetas PIP, EST, CIV e I&C de cada cambio | «Y lo más importante: a quién afecta. La N4 nueva va a tuberías e instrumentación; el peso, a estructuras y civil. Exportamos estos cambios como incidencias BCF para el visor que ya use el cliente.» |
| `CAM-E` 3 s: V3 señala la pantalla grande de la sala | «Qué cambió, cuánto, dónde y a quién afecta.» |

### 4:50–5:30 · Medido contra los IFC de TR

| Pantalla | Voz (V4) |
| --- | --- |
| `DBX` notebook `03_evaluar_contra_tr`: tabla por equipo y un mapa de calor 3D girando. Si los mentores no autorizan enseñar geometría de TR, se usa el mapa del modo ensayo con el `RÓTULO` «Ensayo con datos sintéticos» | «Todo eso hay que medirlo. Comparamos nuestro IFC con el IFC de referencia de TR, superficie contra superficie. En rojo, donde nos separamos.» |
| `RÓTULO` con las cifras medidas el 26, cada una con su intervalo y el número de equipos: error de diámetro [CIFRA TR] %, boquillas encontradas [CIFRA TR], error de posición [CIFRA TR] mm | «En [CIFRA TR] equipos, el diámetro tiene un error medio del [CIFRA TR] % y encontramos [CIFRA TR] de cada diez boquillas. Y el convenio de orientación no lo ajustamos en el propio equipo: lo fijamos con los demás, para no hacernos trampas.» |
| `APP` `/impacto` con el tiempo medido en el campo «Minutos de revisión asistida» | «En revisión asistida tardamos [CIFRA TR] minutos por equipo. Con eso, el proyecto de 4.800 horas baja a [CIFRA TR].» |

Si el 26 no hay IFC de TR o tiempo medido, este bloque dura 20 s. Se enseña el estudio sintético y
se dice: «No tenemos aún la cifra contra los modelos de TR; esto es lo que medimos con datos
sintéticos y así lo mediremos con los vuestros».

### 5:30–6:00 · Límites y cierre

| Pantalla | Voz (V1, a cámara) |
| --- | --- |
| `CAM-A` V1 de frente | «Lo que no escondemos: la salida automática siempre es un borrador. Aprobar exige una persona y queda ligado a los datos: si cambia un valor, la aprobación cae. Y los datos de Técnicas Reunidas no han salido de la plataforma.» |
| `IA-5` (6 s): plano que se aleja desde una tableta con un modelo 3D hasta la planta al atardecer. `RÓTULO` «Imagen generada con IA» | «Siguiente paso: más familias de equipos y medir el tiempo con ingenieros de verdad.» |
| `PROMO` f1170–1350 (6 s): el modelo se recoge y el logo encaja. Después `CAM-D` con los cuatro | «TrazIA-3D: del plano al modelo, con cada cambio trazado. Gracias.» |

## Preparación de la app

Igual que en [DEMO.md](DEMO.md), con estos ajustes para el guion:

1. API en modo offline (`TRAZIA_OFFLINE=1`) y web con `pnpm build; pnpm start`. Si cae la API,
   la web sigue con los datos de `public/demo/` (plan B). El vídeo, en otra pestaña (plan C).
2. Navegador a 1920×1080, zoom 100 %, tema oscuro y sin extensiones. Ratón físico.
3. Pestañas abiertas en el orden del guion: `/documentos`, `/pipeline`, `/modelo?vista=revision`,
   `/bench?vista=estudio`, `/` (sección «Del plano al modelo»), `/modelo?vista=cambios` e
   `/impacto`. Se recorren una vez antes, para que el IFC y los PDF queden en caché.
4. En `/documentos` se dejan preparados los dos archivos de `examples/documents` en una carpeta a
   la vista, para arrastrarlos sin buscar.
5. En `/modelo?vista=cambios` no se pulsa Espacio hasta el momento del guion: la reproducción
   empieza desde el principio.

### Capturas para la presentación (.pptx)

Hacerlas el mismo día del ensayo, a 1920×1080 y en tema oscuro. Se guardan en
`docs/capturas/producto/` con estos nombres:

| Archivo | Ruta | Estado de la pantalla |
| --- | --- | --- |
| `demo-01-documentos.png` | `/documentos` | Bandeja con el GA y la HDM recién añadidos |
| `demo-02-pipeline.png` | `/pipeline` | Recorrido D a mitad, con la fase «Lectura» encendida |
| `demo-03-revision.png` | `/modelo?vista=revision` | Diámetro seleccionado y la cota resaltada en el plano |
| `demo-04-estudio.png` | `/bench?vista=estudio` | Las dos recomendaciones y la gráfica con intervalos |
| `demo-05-modelo.png` | `/modelo?vista=revision` | Vista Iso en Rayos X con la N2 en el inspector |
| `demo-06-cambios.png` | `/modelo?vista=cambios` | N4 seleccionada en naranja e impacto por disciplina |
| `demo-07-mapa.png` | Notebook 03 | Mapa de calor (de ensayo hasta tener permiso para el de TR) |

### Grabación de pantalla para el vídeo

- OBS a 1920×1080 y 30 fps (igual que el vídeo de 45 s), sin sonido del sistema.
- Cursor resaltado y clics visibles. Cada pantalla, en un clip propio con 2 s de margen delante y
  detrás para cortar.
- Movimientos de ratón lentos y en línea recta, sin dar vueltas mientras se habla.

## Tomas de cámara

Se graban el jueves 26 por la tarde en la sala del evento, o antes con el mismo fondo si no da
tiempo. Móvil en horizontal, 1080p a 30 fps, en trípode, con micrófono de solapa o con el móvil a
menos de un metro. Cada frase se graba dos veces: una mirando a cámara y otra mirando a la
pantalla.

| Toma | Encuadre | Quién | Para qué |
| --- | --- | --- | --- |
| `CAM-A` | Frontal, plano medio y a la altura de los ojos; fondo con la pantalla del portátil desenfocada | V1 | Problema y cierre: dirigirse al jurado |
| `CAM-B` | Tres cuartos lateral (unos 45°) desde la izquierda, plano medio corto | V2 y V4 | Entrada de cada voz, 2–3 s antes de pasar a la app |
| `CAM-C` | Detalle cenital de las manos en el ratón y el teclado, con la pantalla de fondo | Cualquiera | Transiciones: «al final decide una persona» |
| `CAM-D` | Plano general de los cuatro delante de la pantalla, cámara fija | Todos | Presentación del equipo y despedida |
| `CAM-E` | Contraplano por detrás del hombro: la persona señala la pantalla grande con la app | V3 | Cambios: «qué cambió, cuánto, dónde y a quién afecta» |

En ninguna toma aparece en pantalla un plano de TR, salvo que los mentores lo autoricen. Si una
toma lo enseña de fondo, se desenfoca en el montaje.

## Clips generados con IA

Para cualquier modelo de texto a vídeo (Veo, Sora, Kling, Runway…), en 16:9 y 1080p. Cada clip,
de 6 a 8 s. Los prompts van en inglés, porque estos modelos los siguen mejor; el texto negativo se
pone donde el modelo lo admita. Generar tres variantes de cada uno y elegir en el montaje.

Las mismas condiciones para todos: sin logotipos, sin texto legible, sin personas reconocibles y
nada que imite a una empresa real. Al montarlos, rótulo «Imagen generada con IA».

### IA-1 · Planta al amanecer (apertura, 8 s)

```text
Cinematic aerial shot at dawn over a large generic petrochemical process plant: tall distillation
columns, vertical pressure vessels, pipe racks and storage tanks, soft cold blue light with warm
sunrise on the horizon, light mist between the units. Slow forward drone push-in, steady, no
cuts. Photorealistic, 35mm lens, shallow haze, muted colors, high detail. No people, no logos,
no company names, no readable text.
```

Negativo: `logos, brand names, readable text, signs, people, flags, cartoon, fast motion`.

### IA-2 · Ingeniería en papel (apertura, 8 s)

```text
Close-up of an engineering desk covered in large-format paper technical drawings of industrial
vessels, several revisions stacked, red ink revision clouds and triangles drawn by hand. A hand
flips through the sheets slowly, another hand holds a scale ruler. Overhead desk lamp, dark
office, cold monitor glow in the background. Photorealistic, slow camera dolly to the side,
shallow depth of field. Drawings are blurry line art, no readable text or numbers, no logos,
face not visible.
```

Negativo: `readable text, numbers, logos, face, cartoon`.

### IA-3 · El plano se levanta (del plano al modelo, 6 s)

```text
A single large technical drawing of a vertical pressure vessel lies flat on a dark matte table
in a black studio. Thin cyan lines lift off the paper and rise into the air, assembling into a
glowing cyan wireframe of a tall cylindrical vessel with domed heads, a skirt support and small
nozzles. Slow orbiting camera, single cold top light, subtle reflections. Minimal, elegant,
photorealistic studio look, 16:9. No text, no logos, no people.
```

Negativo: `text, labels, logos, people, explosion, particles everywhere, neon city`.

Este clip ilustra la idea y nunca sustituye al modelo real: justo después va el IFC de la app.

### IA-4 · El cambio que llega tarde (opcional, reserva para el bloque del problema, 6 s)

```text
Construction site of an industrial plant, daytime, overcast. A crane slowly lifts a large steel
vertical vessel next to a steel structure; workers in generic orange high-visibility vests and
white helmets look up from a distance, small and not recognizable. Camera slowly tilts up
following the vessel. Photorealistic, documentary style, natural light. No logos, no company
names, no readable text, no faces in close-up.
```

Negativo: `logos, brand names, readable text, close-up faces, accident, fire`.

### IA-5 · Del modelo a la planta (cierre, 6 s)

```text
Close-up of a tablet held by gloved hands on an industrial plant walkway at dusk, the screen
shows a clean 3D model of a vertical pressure vessel in cool cyan tones. The camera slowly pulls
back and rises, revealing the real plant behind with warm lights turning on, columns and vessels
in silhouette against an orange and blue sky. Photorealistic, smooth crane movement, cinematic.
No logos, no readable text, no recognizable faces.
```

Negativo: `logos, readable UI text, faces, cartoon, fast motion`.

### Piezas nuevas con video-shotcraft (como el vídeo de prueba)

El vídeo de 45 s se hizo con la skill video-shotcraft en Remotion, sobre capturas reales y el IFC
sintético. Se pueden pedir piezas nuevas de la misma forma, en `promo/trazia-hackathon/`, y se
añaden al montaje como `PROMO`:

```text
Autonomous Free Creation: pieza de 12 s para TrazIA-3D (IndesIAhack 2026, reto GA2MODEL), mismo
proyecto Remotion que promo/trazia-hackathon y misma dirección visual (design-spec.md). 1920×1080,
30 fps, H.264, sin plantilla Ink Press. Escena «Elegimos con datos»: captura real de
/bench?vista=estudio inclinada en 2.5D; las cuatro barras A, B, C y D crecen hasta su
puntuación del estudio 7 (0,578 · 0,609 · 0,600 · 0,708, leídas de web/public/demo) con su
intervalo; la cámara se acerca a D y aparece el rótulo «Elegimos con datos». Etiqueta
«Demostración · datos sintéticos» siempre visible. Dos renders, con y sin BGM.
```

```text
Autonomous Free Creation: pieza de 10 s para TrazIA-3D en el mismo proyecto Remotion. Escena
«Medido contra la referencia»: el IFC sintético de V-101 rev B (web/public/demo/ifc/rev_b.ifc)
y una copia desplazada se superponen; la superficie se colorea con la escala Turbo de 0 a 50 mm
como el mapa de calor de bench.evaluar, y la cámara orbita. Rótulo «Superficie contra
superficie». Etiqueta «Ensayo con datos sintéticos» siempre visible. Sin geometría de TR.
```

## Montaje del vídeo

- Proyecto a 1920×1080 y 30 fps. Música: la del vídeo de 45 s (licencias en
  `promo/trazia-hackathon/public/audio/CREDITS.md`) a −24 dB bajo la voz y subiendo solo en
  apertura y cierre.
- Voz grabada aparte si la de cámara suena mal; se sincroniza por la claqueta (una palmada al
  empezar cada toma).
- Subtítulos en español quemados, porque en la sala puede haber ruido.
- Rótulos con la tipografía de la app (Archivo para títulos, Inter para texto) y el celeste del
  logo. La etiqueta «Demostración · datos sintéticos» va en todos los planos de `APP` y `PROMO`.
- Exportar dos versiones: con datos de TR (solo para la sala, se queda en el portátil) y sin datos
  de TR (para el repo y para enseñarlo fuera).

## Calendario

| Cuándo | Qué |
| --- | --- |
| Antes del 22/11 | Generar los clips IA-1 a IA-5 y las dos piezas de video-shotcraft. Primer ensayo cronometrado leyendo el guion |
| 22/11 | Congelación del alcance: el recorrido por la app ya no cambia |
| Antes del 25 | Grabar la app (todas las filas `APP`) y montar la versión sintética del vídeo |
| 26/11, tarde | Cifras de TR en las filas `[CIFRA TR]`, tomas `CAM` en la sala y grabaciones `DBX` |
| 26/11, noche | Montaje final y segundo ensayo cronometrado con alguien que haga de jurado (tarea 4.3) |
| 27/11, 10:00 | Vídeo y presentación subidos con el código |
| 27/11, 11:00 | Exposición: app en vivo y el vídeo abierto en otra pestaña |
