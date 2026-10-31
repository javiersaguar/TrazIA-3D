"""Sesiones de revisión y deshacer auditado sin cambiar el contrato 0.3."""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "review_sessions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("revision_id", sa.String(), sa.ForeignKey("revisions.id"), nullable=False),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("dataset", sa.String(), nullable=False),
        sa.Column("started_at", sa.Float(), nullable=False),
        sa.Column("finished_at", sa.Float(), nullable=True),
        sa.Column("active_seconds", sa.Float(), nullable=True),
    )
    op.create_index("ix_review_sessions_revision_id", "review_sessions", ["revision_id"])
    op.add_column("audit", sa.Column("review_session_id", sa.String(), nullable=True))
    op.add_column("audit", sa.Column("undo_of", sa.Integer(), nullable=True))
    op.create_index("ix_audit_review_session_id", "audit", ["review_session_id"])


def downgrade():
    op.drop_index("ix_audit_review_session_id", "audit")
    op.drop_column("audit", "undo_of")
    op.drop_column("audit", "review_session_id")
    op.drop_table("review_sessions")
