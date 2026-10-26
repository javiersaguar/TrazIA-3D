import hashlib
from datetime import datetime, timezone

from .model import Approval, Revision, fields


def verify_originals(revision: Revision, originals: dict[str, bytes]) -> list[str]:
    errors = []
    for document in revision.documents:
        data = originals.get(document.id)
        if data is None:
            errors.append(f"{document.id}: falta el original")
        elif hashlib.sha256(data).hexdigest() != document.sha256:
            errors.append(f"{document.id}: el SHA-256 no coincide")
    return errors


def approve(revision: Revision, reviewer: str, originals: dict[str, bytes]) -> Revision:
    if not reviewer.strip() or len(reviewer.strip()) < 2:
        raise ValueError("Indique quién ha revisado los datos")
    errors = verify_originals(revision, originals)
    if errors:
        raise ValueError("; ".join(errors))
    result = revision.model_copy(deep=True)
    result.approval = None
    for field in fields(result.equipment).values():
        field.source.reviewed = True
    result.approval = Approval(
        reviewer=reviewer.strip(),
        timestamp=datetime.now(timezone.utc),
        input_sha256=result.fingerprint(),
    )
    return Revision.model_validate_json(result.model_dump_json())
