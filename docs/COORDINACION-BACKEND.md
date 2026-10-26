# Coordinación del backend: agentes Lectura y Plataforma

Dos agentes trabajan a la vez en el backend. Este documento es el contrato entre ellos: quién es dueño
de qué, qué interfaces no se rompen y cómo es el contrato de datos 0.3. Por qué se decidió así:
[DECISIONES.md](DECISIONES.md) (DEC-33). Plan general en [ROADMAP.md](ROADMAP.md).

## Reparto

| | **Agente Lectura** | **Agente Plataforma** |
| --- | --- | --- |
| Rama · worktree | `feat/lectura` · `../TrazIA-3D-lectura` | `feat/plataforma` · `../TrazIA-3D-plataforma` |
| Roadmap | B (cuatro estrategias), G (generador v2, bench, estudio), tareas 1.8–1.11, 2.1–2.6, 2.11, 3.2–3.4 | C.7 (contrato 0.3), D (familias, IFC), E (estado y aprobación persistidos), F (cambios, BCF), H (API, cola, escala), I.4.8–9 (pantallas Estudio y Copiloto), tareas 1.1, 1.2, 1.6, 2.7, 2.8, 3.1, 3.5–3.8 |
| Es dueño de | `src/trazia/{pipeline,ingest,extraction}.py` · `src/trazia/{strategies,extractors,vision,ocr,geometry2d,rag,reconcile,calibration}/` · `training/` · `synthetic/` · `bench/` · `tests/test_bench.py`, `tests/test_lectura_*.py` · `docs/BENCH.md` · sección de resultados de `docs/ESTUDIO.md` | `src/trazia/{model,ifc,revisions,review,cli,app,viewer,bcf}.py` · `src/trazia/families/` · `src/trazia/{api,store,queue,copilot}/` · `tests/test_pipeline.py`, `tests/test_app.py`, `tests/test_api*.py`, `tests/test_plataforma_*.py` · `docs/API.md`, `docs/DATA_CONTRACT.md` · `docker-compose*.yml`, `Dockerfile*`, `.env.example` · `.github/workflows/ci.yml` · `web/src/lib/**`, `web/src/features/{study,copilot}/**`, `web/src/app/(app)/estudio/**`, `web/src/components/shell/**`, `web/package.json` |
| No toca | `model.py`, `ifc.py`, API ni web | Estrategias, proveedores, OCR, generador ni bench |

Nadie toca el 3D de la web (`web/src/features/{viewer3d,plant,delta3d}`, `web/src/workers`,
`web/src/app/lab`), salvo petición expresa.

### Archivos compartidos

- **`pyproject.toml`:** cada agente solo edita sus grupos de `[project.optional-dependencies]`.
  - Lectura: `vision`, `ocr`, `rag`, `train`.
  - Plataforma: `api`, `geo`.
  - Dependencias del núcleo ya pactadas: `pint`, `scipy` y `scikit-learn`; las añade Lectura en su
    primer commit. Cualquier otra se avisa antes en el informe.
- **`uv.lock`:** nunca se resuelve un conflicto a mano. Se toma la versión de `main` y se ejecuta
  `uv lock`.
- **`.gitignore` y `THIRD_PARTY.md`:** solo se añaden líneas.
- **`tests/conftest.py`, `AGENTS.md`, `CONTRIBUTING.md`, `docs/ROADMAP.md`, `docs/DECISIONES.md`:**
  no se editan; las propuestas van en el informe.

### Integración

- Cada agente hace `git merge main` en su rama al empezar el día.
- Javier fusiona en `main` cada tarea cerrada con CI verde.
- Ninguno hace push ni PR por su cuenta.

---

## Contrato de datos 0.3 (DEC-13)

Lo implementa **Plataforma en su primer commit**, exactamente así. Lectura lo rellena. Se pueden
añadir campos **opcionales**; nunca se quitan ni se renombran.

