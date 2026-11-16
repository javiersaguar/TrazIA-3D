# Plataforma IndesIA y Kit del Participante · 16/11/2026

Resumen operativo del correo «IndesIAhack 2026 | Próximos pasos» (16/11), del Kit del Participante
(9 páginas), de las preguntas frecuentes y de las bases legales de indesiahack.org. Los enlaces y el
código de la reunión de Teams están en el correo; no se copian aquí.

## Lo que cambia para TrazIA-3D

Las bases dicen: «Los participantes que elijan un reto industrial deben usar la plataforma
tecnológica de IndesIA para desarrollar su proyecto». Hasta ahora el plan suponía
«sin entorno IndesIA; portátiles propios» (tarea 0.2 de `PREPARACION_25NOV.md`). Ya no vale:

| Pieza | Plataforma IndesIA | Hoy en TrazIA-3D | Qué hay que preparar |
| --- | --- | --- | --- |
| Acceso | Invitación de Microsoft Azure al correo de inscripción el día 25, tras formar equipos. Sin contraseña nueva; segundo paso con Microsoft Authenticator | — | Cada miembro instala Authenticator y comprueba que entra en su correo de inscripción |
| Programación | Azure Databricks: notebooks en un espacio de trabajo privado por equipo, con libertad para instalar librerías | Paquete Python con `uv`, CLI y API locales | Hecho: `databricks/00_comprobar_entorno` y `01_procesar_lote` (ver abajo) |
| Datos del reto | Volúmenes de Unity Catalog: `/Volumes/<catálogo>/<esquema>/<volumen>/…`, lectura con Python normal | Rutas locales y `generated/` | Hecho: widgets `entrada`/`salida`/`trabajo` y lote por carpeta (`trazia lote`) |
| Código | GitLab de la organización. Subida a las **10:00 del viernes 27** | GitHub `javiersaguar/TrazIA-3D` | Remoto GitLab el día 25; carpeta Git de Databricks enlazada a ese repo |
| Modelos de IA | «Servicios complementarios orientados a la IA generativa». Las claves se publican en el canal general de Teams | Ollama local en la RTX 5070 (visión) y proveedores externos solo con sintéticos | Probar `OpenAICompatibleProvider` con el servicio de la plataforma; confirmar permisos sobre los datos de TR |
| Coordinación | Teams: canal general (comunicaciones, claves, grabación, guía) y canal privado por equipo (entrega de la presentación el viernes) | Chat propio | Usar el canal privado del equipo para la presentación final |

Límites de las carpetas Git de Databricks que nos afectan: rama de trabajo de 1 GB como máximo,
menos de 20.000 archivos recomendados y archivos de más de 10 MB no visibles en la interfaz.
El repo actual tiene 1.283 archivos versionados y unos 91 MB en `HEAD` (47 MB son `promo/`): cabe.

Pendiente de confirmar en la formación o con los mentores, sin suponerlo antes:
- Si hay GPU en los clústeres y qué Databricks Runtime (los volúmenes piden 13.3 LTS o posterior;
  `pyproject.toml` admite Python 3.11–3.13).
- Si el frontend Next.js y la API pueden servirse desde la plataforma (por ejemplo, Databricks Apps)
  o si la demo visual puede ir en el portátil leyendo resultados generados en la plataforma.
- Qué servicios de IA generativa hay (modelo, visión, límites) y si los planos de TR pueden enviarse.
- Si el repositorio de GitLab lo crea la organización o el equipo, y si admite subir el historial previo.

## Notebooks de Databricks (preparados el 16/11)

En `databricks/` hay dos notebooks en formato fuente de Databricks (`.py` con `# COMMAND`)
y las dependencias fijadas. El día 25 solo cambia la ruta de entrada.

| Archivo | Qué hace |
| --- | --- |
| `databricks/requirements.txt` | Versiones exactas de `uv.lock` para el motor (extras `geo` y `ocr`, y `pytest`, que la validación EXPRESS usa al ejecutar). No incluye Streamlit, pandas ni pyarrow, para no pisar los del runtime |
| `databricks/00_comprobar_entorno.py` | `%pip install`, versiones, importaciones, carga del OCR y prueba con `examples/documents` (B y D). Si acaba en verde, el entorno sirve |
| `databricks/01_procesar_lote.py` | Widgets `entrada`, `salida`, `estrategia`, `dataset`, `tags`, `procesos`, `proveedores` y `trabajo`. Procesa la carpeta y muestra el resumen |
| `src/trazia/lote.py` y `trazia lote` | El mismo lote sin notebook: `uv run trazia lote <carpeta> -o <salida> --estrategia d_hibrido` |

