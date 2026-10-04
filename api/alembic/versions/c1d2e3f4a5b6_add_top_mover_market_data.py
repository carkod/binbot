"""add top mover market data

Revision ID: c1d2e3f4a5b6
Revises: b8c9d0e1f2a3
Create Date: 2026-10-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "c1d2e3f4a5b6"
down_revision: str | Sequence[str] | None = "b8c9d0e1f2a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_NAME = "top_gainers_losers_series"
SYMBOL_TIME_INDEX = "ix_top_gainers_losers_series_source_symbol_recorded_at"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns(TABLE_NAME)}

    if "last_price" not in columns:
        op.add_column(TABLE_NAME, sa.Column("last_price", sa.Float(), nullable=True))
    if "turnover_24h" not in columns:
        op.add_column(TABLE_NAME, sa.Column("turnover_24h", sa.Float(), nullable=True))

    indexes = {index["name"] for index in inspector.get_indexes(TABLE_NAME)}
    if SYMBOL_TIME_INDEX not in indexes:
        op.create_index(
            SYMBOL_TIME_INDEX,
            TABLE_NAME,
            ["source", "symbol", "recorded_at"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes(TABLE_NAME)}
    if SYMBOL_TIME_INDEX in indexes:
        op.drop_index(SYMBOL_TIME_INDEX, table_name=TABLE_NAME)

    columns = {column["name"] for column in inspector.get_columns(TABLE_NAME)}
    if "turnover_24h" in columns:
        op.drop_column(TABLE_NAME, "turnover_24h")
    if "last_price" in columns:
        op.drop_column(TABLE_NAME, "last_price")
