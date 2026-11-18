# Automatizaciones para el evento

Comandos preparados para que el trabajo del 25 al 27 de noviembre sea repetir pasos conocidos y
no improvisarlos. Todos se ejecutan desde la raíz del repo. Las reglas de datos son las de
[FLUJO_IA.md](FLUJO_IA.md): al portátil y al repositorio solo llegan agregados.

| Cuándo | Comando | Qué hace |
| --- | --- | --- |
| Una vez por clon | `git config core.hooksPath .githooks` | Activa los hooks: coautores (`commit-msg`) y guardián de datos (`pre-commit`) |
| Antes de integrar | `uv run python scripts/comprobar.py [--completo]` | Guardián, ruff, pruebas y lote sintético; con `--completo`, web y pitch |
| Día 25, al empezar | `uv run python scripts/arranque_evento.py --gitlab <url> --aplicar --push` | Cierra PREVIOUS_WORK.md, crea el tag `pre-hackathon-baseline` y añade GitLab |
| En Databricks | notebook `databricks/04_todo` | Perfil, lote, evaluación, triaje y `cifras_evento.json` de una vez |
| Con el perfil | `uv run python -m synthetic.desde_perfil perfil.json` | Sintéticos parecidos al dataset del reto y lista de lo que no se imita |
| Con un lote | `uv run python -m bench.triaje <salida>` | Fallos por categoría y etapa, con la petición al asistente ya escrita |
| Con las cifras | `uv run python -m bench.cifras aplicar cifras_evento.json` | Cifras de TR al pitch y frases del guion, sin copiarlas a mano |
| Ensayo y demo | `uv run python scripts/demo.py [--pitch]` | API offline, web compilada y pestañas en el orden del guion |
| Capturas | `cd web; corepack pnpm capturas:guion` | Las seis capturas del guion a 1920×1080 |
| Entre ensayos | `uv run python scripts/demo.py --reiniciar` | La API y el navegador vuelven al estado guardado con `--guardar-inicial` |
| Plan C | `uv run --with imageio-ffmpeg python scripts/video_respaldo.py` | Graba el vídeo de respaldo de la demo, 1080p30 con rótulos |
| Pitch para enviar | `uv run --with python-pptx python pitch/web/scripts/exportar_pptx.py` | `pitch/TrazIA-3D.pptx` y `.pdf` con el guion en las notas |
| Viernes, antes de las 9:00 | `uv run python scripts/entrega.py` | Comprueba todo lo que debe estar bien en la entrega |

## Guardián de datos

`scripts/guardian_datos.py` solo usa la biblioteca estándar y corre en tres sitios: el hook
`pre-commit` (lo que va al commit), `scripts/comprobar.py` (todo lo versionado) y
`.gitlab-ci.yml` (lo versionado y las rutas de toda la historia). Bloquea:

- cualquier cosa en `data/private/` y los `.env` salvo `.env.example`;
- documentos y modelos (PDF, XLSX, imágenes, IFC, DWG, ZIP, Office…) fuera de las carpetas de
  [.guardian-permitidos](../.guardian-permitidos), y archivos de más de 5 MB;
- nombres del dataset del reto (`GAD_`, `HDM_`, `VESOR_`…) fuera de `examples/`;
- salidas del lote (`revision.json`, `modelo.ifc`, `eventos.json`, `resumen.json`, `perfil.json`,
  `evaluacion_tr.json`…);
- claves con forma de OpenAI, Anthropic, Groq, Google, NVIDIA, Hugging Face, Databricks, GitLab,
  GitHub, OpenRouter o claves privadas.

Nunca cita el contenido de un archivo: solo su ruta y el motivo. Si algo legítimo queda bloqueado,
se añade su carpeta a `.guardian-permitidos` en un commit aparte para que se vea en la revisión.
En Databricks el hook no corre; por eso el CI repite la comprobación.

## Comprobar antes de integrar

`scripts/comprobar.py` sustituye a las comprobaciones de GitHub Actions, que en GitLab no corren.
Para en el primer paso que falla y enseña su salida; si todo va bien termina con «Listo para
integrar». `.gitlab-ci.yml` hace lo mismo si la organización ofrece runners (preguntarlo).

## Arranque del día 25

`scripts/arranque_evento.py` sin opciones es un ensayo: dice qué haría y no toca nada. Con
`--aplicar` comprueba que el árbol está limpio, en `main` y al día con `origin/main`, rellena el
registro de PREVIOUS_WORK.md (fecha y hora de corte, commit exacto y tag) y crea el tag anotado
sobre la base, no sobre el commit del registro. El commit lleva la identidad Git de quien lo
ejecuta, sin coautores. `--gitlab <url>` añade el remoto oficial y `--push` sube `main` y el tag a
todos los remotos. La línea de la declaración entregada la rellena una persona al entregarla.

## Todo en Databricks

`databricks/04_todo.py` encadena 02, 01 y 03 con los widgets de 01 más `referencias`. Escribe en
la salida `perfil.json`, el lote, `evaluacion_tr.json` (solo con referencias), `triaje.json` y
`cifras_evento.json`. La última celda imprime lo que se puede llevar al portátil: las cifras, el
resumen del lote y el de la evaluación, todos con alias `E01`… Las tablas con tags y los mapas de
calor se quedan en la plataforma.

## Sintéticos que se parecen al dataset

