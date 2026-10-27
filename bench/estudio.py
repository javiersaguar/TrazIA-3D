"""Arnés del estudio comparativo A · B · C · D (docs/ESTUDIO.md, DEC-01, 21 y 22).

    uv run python -m synthetic --conjunto todos
    uv run python -m bench.estudio

Cada variante pasa por `trazia.pipeline.process`, el mismo camino que usa el producto; la rev2
recibe la rev1 como `previous`. Se mide sobre los mismos documentos para todas las variantes, y
la estadística se hace por equipo (bootstrap pareado) y por campo (McNemar).

Escribe `generated/estudio/estudio.json` (Interfaz 3 de COORDINACION-BACKEND.md) y `estudio.md`.

Definiciones (DEC-22):
- geometría: por revisión, fracción de campos geométricos correctos (±1 mm, ±0,5°) multiplicada
  por min(1, IoU/0,95) del IFC frente al de referencia; 0 si la revisión no llega a IFC, porque
  sin modelo no se entrega geometría. La fracción sin penalizar va en `details`.
- atributos: valor + unidad correctos tras convertir a la unidad canónica (pint).
- ECE: sobre todos los campos emitidos que tienen verdad.
- F1 de cambios: rev1 → rev2 frente a los cambios verdaderos; sin dos modelos, todo es «no visto».
- alucinación: valores emitidos cuya región citada no contiene el valor (bench/support.py), sobre
  los verificables. Cobertura de cita: emitidos con página y caja, o celda.
- escala: 1 − (0,5·min(1, s/60) + 0,5·min(1, €/0,50)) por revisión y por equipo.
- innovación: constante 1 para todas las variantes (no se mide; no cambia el orden).
- Restricciones: alucinación < 1 % y cita = 100 %. Una variante que no las cumple no gana.
"""

import argparse
import json
import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from statistics import fmean

from synthetic.cases import flatten, spec_from_dict, spec_to_revision
from trazia.ifc import build_ifc
from trazia.ingest import Bundle, ingest_bytes
from trazia.pipeline import InputDocument, PipelineResult, process
from trazia.revisions import compare
from trazia.strategies import ABLATIONS, STRATEGIES

from .ifc_geometry import compare_models
from .metrics import ece
from .stats import bootstrap_ci, mcnemar, paired_bootstrap_delta, pareto
from .support import is_cited, is_supported
from .units import same, to_canonical

DATASET_NAMES = {
    "s-dev": "S-dev",
    "s-reservado": "S-reservado",
    "s-adversarial": "S-adversarial",
    "s-mecanico": "S-mecánico",
}
SCORED = ("S-dev", "S-reservado")  # la puntuación principal; el adversarial se mide aparte
SCANS = ("escaneado_limpio", "escaneado_pobre")
WEIGHTS = {"geometry": 0.35, "attributes": 0.25, "f1_delta": 0.20, "scale": 0.10, "innov": 0.10}
TIME_BUDGET_S, COST_BUDGET_EUR = 60.0, 0.50


@dataclass(frozen=True)
class VariantSpec:
    id: str
    strategy: str
    providers: tuple[str, ...] = ()
    ablation_of: str | None = None
    description: str = ""
    needs_env: str | None = None
    skip_by_default: str | None = None  # motivo para no medirla salvo que se pida explícitamente


