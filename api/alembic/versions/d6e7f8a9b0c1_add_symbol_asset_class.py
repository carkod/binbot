"""add symbol asset class

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-08-16 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d6e7f8a9b0c1"
down_revision: str | Sequence[str] | None = "c5d6e7f8a9b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "symbol",
        sa.Column(
            "asset_class",
            sa.String(length=32),
            server_default="",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("symbol", "asset_class")
