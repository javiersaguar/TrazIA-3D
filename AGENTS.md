# TrazIA-3D

Producto del reto GA2MODEL de IndesIAhack 2026. El código Python vive en `src/trazia`.

- Instalar: `uv sync --frozen --extra dev`.
- Verificar: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest -q`.
- Arrancar: `uv run trazia serve` (aplicación local en 127.0.0.1).
- Datos privados en `data/private/`; nunca subir originales reales ni claves al repositorio.
- Los ejemplos públicos son sintéticos. Conservar su etiquetado explícito.
- El baseline de etiquetas no es un extractor IA. No presentar resultados sintéticos como
  precisión medida sobre planos del organizador.
- Mantener valor, unidad, fuente y confianza por campo; conservar GUID por ID estable.
- La salida automática es DRAFT. Para exportar aprobado se requieren revisión humana,
  verificación de originales y aprobación vinculada a la huella de los datos.
- Una modificación de los datos invalida la aprobación anterior.
- El visor debe leer la geometría del IFC, no dibujar una segunda versión aproximada.

## Autoría

- Commits sin `Co-authored-by` ni firmas de herramientas o asistentes en mensajes, PR, código o docs.
  Los únicos autores son los cuatro miembros del equipo (ver `CONTRIBUTING.md`).
- Trabajar solo en las carpetas asignadas y en un worktree propio (`docs/ROADMAP.md`, sección 5.4).
