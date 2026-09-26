"""baseline

Revision ID: 5be29ddb30b9
Revises:
Create Date: 2025-12-10 13:53:32.736162

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5be29ddb30b9"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _baseline_metadata() -> sa.MetaData:
    """Return the physical schema that existed when Alembic was introduced."""
    metadata = sa.MetaData()

    user_roles = sa.Enum("user", "admin", "customer", name="userroles")
    order_type = sa.Enum(
        "limit",
        "market",
        "stop_loss",
        "stop_loss_limit",
        "take_profit",
        "take_profit_limit",
        "limit_maker",
        name="ordertype",
    )
    order_status = sa.Enum(
        "NEW",
        "PARTIALLY_FILLED",
        "FILLED",
        "CANCELED",
        "REJECTED",
        "EXPIRED",
        name="orderstatus",
    )
    deal_type = sa.Enum(
        "base_order",
        "take_profit",
        "stop_loss",
        "short_sell",
        "short_buy",
        "margin_short",
        "panic_close",
        "trailling_profit",
        "conversion",
        name="dealtype",
    )
    quote_assets = sa.Enum("USDT", "USDC", "BTC", "ETH", "TRY", name="quoteassets")
    kline_intervals = sa.Enum(
        "one_minute",
        "three_minutes",
        "five_minutes",
        "fifteen_minutes",
        "thirty_minutes",
        "one_hour",
        "two_hours",
        "four_hours",
        "six_hours",
        "eight_hours",
        "twelve_hours",
        "one_day",
        "three_days",
        "one_week",
        "one_month",
        name="binanceklineintervals",
    )
    close_conditions = sa.Enum(
        "dynamic_trailling",
        "timestamp",
        "market_reversal",
        name="closeconditions",
    )
    bot_status = sa.Enum(
        "all", "inactive", "active", "completed", "error", name="status"
    )
    strategy = sa.Enum("long", "margin_short", name="strategy")
    exchange_id = sa.Enum("KUCOIN", "BINANCE", name="exchangeid")
    exchange_link_id = sa.Enum("KUCOIN", "BINANCE", name="exchange_id_enum")

    sa.Table(
        "binbot_user",
        metadata,
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("role", user_roles, nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("password", sa.String(length=40), nullable=False),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
        sa.Index("ix_binbot_user_id", "id", unique=True),
        sa.Index("ix_binbot_user_email", "email", unique=True),
    )

    sa.Table(
        "deal",
        metadata,
        sa.Column("base_order_size", sa.Float(), nullable=True),
        sa.Column("current_price", sa.Float(), nullable=False),
        sa.Column("take_profit_price", sa.Float(), nullable=False),
        sa.Column("trailling_stop_loss_price", sa.Float(), nullable=False),
        sa.Column("trailling_profit_price", sa.Float(), nullable=False),
        sa.Column("stop_loss_price", sa.Float(), nullable=False),
        sa.Column("total_interests", sa.Float(), nullable=True),
        sa.Column("total_commissions", sa.Float(), nullable=True),
        sa.Column("margin_loan_id", sa.BigInteger(), nullable=True),
        sa.Column("margin_repay_id", sa.BigInteger(), nullable=True),
        sa.Column("opening_price", sa.Float(), nullable=False),
        sa.Column("opening_qty", sa.Float(), nullable=False),
        sa.Column("opening_timestamp", sa.BigInteger(), nullable=True),
        sa.Column("closing_price", sa.Float(), nullable=False),
        sa.Column("closing_qty", sa.Float(), nullable=False),
        sa.Column("closing_timestamp", sa.BigInteger(), nullable=True),
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Index("ix_deal_id", "id", unique=True),
    )

    for table_name in ("autotrade", "test_autotrade"):
        sa.Table(
            table_name,
            metadata,
            sa.Column("autotrade", sa.Boolean(), nullable=False),
            sa.Column("updated_at", sa.Float(), nullable=False),
            sa.Column("base_order_size", sa.Float(), nullable=False),
            sa.Column("trailling", sa.Boolean(), nullable=False),
            sa.Column("trailling_deviation", sa.Float(), nullable=False),
            sa.Column("trailling_profit", sa.Float(), nullable=False),
            sa.Column("stop_loss", sa.Float(), nullable=False),
            sa.Column("take_profit", sa.Float(), nullable=False),
            sa.Column("fiat", sa.String(), nullable=False),
            sa.Column("max_request", sa.Integer(), nullable=False),
            sa.Column("telegram_signals", sa.Boolean(), nullable=False),
            sa.Column("max_active_autotrade_bots", sa.Integer(), nullable=False),
            sa.Column("autoswitch", sa.Boolean(), nullable=False),
            sa.Column("exchange_id", exchange_id, nullable=False),
            sa.Column("id", sa.String(), primary_key=True, nullable=False, unique=True),
            sa.Column("candlestick_interval", kline_intervals, nullable=True),
            sa.Column("close_condition", close_conditions, nullable=True),
        )

    sa.Table(
        "consolidated_balances",
        metadata,
        sa.Column(
            "id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False
        ),
        sa.Column("estimated_total_fiat", sa.Float(), nullable=False),
        sa.Index("ix_consolidated_balances_id", "id"),
    )
    sa.Table(
        "staging_consolidated_balances",
        metadata,
        sa.Column(
            "id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False
        ),
        sa.Column("estimated_total_fiat", sa.Float(), nullable=False),
        sa.Index("ix_staging_consolidated_balances_id", "id"),
    )
    sa.Table(
        "asset_index",
        metadata,
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
    )
    sa.Table(
        "symbol",
        metadata,
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("blacklist_reason", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("quote_asset", sa.String(), nullable=False),
        sa.Column("base_asset", sa.String(), nullable=False),
        sa.Column("cooldown", sa.Integer(), nullable=False),
        sa.Column("cooldown_start_ts", sa.BigInteger(), nullable=False),
    )

    def add_bot_table(table_name: str) -> None:
        sa.Table(
            table_name,
            metadata,
            sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
            sa.Column("pair", sa.String(), nullable=False),
            sa.Column("fiat", sa.String(), nullable=False),
            sa.Column("quote_asset", quote_assets, nullable=False),
            sa.Column("fiat_order_size", sa.Float(), nullable=False),
            sa.Column("candlestick_interval", kline_intervals, nullable=True),
            sa.Column("close_condition", close_conditions, nullable=True),
            sa.Column("cooldown", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.Float(), nullable=False),
            sa.Column("updated_at", sa.Float(), nullable=False),
            sa.Column("dynamic_trailling", sa.Boolean(), nullable=False),
            sa.Column("logs", sa.JSON(), nullable=True),
            sa.Column("mode", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("status", bot_status, nullable=True),
            sa.Column("stop_loss", sa.Float(), nullable=False),
            sa.Column("margin_short_reversal", sa.Boolean(), nullable=False),
            sa.Column("take_profit", sa.Float(), nullable=False),
            sa.Column("trailling", sa.Boolean(), nullable=False),
            sa.Column("trailling_deviation", sa.Float(), nullable=False),
            sa.Column("trailling_profit", sa.Float(), nullable=False),
            sa.Column("strategy", strategy, nullable=True),
            sa.Column(
                "deal_id",
                sa.UUID(),
                sa.ForeignKey("deal.id", ondelete="CASCADE"),
                nullable=True,
            ),
            sa.Index(f"ix_{table_name}_id", "id", unique=True),
            sa.Index(f"ix_{table_name}_pair", "pair"),
            sa.Index(f"ix_{table_name}_fiat", "fiat"),
            sa.Index(f"ix_{table_name}_deal_id", "deal_id"),
        )

    add_bot_table("bot")
    add_bot_table("paper_trading")

    def add_balance_table(table_name: str, parent_table: str) -> None:
        sa.Table(
            table_name,
            metadata,
            sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
            sa.Column("timestamp", sa.BigInteger(), nullable=True),
            sa.Column("asset", sa.String(), nullable=False),
            sa.Column("quantity", sa.Float(), nullable=True),
            sa.Column(
                "consolidated_balances_id",
                sa.BigInteger(),
                sa.ForeignKey(f"{parent_table}.id", ondelete="CASCADE"),
                nullable=True,
            ),
            sa.Index(f"ix_{table_name}_id", "id", unique=True),
            sa.Index(f"ix_{table_name}_timestamp", "timestamp"),
            sa.Index(f"ix_{table_name}_asset", "asset"),
        )

    add_balance_table("balances", "consolidated_balances")
    add_balance_table("staging_balances", "staging_consolidated_balances")

    sa.Table(
        "symbol_index_link",
        metadata,
        sa.Column(
            "symbol_id",
            sa.String(),
            sa.ForeignKey("symbol.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "asset_index_id",
            sa.String(),
            sa.ForeignKey("asset_index.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
    )
    sa.Table(
        "symbol_exchange",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("exchange_id", exchange_link_id, nullable=True),
        sa.Column(
            "symbol_id",
            sa.String(),
            sa.ForeignKey("symbol.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("min_notional", sa.Float(), nullable=True),
        sa.Column("is_margin_trading_allowed", sa.Boolean(), nullable=False),
        sa.Column("price_precision", sa.Integer(), nullable=False),
        sa.Column("qty_precision", sa.Integer(), nullable=False),
    )

    def add_order_table(table_name: str, owner_table: str, owner_column: str) -> None:
        sa.Table(
            table_name,
            metadata,
            sa.Column("order_type", order_type, nullable=False),
            sa.Column("time_in_force", sa.String(), nullable=False),
            sa.Column("order_id", sa.Integer(), nullable=False),
            sa.Column("order_side", sa.String(), nullable=False),
            sa.Column("pair", sa.String(), nullable=False),
            sa.Column("qty", sa.Float(), nullable=False),
            sa.Column("status", order_status, nullable=False),
            sa.Column("price", sa.Float(), nullable=False),
            sa.Column("deal_type", deal_type, nullable=False),
            sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
            sa.Column("timestamp", sa.BigInteger(), nullable=True),
            sa.Column(
                owner_column,
                sa.UUID(),
                sa.ForeignKey(f"{owner_table}.id", ondelete="CASCADE"),
                nullable=True,
            ),
            sa.Index(f"ix_{table_name}_id", "id", unique=True),
            sa.Index(f"ix_{table_name}_{owner_column}", owner_column),
        )

    add_order_table("exchange_order", "bot", "bot_id")
    add_order_table("fake_order", "paper_trading", "paper_trading_id")

    return metadata


def upgrade() -> None:
    """Create the legacy schema that the later revisions migrate forward."""
    _baseline_metadata().create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    """Keep the legacy schema adopted by this baseline intact."""
    pass
