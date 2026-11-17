# Pitch web · TrazIA-3D

Boceto de seis minutos para GA2MODEL. La pauta del enunciado (pág. 15) marca
los cambios de bloque en 0:00, 0:45, 1:30, 2:30, 3:45 y 5:00. Las nueve
escenas mantienen estos cortes. Las [bases de IndesIAhack](https://indesiahack.org/bases-legales)
piden entregar un `.pptx` al jurado.

## Probar y presentar

Desde esta carpeta con Node.js 22.12 o posterior:

```powershell
corepack pnpm@10.18.0 install --frozen-lockfile
corepack pnpm@10.18.0 test
corepack pnpm@10.18.0 build
corepack pnpm@10.18.0 preview --port 4173
```

Abrir [localhost:4173](http://127.0.0.1:4173/) y pulsar **F** al empezar a hablar.
El cronómetro de la cabecera cuenta el tiempo real de exposición, también al
volver a una escena anterior o al superar los seis minutos.

| Acción | Control |
| --- | --- |
| Avanzar o retroceder | Flechas ← y → o deslizar horizontalmente en una pantalla táctil |
| Entrar o salir de pantalla completa | F |
| Iniciar, pausar o reanudar el cronómetro | T o pulsar el reloj |
| Ensayar con avance automático hasta 6:00 o pausar el avance | P |
| Consultar el guion y los controles | N |
| Volver a la primera escena y poner los relojes a cero | Inicio |

**R** repite la entrada de la escena activa sin mover el reloj. Abre
`/?fx=0` para usar las transiciones originales. La preferencia del sistema
de movimiento reducido también desactiva los nuevos efectos.

El build incorpora imágenes, fuentes y texto. Una vez preparado `dist/`, el
servidor de presentación y las escenas funcionan sin Internet ni API.
El enlace a la demo en las notas abre la aplicación si está levantada por separado.

La apertura dedica unos doce segundos a tres diseños del catálogo sintético
antes de llegar al caso V-101. Cada clip pasa del alzado de su GA a una órbita
corta de su propio IFC. Los originales BC-CY102, BC-P103 y BC-AC104 están en
[`web/public/demo/industriales`](../../web/public/demo/industriales). Para
cambiar la selección, editar `designs` en `src/design-showcase.jsx` y colocar
en `public/media/catalogo/` un WebM y su fotograma WebP con el tag del equipo.

## Comparar las animaciones en desarrollo

Genera el build original desde un worktree en el commit `10aa32a` y copia
su carpeta `dist/` como `boceto/` dentro de `pitch/web/` en este checkout.
La carpeta `boceto/` se ignora en Git.

```powershell
corepack pnpm@10.18.0 dev --port 5173 --strictPort
```

Abre [comparar.html](http://127.0.0.1:5173/comparar.html). La selección y el avance
se sincronizan entre ambos paneles. **Repetir (R)** vuelve a mostrar la escena
seleccionada y la casilla **?fx=0** cambia solo el panel Actual.

## Actualizar durante el evento

1. Editar [`src/pitch-data.js`](src/pitch-data.js) para cambiar mensajes, guion,
   fuentes, cifras, resultados por estrategia y enlace a la demo.
2. Dejar las imágenes o grabaciones autorizadas en `public/media/`. El archivo
   de datos apunta a las rutas de los medios. Si se rellena `modelVideo` o
   `changesVideo`, aparece el botón **Ver grabación** en esa escena.
   El marcador `revisionDetail` identifica una pieza en un fotograma concreto.
   Al sustituirlo, actualizar el campo y sus coordenadas normalizadas en la
   imagen nueva, o quitar el marcador.
3. Indicar el alcance de los datos de evento donde corresponda. Conservar la
   marca sintética en el material de ensayo que se reutilice y publicar solo
   agregados y medios que el organizador autorice.
4. Ejecutar las pruebas y volver a compilar. Ensayar con el portátil y el
   proyector antes de entregar. El mismo guion sirve para montar el PowerPoint.

## Procedencia del boceto

- Problema y duración: enunciado GA2MODEL, págs. 5 y 15.
- Recorte y confianza: GA y JSON sintéticos de [V-101 Rev. B](../../examples/vessel_rev_b.json).
  El 0,75 corresponde al lector de etiquetas de esta ficha.
- Comparativa: [Estudio 7](../../docs/ESTUDIO.md#estudio-7--calibración-v6-1112026).
  Se recoge una variante por estrategia y la puntuación compuesta; la cifra es sintética.
- Escala: [lote CPU del 02/11](../../docs/PITCH_ESCALA.md). Los DRAFT cuentan
  exportaciones y el rendimiento es la aceleración medida en ese lote.
- Vistas A/B: fotogramas calculados a partir de los IFC públicos de la demo
  con la misma cámara y escala. La animación de escaneo es una transición de presentación.

Para regenerar las vistas y el recorte de V-101 con WebIFC, Python y Poppler:

```powershell
corepack pnpm@10.18.0 assets:ifc
uv run --project ../.. --extra dev python scripts/build_media.py
```