Cómo agrupa el lote: por el nombre de cada archivo (`GAD_<TAG>_rev<R>.pdf`,
`HDM_<TAG>_rev<R>.xlsx`, `VESOR_<TAG>.pdf`, imágenes incluidas), recorriendo subcarpetas. Un
documento sin `_rev` acompaña a todas las revisiones de su tag. Las revisiones van en orden
natural (`2 < 10`, `A < B`) y cada una recibe la anterior como `previous`. Salida por equipo:

```
<salida>/<TAG>/rev<R>/revision.json     contrato 0.3 con fuentes, confianza y RunInfo
<salida>/<TAG>/rev<R>/modelo.ifc        IFC4 DRAFT, validado como en la API
<salida>/<TAG>/rev<R>/eventos.json      etapas, avisos y error
<salida>/<TAG>/cambios_rev<A>_rev<B>.json
<salida>/resumen.csv · resumen.json     una fila por equipo y revisión
```

Un equipo que falla queda en el resumen con su error y no detiene el lote. Las cachés (OCR,
detector, visión, RAG visual) van a `trabajo` (por defecto `/tmp/trazia/trabajo`, disco local
y rápido) salvo que ya estén fijadas con variables `TRAZIA_*`. La salida nunca puede estar
dentro de la carpeta Git: ni datos de TR ni IFC del reto entran en el repositorio.

Ensayo hecho el 16/11 en WSL con un venv limpio de Python 3.12, solo `pip` y una copia del repo
sin `generated/` (como una carpeta Git recién clonada), con un `/Volumes/...` simulado:

| Paso | Resultado |
| --- | --- |
| `pip install -r databricks/requirements.txt` | 24 s. Los modelos ONNX de RapidOCR vienen en el wheel: no se descarga nada al ejecutar |
| `00_comprobar_entorno` | 16 paquetes en la versión fijada; V-101 A y B correctos con B (4 s) y D (6 s), 8 cambios A→B |
| `01_procesar_lote`, D, un equipo | 2 de 2 revisiones en 7 s; no se escribe nada dentro del repo |
| `01_procesar_lote`, B, dos equipos, `procesos=2` | 4 de 4 revisiones en 5 s |

### El día 25, en la plataforma

1. Crear la carpeta Git del equipo (Workspace → Create → Git folder) apuntando al repo de
   GitLab que nos den (o a GitHub mientras tanto).
2. Abrir `databricks/00_comprobar_entorno` y ejecutarlo entero. Anotar el runtime y la versión
   de Python que muestra.
3. Abrir `databricks/01_procesar_lote`, poner en `entrada` la ruta del volumen con los datos del
   reto, en `salida` una carpeta de un volumen nuestro, `dataset = real` y ejecutar. Empezar con
   `tags` = un equipo para medir el tiempo y después el lote completo.
4. Con datos de TR, `proveedores` vacío salvo que los mentores confirmen que el servicio de IA de
   la plataforma puede recibirlos.

### Ensayo antes del 25 en Databricks Free Edition

Free Edition es gratuita y basta con una cuenta propia (la crea cada persona; no la crea el
asistente). Sirve para ensayar con los ejemplos sintéticos, nunca con datos de TR:

1. Iniciar sesión en Free Edition y crear la carpeta Git con la URL del repo de GitHub. Si el
   repo es privado, enlazar antes la cuenta de GitHub en Settings → Linked accounts.
2. Ejecutar `00_comprobar_entorno` (serverless). Debe acabar con «Entorno listo».
3. Opcional: Catalog → `workspace` → `default` → Create volume (`datos`), subir los cuatro
   archivos de `examples/documents` y lanzar `01_procesar_lote` con
   `entrada = /Volumes/workspace/default/datos`, `salida = /Volumes/workspace/default/datos/salida`
   y `dataset = synthetic`.

