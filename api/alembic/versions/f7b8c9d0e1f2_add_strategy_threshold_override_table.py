"""Add strategy_threshold_override table

Revision ID: f7b8c9d0e1f2
Revises: e4a3a439c266
Create Date: 2026-04-25 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "e4a3a439c266"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "strategy_threshold_override",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("strategy_name", sa.String(), nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("buy_trigger_pct", sa.Float(), nullable=False),
        sa.Column("sell_trigger_pct", sa.Float(), nullable=False),
        sa.Column("profile", sa.String(), nullable=False),
        sa.Column("source_provider", sa.String(), nullable=False),
        sa.Column("market_context_timestamp", sa.Float(), nullable=False),
        sa.Column("expires_at", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("raw_model_response", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_strategy_threshold_override_id",
        "strategy_threshold_override",
        ["id"],
        unique=True,
    )
    op.create_index(
        "ix_strategy_threshold_override_strategy_name",
        "strategy_threshold_override",
        ["strategy_name"],
        unique=False,
    )
    op.create_index(
        "ix_strategy_threshold_override_symbol",
        "strategy_threshold_override",
        ["symbol"],
        unique=False,
    )
    op.create_index(
        "ix_strategy_threshold_override_source_provider",
        "strategy_threshold_override",
        ["source_provider"],
        unique=False,
    )
    op.create_index(
        "ix_strategy_threshold_override_expires_at",
        "strategy_threshold_override",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_strategy_threshold_override_expires_at", table_name="strategy_threshold_override")
    op.drop_index("ix_strategy_threshold_override_source_provider", table_name="strategy_threshold_override")
    op.drop_index("ix_strategy_threshold_override_symbol", table_name="strategy_threshold_override")
    op.drop_index("ix_strategy_threshold_override_strategy_name", table_name="strategy_threshold_override")
    op.drop_index("ix_strategy_threshold_override_id", table_name="strategy_threshold_override")
    op.drop_table("strategy_threshold_override")
