"""Selecciona solo feedback vigente, con originales, excluyendo equipo y documentos destino."""

import hashlib
import json
from collections import defaultdict

from sqlmodel import Session, select

from trazia.feedback import Feedback
from trazia.model import Revision, fields
from trazia.store import AuditRecord, DocumentRecord, ReviewSessionRecord, RevisionRecord

from .learning import approved_examples


def epoch(session):
    statement = select(RevisionRecord).where(
        RevisionRecord.id.in_(
            select(AuditRecord.revision_id).where(AuditRecord.path == "$approval")
        )
    )
    entries = [
        (r.id, r.version, hashlib.sha256(r.payload.encode()).hexdigest())
        for r in session.exec(statement).all()
    ]
    sessions = [
        (r.id, r.kind, r.finished_at) for r in session.exec(select(ReviewSessionRecord)).all()
    ]
    return hashlib.sha256(json.dumps([sorted(entries), sorted(sessions)]).encode()).hexdigest()


def build_feedback(store, request):
    if request.get("dataset") != "synthetic" or request.get("use_learning") is False:
        return Feedback()
    with Session(store.engine) as session:
        excluded = {session.get(DocumentRecord, key).sha256 for key in request["documents"]}
        records = session.exec(
            select(RevisionRecord).where(
                RevisionRecord.id.in_(
                    select(AuditRecord.revision_id).where(AuditRecord.path == "$approval")
                )
            )
        ).all()
        eligible, channels, allowed_audit_ids = set(), defaultdict(list), set()
        documents_by_equipment = defaultdict(set)
        try:
            for record in records:
                model = Revision.model_validate_json(record.payload)
                same = (record.project_id, record.equipment_id) == (
                    request["project_id"],
                    request["equipment_id"],
                )
                if (
                    same
                    or model.dataset != "synthetic"
                    or model.approval is None
                    or model.approval.input_sha256 != model.fingerprint()
                    or excluded.intersection(d.sha256 for d in model.documents)
                ):
                    continue
                human_sessions = {
                    s.id
                    for s in session.exec(
                        select(ReviewSessionRecord).where(
                            ReviewSessionRecord.revision_id == record.id
                        )
                    ).all()
                    if s.kind == "human" and s.finished_at is not None
                }
                if not human_sessions:
                    continue
                for document in model.documents:
                    store.read(document.sha256)
                eligible.add(record.id)
                documents_by_equipment[(record.project_id, record.equipment_id)].update(
                    document.sha256 for document in model.documents
                )
                audits = session.exec(
                    select(AuditRecord)
                    .where(AuditRecord.revision_id == record.id)
                    .order_by(AuditRecord.id)
                ).all()
                originals = {}
                for audit in audits:
                    if audit.review_session_id not in human_sessions:
                        continue
                    allowed_audit_ids.add(audit.id)
                    if not audit.path.startswith("$") and audit.path not in originals:
                        originals[audit.path] = fields(
                            Revision.model_validate_json(audit.before_json).equipment
                        ).get(audit.path)
                for path, before in originals.items():
                    after = fields(model.equipment).get(path)
                    if (
                        before is None
                        or after is None
                        or not before.source.channel
                        or before.source.channel == "humano"
                        or before.state in ("accepted", "corrected")
                        or after.state not in ("accepted", "corrected")
                        or before.unit != after.unit
                    ):
                        continue
                    from trazia.families.change_detection import equal_value

                    channels[before.source.channel].append(
                        ((record.project_id, record.equipment_id), equal_value(before, after, path))
                    )
            pairs, cursor = [], 0
            while eligible:
                page = approved_examples(store, after=cursor, limit=200)
                for example in page["examples"]:
                    if (
                        example["revision_id"] in eligible
                        and example["audit_id"] in allowed_audit_ids
                    ):
                        pairs.append(
                            {
                                "id": example["id"],
                                "approval_sha256": example["approval"]["input_sha256"],
                                "path": example["path"],
                                "before": {k: example["prediction"][k] for k in ("value", "unit")},
                                "after": {k: example["correction"][k] for k in ("value", "unit")},
                                "evidence_text": example["correction"]["source"].get(
                                    "text_original"
                                ),
                            }
                        )
                cursor = page["next_cursor"]
                if cursor is None:
                    break
        except (OSError, ValueError, KeyError):
            return Feedback(
                verified=False, stats={"reason": "No se verifican los originales del feedback"}
            )
    priorities, stats = channel_priorities(independent_channels(channels, documents_by_equipment))
    return Feedback(tuple(sorted(pairs, key=lambda e: e["id"])[:3]), priorities, stats)


def channel_priorities(channels):
    total = [row for rows in channels.values() for row in rows]
    baseline = (sum(correct for _, correct in total) + 1) / (len(total) + 2)
    priorities, stats = {}, {}
    for channel, rows in channels.items():
        groups = len({identity for identity, _ in rows})
        stats[channel] = {"fields": len(rows), "equipment": groups}
        if groups >= 6 and len(rows) >= 30:
            rate = (sum(correct for _, correct in rows) + 1) / (len(rows) + 2)
            priorities[channel] = round(min(1.15, max(0.85, rate / baseline)), 6)
    return priorities, stats


def independent_channels(channels, documents):
    parents = {equipment: equipment for equipment in documents}

    def root(key):
        while parents[key] != key:
            key = parents[key]
        return key

    owners = {}
    for equipment, hashes in documents.items():
        for digest in hashes:
            if digest in owners:
                parents[root(equipment)] = root(owners[digest])
            else:
                owners[digest] = equipment
    return {
        channel: [(root(equipment), correct) for equipment, correct in rows]
        for channel, rows in channels.items()
    }