`synthetic/desde_perfil.py` lee el `perfil.json` de 02 y elige proveedores públicos en la
proporción de idioma, pulgadas y coma decimal del dataset; degradaciones según la parte de PDF
escaneados; y equipos sin hoja de datos o con paquetes de varias páginas según los recuentos. Los
proveedores reservados nunca entran, para que sigan midiendo la generalización. Escribe
`s-perfil/` con su `plan.json`, cuyo campo `huecos` lista lo que el generador aún no sabe imitar
(páginas giradas, formatos A1, más de dos revisiones, texto en curvas…): son las mejoras del
generador que tienen sentido pedir al agente. `--solo-plan` enseña el plan sin generar.

## Triaje de fallos

`bench/triaje.py` lee `resumen.json` y los `eventos.json` del lote y agrupa los fallos por categoría
de error y por la primera etapa que falla. Devuelve los cinco problemas más frecuentes con sus
casos (`E03/7` = equipo 3, revisión 7 del lote) y, para cada uno, la plantilla de FLUJO_IA.md
rellena salvo el patrón: ese lo escribe la persona tras mirar el documento en Databricks. No copia
textos de error, avisos ni detalles de eventos.

## Cifras del evento en el pitch y el guion

El pitch (`pitch/web`) lee `pitch/web/src/cifras-evento.js`. Con `null` muestra las cifras
sintéticas. `python -m bench.cifras aplicar cifras_evento.json [--minutos-revision N]` escribe ese
módulo y `generated/cifras_guion.md` con las frases de las marcas `[CIFRA TR]` de
[GUION_DEMO.md](GUION_DEMO.md) ya rellenas. Lo que no está medido sale como «sin medir» o con la
frase alternativa del guion, nunca como un número inventado. `python -m bench.cifras vaciar`
vuelve a las cifras sintéticas.

## Demo con un comando

`scripts/demo.py` instala lo que falte de la web, la compila con la URL de la API (Next la fija
al compilar y el script recompila si cambia), avisa si `data/cache` está vacía (en offline no se
crean cachés), arranca la API con `TRAZIA_OFFLINE=1` y la web, espera a que respondan y abre las
pestañas en el orden del guion. `--sin-api` es el plan B (datos de `web/public/demo`), `--pitch`
sirve además el pitch compilado en el puerto 4173 y `--construir` fuerza recompilar. Ctrl+C para
todo.

### Reiniciar entre ensayos

Con la demo parada y recién preparada (documentos subidos, cachés hechas),
`uv run python scripts/demo.py --guardar-inicial` copia el estado de la API (la base SQLite y
`store/`) a `generated/demo-inicial/`. Después, `--reiniciar` arranca como siempre pero antes:

- aparta el estado actual a `generated/demo-apartado/<fecha>/` (no se borra nada) y copia el
  guardado;
- abre primero `/reiniciar?destino=/documentos`, que vacía lo que la web guarda en el navegador:
  documentos añadidos, familias, borradores, cambios de Diseños y preferencias.

`cache/` y `private/` no se tocan nunca. Sin estado guardado solo se vacía el navegador.
`/reiniciar` también sirve a mano en cualquier portátil, con o sin API.

## Capturas del guion

`corepack pnpm capturas:guion` (proyecto `guion` de Playwright) deja en
`docs/capturas/producto/` las capturas `demo-01-documentos` a `demo-06-cambios` a 1920×1080 en
tema oscuro, en el estado que pide el guion: documentos recién añadidos, recorrido D en la
lectura, diámetro con su cota en el plano, estudio, Rayos X con la N2 y cambios con la N4. Cada
paso es «si se puede»: si la interfaz cambia, la captura sale igual y un aviso `[guion]` indica
qué revisar. El mapa de calor (`demo-07`) sale del notebook 03.

## Vídeo de respaldo

`scripts/video_respaldo.py` compila la web, recorre el guion con Playwright (proyecto `video`,
`web/tests/e2e/video-respaldo.spec.ts`) y graba la pantalla a 1920×1080 con el screencast de
Chrome. Luego lo codifica con ffmpeg en H.264 a 30 fps en
`generated/video-respaldo/TrazIA-3D-demo-respaldo.mp4`, que no se versiona. Dura unos dos minutos
y medio, sin voz. Unos rótulos dicen qué se ve y el cursor se mueve despacio hasta cada control.
Usa solo la web con los datos de `web/public/demo`. Si un paso falla, el vídeo sale igual y la
salida dice qué revisar. `--sin-compilar` reutiliza el build.

## Pitch en PowerPoint y PDF

`pitch/web/scripts/exportar_pptx.py` compila el pitch, captura cada escena ya animada a
1920×1080 y monta `pitch/TrazIA-3D.pptx` con una imagen por diapositiva, el guion de cada escena
en las notas del orador y `pitch/TrazIA-3D.pdf`. Se regenera después de `bench.cifras aplicar`
para que lleve las cifras del evento. Detalles en [pitch/web/README.md](../pitch/web/README.md).

## Entrega del viernes

`scripts/entrega.py` marca cada punto con ✓, ! (aviso) o ✗ (no entregar así):

- árbol limpio, `main` igual a `origin/main` y a `gitlab/main`;
- tag en local y en los remotos;
- PREVIOUS_WORK.md sin líneas del registro pendientes;
- guardián sobre lo versionado y sobre la historia;
- autores y committers desde el tag en `.github/autores.txt`, y ningún coautor ni firma;
- el pitch compila y tiene las cifras del evento;
- están las capturas del guion.

`--rapido` se salta la compilación del pitch.
