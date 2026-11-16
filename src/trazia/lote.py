"""Proceso por lotes de una carpeta de documentos: pensado para Databricks y sus volúmenes.

La entrada es cualquier carpeta (por ejemplo `/Volumes/<catálogo>/<esquema>/<volumen>/...`) con
los nombres del dataset del reto: `GAD_<TAG>_rev<R>.pdf`, `HDM_<TAG>_rev<R>.xlsx`,
`VESOR_<TAG>.pdf`…
Se agrupa por tag y revisión; un documento sin revisión acompaña a todas las de su tag.

Por cada equipo y revisión se ejecuta `pipeline.process` con la revisión anterior como `previous`
y se escribe en la salida:

    <TAG>/rev<R>/revision.json    contrato 0.3 con fuentes, confianza y RunInfo
    <TAG>/rev<R>/modelo.ifc       IFC4 DRAFT (validado como en la API)
    <TAG>/rev<R>/eventos.json     etapas del pipeline, avisos y error
    <TAG>/cambios_rev<A>_rev<B>.json   comparación entre revisiones consecutivas
    resumen.json / resumen.csv    una fila por equipo y revisión

Las cachés van a `<trabajo>/cache` salvo que ya estén fijadas con variables `TRAZIA_*`.
No toca la API ni la base de datos: es el mismo motor que usa la API, sin servidor.
"""

import csv
import json
import os
import re
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .ingest import IMAGE_SUFFIXES

SUFFIXES = (".pdf", ".xlsx", *IMAGE_SUFFIXES)
NAME = re.compile(
    r"^(?P<kind>GAD|GA|HDM|VESOR|ESTRUCTURA)_(?P<tag>.+?)(?:_rev(?P<rev>[^_.]+))?\.\w+$", re.I
)
DOCUMENT_PREFIX = {"GAD": "GA", "GA": "GA", "HDM": "HDM", "VESOR": "VESOR"}
ORDEN_TIPO = {"GA": 0, "HDM": 1, "VESOR": 2, "ESTRUCTURA": 3}  # como bench/estudio: GA primero
CACHES = {
    "TRAZIA_OCR_CACHE": "ocr",
    "TRAZIA_DETECTOR_CACHE": "detector",
    "TRAZIA_VISION_CACHE": "vision",
    "TRAZIA_RAG_VISUAL_CACHE": "rag-visual",
}


@dataclass
class Fila:
    tag: str
    revision: str
    documentos: list[str]
    estado: str  # "ok" o "error"
    error: str | None = None
    familia: str | None = None
    lod: int | None = None
    boquillas: int | None = None
    campos: int | None = None
    pendientes: int | None = None
    avisos: int = 0
    cambios: int | None = None
    segundos: float = 0.0
    carpeta: str = ""


@dataclass
class Documento:
    path: Path
    kind: str
    tag: str
    revision: str | None
    document_id: str = field(init=False)

    def __post_init__(self):
        prefix = DOCUMENT_PREFIX.get(self.kind.upper(), self.kind.upper())
        self.document_id = f"{prefix}-{identificador(self.tag)}"


def identificador(texto: str) -> str:
    """Los ids del contrato solo admiten letras, cifras, `_` y `-`."""
    return re.sub(r"[^A-Za-z0-9_-]+", "-", texto).strip("-") or "sin-tag"


def configurar_cache(trabajo: Path) -> dict[str, str]:
    """Fija las cachés en `trabajo/cache/...` sin pisar las variables que ya estén definidas."""
    fijadas = {}
    for variable, carpeta in CACHES.items():
        if not os.environ.get(variable):
            os.environ[variable] = str(Path(trabajo) / "cache" / carpeta)
        fijadas[variable] = os.environ[variable]
    if not os.environ.get("TRAZIA_REGISTRO_ENVIOS"):
        os.environ["TRAZIA_REGISTRO_ENVIOS"] = str(Path(trabajo) / "registro_envios.jsonl")
    fijadas["TRAZIA_REGISTRO_ENVIOS"] = os.environ["TRAZIA_REGISTRO_ENVIOS"]
    return fijadas


def _orden(revision: str):
    """Revisiones en orden natural: 1 < 2 < 10 y A < B."""
    return [int(t) if t.isdigit() else t.upper() for t in re.split(r"(\d+)", revision) if t]


