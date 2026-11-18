# Flujo de trabajo con asistentes de IA durante el evento

Hasta ahora los agentes de código (Claude Code, Codex…) trabajaban en el portátil con todo a mano:
repo, datos sintéticos, GPU y pruebas. En el evento el código se entrega en GitLab y los datos de
Técnicas Reunidas viven solo en la plataforma IndesIA (Azure Databricks). Programar dentro de
Databricks con un agente es incómodo, y además un agente externo no debe ver datos del reto.

La solución es separar los dos sitios y usar GitLab como puente. El agente escribe y prueba el
código en el portátil con sintéticos; Databricks lo ejecuta sobre los datos reales; de vuelta al
agente solo viajan agregados y descripciones escritas por una persona.

Complementa a [PLATAFORMA_INDESIA.md](PLATAFORMA_INDESIA.md) (acceso, notebooks y calendario) y a
[CONTRIBUTING.md](../CONTRIBUTING.md) (autoría, ramas y comprobaciones).

## Qué pasa en cada sitio

| Sitio | Qué se hace allí | Qué no se hace |
| --- | --- | --- |
| Portátil | Agente de código en un worktree propio, `ruff` y `pytest`, lote con `examples/documents` y conjuntos de `synthetic/`, web y demo | Abrir, copiar o describir con valores un documento de TR |
| Databricks | Carpeta Git personal, `00_comprobar_entorno`, `01_procesar_lote` con los volúmenes del reto, revisar a mano los casos que fallan | Desarrollar con el agente externo; versionar salidas |
| GitLab | Ramas de cada uno, integración en `main`, entrega del viernes a las 10:00 | Datos, salidas del lote, claves |
| Teams | Avisos de integración en el canal privado del equipo, claves de los servicios de IA (canal general) | Pegar planos o resultados del lote |

## La regla de los datos

1. Ningún asistente externo ve datos del reto: ni PDF, XLSX o imágenes, ni capturas o recortes, ni
   `revision.json`, `modelo.ifc` o `eventos.json` del lote real, ni valores de cotas o boquillas.
2. No se bajan datos ni salidas reales al portátil: ni con la CLI de Databricks, ni con Databricks
   Connect, ni con la extensión de VS Code, salvo autorización escrita de la organización.
3. Lo único que cruza hacia el agente es: la celda «Resumen para el asistente» de
   `01_procesar_lote` (`trazia.lote.resumen_compartible`) y de `03_evaluar_contra_tr`
   (`bench.evaluar.resumen_compartible`), el perfil de `02_perfil_dataset` y lo que una persona
   escriba con sus palabras, sin valores.
4. El asistente integrado de Databricks está dentro de la plataforma, pero hasta que los
   mentores confirmen si puede tratar datos de TR se usa solo con código y sintéticos.

`resumen_compartible` no incluye nombres de archivo, rutas, tags ni textos de error. Renombra los
equipos a `E01`, `E02`… y reduce cada error a su categoría (`ifc_invalido`, `ValueError`,
`pipeline`…). Aun así, hay que leerlo antes de pegarlo.

| Se puede pegar al agente | Hay que reescribirlo antes | No se pega nunca |
| --- | --- | --- |
| Resumen para el asistente (01 y 03), perfil del dataset (02), versiones de paquetes, tiempos, trazas de error de nuestro código sin valores | Mensajes de error y avisos (pueden citar tags o cotas): se describen sin datos | Documentos, capturas de planos, JSON o IFC del lote real, nombres de archivo del dataset |

## El ciclo de trabajo

1. **Portátil.** Rama y worktree propios (`git worktree add ../TrazIA-3D-<tema> -b feat/<tema>`) y
   el agente trabajando ahí, como hasta ahora.
2. **Probar con sintéticos.** `ruff`, `pytest` y el mismo lote que correrá en la plataforma:
   `uv run trazia lote examples/documents -o /tmp/trazia/salida --dataset synthetic`.
3. **Subir la rama a GitLab** (`git push gitlab feat/<tema>`).
4. **Databricks.** En tu carpeta Git: cambiar a la rama y hacer *Pull*.
5. **Ejecutar `01_procesar_lote`** primero con `tags` = uno o dos equipos (minutos) y, si va
   bien, con el lote completo.
6. **Revisar en la plataforma.** Una persona abre allí los casos que fallan y mira qué tienen
   de especial.
7. **Volver al agente** con el resumen para el asistente y una descripción del patrón, sin valores.
8. **Reproducir con sintéticos**, arreglar y volver al paso 2.

En el portátil el ciclo dura segundos; el viaje por GitLab y Databricks, unos minutos. Por eso
se agrupan los cambios antes de subirlos y se prueba en local todo lo que se pueda.

## Reproducir un fallo real sin enseñar el plano

El agente no puede abrir el documento que falla, así que se le da el patrón, no el dato:

- «La lista de boquillas sigue en una segunda hoja del XLSX.»
- «Plano escaneado y girado 90°; el cajetín queda a la izquierda.»
- «Las cotas vienen en pulgadas y con fracciones.»
- «El tag lleva barra: `V/101`.»

