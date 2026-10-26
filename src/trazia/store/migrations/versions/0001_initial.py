"""Esquema inicial; no depende de los modelos que puedan cambiar en el futuro."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "documents",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("revision", sa.String(), nullable=False),
        sa.Column("sha256", sa.String(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
    )
    op.create_index("ix_documents_sha256", "documents", ["sha256"])
    op.create_table(
        "revisions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("equipment_id", sa.String(), nullable=False),
        sa.Column("tag", sa.String(), nullable=False),
        sa.Column("revision", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
    )
    for name in ("project_id", "tag"):
        op.create_index(f"ix_revisions_{name}", "revisions", [name])
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tag", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("request_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("run_json", sa.Text()),
        sa.Column("revision_id", sa.String()),
    )
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.String(), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("stage", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("file", sa.String(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
    )
    op.create_index("ix_events_job_id", "events", ["job_id"])
    op.create_table(
        "idempotency",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("request_sha256", sa.String(), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.Float(), nullable=False),
    )
    op.create_table(
        "audit",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("revision_id", sa.String(), sa.ForeignKey("revisions.id"), nullable=False),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column("before_json", sa.Text(), nullable=False),
        sa.Column("after_json", sa.Text(), nullable=False),
        sa.Column("seconds", sa.Float()),
        sa.Column("created_at", sa.Float(), nullable=False),
    )
    op.create_index("ix_audit_revision_id", "audit", ["revision_id"])


def downgrade():
    for table in ("audit", "idempotency", "events", "jobs", "revisions", "documents"):
        op.drop_table(table)
