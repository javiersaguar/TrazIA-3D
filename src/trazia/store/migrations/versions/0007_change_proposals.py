"""Propuestas de cambio de diseño y artefactos publicados por revisión (workstream K)."""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "change_proposals",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("revision_id", sa.String(), sa.ForeignKey("revisions.id"), nullable=False),
        sa.Column("base_version", sa.Integer(), nullable=False),
        sa.Column("base_sha256", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("origin", sa.String(), nullable=False),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column("input_json", sa.Text(), nullable=False),
        sa.Column("evaluation_json", sa.Text(), nullable=False),
        sa.Column("content_json", sa.Text(), nullable=False),
        sa.Column("proposal_sha256", sa.String(), nullable=False),
        sa.Column("target_label", sa.String(), nullable=False),
        sa.Column("preview_json", sa.Text(), nullable=True),
        sa.Column("preview_ifc_sha256", sa.String(), nullable=True),
        sa.Column("candidate_json", sa.Text(), nullable=True),
        sa.Column("params_sha256", sa.String(), nullable=True),
        sa.Column("generator_version", sa.String(), nullable=True),
        sa.Column("applied_revision_id", sa.String(), nullable=True),
        sa.Column("reverts_proposal_id", sa.String(), nullable=True),
        sa.Column("reverted_by", sa.String(), nullable=True),
        sa.Column("stale_reason", sa.String(), nullable=True),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
        sa.Column("expires_at", sa.Float(), nullable=False),
    )
    op.create_index("ix_change_proposals_revision_id", "change_proposals", ["revision_id"])
    op.create_index("ix_change_proposals_status", "change_proposals", ["status"])
    op.create_table(
        "revision_artifacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("revision_id", sa.String(), sa.ForeignKey("revisions.id"), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("sha256", sa.String(), nullable=False),
        sa.Column("media_type", sa.String(), nullable=False),
        sa.Column("input_sha256", sa.String(), nullable=False),
        sa.Column("generator_version", sa.String(), nullable=False),
        sa.Column("proposal_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.Float(), nullable=False),
    )
    op.create_index("ix_revision_artifacts_revision_id", "revision_artifacts", ["revision_id"])
    op.create_index("ix_revision_artifacts_sha256", "revision_artifacts", ["sha256"])


def downgrade():
    op.drop_table("revision_artifacts")
    op.drop_table("change_proposals")