Con eso el agente crea un caso sintético que reproduce el patrón: con el generador
(`uv run python -m synthetic --conjunto … --degradaciones …`) o con un caso mínimo en `tests/`.
Nunca copia un fragmento del original. Después escribe la prueba que falla, la arregla, y la
persona vuelve a lanzar el equipo real en Databricks para confirmar.

`uv run python -m bench.triaje <salida>` (o la celda de triaje de `04_todo`) agrupa los fallos
por categoría y etapa y deja esta plantilla rellena salvo el patrón.

Plantilla para pedírselo:

```text
En la plataforma, <n> de <total> revisiones fallan con la categoría <categoría>.
Resumen para el asistente: <pegar>.
Patrón observado (sin datos del plano): <descripción>.
Reprodúcelo con un caso sintético, añade una prueba que falle y arréglalo sin romper el resto.
```

## Git entre portátil, GitLab y Databricks

- **GitLab es el remoto oficial desde el día 25:** `git remote add gitlab <url>` en cada clon.
  Si se puede seguir usando GitHub como espejo es una de las preguntas abiertas de
  [PLATAFORMA_INDESIA.md](PLATAFORMA_INDESIA.md).
- **Una carpeta Git por persona** en Databricks, dentro de su usuario. Nadie comparte la misma:
  dos personas haciendo *Pull* y *Commit* en una sola carpeta acaban en conflicto.
- **El código se edita en el portátil.** En Databricks solo se cambian los widgets. Si hace falta
  un arreglo urgente allí, se hace commit y push desde la carpeta Git en ese momento y `git pull`
  en el portátil antes de que el agente siga.
- **Sin salidas en el repo.** Los notebooks del repo están en formato fuente (`.py`), que no
  guarda salidas. No se versionan notebooks `.ipynb` con resultados; para explorar, copias
  personales fuera de la carpeta Git.
- **Autoría.** Los commits hechos desde Databricks llevan la identidad de la cuenta de GitLab:
  hay que usar el mismo nombre y correo que en `.github/autores.txt` (o añadir ese correo). El
  hook de `.githooks` no corre allí, así que nadie añade coautores a mano.
- **Comprobaciones.** Los workflows de GitHub Actions no se ejecutan en GitLab. Antes de integrar
  en `main` se pasa en local `uv run python scripts/comprobar.py` (guardián de datos, ruff,
  pruebas y lote sintético). El `.gitlab-ci.yml` hace lo mismo si la organización ofrece
  runners: preguntarlo. Detalle en [AUTOMATIZACION.md](AUTOMATIZACION.md).
- **Integración.** Una persona integra cada vez y lo avisa en el canal privado del equipo:
  `git pull`, comprobaciones, `merge --no-ff` y push. Recomendación: congelar `main` el viernes a
  las 9:00 para tener margen hasta la entrega de las 10:00.

## Reparto recomendado

Para que el viaje a Databricks no frene a todos, una persona por turno hace de **operadora de la
plataforma**: mantiene su carpeta Git al día, lanza los lotes, revisa los fallos en los planos
reales y pasa al resto el resumen y el patrón de cada fallo. Los otros tres programan en local
con su agente y con sintéticos. El turno rota para que los cuatro dominen la plataforma, como
piden las bases.

## IA dentro del producto: servicios de la plataforma

Esto es otra cosa: la visión que usa el pipeline, no el asistente que programa.

- El widget `proveedores` de `01_procesar_lote` pasa los proveedores al pipeline. Vacío significa
  que no hay llamadas externas.
- Con `dataset = real` cualquier proveedor externo se bloquea salvo con
  `TRAZIA_EXTERNAL_PROVIDERS=allow` y `TRAZIA_EXTERNAL_AUTH` citando la autorización escrita
  (`src/trazia/vision/policy.py`).
- Cada envío queda en `registro_envios.jsonl` dentro de `trabajo`. Con datos reales, `trabajo`
  debe apuntar a un volumen para conservar ese registro.
- Hoy no hay adaptador para el servicio de la plataforma: las familias de
  `OpenAICompatibleProvider` tienen las URL fijas (Groq, OpenRouter, NVIDIA y Cloudflare). Cuando
  sepamos qué servicio hay, se añade una familia con su URL y la clave por variable de entorno.
- Las claves de Teams se guardan en un *secret scope* de Databricks o en variables de la sesión.
  Nunca en el repo ni en el chat con el agente.

## Chuleta

En el portátil:

```bash
git worktree add ../TrazIA-3D-<tema> -b feat/<tema>
uv run ruff check . && uv run ruff format --check . && uv run pytest -q
uv run trazia lote examples/documents -o /tmp/trazia/salida --dataset synthetic
git push gitlab feat/<tema>
```

En Databricks: carpeta Git → rama `feat/<tema>` → *Pull* → `databricks/01_procesar_lote` →
widgets → *Run all* → celda «Resumen para el asistente».

## Antes del 25

Ensayar el ciclo entero en Databricks Free Edition con GitHub en lugar de GitLab:

1. Subir una rama.
2. Hacer *Pull* en la carpeta Git.
3. Lanzar `01_procesar_lote` con `examples/documents`.
4. Copiar el resumen y medir cuánto tarda la vuelta completa.

Ese tiempo dice cada cuánto conviene subir cambios durante el evento.
