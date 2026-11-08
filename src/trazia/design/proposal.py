"""Motor determinista de propuestas de cambio de diseño (K.1).

Recibe operaciones tipadas, normaliza unidades y valida el lote completo sobre una copia de
la revisión base. Nunca persiste ni corrige silenciosamente otros campos: un conflicto se
informa con su campo y su motivo.
"""

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Literal

from pydantic import Field, ValidationError

from trazia.model import (
    Derivation,
    DesignRef,
    Document,
    Identifier,
    Model,
    Revision,
    Source,
    fields,
    nozzle_misfit,
)
from trazia.units import UnitError, normalize

from .catalog import AZIMUTH_NORTH, DATUM_TANGENT, Target, targets

ENGINE_VERSION = "k1-1"
Datum = Literal["suelo", "tangente_inferior", "interno", "norte"]
Origin = Literal["formulario", "chat", "deshacer"]


class OperationInput(Model):
    id: Identifier | None = None
    target: str = Field(min_length=1, max_length=200)
    value: float | str
    unit: str | None = Field(default=None, min_length=1, max_length=20)
    decimal_separator: Literal[".", ","] | None = None
    datum: Datum | None = None


class Clarification(Model):
    question: str = Field(min_length=1, max_length=500)
    options: list[str] = Field(default_factory=list, max_length=6)
    operation_id: Identifier | None = None


class ProposalInput(Model):
    operations: list[OperationInput] = Field(default_factory=list, max_length=20)
    reason: str = Field(min_length=3, max_length=1000)
    actor: str = Field(min_length=2, max_length=100)
    origin: Origin = "formulario"
    request_text: str | None = Field(default=None, max_length=2000)
    clarifications: list[Clarification] = Field(default_factory=list, max_length=6)


@dataclass
class Evaluation:
    status: str
    operations: list[dict] = field(default_factory=list)
    issues: list[dict] = field(default_factory=list)
    effects: list[dict] = field(default_factory=list)
    derived: dict = field(default_factory=dict)
    candidate: Revision | None = None

    @property
    def errors(self):
        return [i for i in self.issues if i["severity"] == "error"]

    def summary(self) -> dict:
        return {
            "status": self.status,
            "operations": self.operations,
            "issues": self.issues,
            "effects": self.effects,
            "derived": self.derived,
            "engine_version": ENGINE_VERSION,
        }


def issue(severity, code, message, *, path=None, operation_id=None, **extra):
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "path": path,
        "operation_id": operation_id,
        **extra,
    }


def canonical(data) -> str:
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(data) -> str:
    return hashlib.sha256(canonical(data).encode()).hexdigest()


def resolve(path: str, equipment):
    """Campo trazado por ruta estable (`nozzles.N3.elevation`)."""
    return fields(equipment).get(path)


def current_values(equipment) -> dict[str, dict]:
    traced = fields(equipment)
    result = {}
    for key, spec in targets(equipment).items():
        if spec.derived:
            result[key] = {"value": equipment.total_height, "unit": "mm", "state": None}
            continue
        value = traced[spec.path]
        result[key] = {
            "value": value.value,
            "unit": value.unit,
            "state": value.state,
            "channel": value.source.channel,
        }
    return result


def catalog(revision: Revision) -> dict:
    equipment = revision.equipment
    values = current_values(equipment)
    return {
        "equipment_id": equipment.id,
        "kind": equipment.kind,
        "lod": equipment.lod,
        "datum": {
            "elevation": "Suelo local: z = 0 en la base del faldón.",
            "azimuth": "0° = +X, 90° = +Y, antihorario visto desde +Z. Norte de planta no "
            "verificado.",
            "shell_bottom_mm": equipment.shell_bottom,
        },
        "targets": [spec.describe(values[key]) for key, spec in targets(equipment).items()],
    }