def agrupar(entrada: Path) -> dict[str, dict[str, list[Documento]]]:
    """{tag: {revisión: documentos}} en orden. Los archivos con otro nombre se ignoran."""
    encontrados: dict[str, list[Documento]] = defaultdict(list)
    for path in sorted(Path(entrada).rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUFFIXES:
            continue
        match = NAME.match(path.name)
        if match:
            doc = Documento(path, match["kind"], match["tag"], match["rev"])
            encontrados[doc.tag].append(doc)
    grupos = {}
    for tag in sorted(encontrados):
        docs = encontrados[tag]
        revisiones = sorted({d.revision for d in docs if d.revision}, key=_orden)
        comunes = [d for d in docs if d.revision is None]
        if not revisiones:
            grupos[tag] = {"1": comunes}
            continue
        grupos[tag] = {r: [d for d in docs if d.revision == r] + comunes for r in revisiones}
    for revisiones in grupos.values():
        for docs in revisiones.values():
            docs.sort(key=lambda d: (ORDEN_TIPO.get(d.document_id.split("-")[0], 9), d.path.name))
    return grupos


def _escribir(path: Path, contenido: str | bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(contenido, bytes):
        path.write_bytes(contenido)
    else:
        path.write_text(contenido, encoding="utf-8")


def procesar_equipo(
    tag: str,
    revisiones: dict[str, list[Documento]],
    salida: Path,
    *,
    proyecto: str,
    estrategia: str,
    proveedores: list[str] | None = None,
    dataset: str = "real",
) -> list[Fila]:
    from .ifc import build_ifc, validate_ifc
    from .model import Revision
    from .pipeline import InputDocument, process
    from .revisions import compare

    filas, anterior, etiqueta_anterior = [], None, None
    for etiqueta, docs in revisiones.items():
        carpeta = Path(salida) / tag / f"rev{etiqueta}"
        nombres = [d.path.name for d in docs]
        fila = Fila(tag, etiqueta, nombres, "error", carpeta=str(carpeta))
        eventos = []
        inicio = time.perf_counter()
        try:
            entradas = [
                InputDocument(d.path.name, d.path.read_bytes(), d.document_id) for d in docs
            ]
            result = process(
                entradas,
                project_id=proyecto,
                equipment_id=identificador(tag).lower(),
                revision=etiqueta,
                strategy=estrategia,
                previous=anterior,
                providers=proveedores,
                dataset=dataset,
                on_event=lambda e: eventos.append(asdict(e)),
            )
            fila.avisos = len(result.warnings)
            if result.error or result.revision is None:
                fila.error = result.error or "Sin revisión"
            else:
                revision = Revision.model_validate_json(result.revision.model_dump_json())
                revision.approval = None
                if anterior is not None:
                    from .families.change_detection import preserve_nozzle_identity

                    revision = preserve_nozzle_identity(anterior, revision)
                revision.run = result.run
                modelo = build_ifc(revision, draft=True)
                problemas = validate_ifc(modelo)
                if problemas:
                    fila.error = "IFC inválido: " + problemas[0]["message"][:300]
                else:
                    _escribir(carpeta / "revision.json", revision.model_dump_json(indent=2))
                    _escribir(carpeta / "modelo.ifc", modelo.to_string())
                    equipo = revision.equipment
                    fila.estado = "ok"
                    fila.familia, fila.lod = equipo.kind, equipo.lod
                    fila.boquillas = len(equipo.nozzles)
                    from .model import fields

                    campos = fields(equipo)
                    fila.campos = len(campos)
                    fila.pendientes = len(revision.pending_review())
                    if anterior is not None:
                        cambios = compare(anterior, revision)
                        nombre = f"cambios_rev{etiqueta_anterior}_rev{etiqueta}.json"
                        _escribir(
                            Path(salida) / tag / nombre,
                            json.dumps(cambios, ensure_ascii=False, indent=2, default=str),
                        )
                        fila.cambios = len(cambios.get("changes", []))
                    anterior, etiqueta_anterior = revision, etiqueta
            avisos = result.warnings
        except Exception as exc:  # un equipo roto no detiene el lote: queda en el resumen
            fila.error = f"{type(exc).__name__}: {str(exc).splitlines()[0] if str(exc) else ''}"
            avisos = []
        fila.segundos = round(time.perf_counter() - inicio, 3)
        _escribir(
            carpeta / "eventos.json",
            json.dumps(
                {"eventos": eventos, "avisos": avisos, "error": fila.error},
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
        )
        filas.append(fila)
    return filas


def _uno(argumentos):
    return procesar_equipo(*argumentos[:3], **argumentos[3])


def procesar_carpeta(
    entrada: Path,
    salida: Path,
    *,
    proyecto: str = "INDESIAHACK",
    estrategia: str = "d_hibrido",
    proveedores: list[str] | None = None,
    dataset: str = "real",
    trabajo: Path | None = None,
    procesos: int = 1,
    tags: list[str] | None = None,
) -> list[Fila]:
    """Procesa todos los equipos de `entrada` y deja resultados y resumen en `salida`."""
    salida = Path(salida)
    configurar_cache(Path(trabajo) if trabajo else salida / "_trabajo")
    grupos = agrupar(Path(entrada))
    if tags:
        wanted = {t.upper() for t in tags}
        grupos = {t: r for t, r in grupos.items() if t.upper() in wanted}
    opciones = {
        "proyecto": proyecto,
        "estrategia": estrategia,
        "proveedores": proveedores,
        "dataset": dataset,
    }
    tareas = [(tag, revisiones, salida, opciones) for tag, revisiones in grupos.items()]
    if procesos > 1 and len(tareas) > 1:
        from concurrent.futures import ProcessPoolExecutor

        with ProcessPoolExecutor(max_workers=procesos) as pool:
            bloques = list(pool.map(_uno, tareas))
    else:
        bloques = [_uno(t) for t in tareas]
    filas = [fila for bloque in bloques for fila in bloque]
    escribir_resumen(filas, salida)
    return filas


def escribir_resumen(filas: list[Fila], salida: Path):
    datos = [asdict(f) for f in filas]
    _escribir(Path(salida) / "resumen.json", json.dumps(datos, ensure_ascii=False, indent=2))
    path = Path(salida) / "resumen.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        columnas = list(Fila.__dataclass_fields__)
        writer = csv.DictWriter(handle, fieldnames=columnas)
        writer.writeheader()
        for fila in datos:
            writer.writerow({**fila, "documentos": "; ".join(fila["documentos"])})


def _tipo_error(error: str | None) -> str | None:
    """Categoría del error sin su texto, que puede citar valores o tags del plano."""
    if not error:
        return None
    if error.startswith("IFC inválido"):
        return "ifc_invalido"
    clase = re.match(r"^([A-Z]\w*(?:Error|Exception|Failure|Unavailable))\b", error)
    return clase[1] if clase else "pipeline"


def resumen_compartible(filas: list[Fila]) -> dict:
    """Agregados del lote que se pueden pegar al asistente de código (docs/FLUJO_IA.md).

    Sin nombres de archivo, rutas, tags reales ni textos de error o avisos: cada equipo pasa a
    `E01`, `E02`… en el orden del lote y los errores quedan como categoría.
    """
    alias = {tag: f"E{i:02d}" for i, tag in enumerate(dict.fromkeys(f.tag for f in filas), 1)}
    segundos = sorted(f.segundos for f in filas)

    def cuenta(valores):
        return dict(sorted(Counter(str(v) for v in valores if v is not None).items()))

    return {
        "revisiones": len(filas),
        "equipos": len(alias),
        "estado": cuenta(f.estado for f in filas),
        "familia": cuenta(f.familia for f in filas),
        "lod": cuenta(f.lod for f in filas),
        "errores": cuenta(_tipo_error(f.error) for f in filas),
        "avisos": sum(f.avisos for f in filas),
        "segundos": {
            "total": round(sum(segundos), 1),
            "mediana": round(segundos[len(segundos) // 2], 1) if segundos else 0,
            "max": round(segundos[-1], 1) if segundos else 0,
        },
        "por_revision": [
            {
                "equipo": alias[f.tag],
                "orden": i,
                "estado": f.estado,
                "error": _tipo_error(f.error),
                "familia": f.familia,
                "lod": f.lod,
                "boquillas": f.boquillas,
                "campos": f.campos,
                "pendientes": f.pendientes,
                "avisos": f.avisos,
                "cambios": f.cambios,
                "segundos": f.segundos,
            }
            for i, f in enumerate(filas, 1)
        ],
    }
