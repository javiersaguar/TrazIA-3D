# Coordinación del backend: API y motor

Dos agentes trabajan a la vez en el backend. Este documento es el contrato entre ellos: quién es dueño
de qué y qué interfaz no se rompe. Plan general en [ROADMAP.md](ROADMAP.md).

| | **Agente API** (plataforma) | **Agente Motor** (ingeniería) |
| --- | --- | --- |
| Rama · worktree | `feat/backend-api` · `../TrazIA-3D-api` | `feat/motor` · `../TrazIA-3D-motor` |
| Roadmap | H (API, trabajos, persistencia, escala), E.3–E.5 (estado de revisión y aprobación persistidos), conexión de la web | B (extractores, OCR, citas, reconciliación, calibración), C (unidades, contrato 0.3), D (IFC, familias), F (cambios, BCF), G (bench) |
| Es dueño de | `src/trazia/api/**`, `src/trazia/store/**`, `tests/test_api*.py`, `docs/API.md`, `docker-compose*.yml`, `Dockerfile*`, `.env.example`, `.github/workflows/ci.yml`, `web/src/lib/api/**`, `web/src/lib/queries.ts`, `web/src/lib/mock/**`, `web/package.json` | `src/trazia/{pipeline,ingest,extraction,model,ifc,revisions,review,cli,app,viewer}.py`, `src/trazia/extractors/**`, `src/trazia/families/**`, `src/trazia/bcf.py`, `src/trazia/calibration*`, `synthetic/**`, `bench/**`, `tests/test_pipeline.py`, `tests/test_bench.py`, `tests/test_motor*.py`, `docs/DATA_CONTRACT.md`, `docs/BENCH.md`, `web/src/lib/types/revision.ts` (generado) |
| No toca | El motor: lo usa a través de `trazia.pipeline` y de los modelos de `trazia.model` | HTTP, base de datos, colas, la web (salvo regenerar los tipos del contrato) |

Archivos compartidos, con estas reglas:

- **`pyproject.toml`**: cada agente solo edita su grupo en `[project.optional-dependencies]`: `api`
  el Agente API y `ocr` el Agente Motor. Una dependencia nueva del núcleo (`dependencies`) se avisa en
  el informe antes de añadirla.
- **`uv.lock`**: nunca se resuelve un conflicto a mano. Se toma la versión de `main` y se ejecuta
  `uv lock`.
- **`.gitignore`**: solo se añaden líneas.
- **`tests/conftest.py`, `AGENTS.md`, `CONTRIBUTING.md`, `docs/ROADMAP.md`**: no se editan; las
  propuestas van en el informe.
- **Frontend 3D** (`web/src/features/viewer3d`, `plant`, `delta3d`, `workers`, `app/lab`): no se
  toca.

## Interfaz 1 · `trazia.pipeline` (la crea el Motor el primer día)

```python
# src/trazia/pipeline.py
from collections.abc import Callable
from dataclasses import dataclass

@dataclass(frozen=True)
class InputDocument:
    filename: str          # GAD_<TAG>_rev1.pdf, HDM_<TAG>_rev1.xlsx…
    data: bytes
    document_id: str       # GA-<TAG>, HDM-<TAG>

@dataclass(frozen=True)
class StageEvent:
    stage: str             # ingest | classify | extract_labels | extract_tables | extract_ocr |
                           # extract_vision | extract_hdm | reconcile | family | ifc | validate
    status: str            # "ok" | "omitido" | "error"
    file: str
    detail: str            # frase en español para la tabla de eventos de la web

@dataclass(frozen=True)
class PipelineResult:
    revision: "Revision | None"   # trazia.model.Revision, DRAFT
    candidates: list               # trazia.extraction.Candidate
    warnings: list[str]
    error: str | None              # motivo en español si no hay modelo

def process(
    documents: list[InputDocument],
    *,
    project_id: str,
    equipment_id: str,
    revision: str,
    extractor: str = "combinado",          # "etiquetas" | "tablas" | "combinado" | los que añada el Motor
    dataset: str = "synthetic",
    on_event: Callable[[StageEvent], None] | None = None,
) -> PipelineResult: ...
```

- Los identificadores de etapa son los de la web (`web/src/lib/mock/pipeline.ts`). Una etapa que
  no exista se emite como `omitido`.
- `process` no hace E/S de red ni de disco y no lanza excepciones por datos malos: devuelve `error`.
- El Motor puede añadir parámetros opcionales, pero nunca quitar ni renombrar.

## Interfaz 2 · contrato de datos

- La API sirve `Revision.model_dump(mode="json")` tal cual y su OpenAPI se genera desde los modelos
  Pydantic. Si el Motor cambia el contrato (0.3), la API no duplica esquemas.
- Al cambiar el contrato, el Motor:
  1. regenera `generated/revision.schema.json` (`uv run trazia schema`);
  2. regenera los tipos de la web (`cd web && pnpm gen:types`);
  3. actualiza `docs/DATA_CONTRACT.md`;
  4. avisa en su informe.
- Hay que mantener los **nombres de elementos del IFC** (`<TAG>`, `<TAG>/top_head`, `<TAG>/N1`…) y
  los **GUID estables**. El visor 3D depende de ellos (`web/src/lib/mock/fields.ts`,
  `web/src/features/viewer3d/semantic.ts`).

## Interfaz 3 · API para la web

- La web ya consume estas funciones de `web/src/lib/mock/api.ts`: `getRevision`,
  `getReviewFields`, `updateField` (con `Idempotency-Key`), `getChanges`, `getEquipment` y
  `getBench`.
- El Agente API las sirve con los endpoints de la sección H del roadmap y añade un cliente
  `web/src/lib/api/`.
- Si `NEXT_PUBLIC_API_URL` está definida, la web usa la API; si no, sigue con los mocks. La demo
  offline nunca se rompe.

## Fuera de alcance por ahora

- **Llamadas a modelos de lenguaje externos (B.3):** el proveedor depende de la plataforma IndesIA y
  de claves que aún no hay. El Motor puede definir la interfaz `VisionExtractor` con caché y modo
  offline, pero sin llamadas de red.

## Informes

Cada agente termina con `docs/agentes/INFORME_API.md` o `docs/agentes/INFORME_MOTOR.md`: qué está
hecho, cómo se prueba, qué ha cambiado en las interfaces y qué necesita del otro.
