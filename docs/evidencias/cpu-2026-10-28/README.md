# Evidencias CPU · 27 y 28 de octubre de 2026

Datos sintéticos v1: 40 equipos, semilla 2026, tres estilos y dos revisiones.
Código base `10f649d`; cambios locales de exportación y metadatos de impacto en
`chore/roadmap-cpu`, sin cambios del generador, las estrategias o las fórmulas del banco.

- [Informe de carga](prueba_carga.md): métricas, tiempos y límites de interpretación.
- [Banco v1](bench-v1.json), [B inicial](estudio-b.json), [diez variantes](estudio-variantes.json).
- [Ejecuciones](ejecuciones.json): comandos, timestamps UTC, duración y códigos de salida.
- [Entorno](entorno.json): versiones y huella del conjunto.
- [Integridad](integridad.json): condiciones, IFC, errores y suma del tiempo por variante.
  Sus arrays contienen, en orden: condiciones, IFC construidos, revisiones con error y segundos.

Se recuperaron 843 condiciones completas y se midieron las 357 restantes el 28/10.
La interrupción conserva su estado explícito: su duración original de pared no se inventa.
Las tres pasadas completas con `uv run pytest -q` terminaron con 225 pruebas superadas
cada una, sin fallos ni omisiones. Los tiempos del informe separan pared e informe pytest.
Un IFC construido no acredita acierto de todos sus campos; los errores no se descartan.
Esta evaluación v1 no cierra el estudio S-dev/S-reservado v2, ni mide hardware/GPU o datos de TR.

## Reproducción

Los scripts auxiliares usados se conservan como texto junto a estos datos para dejar constancia
de la adaptación v1 del arnés v2 y la reanudación. Se ejecutan después de copiarlos a su ubicación
original, desde la raíz del repositorio. No son ejecutores de producción de la API.

```powershell
uv sync --frozen --extra dev --extra api --extra ocr
uv run python -m synthetic --casos 40 --semilla 2026
uv run python -m bench --detalle
Copy-Item docs/evidencias/cpu-2026-10-28/estudio_v1.py.txt generated/bench/estudio_v1.py
$env:TRAZIA_RAG_LIBRARY=(Join-Path (Get-Location) 'generated/rag/biblioteca.json')
uv run python generated/bench/estudio_v1.py b
uv run python generated/bench/estudio_v1.py biblioteca
uv run python generated/bench/estudio_v1.py variantes
uv run pytest -q
uv run pytest -q
uv run pytest -q
```

La selección predeterminada excluye visión local cara, proveedores sin credenciales y detector
no implementado; se mide íntegra sobre los 40 equipos. El script reutiliza condiciones ya
completas si existe su JSONL local. Para una nueva medición sin checkpoints se usa un worktree
limpio con los extras instalados, siguiendo AGENTS.md. Las horas internas de PDF/Excel pueden
cambiar sus bytes al regenerar; semillas, valores verdaderos y comandos permiten contrastar el caso.
Los originales sintéticos se regeneran con el comando indicado. Los logs, cachés y JSONL por
condición permanecen locales bajo generated/bench; aquí se versionan las métricas agregadas.
