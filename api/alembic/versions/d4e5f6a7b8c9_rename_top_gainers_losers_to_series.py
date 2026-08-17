"""rename top_gainers_losers table to top_gainers_losers_series

Revision ID: d4e5f6a7b8c9
Revises: c32fcddff2d7
Create Date: 2026-08-17 01:30:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c32fcddff2d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.rename_table("top_gainers_losers", "top_gainers_losers_series")
    op.execute(
        "ALTER TABLE top_gainers_losers_series "
        "RENAME CONSTRAINT top_gainers_losers_pkey TO top_gainers_losers_series_pkey"
    )
    op.execute(
        "ALTER SEQUENCE top_gainers_losers_id_seq "
        "RENAME TO top_gainers_losers_series_id_seq"
    )
    op.execute(
        "ALTER INDEX ix_top_gainers_losers_recorded_at "
        "RENAME TO ix_top_gainers_losers_series_recorded_at"
    )
    op.execute(
        "ALTER INDEX ix_top_gainers_losers_side "
        "RENAME TO ix_top_gainers_losers_series_side"
    )
    op.execute(
        "ALTER INDEX ix_top_gainers_losers_symbol "
        "RENAME TO ix_top_gainers_losers_series_symbol"
    )
    op.execute(
        "ALTER TABLE top_gainers_losers_series "
        "RENAME CONSTRAINT uq_top_gainers_losers_recorded_at_side_rank "
        "TO uq_top_gainers_losers_series_recorded_at_side_rank"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "ALTER TABLE top_gainers_losers_series "
        "RENAME CONSTRAINT uq_top_gainers_losers_series_recorded_at_side_rank "
        "TO uq_top_gainers_losers_recorded_at_side_rank"
    )
    op.execute(
        "ALTER INDEX ix_top_gainers_losers_series_symbol "
        "RENAME TO ix_top_gainers_losers_symbol"
    )
    op.execute(
        "ALTER INDEX ix_top_gainers_losers_series_side "
        "RENAME TO ix_top_gainers_losers_side"
    )
    op.execute(
        "ALTER INDEX ix_top_gainers_losers_series_recorded_at "
        "RENAME TO ix_top_gainers_losers_recorded_at"
    )
    op.execute(
        "ALTER SEQUENCE top_gainers_losers_series_id_seq "
        "RENAME TO top_gainers_losers_id_seq"
    )
    op.execute(
        "ALTER TABLE top_gainers_losers_series "
        "RENAME CONSTRAINT top_gainers_losers_series_pkey TO top_gainers_losers_pkey"
    )
    op.rename_table("top_gainers_losers_series", "top_gainers_losers")
