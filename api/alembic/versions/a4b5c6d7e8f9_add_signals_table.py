"""Add signals table with JSONB context/bot_params/indicators

Revision ID: a4b5c6d7e8f9
Revises: d8e9f0a1b2c3
Create Date: 2026-05-01 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = "a4b5c6d7e8f9"
down_revision: Union[str, Sequence[str], None] = "d8e9f0a1b2c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "signals",
        sa.Column(
            "id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False
        ),
        sa.Column("algorithm_name", sa.String(length=128), nullable=False),
        sa.Column("symbol", sa.String(length=64), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("autotrade", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("current_regime", sa.String(length=32), nullable=True),
        sa.Column(
            "context", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "bot_params", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "indicators", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
    )
    op.create_index(
        "ix_signals_algorithm_name_generated_at",
        "signals",
        ["algorithm_name", sa.text("generated_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_signals_symbol_generated_at",
        "signals",
        ["symbol", sa.text("generated_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_signals_current_regime", "signals", ["current_regime"], unique=False
    )
    # GIN index lets queries like context @> '{"market_regime": "CHOPPY"}'
    # stay fast as the JSONB payload evolves.
    op.create_index(
        "ix_signals_context_gin",
        "signals",
        ["context"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"context": "jsonb_path_ops"},
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_signals_context_gin", table_name="signals")
    op.drop_index("ix_signals_current_regime", table_name="signals")
    op.drop_index("ix_signals_symbol_generated_at", table_name="signals")
    op.drop_index("ix_signals_algorithm_name_generated_at", table_name="signals")
    op.drop_table("signals")
