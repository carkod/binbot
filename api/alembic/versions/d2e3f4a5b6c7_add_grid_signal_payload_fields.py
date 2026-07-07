"""add grid signal payload fields

Revision ID: d2e3f4a5b6c7
Revises: c8d9e0f1a2b3
Create Date: 2026-07-07 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "d2e3f4a5b6c7"
down_revision: Union[str, Sequence[str], None] = "c8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "signals",
        sa.Column(
            "signal_kind",
            sa.String(length=32),
            nullable=False,
            server_default="bot",
        ),
    )
    op.add_column(
        "signals",
        sa.Column(
            "grid_params",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("signals", "grid_params")
    op.drop_column("signals", "signal_kind")
