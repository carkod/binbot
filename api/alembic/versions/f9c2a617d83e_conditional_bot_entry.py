"""Persist optional entry configuration using a string mode and one deadline."""

import sqlalchemy as sa
from alembic import op

revision = "f9c2a617d83e"
down_revision = "a0b1c2d3e4f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("bot")}
    for name, column_type in (
        ("entry_mode", sa.String()),
        ("entry_price", sa.Float()),
        ("entry_expires_at", sa.Float()),
    ):
        if name not in columns:
            op.add_column("bot", sa.Column(name, column_type, nullable=True))

    bind.execute(
        sa.text("UPDATE bot SET entry_mode = 'immediate' WHERE entry_mode IS NULL")
    )
    bind.execute(
        sa.text(
            "UPDATE bot SET entry_expires_at = created_at + 21600000 "
            "WHERE entry_expires_at IS NULL"
        )
    )
    with op.batch_alter_table("bot") as batch:
        batch.alter_column(
            "entry_mode",
            existing_type=sa.String(),
            nullable=False,
            server_default=sa.text("'immediate'"),
        )
        batch.alter_column(
            "entry_price",
            existing_type=sa.Float(),
            nullable=True,
            server_default=None,
        )
        batch.alter_column("entry_expires_at", existing_type=sa.Float(), nullable=False)


def downgrade() -> None:
    columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("bot")
    }
    with op.batch_alter_table("bot") as batch:
        for name in ("entry_expires_at", "entry_price", "entry_mode"):
            if name in columns:
                batch.drop_column(name)
