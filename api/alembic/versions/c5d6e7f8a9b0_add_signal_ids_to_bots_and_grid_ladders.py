"""add signal ids to bots and grid ladders

Revision ID: c5d6e7f8a9b0
Revises: b1c2d3e4f5a6
Create Date: 2026-08-15 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c5d6e7f8a9b0"
down_revision: str | Sequence[str] | None = "b1c2d3e4f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("bot", sa.Column("signal_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_bot_signal_id_signals",
        "bot",
        "signals",
        ["signal_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_bot_signal_id", "bot", ["signal_id"], unique=False)

    op.add_column("grid_ladder", sa.Column("signal_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_grid_ladder_signal_id_signals",
        "grid_ladder",
        "signals",
        ["signal_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_grid_ladder_signal_id", "grid_ladder", ["signal_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_grid_ladder_signal_id", table_name="grid_ladder")
    op.drop_constraint(
        "fk_grid_ladder_signal_id_signals",
        "grid_ladder",
        type_="foreignkey",
    )
    op.drop_column("grid_ladder", "signal_id")

    op.drop_index("ix_bot_signal_id", table_name="bot")
    op.drop_constraint("fk_bot_signal_id_signals", "bot", type_="foreignkey")
    op.drop_column("bot", "signal_id")
