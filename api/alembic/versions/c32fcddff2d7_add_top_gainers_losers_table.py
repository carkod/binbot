"""add top gainers losers table

Revision ID: c32fcddff2d7
Revises: c5d6e7f8a9b0
Create Date: 2026-08-17 00:58:23.280464

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c32fcddff2d7"
down_revision: Union[str, Sequence[str], None] = "c5d6e7f8a9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "top_gainers_losers",
        sa.Column(
            "id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False
        ),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("side", sa.String(length=8), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=64), nullable=False),
        sa.Column("price_change_percent", sa.Float(), nullable=False),
        sa.UniqueConstraint(
            "recorded_at",
            "side",
            "rank",
            name="uq_top_gainers_losers_recorded_at_side_rank",
        ),
    )
    op.create_index(
        "ix_top_gainers_losers_recorded_at",
        "top_gainers_losers",
        ["recorded_at"],
        unique=False,
    )
    op.create_index(
        "ix_top_gainers_losers_side", "top_gainers_losers", ["side"], unique=False
    )
    op.create_index(
        "ix_top_gainers_losers_symbol", "top_gainers_losers", ["symbol"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_top_gainers_losers_symbol", table_name="top_gainers_losers")
    op.drop_index("ix_top_gainers_losers_side", table_name="top_gainers_losers")
    op.drop_index("ix_top_gainers_losers_recorded_at", table_name="top_gainers_losers")
    op.drop_table("top_gainers_losers")
