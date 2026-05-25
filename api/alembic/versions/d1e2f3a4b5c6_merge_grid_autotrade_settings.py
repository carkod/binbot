"""merge grid autotrade settings heads

Revision ID: d1e2f3a4b5c6
Revises: c4d5e6f7a8b9, fdbf67d71448
Create Date: 2026-05-25 13:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = (
    "c4d5e6f7a8b9",
    "fdbf67d71448",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


GRID_COLUMNS = (
    ("grid_allocation_pct", sa.Float(), "1.0"),
    ("grid_cash_reserve_pct", sa.Float(), "0.0"),
    ("grid_total_margin", sa.Float(), "1.0"),
    ("grid_level_count", sa.Integer(), "3"),
    ("grid_max_active_ladders", sa.Integer(), "3"),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table in ("autotrade", "test_autotrade"):
        existing_columns = {column["name"] for column in inspector.get_columns(table)}

        for column_name, column_type, _ in GRID_COLUMNS:
            if column_name not in existing_columns:
                op.add_column(table, sa.Column(column_name, column_type, nullable=True))

        assignments = ", ".join(
            f"{column_name} = COALESCE({column_name}, {default_value})"
            for column_name, _, default_value in GRID_COLUMNS
        )
        op.execute(f"UPDATE {table} SET {assignments}")


def downgrade() -> None:
    pass
