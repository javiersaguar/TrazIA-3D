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
| Programación | Azure Databricks: notebooks en un espacio de trabajo privado por equipo, con libertad para instalar librerías | Paquete Python con `uv`, CLI y API locales | Notebook de entrada que instale el paquete y llame a `trazia.pipeline.process` |
| Datos del reto | Volúmenes de Unity Catalog: `/Volumes/<catálogo>/<esquema>/<volumen>/…`, lectura con Python normal | Rutas locales y `generated/` | Que las rutas de entrada, salida y cachés sean configurables (variables `TRAZIA_*`) y apunten a un volumen o a `$TEMPDIR` |
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