```python
FieldState = Literal["candidate", "conflict", "abstained", "accepted", "corrected", "assumed"]
Channel = Literal["texto", "tabla", "cota", "cajetin", "hoja_datos", "vesor", "ocr",
                  "detector", "vision", "geometria", "rag", "memoria_revision", "humano"]

class Source(Model):                     # 0.2 + campos opcionales nuevos
    document_id: Identifier
    page: int | None; sheet: str | None; cell: str | None
    locator: str
    bbox: tuple[float, float, float, float] | None     # normalizada, origen arriba a la izquierda
    confidence: float                    # CALIBRADA (0–1)
    reviewed: bool = False               # se mantiene por compatibilidad = state in (accepted, corrected)
    confidence_raw: float | None = None
    channel: Channel | None = None
    strategy: str | None = None          # a_vision | b_reglas | c_rag | d_hibrido
    model: str | None = None             # p. ej. "qwen3-vl:4b@ollama", "florence2-trazia@local"
    prompt_sha256: str | None = None
    grounded: bool | None = None         # cita comprobada con OCR del recorte
    text_original: str | None = None     # texto literal leído
    unit_original: str | None = None     # unidad tal como aparece

class Interval(Model):
    low: float; high: float
    level: float                         # p. ej. 0.9
    method: Literal["conformal"] = "conformal"

class Alternative(Model):
    value: float | str; unit: str; source: Source

# Mixin para Tag, Dimension, Elevation, Angle y Attribute:
    state: FieldState = "candidate"
    interval: Interval | None = None
    alternatives: list[Alternative] = []
    explanation: str | None = None       # en español: por qué conflict / abstained / assumed

class Vector3(Model):                    # x, y, z en mm, cada componente con su Source
    x: Dimension; y: Dimension; z: Dimension

class Envelope(Model):                   # nivel de detalle 1
    origin: Vector3; size: Vector3

class Equipment(Model):
    id; tag
    kind: Literal["vertical_vessel", "horizontal_vessel", "column", "tank",
                  "pump", "compressor", "generic"] = "vertical_vessel"
    lod: Literal[1, 2, 3] = 2
    support: Literal["skirt", "legs", "saddles", "lugs", "baseplate", "none"] | None = None
    # Campos de la familia vertical (0.2): obligatorios solo si kind == "vertical_vessel" y lod >= 2
    diameter | height | head_depth | skirt_height | skirt_thickness
    # Familias nuevas: campos opcionales que define Plataforma en families/
    envelope: Envelope | None = None     # obligatorio si lod == 1
    attributes: dict[Identifier, Attribute]
    nozzles: list[Nozzle]                # mínimo 3 solo en vertical_vessel con lod >= 2

class Nozzle(Model):                     # 0.2 + opcionales
    id; diameter; projection; elevation; azimuth
    service: Attribute | None = None; rating: Attribute | None = None
    nozzle_type: Literal["radial", "tangential", "top", "bottom", "inclined"] | None = None

class RunInfo(Model):
    strategy: str; providers: list[str]
    seconds: float; gpu_seconds: float | None
    tokens_in: int | None; tokens_out: int | None; cost_eur: float | None
    external_calls: int                  # envíos a proveedores externos (DEC-31)

class Revision(Model):
    schema_version: Literal["0.3"] = "0.3"
    ...                                  # como en 0.2
    run: RunInfo | None = None
```

Reglas que no cambian:
- Nombres de elementos del IFC (`<TAG>`, `<TAG>/top_head`, `<TAG>/N1`…) y GUID estables. El visor 3D
  depende de ellos.
- Una modificación de datos invalida la aprobación.
- La salida automática es DRAFT.

Migración:
- Plataforma escribe el migrador 0.2 → 0.3.
- Regenera `generated/revision.schema.json` y los tipos de la web (`cd web && pnpm gen:types`).
- Comprueba que la web pasa typecheck, build y e2e.

---

## Interfaz 1 · `trazia.pipeline` (Lectura)

```python
@dataclass(frozen=True)
class InputDocument:
    filename: str          # GAD_<TAG>_rev1.pdf, HDM_<TAG>_rev1.xlsx, VESOR_<TAG>.pdf…
    data: bytes
    document_id: str       # GA-<TAG>, HDM-<TAG>, VESOR-<TAG>

@dataclass(frozen=True)
class StageEvent:
    stage: str             # ingest | classify | extract_labels | extract_tables | extract_ocr |
                           # extract_detector | extract_vision | extract_hdm | geometry2d | rag |
                           # memory | reconcile | calibrate | family | ifc | validate
    status: str            # "ok" | "omitido" | "error"
    file: str
    detail: str            # frase en español para la tabla de eventos de la web

@dataclass(frozen=True)
class PipelineResult:
    revision: Revision | None      # DRAFT, contrato 0.3
    candidates: list[Candidate]
    warnings: list[str]
    error: str | None              # motivo en español si no hay modelo
    run: RunInfo

def process(
    documents: list[InputDocument], *,
    project_id: str, equipment_id: str, revision: str,
    strategy: str = "d_hibrido",            # a_vision | b_reglas | c_rag | d_hibrido | variantes del estudio
    previous: Revision | None = None,       # memoria de revisión (rev1 aprobada)
    providers: list[str] | None = None,     # p. ej. ["ollama:qwen3-vl:4b"]
    dataset: Literal["synthetic", "real"] = "synthetic",
    on_event: Callable[[StageEvent], None] | None = None,
) -> PipelineResult: ...
```

