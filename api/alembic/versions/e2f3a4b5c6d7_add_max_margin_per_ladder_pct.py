"""Add max margin per ladder pct to autotrade settings

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-05-26 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e2f3a4b5c6d7"
down_revision: Union[str, Sequence[str], None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table in ("autotrade", "test_autotrade"):
        existing_columns = {column["name"] for column in inspector.get_columns(table)}
        if "max_margin_per_ladder_pct" not in existing_columns:
            op.add_column(
                table,
                sa.Column("max_margin_per_ladder_pct", sa.Float(), nullable=True),
            )
        op.execute(
            f"UPDATE {table} "
            "SET max_margin_per_ladder_pct = "
            "COALESCE(max_margin_per_ladder_pct, 0.25)"
        )


def downgrade() -> None:
    for table in ("autotrade", "test_autotrade"):
        op.drop_column(table, "max_margin_per_ladder_pct")
