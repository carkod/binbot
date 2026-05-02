"""Drop signal_generated_at column from deal

Revision ID: c7d8e9f0a1b2
Revises: b5c6d7e8f9a0
Create Date: 2026-05-02 12:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, Sequence[str], None] = "b5c6d7e8f9a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index("ix_deal_signal_generated_at", table_name="deal")
    op.drop_column("deal", "signal_generated_at")


def downgrade() -> None:
    """Downgrade schema."""
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
