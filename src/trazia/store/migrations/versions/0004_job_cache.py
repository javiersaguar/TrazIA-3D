"""Caché persistida de trabajos por contenido y estrategia."""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "jobs", sa.Column("cache_hit", sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.create_table(
        "job_cache",
        sa.Column("key", sa.String(), primary_key=True),
        sa.Column("result_sha256", sa.String(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
    )


def downgrade():
    op.drop_table("job_cache")
    op.drop_column("jobs", "cache_hit")
