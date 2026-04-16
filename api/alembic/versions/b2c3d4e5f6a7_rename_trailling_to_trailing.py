"""Rename trailling to trailing in columns and enum values

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-15 00:01:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables that have trailling/dynamic_trailling/trailling_deviation/trailling_profit columns
_BOT_TABLES = ["bot", "paper_trading"]
_SETTINGS_TABLES = ["autotrade", "test_autotrade"]


def _rename_column_if_exists(table: str, old_col: str, new_col: str) -> None:
    """Rename a column only if it exists (idempotent helper)."""
    op.execute(sa.text(f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = '{table}' AND column_name = '{old_col}'
            ) THEN
                ALTER TABLE "{table}" RENAME COLUMN "{old_col}" TO "{new_col}";
            END IF;
        END $$;
    """))


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Rename trailling columns in bot and paper_trading tables
    for table in _BOT_TABLES:
        _rename_column_if_exists(table, "trailling", "trailing")
        _rename_column_if_exists(table, "trailling_deviation", "trailing_deviation")
        _rename_column_if_exists(table, "trailling_profit", "trailing_profit")
        _rename_column_if_exists(table, "dynamic_trailling", "dynamic_trailing")

    # 2. Rename trailling columns in autotrade settings tables
    for table in _SETTINGS_TABLES:
        _rename_column_if_exists(table, "trailling", "trailing")
        _rename_column_if_exists(table, "trailling_deviation", "trailing_deviation")
        _rename_column_if_exists(table, "trailling_profit", "trailing_profit")

    # 3. Rename trailling price columns in deal table
    _rename_column_if_exists("deal", "trailling_stop_loss_price", "trailing_stop_loss_price")
    _rename_column_if_exists("deal", "trailling_profit_price", "trailing_profit_price")

    # 4. Rename 'dynamic_trailling' → 'dynamic_trailing' in closeconditions enum
    op.execute(
        "ALTER TYPE closeconditions ADD VALUE IF NOT EXISTS 'dynamic_trailing'"
    )
    op.execute(
        "UPDATE bot SET close_condition = 'dynamic_trailing' "
        "WHERE close_condition = 'dynamic_trailling'"
    )
    op.execute(
        "UPDATE paper_trading SET close_condition = 'dynamic_trailing' "
        "WHERE close_condition = 'dynamic_trailling'"
    )
    op.execute(
        "UPDATE autotrade SET close_condition = 'dynamic_trailing' "
        "WHERE close_condition = 'dynamic_trailling'"
    )
    op.execute(
        "UPDATE test_autotrade SET close_condition = 'dynamic_trailing' "
        "WHERE close_condition = 'dynamic_trailling'"
    )

    # 5. Rename 'trailling_profit' → 'trailing_profit' in dealtype enum
    op.execute(
        "ALTER TYPE dealtype ADD VALUE IF NOT EXISTS 'trailing_profit'"
    )
    op.execute(
        "UPDATE exchange_order SET deal_type = 'trailing_profit' "
        "WHERE deal_type = 'trailling_profit'"
    )
    op.execute(
        "UPDATE fake_order SET deal_type = 'trailing_profit' "
        "WHERE deal_type = 'trailling_profit'"
    )


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Revert trailling columns in bot and paper_trading tables
    for table in _BOT_TABLES:
        _rename_column_if_exists(table, "trailing", "trailling")
        _rename_column_if_exists(table, "trailing_deviation", "trailling_deviation")
        _rename_column_if_exists(table, "trailing_profit", "trailling_profit")
        _rename_column_if_exists(table, "dynamic_trailing", "dynamic_trailling")

    # 2. Revert trailling columns in autotrade settings tables
    for table in _SETTINGS_TABLES:
        _rename_column_if_exists(table, "trailing", "trailling")
        _rename_column_if_exists(table, "trailing_deviation", "trailling_deviation")
        _rename_column_if_exists(table, "trailing_profit", "trailling_profit")

    # 3. Revert trailling price columns in deal table
    _rename_column_if_exists("deal", "trailing_stop_loss_price", "trailling_stop_loss_price")
    _rename_column_if_exists("deal", "trailing_profit_price", "trailling_profit_price")

    # 4. Revert close_condition enum values
    op.execute(
        "UPDATE bot SET close_condition = 'dynamic_trailling' "
        "WHERE close_condition = 'dynamic_trailing'"
    )
    op.execute(
        "UPDATE paper_trading SET close_condition = 'dynamic_trailling' "
        "WHERE close_condition = 'dynamic_trailing'"
    )
    op.execute(
        "UPDATE autotrade SET close_condition = 'dynamic_trailling' "
        "WHERE close_condition = 'dynamic_trailing'"
    )
    op.execute(
        "UPDATE test_autotrade SET close_condition = 'dynamic_trailling' "
        "WHERE close_condition = 'dynamic_trailing'"
    )

    # 5. Revert deal_type enum values
    op.execute(
        "UPDATE exchange_order SET deal_type = 'trailling_profit' "
        "WHERE deal_type = 'trailing_profit'"
    )
    op.execute(
        "UPDATE fake_order SET deal_type = 'trailling_profit' "
        "WHERE deal_type = 'trailing_profit'"
    )

