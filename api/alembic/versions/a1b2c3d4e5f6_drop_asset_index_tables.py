"""Drop asset_index and symbol_index_link tables

Revision ID: a1b2c3d4e5f6
Revises: fdbf67d71448
Create Date: 2026-07-01 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "fdbf67d71448"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("symbol_index_link")
    op.drop_table("asset_index")


def downgrade() -> None:
    op.create_table(
        "asset_index",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, server_default=""),
    )
    op.create_table(
        "symbol_index_link",
        sa.Column(
            "symbol_id",
            sa.String(),
            sa.ForeignKey("symbol.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "asset_index_id",
            sa.String(),
            sa.ForeignKey("asset_index.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
