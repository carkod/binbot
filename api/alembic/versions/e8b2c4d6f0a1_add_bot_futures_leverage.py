"""Persist per-bot futures leverage, preserving legacy symbol settings."""

import sqlalchemy as sa
from alembic import op

revision = "e8b2c4d6f0a1"
down_revision = "d7e8f9a0b1c2"
branch_labels = None
depends_on = None

CONSTRAINT_NAME = "ck_bot_futures_leverage_range"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("bot")}
    if "futures_leverage" not in columns:
        # Leave legacy rows null until their symbol leverage is copied below.
        op.add_column("bot", sa.Column("futures_leverage", sa.Integer(), nullable=True))

    bot = sa.table(
        "bot",
        sa.column("pair"),
        sa.column("market_type"),
        sa.column("futures_leverage", sa.Integer()),
    )
    legacy_leverage = sa.literal(1)
    if "symbol" in inspector.get_table_names() and "futures_leverage" in {
        column["name"] for column in inspector.get_columns("symbol")
    }:
        symbol = sa.table("symbol", sa.column("id"), sa.column("futures_leverage"))
        legacy_leverage = sa.case(
            (
                bot.c.market_type == "FUTURES",
                sa.func.coalesce(
                    sa.select(symbol.c.futures_leverage)
                    .where(symbol.c.id == bot.c.pair)
                    .scalar_subquery(),
                    1,
                ),
            ),
            else_=1,
        )
    # Replay also repairs a partially migrated nullable column without
    # overwriting leverage already chosen for individual bots.
    bind.execute(
        bot.update()
        .where(bot.c.futures_leverage.is_(None))
        .values(futures_leverage=legacy_leverage)
    )

    constraints = {
        constraint["name"]
        for constraint in sa.inspect(bind).get_check_constraints("bot")
    }
    with op.batch_alter_table("bot") as batch:
        batch.alter_column(
            "futures_leverage",
            existing_type=sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        )
        if CONSTRAINT_NAME not in constraints:
            batch.create_check_constraint(
                CONSTRAINT_NAME, "futures_leverage >= 1 AND futures_leverage <= 5"
            )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("bot")}
    if "futures_leverage" not in columns:
        return
    constraints = {
        constraint["name"] for constraint in inspector.get_check_constraints("bot")
    }
    with op.batch_alter_table("bot") as batch:
        if CONSTRAINT_NAME in constraints:
            batch.drop_constraint(CONSTRAINT_NAME, type_="check")
        batch.drop_column("futures_leverage")
