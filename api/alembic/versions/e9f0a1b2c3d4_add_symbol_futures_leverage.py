"""add symbol futures leverage

Revision ID: e9f0a1b2c3d4
Revises: c7d8e9f0a1b2
Create Date: 2026-05-08 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e9f0a1b2c3d4"
down_revision: Union[str, Sequence[str], None] = "c7d8e9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "symbol",
        sa.Column(
            "futures_leverage",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )
    op.create_check_constraint(
        "ck_symbol_futures_leverage_range",
        "symbol",
        "futures_leverage >= 1 AND futures_leverage <= 3",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "ck_symbol_futures_leverage_range",
        "symbol",
        type_="check",
    )
    op.drop_column("symbol", "futures_leverage")
