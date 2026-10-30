"""Correcciones humanas y cursor para publicar JSONL sin duplicados tras un fallo."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "corrections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("at", sa.String(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("exported", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_corrections_at", "corrections", ["at"])
    op.create_index("ix_corrections_exported", "corrections", ["exported"])
    op.create_table(
        "correction_cursors",
        sa.Column("key", sa.String(), primary_key=True),
        sa.Column("byte_offset", sa.BigInteger(), nullable=False),
    )


def downgrade():
    op.drop_table("correction_cursors")
    op.drop_table("corrections")
