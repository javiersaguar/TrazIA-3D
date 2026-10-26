# Cómo trabajar en TrazIA-3D

Plan completo y reparto: [docs/ROADMAP.md](docs/ROADMAP.md). Aquí está lo mínimo para no romper nada.

## Autoría

Los únicos autores del repositorio son **Javier Saguar Antona, Iria Lozano Carrasco, Miguel Vera del
Castillo y Alejandro Cuevas Cid**.

- Nada de `Co-authored-by`, «Generated with…» ni firmas de herramientas en commits, PR, código o
  documentación. Los asistentes y agentes son herramientas: el autor es quien hace el commit.
- Configura tu identidad en este clon y añade tu correo a [.github/autores.txt](.github/autores.txt):

  ```bash
  git config user.name "Nombre Apellido Apellido"
  git config user.email "tu-correo@ejemplo.com"
  ```

- Activa el hook que rechaza coautores (una vez por clon):

  ```bash
  git config core.hooksPath .githooks
  ```

- El workflow **Autoría** falla si algún commit trae coautores o un correo fuera de la lista.
- Si se cuela un coautor, corrige el commit **antes** de subirlo (`git commit --amend`).

## Ramas y commits

- Una rama por tarea: `feat/<área>-<tema>`, `fix/…`, `docs/…`, `bench/…`. PR pequeño a `main`.
- `main` siempre demostrable: CI en verde para fusionar.
- Mensajes en español, en imperativo y con prefijo de área: `bench: añade F1 de cambios`.
- Un agente por worktree: `git worktree add ../TrazIA-3D-<tema> -b feat/<tema>`. Dos agentes nunca
  comparten directorio de trabajo.

## Propiedad de carpetas

Cada carpeta tiene un dueño (ROADMAP, sección 5.4). Para tocar una carpeta ajena se abre un PR y se
pide revisión a su dueño. El contrato de datos (`docs/DATA_CONTRACT.md` y el esquema JSON) solo cambia
con revisión de los dueños afectados.

## Datos

- El dataset de Técnicas Reunidas va en `data/private/` y **nunca** se sube.
- Todo lo que hay en el repositorio es sintético y se rotula como tal.
- No subir claves: usa `.env` (ignorado) y documenta las variables en `.env.example`.

## Comprobaciones antes de un PR

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
```

Si tocas `web/`: `pnpm typecheck`, `pnpm lint`, `pnpm build` y `pnpm test:e2e` dentro de `web/`.

## Licencia

MIT ([LICENSE](LICENSE)). El código previo al hackatón se declara en `PREVIOUS_WORK.md` al empezar el
evento (25/11/2026).