VARIANTS = (
    VariantSpec(
        "a_vision",
        "a_vision",
        ("ollama:qwen3-vl:4b-instruct",),
        None,
        "A con Qwen3-VL local como lector",
        skip_by_default="unos 4 min de GPU por página: se mide aparte en un subconjunto",
    ),
    VariantSpec("a_vision@gemini", "a_vision", ("gemini",), None, "A con Gemini", "GEMINI_API_KEY"),
    VariantSpec(
        "a_vision@mistral", "a_vision", ("mistral",), None, "A con Mistral", "MISTRAL_API_KEY"
    ),
    VariantSpec("a_geometria", "a_geometria", (), None, "A: trazos + capa de texto u OCR"),
    VariantSpec("a_detector", "a_detector", (), None, "A con el detector propio (Florence-2)"),
    VariantSpec("b_reglas", "b_reglas", (), None, "B: texto, tablas, cotas, cajetín y HDM"),
    VariantSpec("b_reglas+ocr", "b_reglas+ocr", (), None, "B sobre líneas de OCR"),
    VariantSpec("c_rag", "c_rag", (), None, "C: recuperación y adaptación de plantilla"),
    VariantSpec("d_hibrido", "d_hibrido", (), None, "D: cascada B, C, memoria y geometría"),
    VariantSpec("b_reglas-tablas", "b_reglas-tablas", (), "b_reglas", "B sin tablas ni cotas"),
    VariantSpec("b_reglas-hdm", "b_reglas-hdm", (), "b_reglas", "B sin hoja de datos"),
    *(
        VariantSpec(f"d_hibrido-{c}", f"d_hibrido-{c}", (), "d_hibrido", f"D sin {c}")
        for c in ("geometria", "memoria", "rag", "detector")
    ),
    VariantSpec(
        "d_hibrido-vision",
        "d_hibrido-vision",
        (),
        "d_hibrido",
        "D sin modelo de visión",
        skip_by_default="el estudio no da proveedor de visión a D: sería idéntica a d_hibrido",
    ),
)


def availability(variant: VariantSpec, explicit: bool = False) -> str | None:
    """None si se puede medir; si no, el motivo en español."""
    if variant.strategy not in STRATEGIES and variant.strategy not in ABLATIONS:
        return "estrategia aún no implementada"
    if variant.skip_by_default and not explicit:
        return variant.skip_by_default
    if variant.needs_env and not os.environ.get(variant.needs_env):
        return f"sin {variant.needs_env} en .env: sin medir"
    return None


# Resultados por equipo -----------------------------------------------------------------------
@dataclass
class FieldRow:
    path: str
    kind: str  # geo | attr | tag | spurious
    expected: bool
    emitted: bool
    correct: bool
    confidence: float | None = None
    cited: bool = False
    supported: bool | None = None
    interval_hit: bool | None = None


@dataclass
class RevResult:
    rows: list[FieldRow]
    built: bool
    iou_factor: float
    seconds: float
    cost_eur: float
    external_calls: int
    error: str | None


@dataclass
class CaseResult:
    dataset: str
    degradation: str
    tag: str
    vendor: str
    revs: list[RevResult]
    tp: int
    fp: int
    fn: int
    traps: list[dict] = field(default_factory=list)  # {"kind", "poisoned"}

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.dataset, self.degradation, self.tag)


@lru_cache(maxsize=4096)
def _bundle(path: str, document_id: str, revision: str) -> Bundle | None:
    try:
        file = Path(path)
        bundle = ingest_bytes(file.read_bytes(), file.name, document_id, revision)
    except Exception:  # noqa: BLE001 - un documento ilegible no se puede verificar
        return None
    if bundle.media_type == "pdf" and not bundle.lines:
        # Escaneado: se verifica contra el OCR de la página (misma caché que la estrategia).
        try:
            from trazia.ocr import ocr_pdf_lines

            bundle = bundle.model_copy(
                update={"lines": ocr_pdf_lines(Path(path).read_bytes(), document_id)}
            )
        except Exception:  # noqa: BLE001 - sin OCR, la cita queda «no verificable»
            pass
    return bundle


@lru_cache(maxsize=1024)
def _reference_ifc(truth_json: str, revision: str):
    return build_ifc(spec_to_revision(spec_from_dict(json.loads(truth_json)), revision), draft=True)


def _documents(folder: Path, tag: str, rev: str) -> list[tuple[Path, str]]:
    docs = [(folder / f"GAD_{tag}_rev{rev}.pdf", f"GA-{tag}")]
    hdm = folder / f"HDM_{tag}_rev{rev}.xlsx"
    if hdm.exists():
        docs.append((hdm, f"HDM-{tag}"))
    return docs


