"""add symbol multiplier

Revision ID: a0e265d5cb35
Revises: d2e3f4a5b6c7
Create Date: 2026-07-26 18:38:14.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a0e265d5cb35"
down_revision: str | Sequence[str] | None = "d2e3f4a5b6c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "symbol_exchange",
        sa.Column(
            "multiplier",
            sa.Float(),
            nullable=False,
            server_default="1.0",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("symbol_exchange", "multiplier")