Diferencias de Free Edition que no hay que extrapolar a la plataforma del reto: solo cómputo
serverless, sin GPU, salida a internet restringida y cuotas de uso. Si `%pip` no llega a PyPI,
anotarlo y preguntarlo en la formación, porque la plataforma del reto puede no tener esa
limitación.

Riesgo conocido: `requirements.txt` fija `numpy` 2.x. En un runtime con pandas antiguo (1.x),
`import pandas` puede fallar en ese notebook después de la instalación. Los notebooks no usan
pandas (el resumen se muestra con HTML), así que el lote no se ve afectado. Si se necesita pandas,
elegir un entorno serverless o runtime más reciente.

Si cambia `uv.lock`, regenerar `databricks/requirements.txt` desde Linux o WSL. Primero se
exportan las versiones de `uv.lock` con
`uv export --frozen --extra geo --extra ocr --extra dev --no-hashes --no-emit-project`. Después,
`uv pip compile --universal` sobre la lista de paquetes de `00_comprobar_entorno`, con esas
versiones como restricciones.

## Código previo

Preguntas frecuentes: se puede usar código previo «siempre que lo declares explícitamente al
comienzo del hackatón y quede claro qué parte del proyecto existía antes del evento». Los derechos
sobre ese código siguen siendo nuestros (DPI previos). Lo creado durante el evento se licencia como
MIT, salvo que las bases del reto digan otra cosa.

Por eso, el miércoles 25 al empezar: cerrar `PREVIOUS_WORK.md` con fecha, hora y commit, crear el tag
`pre-hackathon-baseline` y entregar la declaración a la organización. Los commits del evento van
después del tag.

## Calendario

| Día | Hora | Qué |
| --- | --- | --- |
| Vie 20 nov | 9:00–9:45 | Formación online de la plataforma (opción A, Teams) |
| Lun 23 nov | 16:00–16:45 | Formación online de la plataforma (opción B, Teams) |
| Lun 23 nov | 23:59 | Cierre de inscripciones |
| Mié 25 nov | 11:00 | Acreditaciones y confirmación de equipos (vestíbulo, edificio A). La plaza se confirma solo en persona, por orden de llegada: llegar pronto |
| Mié 25 nov | 15:00 | Formación presencial de la plataforma (salón de actos, edificio A) |
| Mié 25 nov | 16:00 / 17:00 / 17:30 | Bienvenida · reunión con mentores · inicio del trabajo (hasta 21:00) |
| Jue 26 nov | 8:00–21:00 | Trabajo; sesión inspiradora a las 16:00 |
| Vie 27 nov | **10:00** | Subida del código y la presentación al repositorio |
| Vie 27 nov | 11:00 | Exposiciones por reto ante el jurado |
| Vie 27 nov | 13:00 / 14:00 | Gala de clausura (Aula Magna, edificio C) y premios |

Comprometerse con la inscripción incluye formarse en la plataforma antes del evento. En cada equipo
debe haber al menos una persona que domine la creación de modelos en ella. Recomendación: que los
cuatro vayan a una de las dos sesiones online.

## Lista por persona antes del 25

- [ ] Microsoft Authenticator instalado en el móvil.
- [ ] Acceso al correo con el que se hizo la inscripción (ahí llega la invitación de Azure).
- [ ] Sesión de formación elegida (20 o 23) y añadida al calendario.
- [ ] Recursos del correo leídos (10–15 min cada uno): primeros pasos en Azure Databricks,
      notebooks de Databricks, volúmenes de Unity Catalog, tutorial de Git de GitLab y Teams.
- [ ] Portátil con navegador actualizado y cargador; móvil. Si es posible, memoria USB y regleta.

## Criterios de evaluación (bases legales)

El jurado de cada reto (Técnicas Reunidas, con apoyo de Multiplica) aplica criterios generales y
los específicos del reto, con una rúbrica de ponderación:

- **No técnicos:** aproximación y viabilidad, creatividad, uso de la IA (precisión, fiabilidad,
  mejora futura), presentación y demostración, potencial para la empresa, ética y uso responsable,
  experiencia de usuario.
- **Técnicos:** calidad del software, ciclo de vida del dato y preparación del modelo,
  reproducibilidad y escalabilidad.

Premios: 1.000 € por reto; el ganador de cada reto opta a los 2.000 € del premio IndesIAhack.
Al terminar el evento hay que dejar de usar la plataforma y los datos del reto.