def _score_revision(
    result: PipelineResult, truth: dict, rev: str, docs: list[tuple[Path, str]]
) -> RevResult:
    spec = spec_from_dict(truth)
    expected = flatten(spec)
    chosen = {c.path: c for c in result.candidates}
    bundles = {doc_id: _bundle(str(path), doc_id, rev) for path, doc_id in docs}
    rows = []
    for path in sorted(expected.keys() | chosen.keys()):
        c = chosen.get(path)
        known = path in expected
        kind = (
            "spurious"
            if not known
            else "attr"
            if path.startswith("attributes.")
            else "tag"
            if path == "tag"
            else "geo"
        )
        row = FieldRow(path=path, kind=kind, expected=known, emitted=c is not None, correct=False)
        if c is not None:
            row.confidence = c.source.confidence
            row.cited = is_cited(c)
            row.supported = is_supported(c, bundles.get(c.source.document_id))
            if known:
                value, unit = expected[path]
                row.correct = same(c.value, c.unit, value, unit)
                if c.interval is not None and not isinstance(value, str):
                    low, _ = to_canonical(c.interval.low, c.unit)
                    high, _ = to_canonical(c.interval.high, c.unit)
                    row.interval_hit = low <= value <= high
        rows.append(row)
    factor = 0.0
    if result.revision is not None:
        reference = _reference_ifc(json.dumps(truth, sort_keys=True), result.revision.revision)
        elements = compare_models(build_ifc(result.revision, draft=True), reference)["elements"]
        iou = fmean(e["iou"] for e in elements) if elements else 0.0
        factor = min(1.0, iou / 0.95)
    return RevResult(
        rows=rows,
        built=result.revision is not None,
        iou_factor=factor,
        seconds=result.run.seconds,
        cost_eur=result.run.cost_eur or 0.0,
        external_calls=result.run.external_calls,
        error=result.error,
    )


def run_case(
    variant: VariantSpec, root: Path, dataset: str, degradation: str, tag: str
) -> CaseResult:
    truth = json.loads((root / "truth" / f"{tag}.json").read_text(encoding="utf-8"))
    folder = root / degradation / tag
    revs, results = [], []
    previous = None
    for rev in ("1", "2"):
        docs = _documents(folder, tag, rev)
        inputs = [InputDocument(path.name, path.read_bytes(), doc_id) for path, doc_id in docs]
        result = process(
            inputs,
            project_id="ESTUDIO",
            equipment_id=tag.lower(),
            revision=rev,
            strategy=variant.strategy,
            previous=previous,
            providers=list(variant.providers) or None,
            dataset="synthetic",
        )
        previous = result.revision
        results.append(result)
        revs.append(_score_revision(result, truth[f"rev{rev}"], rev, docs))
    expected = {(c["path"], c["operation"]) for c in truth["changes"]}
    if results[0].revision is not None and results[1].revision is not None:
        detected = compare(results[0].revision, results[1].revision)["changes"]
        mine = {(c["path"], c["operation"]) for c in detected}
        tp, fp, fn = len(mine & expected), len(mine - expected), len(expected - mine)
    else:
        tp, fp, fn = 0, 0, len(expected)
    traps = []
    for trap in truth.get("traps", []):
        poisoned = False
        for result in results:
            chosen = {c.path: c for c in result.candidates}
            if trap["path"].startswith("nozzles.N9."):
                poisoned |= any(p.startswith("nozzles.N9.") for p in chosen)
            elif (c := chosen.get(trap["path"])) is not None:
                poisoned |= same(c.value, c.unit, trap["value"], trap["unit"])
        traps.append({"kind": trap["kind"], "poisoned": poisoned})
    return CaseResult(dataset, degradation, tag, truth.get("vendor", "?"), revs, tp, fp, fn, traps)


# Métricas ------------------------------------------------------------------------------------
def _rows(cases, predicate=lambda r: True):
    return [row for c in cases for r in c.revs for row in r.rows if predicate(row)]


