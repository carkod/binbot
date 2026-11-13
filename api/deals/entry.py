"""Conditional KuCoin entry workflow."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING

from pybinbot import (
    BinbotErrors,
    BotModel,
    DealType,
    EntryMode,
    Position,
    Status,
    ceil_price_to_tick,
    floor_price_to_tick,
    timestamp,
)
from sqlalchemy import or_
from sqlmodel import col, func, select

from api.databases.crud.autotrade_crud import AutotradeCrud
from api.databases.tables.bot_table import BotTable
from api.databases.tables.deal_table import DealTable
from api.tools.utils import submission_guard
from api.exchange_apis.kucoin.futures.balance import KucoinFuturesBalance
from api.exchange_apis.kucoin.futures.liquidity import load_futures_order_book

if TYPE_CHECKING:
    from api.exchange_apis.kucoin.futures.futures_deal import KucoinPositionDeal


class EntryCapacityError(BinbotErrors):
    """The candidate may retry when an execution slot becomes available."""


class ConditionalEntryDeleted(BinbotErrors):
    """An unfunded or expired candidate was deleted before exchange submission."""


class ConditionalEntry:
    """Arm, trigger or adopt an explicit-price entry without immediate repricing."""

    def __init__(self, execution: KucoinPositionDeal) -> None:
        self.execution = execution

    @contextmanager
    def entry_submission(self, *, check_capacity: bool = True) -> Generator[BotModel]:
        with submission_guard(self.execution.active_bot.id) as (bot, session):
            if (
                check_capacity
                and bot.entry_mode == EntryMode.conditional_limit
                and bot.status == Status.pending
                and bot.deal.entry_client_oid is None
                and not bot.orders
                and timestamp() < bot.entry_expires_at
            ):
                settings = AutotradeCrud(session).get_settings()
                occupied = session.exec(
                    select(func.count())
                    .select_from(BotTable)
                    .join(DealTable)
                    .where(BotTable.id != bot.id)
                    .where(col(BotTable.status).in_((Status.active, Status.pending)))
                    .where(
                        or_(
                            col(BotTable.status) == Status.active,
                            col(BotTable.entry_mode) == EntryMode.immediate,
                            col(DealTable.entry_client_oid).is_not(None),
                            col(DealTable.opening_qty) > 0,
                        )
                    )
                ).one()
                if occupied >= settings.max_active_autotrade_bots:
                    raise EntryCapacityError("Waiting for an available bot slot")
            yield bot

    def arm(self) -> BotModel:
        """Manual activation waits for streaming rather than submitting an order."""
        with self.entry_submission(check_capacity=False) as bot:
            self.execution.active_bot = bot
            if bot.entry_mode != EntryMode.conditional_limit:
                return bot
            if bot.deal.entry_client_oid is None and not bot.orders:
                if timestamp() >= bot.entry_expires_at:
                    self.execution.controller.delete([str(bot.id)])
                    raise ConditionalEntryDeleted(
                        "Conditional entry deleted: expired before activation"
                    )
                bot.status = Status.pending
                bot.add_log("Conditional entry waiting for its limit price")
                self.execution.controller.save(bot)
            return bot

    def submit(self) -> BotModel:
        """Trigger at the explicit limit, retaining identity and expiry on retries."""
        execution = self.execution
        with self.entry_submission() as bot:
            execution.active_bot = bot
            if (
                bot.entry_mode != EntryMode.conditional_limit
                or bot.status != Status.pending
                or any(order.deal_type == DealType.base_order for order in bot.orders)
            ):
                return bot

            client_oid = bot.deal.entry_client_oid
            if client_oid is not None:
                restored = execution.restore_entry_order(client_oid)
                if restored is None:
                    return bot
                order, contracts, limit_price = restored
            else:
                if timestamp() >= bot.entry_expires_at:
                    execution.controller.delete([str(bot.id)])
                    raise ConditionalEntryDeleted(
                        "Conditional entry deleted: expired before submission"
                    )
                if bot.entry_price is None:
                    raise BinbotErrors("Conditional entry requires an entry price")
                tick_size = float(execution.kucoin_symbol_data.tick_size)
                limit_price = (
                    ceil_price_to_tick(bot.entry_price, tick_size)
                    if bot.position == Position.short
                    else floor_price_to_tick(bot.entry_price, tick_size)
                )
                book = load_futures_order_book(
                    execution.kucoin_futures_api, execution.kucoin_symbol
                )
                if not 0 <= timestamp() - book.exchange_timestamp_ms <= 5000:
                    raise BinbotErrors("Conditional entry requires a fresh order book")
                eligible = (
                    book.bids[0].price >= limit_price
                    if bot.position == Position.short
                    else book.asks[0].price <= limit_price
                )
                if not eligible:
                    return bot

                if bot.fiat_order_size <= 0:
                    raise BinbotErrors("Fiat order size must be set.")
                _, _, available_balance = (
                    KucoinFuturesBalance().compute_futures_balance()
                )
                sized_contracts = execution.size_entry_contracts(
                    available_balance, limit_price
                )
                if sized_contracts <= 0:
                    execution.controller.delete([str(bot.id)])
                    raise ConditionalEntryDeleted(
                        "Conditional entry deleted: insufficient futures funds"
                    )
                execution.validate_entry_margin(
                    sized_contracts, limit_price, available_balance
                )
                if timestamp() >= bot.entry_expires_at:
                    execution.controller.delete([str(bot.id)])
                    raise ConditionalEntryDeleted(
                        "Conditional entry deleted: expired before submission"
                    )
                contracts = sized_contracts
                order = execution.submit_entry_order(
                    sized_contracts, limit_price, post_only=False
                )

            return execution.record_entry_order(
                order,
                contracts,
                limit_price,
                pending_entry_minutes=max(
                    0, (bot.entry_expires_at - timestamp()) / 60_000
                ),
            )