def _normalize(spec: Target, operation: OperationInput, op_id: str):
    """(valor canónico, texto original, unidad original) o un issue de error."""
    if spec.text:
        if not isinstance(operation.value, str):
            return None, issue(
                "error",
                "text_type",
                f"{spec.label}: escribe un texto.",
                path=spec.path,
                operation_id=op_id,
            )
        text = operation.value.strip()
        if not 1 <= len(text) <= 200:
            return None, issue(
                "error",
                "text_length",
                "Escribe de 1 a 200 caracteres.",
                path=spec.path,
                operation_id=op_id,
            )
        return (text, text, None), None
    if spec.magnitude is None:
        if isinstance(operation.value, str):
            return None, issue(
                "error",
                "number_type",
                f"{spec.label}: escribe un número.",
                path=spec.path,
                operation_id=op_id,
            )
        if operation.unit not in (None, spec.unit):
            return None, issue(
                "error",
                "unit_unsupported",
                f"Este atributo se registra en {spec.unit} sin conversión.",
                path=spec.path,
                operation_id=op_id,
            )
        number = float(operation.value)
        if not math.isfinite(number):
            return None, issue(
                "error",
                "not_finite",
                "El valor debe ser finito.",
                path=spec.path,
                operation_id=op_id,
            )
        return (number, str(operation.value), spec.unit), None
    if isinstance(operation.value, str) and not operation.value.strip():
        return None, issue(
            "error", "empty", "Escribe un valor.", path=spec.path, operation_id=op_id
        )
    value = operation.value
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    raw = str(value).strip() + (f" {operation.unit}" if operation.unit else "")
    try:
        result = normalize(
            raw, spec.magnitude, decimal=operation.decimal_separator, default_unit=None
        )
    except UnitError as error:
        message = str(error)
        if "Unidad no admitida: ''" in message:
            message = f"Indica la unidad (por ejemplo {spec.unit}); no se supone ninguna."
        return None, issue("error", "unit", message, path=spec.path, operation_id=op_id)
    if result.notices:
        return None, issue(
            "error", "unit_ambiguous", "; ".join(result.notices), path=spec.path, operation_id=op_id
        )
    if result.unit != spec.unit:
        return None, issue(
            "error",
            "unit_basis",
            f"La unidad {result.unit_original!r} da {result.unit}; el campo está en {spec.unit}. "
            "No se mezclan presión absoluta y manométrica.",
            path=spec.path,
            operation_id=op_id,
        )
    return (round(result.value, 6), raw, result.unit_original), None


def _range(spec: Target, value: float, op_id: str):
    low, high = spec.minimum, spec.maximum
    if low is not None and (value <= low if spec.exclusive_minimum else value < low):
        word = "mayor que" if spec.exclusive_minimum else "al menos"
        return issue(
            "error",
            "range",
            f"{spec.label}: debe ser {word} {low:g} {spec.unit}.",
            path=spec.path,
            operation_id=op_id,
        )
    if high is not None and (value >= high if spec.exclusive_maximum else value > high):
        hint = " Usa 0° en lugar de 360°." if spec.unit == "deg" else ""
        word = "menor que" if spec.exclusive_maximum else "como máximo"
        return issue(
            "error",
            "range",
            f"{spec.label}: debe ser {word} {high:g} {spec.unit}.{hint}",
            path=spec.path,
            operation_id=op_id,
        )
    return None


def order_document(proposal: dict) -> tuple[Document, bytes]:
    """Documento propio de la orden: JSON canónico, almacenado por SHA-256."""
    content = {
        "tipo": "orden_cambio_diseno",
        "schema": "1",
        "aviso": "Orden de diseño confirmada por una persona. No es una lectura del plano "
        "original ni una evidencia de extracción.",
        **{
            k: proposal[k]
            for k in (
                "proposal_id",
                "kind",
                "base",
                "actor",
                "reason",
                "origin",
                "request_text",
                "created_at",
            )
        },
        "operations": proposal["operations"],
    }
    payload = canonical(content).encode()
    identity = f"ORD-{proposal['proposal_id'][:12]}"
    document = Document(
        id=identity,
        filename=f"orden_diseno_{proposal['proposal_id'][:12]}.json",
        revision="1",
        sha256=hashlib.sha256(payload).hexdigest(),
        role="orden_diseno",
    )
    return document, payload


def _design_source(proposal_id, op_id, order_id, text, unit_original):
    return Source(
        document_id=order_id,
        locator=f"Orden de diseño {proposal_id[:8]} · {op_id}",
        confidence=1.0,
        channel="diseno",
        design=DesignRef(proposal_id=proposal_id, operation_id=op_id),
        text_original=text,
        unit_original=unit_original,
    )


def _assign(equipment, path, value, unit, source, reason):
    target = resolve(path, equipment)
    target.value = value
    target.unit = unit
    target.source = source
    target.state = "candidate"
    target.interval = None
    target.alternatives = []
    target.explanation = f"Cambio de diseño: {reason}"