def metrics(cases: list[CaseResult]) -> dict | None:
    if not cases:
        return None
    revs = [r for c in cases for r in c.revs]
    geo_rev, geo_raw = [], []
    for r in revs:
        geo = [row for row in r.rows if row.kind == "geo"]
        if geo:
            share = sum(row.correct for row in geo) / len(geo)
            geo_raw.append(share)
            geo_rev.append(share * r.iou_factor)
    attrs = _rows(cases, lambda row: row.kind == "attr")
    emitted = _rows(cases, lambda row: row.emitted)
    pairs = [(row.confidence, row.correct) for row in emitted if row.expected]
    verifiable = [row for row in emitted if row.supported is not None]
    intervals = [row.interval_hit for row in emitted if row.interval_hit is not None]
    tp, fp, fn = (sum(getattr(c, k) for c in cases) for k in ("tp", "fp", "fn"))
    f1 = 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else None
    seconds = fmean(r.seconds for r in revs)
    cost = fmean(sum(r.cost_eur for r in c.revs) for c in cases)
    geometry = fmean(geo_rev) if geo_rev else 0.0
    attributes = sum(row.correct for row in attrs) / len(attrs) if attrs else 0.0
    calibration = ece(pairs)
    scale = 1 - (0.5 * min(1, seconds / TIME_BUDGET_S) + 0.5 * min(1, cost / COST_BUDGET_EUR))
    score = (
        WEIGHTS["geometry"] * geometry
        + WEIGHTS["attributes"] * attributes * (1 - (calibration or 0.0))
        + WEIGHTS["f1_delta"] * (f1 or 0.0)
        + WEIGHTS["scale"] * scale
        + WEIGHTS["innov"] * 1.0
    )
    hallucination = (
        sum(not row.supported for row in verifiable) / len(verifiable) if verifiable else 0.0
    )
    traps = [t for c in cases for t in c.traps]
    return {
        "score": round(score, 4),
        "geometry": round(geometry, 4),
        "attributes": round(attributes, 4),
        "ece": None if calibration is None else round(calibration, 4),
        "f1_delta": None if f1 is None else round(f1, 4),
        "hallucination_rate": round(hallucination, 4),
        "citation_coverage": round(sum(r.cited for r in emitted) / len(emitted), 4)
        if emitted
        else 1.0,
        "interval_coverage": round(fmean(intervals), 4) if intervals else None,
        "cost_eur_per_equipment": round(cost, 4),
        "seconds_per_revision": round(seconds, 4),
        "_details": {
            "equipment": len(cases),
            "revisions": len(revs),
            "models_built": round(sum(r.built for r in revs) / len(revs), 4),
            "geometry_fields_unpenalized": round(fmean(geo_raw), 4) if geo_raw else 0.0,
            "scale": round(scale, 4),
            "emitted_fields": len(emitted),
            "unverifiable_fields": len(emitted) - len(verifiable),
            "spurious_fields": sum(1 for row in emitted if not row.expected),
            "external_calls": sum(r.external_calls for r in revs),
            "poisoning_rate": round(sum(t["poisoned"] for t in traps) / len(traps), 4)
            if traps
            else None,
            "errors": sorted({r.error.splitlines()[0][:120] for r in revs if r.error})[:5],
        },
    }


def _public(m: dict | None) -> dict | None:
    if m is None:
        return None
    return {k: v for k, v in m.items() if not k.startswith("_")}


def _score_of(cases) -> float | None:
    m = metrics(list(cases))
    return None if m is None else m["score"]


def _group(cases, key) -> dict[str, list[CaseResult]]:
    out: dict[str, list[CaseResult]] = defaultdict(list)
    for c in cases:
        out[key(c)].append(c)
    return dict(out)


def eligible(m: dict) -> bool:
    return m["hallucination_rate"] < 0.01 and m["citation_coverage"] >= 1.0


