"""Add signal_generated_at column to deal

Revision ID: b5c6d7e8f9a0
Revises: a4b5c6d7e8f9
Create Date: 2026-05-01 00:00:01.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b5c6d7e8f9a0"
down_revision: Union[str, Sequence[str], None] = "a4b5c6d7e8f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "deal",
        sa.Column("signal_generated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_deal_signal_generated_at",
        "deal",
        ["signal_generated_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_deal_signal_generated_at", table_name="deal")
    op.drop_column("deal", "signal_generated_at")
