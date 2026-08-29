"""add gainers losers series source

Revision ID: e6f7a8b9c0d1
Revises: d4e5f6a7b8c9
Create Date: 2026-08-25 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e6f7a8b9c0d1"
down_revision: str | Sequence[str] | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "top_gainers_losers_series",
        sa.Column(
            "source",
            sa.String(length=32),
            server_default="binance_spot",
            nullable=False,
        ),
    )
    op.alter_column(
        "top_gainers_losers_series",
        "source",
        server_default=None,
    )
    op.create_index(
        "ix_top_gainers_losers_series_source",
        "top_gainers_losers_series",
        ["source"],
        unique=False,
    )
    op.drop_constraint(
        "uq_top_gainers_losers_series_recorded_at_side_rank",
        "top_gainers_losers_series",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_top_gainers_losers_series_source_recorded_at_side_rank",
        "top_gainers_losers_series",
        ["source", "recorded_at", "side", "rank"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_top_gainers_losers_series_source_recorded_at_side_rank",
        "top_gainers_losers_series",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_top_gainers_losers_series_recorded_at_side_rank",
        "top_gainers_losers_series",
        ["recorded_at", "side", "rank"],
    )
    op.drop_index(
        "ix_top_gainers_losers_series_source",
        table_name="top_gainers_losers_series",
    )
    op.drop_column("top_gainers_losers_series", "source")
