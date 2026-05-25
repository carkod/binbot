"""Add grid settings to autotrade table

Revision ID: fdbf67d71448
Revises: 9a40b3d1f7a0
Create Date: 2026-05-25 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fdbf67d71448"
down_revision: Union[str, Sequence[str], None] = "9a40b3d1f7a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in ("autotrade", "test_autotrade"):
        op.add_column(
            table, sa.Column("grid_allocation_pct", sa.Float(), nullable=True)
        )
        op.add_column(
            table, sa.Column("grid_cash_reserve_pct", sa.Float(), nullable=True)
        )
        op.add_column(table, sa.Column("grid_total_margin", sa.Float(), nullable=True))
        op.add_column(table, sa.Column("grid_level_count", sa.Integer(), nullable=True))
        op.add_column(
            table, sa.Column("grid_max_active_ladders", sa.Integer(), nullable=True)
        )
        op.execute(
            f"UPDATE {table} SET "
            "grid_allocation_pct = 1.0, "
            "grid_cash_reserve_pct = 0.0, "
            "grid_total_margin = 1.0, "
            "grid_level_count = 3, "
            "grid_max_active_ladders = 3"
        )


def downgrade() -> None:
    for table in ("autotrade", "test_autotrade"):
        op.drop_column(table, "grid_max_active_ladders")
        op.drop_column(table, "grid_level_count")
        op.drop_column(table, "grid_total_margin")
        op.drop_column(table, "grid_cash_reserve_pct")
        op.drop_column(table, "grid_allocation_pct")