def evaluate(
    base: Revision,
    body: ProposalInput,
    *,
    proposal_id: str,
    label: str,
    created_at: str,
    base_id: str,
    kind: Literal["cambio_diseno", "reversion"] = "cambio_diseno",
) -> tuple[Evaluation, dict]:
    """Valida el lote completo y devuelve la evaluación y el contenido de la orden."""
    equipment = base.equipment
    specs = targets(equipment)
    evaluation = Evaluation(status="ready")
    issues = evaluation.issues
    if body.clarifications:
        for item in body.clarifications:
            issues.append(
                issue(
                    "clarification",
                    "clarification",
                    item.question,
                    operation_id=item.operation_id,
                    options=item.options,
                )
            )
    if not body.operations and not body.clarifications:
        issues.append(issue("error", "empty", "La propuesta no contiene operaciones."))
    resolved, seen_paths = [], {}
    for index, operation in enumerate(body.operations, start=1):
        op_id = operation.id or f"op-{index}"
        spec = specs.get(operation.target)
        if spec is None:
            reason = (
                "La edición geométrica de esta familia aún no está cubierta."
                if equipment.kind != "vertical_vessel" or equipment.lod < 2
                else "No es una operación admitida para este equipo."
            )
            issues.append(
                issue(
                    "error",
                    "unknown_target",
                    f"{operation.target}: {reason}",
                    path=operation.target,
                    operation_id=op_id,
                )
            )
            continue
        if spec.path in seen_paths:
            issues.append(
                issue(
                    "error",
                    "duplicate",
                    f"{spec.label}: el lote ya modifica este campo en {seen_paths[spec.path]}.",
                    path=spec.path,
                    operation_id=op_id,
                )
            )
            continue
        seen_paths[spec.path] = op_id
        datum = operation.datum
        if datum is not None and datum not in spec.datums:
            if datum == AZIMUTH_NORTH:
                message = (
                    "El Norte de planta no está establecido para este equipo (C.4): "
                    "indica el azimut en el convenio interno."
                )
            else:
                allowed = ", ".join(spec.datums) or "ninguna"
                message = f"{spec.label}: referencia {datum!r} no admitida (admitidas: {allowed})."
            issues.append(issue("error", "datum", message, path=spec.path, operation_id=op_id))
            continue
        normalized, problem = _normalize(spec, operation, op_id)
        if problem:
            issues.append(problem)
            continue
        value, text, unit_original = normalized
        if isinstance(value, float):
            problem = _range(spec, value, op_id)
            if problem:
                issues.append(problem)
                continue
        resolved.append((op_id, spec, value, text, unit_original, datum))

    candidate = Revision.model_validate_json(base.model_dump_json())
    new = candidate.equipment
    # Primero el equipo; después las boquillas, cuya referencia puede depender de él.
    resolved.sort(key=lambda item: item[1].group != "equipo")
    pending, order_operations = [], []
    for op_id, spec, value, text, unit_original, datum in resolved:
        before = resolve(spec.path, equipment)
        stored = value
        if spec.derived:
            stored = round(value - new.shell_bottom - new.head_depth.value, 6)
            if stored <= 0:
                issues.append(
                    issue(
                        "error",
                        "derived_range",
                        f"Con faldón {new.shell_bottom:g} mm y fondo {new.head_depth.value:g} mm, "
                        f"una altura total de {value:g} mm deja la virola sin longitud.",
                        path=spec.path,
                        operation_id=op_id,
                    )
                )
                continue
        if datum == DATUM_TANGENT:
            stored = round(value + new.shell_bottom, 6)
        operation = {
            "id": op_id,
            "target": spec.target,
            "path": spec.path,
            "label": spec.label,
            "input": {"text": text, "unit_original": unit_original, "datum": datum},
            "before": {"value": before.value, "unit": before.unit},
            "after": {"value": stored, "unit": spec.unit},
        }
        if spec.derived:
            operation["resolution"] = (
                f"Altura total {value:g} mm → longitud entre tangentes {stored:g} mm "
                f"(faldón {new.shell_bottom:g} + fondo superior {new.head_depth.value:g})."
            )
        if datum == DATUM_TANGENT:
            operation["resolution"] = (
                f"{value:g} mm sobre la tangente inferior = {stored:g} mm sobre el suelo."
            )
        if before.value == stored and before.unit == spec.unit:
            issues.append(
                issue(
                    "warning",
                    "no_change",
                    f"{spec.label}: ya vale {stored:g}.",
                    path=spec.path,
                    operation_id=op_id,
                )
            )
            continue
        order_operations.append(
            {
                **operation,
                "before_source": before.source.model_dump(mode="json"),
                "before_state": before.state,
            }
        )
        evaluation.operations.append(operation)
        pending.append((op_id, spec, stored, text, unit_original))

    proposal_content = {
        "proposal_id": proposal_id,
        "kind": kind,
        "base": {
            "revision_id": base_id,
            "revision": base.revision,
            "input_sha256": base.fingerprint(),
        },
        "actor": body.actor,
        "reason": body.reason,
        "origin": body.origin,
        "request_text": body.request_text,
        "created_at": created_at,
        "operations": order_operations,
    }
    document, _ = order_document(proposal_content)
    for op_id, spec, stored, text, unit_original in pending:
        source = _design_source(proposal_id, op_id, document.id, text, unit_original)
        _assign(new, spec.path, stored, spec.unit, source, body.reason)

    if not evaluation.operations and not evaluation.errors and not body.clarifications:
        issues.append(issue("error", "empty", "La propuesta no cambia ningún valor."))

    _check_nozzles(base, candidate, evaluation)
    _effects(base, candidate, evaluation)
    if base.approval is not None:
        issues.append(
            issue(
                "warning",
                "approval_not_inherited",
                "La revisión base está aprobada; la derivada nace DRAFT y requiere revisión.",
            )
        )
    _publishable(evaluation, candidate, base, document, label, kind, base_id, proposal_id)
    return evaluation, proposal_content


