"""Leases para reclamar trabajos de forma atómica y avisos de Lectura."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("jobs", sa.Column("lease_until", sa.Float(), nullable=True))
    op.add_column(
        "jobs", sa.Column("warnings_json", sa.Text(), nullable=False, server_default="[]")
    )


def downgrade():
    op.drop_column("jobs", "warnings_json")
    op.drop_column("jobs", "lease_until")
