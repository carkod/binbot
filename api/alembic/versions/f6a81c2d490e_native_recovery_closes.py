"""Native conditional closes, durable client IDs and linked recovery bots."""

from uuid import uuid4
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "f6a81c2d490e"
down_revision = "e8b2c4d6f0a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    additions: dict[str, list[sa.Column[Any]]] = {
        "deal": [
            sa.Column("conditional_close_order", sa.JSON(), nullable=True),
            sa.Column("entry_client_oid", sa.String(), nullable=True),
            sa.Column(
                "recovery_cancelled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        ],
        "exchange_order": [
            sa.Column("client_oid", sa.String(), nullable=True),
            sa.Column("requested_qty", sa.Float(), nullable=False, server_default="0"),
            sa.Column("stop_price", sa.Float(), nullable=False, server_default="0"),
        ],
        "recovery_bot_table": [
            sa.Column("source_bot_id", sa.Uuid(), nullable=True),
            sa.Column("source_close_order_id", sa.String(), nullable=True),
        ],
    }
    for table, columns in additions.items():
        existing = {column["name"] for column in sa.inspect(bind).get_columns(table)}
        for column in columns:
            if column.name not in existing:
                op.add_column(table, column)

    for table, name, columns, unique in (
        ("exchange_order", "ix_exchange_order_client_oid", ["client_oid"], False),
        (
            "recovery_bot_table",
            "ix_recovery_bot_table_source_bot_id",
            ["source_bot_id"],
            True,
        ),
    ):
        indexes = {index["name"] for index in sa.inspect(bind).get_indexes(table)}
        if name not in indexes:
            op.create_index(name, table, columns, unique=unique)

    foreign_keys = sa.inspect(bind).get_foreign_keys("recovery_bot_table")
    if not any(fk["constrained_columns"] == ["source_bot_id"] for fk in foreign_keys):
        with op.batch_alter_table("recovery_bot_table") as batch:
            batch.create_foreign_key(
                "fk_recovery_source_bot",
                "bot",
                ["source_bot_id"],
                ["id"],
                ondelete="SET NULL",
            )

    metadata = sa.MetaData()
    bot = sa.Table("bot", metadata, autoload_with=bind)
    recovery = sa.Table("recovery_bot_table", metadata, autoload_with=bind)
    orders = sa.Table("exchange_order", metadata, autoload_with=bind)
    if {"status", "deal_type", "price", "qty"} <= set(orders.c.keys()):
        # Legacy pending protection stored the requested size/trigger in the
        # execution columns. Preserve those inputs, leaving fills unconfirmed.
        bind.execute(
            orders.update()
            .where(
                orders.c.client_oid.is_(None),
                orders.c.requested_qty == 0,
                orders.c.status == "NEW",
                orders.c.deal_type.in_(["stop_loss", "trailing_profit"]),
            )
            .values(
                requested_qty=orders.c.qty,
                stop_price=orders.c.price,
                qty=0,
                price=0,
            )
        )
    # Configuration presence is now the sole recovery switch. Sizing wins any
    # legacy conflict; existing source/recovery metadata is otherwise preserved.
    disabled = bot.c.dynamic_position_sizing.is_(True)
    deals = sa.Table("deal", metadata, autoload_with=bind)
    if "deal_id" in bot.c and "position_size_order" in deals.c:
        disabled = disabled | bot.c.deal_id.in_(
            sa.select(deals.c.id).where(
                deals.c.position_size_order.is_not(None),
                sa.cast(deals.c.position_size_order, sa.String()) != "null",
            )
        )
    bind.execute(bot.update().where(disabled).values(recovery_mode_id=None))
    if "margin_short_reversal" in bot.c:
        candidates = (
            bind.execute(
                sa.select(bot.c.id).where(
                    bot.c.margin_short_reversal.is_(True),
                    bot.c.recovery_mode_id.is_(None),
                    ~disabled,
                )
            )
            .scalars()
            .all()
        )
        for bot_id in candidates:
            identifier = uuid4()
            recovery_id = (
                identifier
                if isinstance(recovery.c.id.type, sa.Uuid)
                else identifier.hex
            )
            bind.execute(
                recovery.insert().values(
                    id=recovery_id,
                    reversal_path="source",
                    source_contracts=0,
                    source_loss_fiat=0,
                    stop_loss_pct=0,
                    created_at=0,
                    updated_at=0,
                )
            )
            bind.execute(
                bot.update()
                .where(bot.c.id == bot_id)
                .values(recovery_mode_id=recovery_id)
            )
        with op.batch_alter_table("bot") as batch:
            batch.drop_column("margin_short_reversal")


def downgrade() -> None:
    # Keep durable execution identities and historical parentage on rollback.
    bind = op.get_bind()
    if "margin_short_reversal" not in {
        column["name"] for column in sa.inspect(bind).get_columns("bot")
    }:
        op.add_column(
            "bot",
            sa.Column(
                "margin_short_reversal",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )
    op.execute("UPDATE bot SET margin_short_reversal = (recovery_mode_id IS NOT NULL)")
