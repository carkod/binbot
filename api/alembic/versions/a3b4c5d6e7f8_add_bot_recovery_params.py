"""add bot recovery params

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-06-06 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a3b4c5d6e7f8"
down_revision: Union[str, Sequence[str], None] = "f2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recovery_bot_table",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reversal_path", sa.String(), nullable=False),
        sa.Column("source_contracts", sa.Float(), nullable=False),
        sa.Column("source_loss_fiat", sa.Float(), nullable=False),
        sa.Column("stop_loss_pct", sa.Float(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_recovery_bot_table_id",
        "recovery_bot_table",
        ["id"],
        unique=True,
    )
    op.add_column("bot", sa.Column("recovery_mode_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_bot_recovery_mode_id_recovery_bot_table",
        "bot",
        "recovery_bot_table",
        ["recovery_mode_id"],
        ["id"],
    )
    op.create_index(
        "ix_bot_recovery_mode_id",
        "bot",
        ["recovery_mode_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_bot_recovery_mode_id", table_name="bot")
    op.drop_constraint(
        "fk_bot_recovery_mode_id_recovery_bot_table",
        "bot",
        type_="foreignkey",
    )
    op.drop_column("bot", "recovery_mode_id")
    op.drop_index("ix_recovery_bot_table_id", table_name="recovery_bot_table")
    op.drop_table("recovery_bot_table")