def _check_nozzles(base: Revision, candidate: Revision, evaluation: Evaluation):
    """Informa de cada boquilla que el lote deja fuera de la virola; no la desplaza."""
    old, new = base.equipment, candidate.equipment
    if new.kind != "vertical_vessel" or new.lod < 2:
        return
    touched = {
        op["path"].split(".")[1]
        for op in evaluation.operations
        if op["path"].startswith("nozzles.")
    }
    for nozzle in new.nozzles:
        if nozzle.position is not None:
            continue
        problem = nozzle_misfit(
            nozzle.diameter.value,
            nozzle.elevation.value,
            new.diameter.value,
            new.shell_bottom,
            new.height.value,
        )
        if not problem:
            continue
        previous = next((n for n in old.nozzles if n.id == nozzle.id), None)
        was_ok = previous is not None and not nozzle_misfit(
            previous.diameter.value,
            previous.elevation.value,
            old.diameter.value,
            old.shell_bottom,
            old.height.value,
        )
        radius = nozzle.diameter.value / 2
        low, high = new.shell_bottom + radius, new.shell_bottom + new.height.value - radius
        cause = "su propio cambio" if nozzle.id in touched else "otros cambios del lote"
        evaluation.issues.append(
            issue(
                "error",
                "nozzle_conflict",
                f"{nozzle.id} ({problem}) a {nozzle.elevation.value:g} mm por {cause}: la virola "
                f"admite su eje entre {low:g} y {high:g} mm. No se desplaza automáticamente; "
                f"incluye en el lote su nueva elevación o revisa la dimensión.",
                path=f"nozzles.{nozzle.id}.elevation",
                nozzle_id=nozzle.id,
                allowed=[low, high] if low <= high else None,
                introduced=was_ok,
            )
        )


def _effects(base: Revision, candidate: Revision, evaluation: Evaluation):
    """Piezas que se regeneran y magnitudes derivadas, para mostrarlas antes de confirmar."""
    from trazia.families import parts

    old, new = base.equipment, candidate.equipment
    by_op = {}
    specs = targets(old)
    for operation in evaluation.operations:
        spec = specs[operation["target"]]
        for part in spec.affects:
            ids = (
                [n.id for n in new.nozzles if n.position is None] if part == "*nozzles" else [part]
            )
            for identifier in ids:
                by_op.setdefault(identifier, set()).add(operation["id"])
    try:
        before_parts = {p.id: p for p in parts(old)}
        after_parts = {p.id: p for p in parts(new)}
    except (AttributeError, TypeError, ValueError):
        before_parts = after_parts = {}
    geometry = {
        identifier
        for identifier in before_parts.keys() | after_parts.keys()
        if before_parts.get(identifier) != after_parts.get(identifier)
    }
    for identifier in sorted(by_op.keys() | geometry):
        evaluation.effects.append(
            {
                "part": identifier,
                "geometry_changed": identifier in geometry,
                "operations": sorted(by_op.get(identifier, ())),
            }
        )
    try:
        before_total, after_total = old.total_height, new.total_height
    except (AttributeError, TypeError):
        return
    if before_total != after_total:
        evaluation.derived["total_height"] = {
            "before": before_total,
            "after": after_total,
            "unit": "mm",
        }
        evaluation.issues.append(
            issue(
                "warning",
                "total_height",
                f"La altura total pasa de {before_total:g} a {after_total:g} mm.",
            )
        )
    if old.shell_bottom != new.shell_bottom:
        evaluation.issues.append(
            issue(
                "warning",
                "shell_shift",
                "Cambia la cota de la tangente inferior: las boquillas conservan su elevación "
                "sobre el suelo, pero cambia su posición relativa en la virola.",
            )
        )
    if old.diameter and new.diameter and old.diameter.value != new.diameter.value:
        evaluation.issues.append(
            issue(
                "warning",
                "radial_shift",
                "Cambia el diámetro: las boquillas radiales se regeneran sobre el nuevo radio.",
            )
        )