# Estudio -------------------------------------------------------------------------------------
def run_study(
    data: Path,
    sets: list[str],
    variant_ids: list[str] | None = None,
    *,
    cases_limit: int | None = None,
    degradations: list[str] | None = None,
    resamples: int = 1000,
    seed: int = 2026,
    log=print,
) -> dict:
    chosen = [v for v in VARIANTS if variant_ids is None or v.id in variant_ids]
    measured, unmeasured = [], []
    for v in chosen:
        reason = availability(v, explicit=variant_ids is not None and v.id in variant_ids)
        (unmeasured.append({"id": v.id, "reason": reason}) if reason else measured.append(v))
    set_info, plan = {}, []
    for name in sets:
        root = data / name
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        label = DATASET_NAMES.get(name, name)
        set_info[label] = {"seed": manifest["seed"], "cases": len(manifest["cases"])}
        if manifest.get("kind", "vessel") != "vessel":
            unmeasured.append(
                {"id": label, "reason": "mecánicos: el contrato aún no tiene envolvente (LOD 1)"}
            )
            continue
        styles = [s for s in manifest["styles"] if not degradations or s in degradations]
        for case in manifest["cases"][:cases_limit]:
            for degradation in styles:
                plan.append((root, label, degradation, case["tag"]))
    needs_library = any(v.strategy.startswith(("c_rag", "d_hibrido")) for v in measured)
    if needs_library and (data / "s-dev" / "manifest.json").exists():
        from trazia.rag.library import build
        from trazia.strategies.c_rag import library_path

        if not library_path().exists():
            log(f"· biblioteca de C desde {data / 's-dev'}")
            build(data / "s-dev", library_path())
    results: dict[str, list[CaseResult]] = {}
    for v in measured:
        equipment_count = len({(item[1], item[3]) for item in plan})
        log(f"· {v.id}: {equipment_count} equipos · {len(plan)} condiciones × 2 revisiones")
        results[v.id] = [run_case(v, *item) for item in plan]

    def scored(cases):
        return [c for c in cases if c.dataset in SCORED]

    variants_out = []
    for v in measured:
        cases = results[v.id]
        main = metrics(scored(cases)) or metrics(cases)
        # Las degradaciones son observaciones correlacionadas del mismo equipo.
        units = list(_group(scored(cases) or cases, lambda c: (c.dataset, c.tag)).values())
        entry = {
            "id": v.id,
            "strategy": v.strategy,
            "providers": list(v.providers),
            "description": v.description,
            "metrics": _public(main),
            "ci95": {
                k: bootstrap_ci(
                    units,
                    lambda s, k=k: (metrics([c for group in s for c in group]) or {}).get(k),
                    resamples=resamples,
                    seed=seed,
                )
                for k in ("score", "geometry", "attributes", "f1_delta")
            },
            "by_dataset": {
                d: {**_public(m), **m["_details"]}
                for d, cs in _group(cases, lambda c: c.dataset).items()
                if (m := metrics(cs))
            },
            "by_style": {
                s: _public(metrics(cs))
                for s, cs in _group(scored(cases), lambda c: c.vendor).items()
            },
            "by_degradation": {
                d: _public(metrics(cs))
                for d, cs in _group(scored(cases), lambda c: c.degradation).items()
            },
            "details": {**main["_details"], "bootstrap_equipment_units": len(units)},
            "eligible": eligible(main),
        }
        variants_out.append(entry)

    by_id = {v.id: v for v in measured}
    ablations = []
    for v in measured:
        if v.ablation_of and v.ablation_of in results:
            full = {c.key: c for c in scored(results[v.ablation_of])}
            mine = {c.key: c for c in scored(results[v.id])}
            keys = sorted(full.keys() & mine.keys())
            clusters = defaultdict(list)
            for key in keys:
                clusters[(key[0], key[2])].append(key)
            delta = paired_bootstrap_delta(
                list(clusters.values()),
                lambda s, mine=mine: _score_of(mine[k] for group in s for k in group),
                lambda s, full=full: _score_of(full[k] for group in s for k in group),
                resamples=resamples,
                seed=seed,
            )
            point = (_score_of(mine[k] for k in keys) or 0) - (
                _score_of(full[k] for k in keys) or 0
            )
            ablations.append(
                {"id": v.id, "of": v.ablation_of, "delta_score": round(point, 4), "ci95": delta}
            )

    def field_flags(variant_id):
        return {
            (c.key, i, row.path): row.correct
            for c in scored(results[variant_id])
            for i, r in enumerate(c.revs)
            for row in r.rows
            if row.expected
        }

    ranked = sorted(variants_out, key=lambda e: e["metrics"]["score"], reverse=True)
    pairwise = []
    for i, a in enumerate(ranked):
        for b in ranked[i + 1 :]:
            fa, fb = field_flags(a["id"]), field_flags(b["id"])
            keys = sorted(fa.keys() & fb.keys(), key=str)
            test = mcnemar([fa[k] for k in keys], [fb[k] for k in keys])
            pairwise.append(
                {
                    "a": a["id"],
                    "b": b["id"],
                    "mcnemar_p": test["p"],
                    "only_a": test["only_a"],
                    "only_b": test["only_b"],
                    "fields": len(keys),
                }
            )
    front = pareto(
        {
            e["id"]: (
                e["metrics"]["cost_eur_per_equipment"],
                e["metrics"]["seconds_per_revision"],
                -e["metrics"]["score"],
            )
            for e in variants_out
        }
    )
    recommendation = _recommend(variants_out, results, by_id, scored)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seed": seed,
        "synthetic": True,
        "generator": "v2",
        "sets": set_info,
        "datasets": sorted({c.dataset for cs in results.values() for c in cs}),
        "variants": variants_out,
        "unmeasured": unmeasured,
        "ablations": ablations,
        "pairwise": pairwise,
        "pareto": front,
        "recommendation": recommendation,
    }


