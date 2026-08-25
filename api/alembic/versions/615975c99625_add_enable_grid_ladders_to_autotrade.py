"""Add enable_grid_ladders to autotrade table

Revision ID: 615975c99625
Revises: d4e5f6a7b8c9
Create Date: 2026-08-20 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "615975c99625"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in ("autotrade", "test_autotrade"):
        op.add_column(
            table,
            sa.Column("enable_grid_ladders", sa.Boolean(), nullable=True),
        )
        op.execute(f"UPDATE {table} SET enable_grid_ladders = false")


def downgrade() -> None:
    for table in ("autotrade", "test_autotrade"):
        op.drop_column(table, "enable_grid_ladders")
