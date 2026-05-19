"""add grid ladder tables

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-05-18 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    exchange_enum = postgresql.ENUM(
        "BINANCE", "KUCOIN", name="grid_ladder_exchange_enum", create_type=False
    )
    market_type_enum = postgresql.ENUM(
        "SPOT",
        "MARGIN",
        "FUTURES",
        name="grid_ladder_market_type_enum",
        create_type=False,
    )
    status_enum = postgresql.ENUM(
        "pending",
        "active",
        "closing",
        "closed",
        "cancelled",
        "error",
        name="grid_ladder_status_enum",
        create_type=False,
    )
    exchange_enum.create(op.get_bind(), checkfirst=True)
    market_type_enum.create(op.get_bind(), checkfirst=True)
    status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "grid_ladder",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("fiat", sa.String(), nullable=False),
        sa.Column("exchange", exchange_enum, nullable=True),
        sa.Column("market_type", market_type_enum, nullable=True),
        sa.Column("algorithm_name", sa.String(), nullable=False),
        sa.Column("status", status_enum, nullable=False),
        sa.Column("range_low", sa.Float(), nullable=False),
        sa.Column("range_high", sa.Float(), nullable=False),
        sa.Column("grid_step", sa.Float(), nullable=False),
        sa.Column("level_count", sa.Integer(), nullable=False),
        sa.Column("total_margin", sa.Float(), nullable=False),
        sa.Column("reserved_margin", sa.Float(), nullable=False),
        sa.Column("used_margin", sa.Float(), nullable=False),
        sa.Column("realized_pnl", sa.Float(), nullable=False),
        sa.Column("unrealized_pnl", sa.Float(), nullable=False),
        sa.Column("breakout_low", sa.Float(), nullable=False),
        sa.Column("breakout_high", sa.Float(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
        sa.Column("closed_at", sa.Float(), nullable=True),
        sa.Column("context", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_grid_ladder_id", "grid_ladder", ["id"], unique=True)
    op.create_index("ix_grid_ladder_symbol", "grid_ladder", ["symbol"], unique=False)
    op.create_index("ix_grid_ladder_fiat", "grid_ladder", ["fiat"], unique=False)
    op.create_index(
        "ix_grid_ladder_algorithm_name", "grid_ladder", ["algorithm_name"], unique=False
    )
    op.create_index("ix_grid_ladder_status", "grid_ladder", ["status"], unique=False)

    op.create_table(
        "grid_level",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ladder_id", sa.Uuid(), nullable=False),
        sa.Column("level_index", sa.Integer(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("side", sa.String(), nullable=False),
        sa.Column("contracts", sa.Integer(), nullable=False),
        sa.Column("margin_required", sa.Float(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("entry_order_id", sa.String(), nullable=True),
        sa.Column("take_profit_order_id", sa.String(), nullable=True),
        sa.Column("filled_entry_price", sa.Float(), nullable=True),
        sa.Column("filled_entry_qty", sa.Float(), nullable=False),
        sa.Column("take_profit_price", sa.Float(), nullable=True),
        sa.Column("realized_pnl", sa.Float(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["ladder_id"], ["grid_ladder.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_grid_level_id", "grid_level", ["id"], unique=True)
    op.create_index(
        "ix_grid_level_ladder_id", "grid_level", ["ladder_id"], unique=False
    )
    op.create_index(
        "ix_grid_level_level_index", "grid_level", ["level_index"], unique=False
    )
    op.create_index("ix_grid_level_side", "grid_level", ["side"], unique=False)
    op.create_index("ix_grid_level_status", "grid_level", ["status"], unique=False)
    op.create_index(
        "ix_grid_level_entry_order_id", "grid_level", ["entry_order_id"], unique=False
    )
    op.create_index(
        "ix_grid_level_take_profit_order_id",
        "grid_level",
        ["take_profit_order_id"],
        unique=False,
    )

    op.create_table(
        "grid_order",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ladder_id", sa.Uuid(), nullable=False),
        sa.Column("level_id", sa.Uuid(), nullable=True),
        sa.Column("exchange_order_id", sa.String(), nullable=False),
        sa.Column("client_oid", sa.String(), nullable=False),
        sa.Column("order_role", sa.String(), nullable=False),
        sa.Column("side", sa.String(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("contracts", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("filled_qty", sa.Float(), nullable=False),
        sa.Column("filled_price", sa.Float(), nullable=True),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
        sa.Column("raw_response", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["ladder_id"], ["grid_ladder.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["level_id"], ["grid_level.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_grid_order_id", "grid_order", ["id"], unique=True)
    op.create_index(
        "ix_grid_order_ladder_id", "grid_order", ["ladder_id"], unique=False
    )
    op.create_index("ix_grid_order_level_id", "grid_order", ["level_id"], unique=False)
    op.create_index(
        "ix_grid_order_exchange_order_id",
        "grid_order",
        ["exchange_order_id"],
        unique=False,
    )
    op.create_index(
        "ix_grid_order_client_oid", "grid_order", ["client_oid"], unique=False
    )
    op.create_index(
        "ix_grid_order_order_role", "grid_order", ["order_role"], unique=False
    )
    op.create_index("ix_grid_order_side", "grid_order", ["side"], unique=False)
    op.create_index("ix_grid_order_status", "grid_order", ["status"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_grid_order_status", table_name="grid_order")
    op.drop_index("ix_grid_order_side", table_name="grid_order")
    op.drop_index("ix_grid_order_order_role", table_name="grid_order")
    op.drop_index("ix_grid_order_client_oid", table_name="grid_order")
    op.drop_index("ix_grid_order_exchange_order_id", table_name="grid_order")
    op.drop_index("ix_grid_order_level_id", table_name="grid_order")
    op.drop_index("ix_grid_order_ladder_id", table_name="grid_order")
    op.drop_index("ix_grid_order_id", table_name="grid_order")
    op.drop_table("grid_order")

    op.drop_index("ix_grid_level_take_profit_order_id", table_name="grid_level")
    op.drop_index("ix_grid_level_entry_order_id", table_name="grid_level")
    op.drop_index("ix_grid_level_status", table_name="grid_level")
    op.drop_index("ix_grid_level_side", table_name="grid_level")
    op.drop_index("ix_grid_level_level_index", table_name="grid_level")
    op.drop_index("ix_grid_level_ladder_id", table_name="grid_level")
    op.drop_index("ix_grid_level_id", table_name="grid_level")
    op.drop_table("grid_level")

    op.drop_index("ix_grid_ladder_status", table_name="grid_ladder")
    op.drop_index("ix_grid_ladder_algorithm_name", table_name="grid_ladder")
    op.drop_index("ix_grid_ladder_fiat", table_name="grid_ladder")
    op.drop_index("ix_grid_ladder_symbol", table_name="grid_ladder")
    op.drop_index("ix_grid_ladder_id", table_name="grid_ladder")
    op.drop_table("grid_ladder")

    postgresql.ENUM(name="grid_ladder_market_type_enum").drop(
        op.get_bind(), checkfirst=True
    )
    postgresql.ENUM(name="grid_ladder_exchange_enum").drop(
        op.get_bind(), checkfirst=True
    )
    postgresql.ENUM(name="grid_ladder_status_enum").drop(op.get_bind(), checkfirst=True)
