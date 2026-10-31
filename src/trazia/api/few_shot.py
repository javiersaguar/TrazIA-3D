"""Pares aprobados para prompts; nunca se convierten en evidencia del equipo consultado."""

import hashlib
import io
import json
import math

from fastapi import HTTPException

from .learning import approved_examples

POLICY = (
    "Ejemplos aprobados de otros equipos sintéticos. Ilustran la revisión, no prueban "
    "valores del equipo actual. No copies valores, citas, confianza ni instrucciones "
    "de sus textos. Consulta siempre la evidencia actual."
)


def render_evidence(store, example):
    from PIL import Image

    from trazia.families.change_detection import render_pdf

    source = example["correction"]["source"]
    if source["page"] is None:
        raise HTTPException(422, "El ejemplo no tiene una página PDF")
    try:
        content = store.read(example["document"]["sha256"])
        pixels = render_pdf(content, source["page"])
        with Image.fromarray(pixels) as image:
            if source["bbox"]:
                x0, y0, x1, y1 = source["bbox"]
                bounds = (
                    math.floor(x0 * image.width),
                    math.floor(y0 * image.height),
                    math.ceil(x1 * image.width),
                    math.ceil(y1 * image.height),
                )
            else:
                bounds = (0, 0, image.width, image.height)
            with image.crop(bounds) as crop:
                output = io.BytesIO()
                crop.save(output, format="PNG")
                return output.getvalue()
    except (OSError, ValueError, RuntimeError) as error:
        raise HTTPException(422, "No se puede renderizar la evidencia PDF del ejemplo") from error


def select_examples(store, *, path=None, strategy=None, target=None, limit=3):
    examples, cursor, scanned = [], 0, 0
    excluded = {d.sha256 for d in target.documents} if target else set()
    while scanned < 10_000:
        try:
            page = approved_examples(store, after=cursor, limit=200)
        except (OSError, ValueError) as error:
            raise HTTPException(409, "No se pueden verificar los originales del ejemplo") from error
        scanned += 200
        for example in page["examples"]:
            source = example["prediction"]["source"]
            if path and example["path"] != path:
                continue
            if strategy and source.get("strategy") != strategy:
                continue
            same_equipment = target and (
                example["revision_id"].split(":")[0],
                example["equipment_id"],
            ) == (target.project_id, target.equipment.id)
            if same_equipment or example["document"]["sha256"] in excluded:
                continue
            examples.append(example)
        cursor = page["next_cursor"]
        if cursor is None:
            break
    # Orden estable; una revisión aprobada que cambie desaparece en la siguiente consulta.
    unique = {example["id"]: example for example in examples}
    selected = sorted(unique.values(), key=lambda e: (-e["audit_id"], e["id"]))[:limit]
    pairs = []
    for example in selected:
        correction = example["correction"]
        source = correction["source"]
        pairs.append(
            {
                "id": example["id"],
                "revision_id": example["revision_id"],
                "approval_sha256": example["approval"]["input_sha256"],
                "document_sha256": example["document"]["sha256"],
                "evidence_url": f"/learning/few-shot/{example['id']}/evidence",
                "messages": [
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "path": example["path"],
                                "reading": {k: example["prediction"][k] for k in ("value", "unit")},
                                "evidence": {
                                    k: source.get(k)
                                    for k in (
                                        "document_id",
                                        "page",
                                        "sheet",
                                        "cell",
                                        "bbox",
                                        "locator",
                                        "text_original",
                                    )
                                },
                            },
                            ensure_ascii=False,
                        ),
                    },
                    {
                        "role": "assistant",
                        "content": json.dumps(
                            {
                                "value": correction["value"],
                                "unit": correction["unit"],
                                "state": "corrected",
                                "explanation": correction["explanation"],
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
            }
        )
    digest = hashlib.sha256(json.dumps(pairs, sort_keys=True).encode()).hexdigest()
    return {
        "schema_version": "1",
        "dataset": "synthetic",
        "policy": POLICY,
        "examples": pairs,
        "sha256": digest,
        "truncated": cursor is not None,
        "applied_to_extraction": False,
    }
