"""grid ladder: make exchange/market_type NOT NULL

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-05-20 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, Sequence[str], None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Backfill any rows missing the enum value before we tighten the column.
    op.execute("UPDATE grid_ladder SET exchange = 'KUCOIN' WHERE exchange IS NULL")
    op.execute(
        "UPDATE grid_ladder SET market_type = 'FUTURES' WHERE market_type IS NULL"
    )
    op.alter_column("grid_ladder", "exchange", nullable=False)
    op.alter_column("grid_ladder", "market_type", nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("grid_ladder", "exchange", nullable=True)
    op.alter_column("grid_ladder", "market_type", nullable=True)
