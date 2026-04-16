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


def _rename_column_if_exists(
    conn: sa.engine.Connection,
    table: str,
    old_col: str,
    new_col: str,
) -> None:
    """Rename a column only when the old name exists and the new one does not."""
    old_exists = bool(
        conn.execute(
            sa.text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = current_schema()
                      AND table_name = :table
                      AND column_name = :column
                )
                """
            ),
            {"table": table, "column": old_col},
        ).scalar()
    )
    new_exists = bool(
        conn.execute(
            sa.text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = current_schema()
                      AND table_name = :table
                      AND column_name = :column
                )
                """
            ),
            {"table": table, "column": new_col},
        ).scalar()
    )

    if old_exists and not new_exists:
        op.alter_column(
            table_name=table,
            column_name=old_col,
            new_column_name=new_col,
        )


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()

    # 1. Rename trailling columns in bot and paper_trading tables
    for table in ("bot", "paper_trading"):
        _rename_column_if_exists(conn, table, "trailling", "trailing")
        _rename_column_if_exists(
            conn, table, "trailling_deviation", "trailing_deviation"
        )
        _rename_column_if_exists(conn, table, "trailling_profit", "trailing_profit")
        _rename_column_if_exists(conn, table, "dynamic_trailling", "dynamic_trailing")

    # 2. Rename trailling columns in autotrade settings tables
    for table in ("autotrade", "test_autotrade"):
        _rename_column_if_exists(conn, table, "trailling", "trailing")
        _rename_column_if_exists(
            conn, table, "trailling_deviation", "trailing_deviation"
        )
        _rename_column_if_exists(conn, table, "trailling_profit", "trailing_profit")

    # 3. Rename trailling price columns in deal table
    _rename_column_if_exists(
        conn, "deal", "trailling_stop_loss_price", "trailing_stop_loss_price"
    )
    _rename_column_if_exists(
        conn, "deal", "trailling_profit_price", "trailing_profit_price"
    )

    # 4. Rename 'dynamic_trailling' → 'dynamic_trailing' in closeconditions enum
    # PostgreSQL requires the enum value addition to be committed before it can be used.
    op.execute("COMMIT")
    op.execute("ALTER TYPE closeconditions ADD VALUE IF NOT EXISTS 'dynamic_trailing'")
    op.execute("BEGIN")
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
    # Same PostgreSQL enum rule applies here as well.
    op.execute("COMMIT")
    op.execute("ALTER TYPE dealtype ADD VALUE IF NOT EXISTS 'trailing_profit'")
    op.execute("BEGIN")
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
    conn = op.get_bind()

    # 1. Revert trailling columns in bot and paper_trading tables
    for table in ("bot", "paper_trading"):
        _rename_column_if_exists(conn, table, "trailing", "trailling")
        _rename_column_if_exists(
            conn, table, "trailing_deviation", "trailling_deviation"
        )
        _rename_column_if_exists(conn, table, "trailing_profit", "trailling_profit")
        _rename_column_if_exists(conn, table, "dynamic_trailing", "dynamic_trailling")

    # 2. Revert trailling columns in autotrade settings tables
    for table in ("autotrade", "test_autotrade"):
        _rename_column_if_exists(conn, table, "trailing", "trailling")
        _rename_column_if_exists(
            conn, table, "trailing_deviation", "trailling_deviation"
        )
        _rename_column_if_exists(conn, table, "trailing_profit", "trailling_profit")

    # 3. Revert trailling price columns in deal table
    _rename_column_if_exists(
        conn, "deal", "trailing_stop_loss_price", "trailling_stop_loss_price"
    )
    _rename_column_if_exists(
        conn, "deal", "trailing_profit_price", "trailling_profit_price"
    )

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