def _recommend(variants_out, results, by_id, scored) -> dict:
    candidates = [e for e in variants_out if not by_id[e["id"]].ablation_of]
    out, notes = {}, []
    for label, wanted in (("vectorial", ("vectorial",)), ("escaneado", SCANS)):
        scores = []
        for e in candidates:
            cases = [c for c in scored(results[e["id"]]) if c.degradation in wanted]
            m = metrics(cases)
            if m:
                scores.append((eligible(m), m["score"], e["id"], m))
        if not scores:
            out[label] = None
            continue
        scores.sort(key=lambda s: (s[0], s[1]), reverse=True)
        ok, score, winner, m = scores[0]
        out[label] = winner
        notes.append(
            f"{label}: {winner} (puntuación {_num(score)}, geometría {_pct(m['geometry'])}, "
            f"atributos {_pct(m['attributes'])})" + ("" if ok else " — no cumple las restricciones")
        )
    out["rationale"] = (
        "Elegida por mayor Puntuación GA2MODEL entre las variantes que cumplen alucinación < 1 % "
        "y cita = 100 %, sobre S-dev y S-reservado (sintéticos). " + "; ".join(notes) + "."
    )
    return out


# Informe -------------------------------------------------------------------------------------
def _pct(x):
    return "—" if x is None else f"{100 * x:.1f} %".replace(".", ",")


def _num(x, d=3):
    return "—" if x is None else f"{x:.{d}f}".replace(".", ",")


def _ci(ci):
    return "—" if not ci else f"[{_num(ci[0])}; {_num(ci[1])}]"