def evaluate_reversion(
    current: Revision,
    applied: dict,
    snapshot: Revision,
    *,
    proposal_id: str,
    label: str,
    created_at: str,
    base_id: str,
    actor: str,
    reason: str,
) -> tuple[Evaluation, dict]:
    """Revisión compensatoria: restaura cada campo de la orden tal como estaba en la base.

    `applied` es el contenido de la orden aplicada y `snapshot` la base en el momento de
    aplicarla. Si un campo cambió después de aplicar, no se pisa: se informa del conflicto.
    """
    evaluation = Evaluation(status="ready")
    candidate = Revision.model_validate_json(current.model_dump_json())
    order_operations = []
    for operation in applied["operations"]:
        path, op_id = operation["path"], operation["id"]
        now = resolve(path, current.equipment)
        restored = resolve(path, snapshot.equipment)
        design = getattr(now.source, "design", None) if now is not None else None
        if now is None or restored is None:
            evaluation.issues.append(
                issue(
                    "error",
                    "missing_field",
                    f"{path}: el campo ya no existe en esta revisión.",
                    path=path,
                    operation_id=op_id,
                )
            )
            continue
        if design is None or design.proposal_id != applied["proposal_id"]:
            evaluation.issues.append(
                issue(
                    "error",
                    "changed_after_apply",
                    f"{operation['label']}: cambió después de aplicar la orden; revísalo antes de "
                    "deshacer para no perder ese cambio.",
                    path=path,
                    operation_id=op_id,
                )
            )
            continue
        target = resolve(path, candidate.equipment)
        for key in type(restored).model_fields:
            setattr(target, key, getattr(restored, key))
        item = {
            "id": op_id,
            "target": operation["target"],
            "path": path,
            "label": operation["label"],
            "input": {"text": "deshacer", "unit_original": None, "datum": None},
            "before": {"value": now.value, "unit": now.unit},
            "after": {"value": restored.value, "unit": restored.unit},
            "resolution": "Se restaura el valor, la evidencia y el estado de la revisión base.",
        }
        evaluation.operations.append(item)
        order_operations.append(
            {
                **item,
                "before_source": now.source.model_dump(mode="json"),
                "before_state": now.state,
            }
        )
    content = {
        "proposal_id": proposal_id,
        "kind": "reversion",
        "base": {
            "revision_id": base_id,
            "revision": current.revision,
            "input_sha256": current.fingerprint(),
        },
        "reverts": applied["proposal_id"],
        "actor": actor,
        "reason": reason,
        "origin": "deshacer",
        "request_text": None,
        "created_at": created_at,
        "operations": order_operations,
    }
    document, _ = order_document(content)
    _check_nozzles(current, candidate, evaluation)
    _effects(current, candidate, evaluation)
    _publishable(evaluation, candidate, current, document, label, "reversion", base_id, proposal_id)
    return evaluation, content


def _publishable(evaluation, candidate, base, document, label, kind, base_id, proposal_id):
    if not evaluation.errors and evaluation.operations:
        candidate.revision = label
        candidate.approval = None
        candidate.documents = [*candidate.documents, document]
        candidate.derived_from = Derivation(
            kind=kind,
            revision_id=base_id,
            input_sha256=base.fingerprint(),
            proposal_id=proposal_id,
            order_document_id=document.id,
        )
        try:
            evaluation.candidate = Revision.model_validate_json(candidate.model_dump_json())
        except ValidationError as error:
            from trazia.api.validation import issues_for

            for item in issues_for(error):
                evaluation.issues.append(
                    issue("error", "model", item["message"], path=item["path"])
                )
    if evaluation.errors:
        evaluation.status = "invalid"
        evaluation.candidate = None
    elif any(i["severity"] == "clarification" for i in evaluation.issues):
        evaluation.status = "needs_clarification"
        evaluation.candidate = None
