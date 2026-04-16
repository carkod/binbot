"""Rename Strategy to Position: margin_short -> short in strategy enum

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-15 00:02:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_BOT_TABLES = ["bot", "paper_trading"]


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add the new 'short' value to the existing strategy enum type
    # Must commit before using the new value in DML statements
    op.execute("COMMIT")
    op.execute("ALTER TYPE strategy ADD VALUE IF NOT EXISTS 'short'")
    op.execute("BEGIN")

    # 2. Update existing data: 'margin_short' -> 'short'
    for table in _BOT_TABLES:
        op.execute(
            f"UPDATE {table} SET strategy = 'short' WHERE strategy = 'margin_short'"
        )

    # 3. Rename the PostgreSQL enum type from 'strategy' to 'position'
    op.execute("ALTER TYPE strategy RENAME TO position")


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Rename the PostgreSQL enum type back from 'position' to 'strategy'
    op.execute("ALTER TYPE position RENAME TO strategy")

    # 2. Revert data: 'short' -> 'margin_short'
    for table in _BOT_TABLES:
        op.execute(
            f"UPDATE {table} SET strategy = 'margin_short' WHERE strategy = 'short'"
        )
    # Note: 'short' value remains in the enum type but will not be used after downgrade.