def to_markdown(study: dict) -> str:
    lines = [
        "# Estudio comparativo de estrategias · resultados",
        "",
        f"Generado {study['generated_at']} · generador {study['generator']} · semilla del "
        f"bootstrap {study['seed']}.",
        "",
        "> **Datos sintéticos.** Proveedores ficticios con verdad conocida. No es precisión sobre "
        "planos reales de Técnicas Reunidas.",
        "",
        "Conjuntos: "
        + ", ".join(
            f"{k} (semilla {v['seed']}, {v['cases']} equipos)" for k, v in study["sets"].items()
        ),
        "",
        "## Variantes medidas (" + " + ".join(d for d in study["datasets"] if d in SCORED) + ")",
        "",
        "| Variante | Puntuación | IC 95 % | Geometría | Atributos | ECE | F1 cambios "
        "| Alucinación | Cita | s/rev | €/equipo | Elegible |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for e in sorted(study["variants"], key=lambda e: e["metrics"]["score"], reverse=True):
        m = e["metrics"]
        lines.append(
            f"| `{e['id']}` | {_num(m['score'])} | {_ci(e['ci95']['score'])} "
            f"| {_pct(m['geometry'])} | {_pct(m['attributes'])} | {_num(m['ece'])} "
            f"| {_pct(m['f1_delta'])} "
            f"| {_pct(m['hallucination_rate'])} | {_pct(m['citation_coverage'])} "
            f"| {_num(m['seconds_per_revision'], 2)} | {_num(m['cost_eur_per_equipment'], 2)} "
            f"| {'sí' if e['eligible'] else 'no'} |"
        )
    lines += ["", "## Por conjunto", ""]
    lines += [
        "| Variante | Conjunto | Puntuación | Geometría | Geometría sin penalizar | Atributos "
        "| Modelos IFC | Envenenamiento |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for e in study["variants"]:
        for d, m in e["by_dataset"].items():
            lines.append(
                f"| `{e['id']}` | {d} | {_num(m['score'])} | {_pct(m['geometry'])} "
                f"| {_pct(m['geometry_fields_unpenalized'])} | {_pct(m['attributes'])} "
                f"| {_pct(m['models_built'])} | {_pct(m['poisoning_rate'])} |"
            )
    for title, key in (("Por proveedor", "by_style"), ("Por degradación", "by_degradation")):
        lines += [
            "",
            f"## {title}",
            "",
            "| Variante | Grupo | Puntuación | Geometría | Atributos |",
        ]
        lines.append("| --- | --- | --- | --- | --- |")
        for e in study["variants"]:
            for g, m in e[key].items():
                lines.append(
                    f"| `{e['id']}` | {g} | {_num(m['score'])} | {_pct(m['geometry'])} "
                    f"| {_pct(m['attributes'])} |"
                )
    if study["ablations"]:
        lines += ["", "## Ablaciones", "", "| Ablación | De | Δ puntuación | IC 95 % |"]
        lines.append("| --- | --- | --- | --- |")
        for a in study["ablations"]:
            lines.append(
                f"| `{a['id']}` | `{a['of']}` | {_num(a['delta_score'])} | {_ci(a['ci95'])} |"
            )
    if study["pairwise"]:
        lines += ["", "## Comparaciones pareadas (McNemar exacto, campo a campo)", ""]
        lines += [
            "| A | B | Solo A acierta | Solo B acierta | Campos | p |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for p in study["pairwise"]:
            lines.append(
                f"| `{p['a']}` | `{p['b']}` | {p['only_a']} | {p['only_b']} | {p['fields']} "
                f"| {p['mcnemar_p']:.2g} |"
            )
    lines += [
        "",
        "## Frontera de Pareto (coste, tiempo, puntuación)",
        "",
        ", ".join(f"`{v}`" for v in study["pareto"]) or "—",
        "",
        "## Recomendación",
        "",
        f"- Vectorial: `{study['recommendation'].get('vectorial')}`",
        f"- Escaneado: `{study['recommendation'].get('escaneado')}`",
        f"- {study['recommendation']['rationale']}",
        "",
        "## Sin medir",
        "",
    ]
    lines += [f"- `{u['id']}`: {u['reason']}" for u in study["unmeasured"]] or ["- Nada."]
    lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Estudio comparativo A/B/C/D (DEC-01, 22)")
    parser.add_argument("--datos", type=Path, default=Path("generated/synthetic_v2"))
    parser.add_argument(
        "--conjuntos", nargs="+", default=["s-dev", "s-reservado", "s-adversarial", "s-mecanico"]
    )
    parser.add_argument("--variantes", nargs="+", default=None)
    parser.add_argument("--casos", type=int, default=None, help="Primeros N equipos por conjunto")
    parser.add_argument("--degradaciones", nargs="+", default=None)
    parser.add_argument("--remuestreos", type=int, default=1000)
    parser.add_argument("--semilla", type=int, default=2026)
    parser.add_argument("--salida", type=Path, default=Path("generated/estudio"))
    args = parser.parse_args(argv)
    sets = [s for s in args.conjuntos if (args.datos / s / "manifest.json").exists()]
    missing = sorted(set(args.conjuntos) - set(sets))
    if not sets:
        parser.error(
            f"No hay conjuntos en {args.datos}. Genéralos con: "
            "uv run python -m synthetic --conjunto todos"
        )
    study = run_study(
        args.datos,
        sets,
        args.variantes,
        cases_limit=args.casos,
        degradations=args.degradaciones,
        resamples=args.remuestreos,
        seed=args.semilla,
    )
    study["unmeasured"] += [
        {"id": DATASET_NAMES.get(m, m), "reason": "conjunto no generado"} for m in missing
    ]
    args.salida.mkdir(parents=True, exist_ok=True)
    (args.salida / "estudio.json").write_text(
        json.dumps(study, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.salida / "estudio.md").write_text(to_markdown(study), encoding="utf-8")
    for e in sorted(study["variants"], key=lambda e: e["metrics"]["score"], reverse=True):
        m = e["metrics"]
        print(
            f"{e['id']:18s} puntuación {m['score']:.3f} {e['ci95']['score']} · geometría "
            f"{m['geometry']:.0%} · atributos {m['attributes']:.0%} · F1 {m['f1_delta'] or 0:.0%} "
            f"· alucinación {m['hallucination_rate']:.1%} · elegible {e['eligible']}"
        )
    print(f"Informe: {args.salida / 'estudio.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