- `process` no hace E/S de red salvo a los proveedores de visión permitidos.
- No escribe en disco fuera de la caché de `generated/cache/`.
- No lanza excepciones por datos malos: devuelve `error`.
- Plataforma añade los ids de etapa nuevos al grafo del Pipeline de la web.

## Interfaz 2 · proveedores de visión (Lectura)

```python
class VisionProvider(Protocol):
    name: str                  # "ollama:qwen3-vl:4b", "gemini:…", "mistral-ocr:…", "plataforma:…"
    external: bool             # True si los datos salen del equipo
    def read(self, image_png: bytes, task: str, schema: dict, *, page_ref: str) -> ProviderResult: ...
    # ProviderResult: json validado, cajas normalizadas 0–1, tokens, segundos, coste €
```

- Política `TRAZIA_EXTERNAL_PROVIDERS` = `deny` | `synthetic_only` (por defecto) | `allow`.
- Con `dataset="real"`, un proveedor externo **solo** funciona con `allow`, y `allow` exige
  `TRAZIA_EXTERNAL_AUTH` (referencia a la autorización escrita).
- Cada llamada externa queda en `generated/registro_envios.jsonl`: hash del documento, proveedor,
  fecha y página.
- Claves en `.env`, nunca en el repo.

## Interfaz 3 · resultados del estudio (Lectura produce, Plataforma sirve y pinta)

Archivo `generated/estudio/estudio.json`:

```json
{
  "generated_at": "…", "seed": 2026, "datasets": ["S-dev", "S-reservado", "R-ref"],
  "variants": [{
    "id": "d_hibrido", "strategy": "d_hibrido", "providers": ["ollama:qwen3-vl:4b"],
    "metrics": {
      "score": 0.0, "geometry": 0.0, "attributes": 0.0, "ece": 0.0, "f1_delta": 0.0,
      "hallucination_rate": 0.0, "citation_coverage": 0.0, "interval_coverage": 0.0,
      "cost_eur_per_equipment": 0.0, "seconds_per_revision": 0.0
    },
    "ci95": {"score": [0.0, 0.0]},
    "by_dataset": {"S-reservado": {}}, "by_style": {}, "by_degradation": {}
  }],
  "ablations": [{"id": "d_hibrido-geometria", "delta_score": 0.0, "ci95": [0.0, 0.0]}],
  "pairwise": [{"a": "d_hibrido", "b": "b_reglas", "mcnemar_p": 0.0}],
  "pareto": ["b_reglas", "d_hibrido"],
  "recommendation": {"vectorial": "d_hibrido", "escaneado": "d_hibrido", "rationale": "…"}
}
```

- Plataforma lo sirve en `GET /estudio` y lo pinta en la pantalla **Estudio**.
- Mientras no exista, la web muestra un estado vacío honesto.

## Interfaz 4 · API para la web (Plataforma)

- La web ya consume `getRevision`, `getReviewFields`, `updateField` (con `Idempotency-Key`),
  `getChanges`, `getEquipment` y `getBench` de `web/src/lib/mock/api.ts`.
- Plataforma las sirve con los endpoints de la sección H y añade `web/src/lib/api/`.
- Con `NEXT_PUBLIC_API_URL`, la web usa la API; sin ella, los mocks. La demo offline nunca se rompe.

---

## Informes

Cada agente termina cada fase con `docs/agentes/INFORME_LECTURA.md` o
`docs/agentes/INFORME_PLATAFORMA.md`:
- qué está hecho y cómo se prueba;
- cifras medidas;
- cambios en interfaces;
- qué necesita del otro;
- límites.
