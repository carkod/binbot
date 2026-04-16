"""Rename strategy columns to position

Revision ID: e4a3a439c266
Revises: c3d4e5f6a7b8
Create Date: 2026-04-16 21:20:13.417329

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e4a3a439c266"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_BOT_TABLES = ("bot", "paper_trading")


def upgrade() -> None:
    """Upgrade schema."""
    for table in _BOT_TABLES:
        op.alter_column(table, "strategy", new_column_name="position")


def downgrade() -> None:
    """Downgrade schema."""
    for table in _BOT_TABLES:
        op.alter_column(table, "position", new_column_name="strategy")
