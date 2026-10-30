"""Resultados de estudio en el mismo almacén y cola de trabajos."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("jobs", sa.Column("kind", sa.String(), nullable=False, server_default="pipeline"))
    op.add_column("jobs", sa.Column("result_sha256", sa.String(), nullable=True))
    op.add_column("jobs", sa.Column("elapsed_seconds", sa.Float(), nullable=True))


def downgrade():
    op.drop_column("jobs", "elapsed_seconds")
    op.drop_column("jobs", "result_sha256")
    op.drop_column("jobs", "kind")
