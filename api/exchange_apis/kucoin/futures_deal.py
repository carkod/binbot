import logging
from typing import Type, Union
from time import time

from pybinbot import (
    round_numbers,
    DealType,
    OrderStatus,
    Strategy,
    Status,
)
from databases.tables.bot_table import BotTable, PaperTradingTable
from databases.crud.paper_trading_crud import PaperTradingTableCrud
from databases.crud.bot_crud import BotTableCrud
from databases.crud.symbols_crud import SymbolsCrud
from bots.models import BotModel, OrderModel
from exchange_apis.kucoin.deals.base import KucoinBaseBalance
from kucoin_universal_sdk.model.common import RestError
from kucoin_universal_sdk.generate.futures.order.model_add_order_req import AddOrderReq
from pybinbot import BinbotErrors
from exchange_apis.kucoin.models import FuturesBot

class KucoinFuturesDeal(KucoinBaseBalance):
    """
    Futures-only deal implementation (USDT-M).

    - Position-based (not balance-based)
    - Uses contracts, not qty
    - Orders create / modify positions
    - SL / TP are reduce-only orders
    """

    def __init__(
        self,
        bot: FuturesBot,
        db_table: Type[Union[PaperTradingTable, BotTable]] = BotTable,
    ) -> None:
        super().__init__()
        self.active_bot = bot
        self.db_table = db_table

        if db_table == PaperTradingTable:
            self.controller = PaperTradingTableCrud()
        else:
            self.controller = BotTableCrud()

        self.symbol_info = SymbolsCrud().get_symbol(bot.pair)
        self.price_precision = self.symbol_info.price_precision
        self.symbol = bot.pair

    # ---------------------------------------------------------
    # ENTRY
    # ---------------------------------------------------------

    def open_position(self) -> BotModel:
        """
        Opens a futures LONG position.
        """
        if self.active_bot.status == Status.active:
            return self.active_bot

        if self.active_bot.contracts <= 0:
            raise BinbotErrors("Futures contracts must be > 0")

        try:
            # Explicit leverage (important)
            self.kucoin_api.set_futures_leverage(
                symbol=self.symbol,
                leverage=self.active_bot.leverage,
            )

            order = self.kucoin_api.place_futures_order(
                symbol=self.symbol,
                side=AddOrderReq.SideEnum.BUY,
                order_type="market",
                size=self.active_bot.contracts,
            )

        except RestError as e:
            raise BinbotErrors(
                f"Futures entry failed ({e.response.code}): {e.response.message}"
            )

        if not order:
            raise BinbotErrors("Futures entry returned empty order")

        # Fetch position as source of truth
        position = self.kucoin_api.get_futures_position(self.symbol)

        if not position or float(position.currentQty) == 0:
            raise BinbotErrors("Order placed but no position found")

        entry_price = float(position.avgEntryPrice)
        qty = abs(float(position.currentQty))

        self.active_bot.deal.opening_price = entry_price
        self.active_bot.deal.opening_qty = qty
        self.active_bot.deal.opening_timestamp = int(time() * 1000)
        self.active_bot.deal.current_price = entry_price
        self.active_bot.status = Status.active

        self.active_bot.orders.append(
            OrderModel(
                timestamp=order.created_at,
                order_id=order.id,
                deal_type=DealType.base_order,
                pair=self.symbol,
                order_side=order.side,
                order_type=order.type,
                price=entry_price,
                qty=qty,
                status=OrderStatus.FILLED,
            )
        )

        self.controller.update_logs(
            bot=self.active_bot,
            log_message=f"Futures LONG opened @ {entry_price}",
        )

        self.controller.save(self.active_bot)
        return self.active_bot

    # ---------------------------------------------------------
    # STOP LOSS
    # ---------------------------------------------------------

    def place_stop_loss(self) -> None:
        if self.active_bot.stop_loss <= 0:
            return

        stop_price = round_numbers(
            self.active_bot.deal.opening_price
            * (1 - self.active_bot.stop_loss / 100),
            self.price_precision,
        )

        self.kucoin_api.place_futures_order(
            symbol=self.symbol,
            side="sell",
            order_type="market",
            stop="down",
            stopPrice=stop_price,
            reduceOnly=True,
            size=self.active_bot.deal.opening_qty,
        )

        self.active_bot.deal.stop_loss_price = stop_price

        self.controller.update_logs(
            bot=self.active_bot,
            log_message=f"Stop loss set @ {stop_price}",
        )

    # ---------------------------------------------------------
    # TAKE PROFIT
    # ---------------------------------------------------------

    def place_take_profit(self, price: float) -> None:
        price = round_numbers(price, self.price_precision)

        self.kucoin_api.cancel_all_futures_orders(self.symbol)

        self.kucoin_api.place_futures_order(
            symbol=self.symbol,
            side="sell",
            order_type="limit",
            price=price,
            size=self.active_bot.deal.opening_qty,
            reduceOnly=True,
        )

        self.active_bot.deal.take_profit_price = price

        self.controller.update_logs(
            bot=self.active_bot,
            log_message=f"Take profit set @ {price}",
        )

    # ---------------------------------------------------------
    # DYNAMIC TRAILING (your system controls price updates)
    # ---------------------------------------------------------

    def update_trailing_take_profit(self, new_price: float) -> None:
        self.place_take_profit(new_price)

    # ---------------------------------------------------------
    # CLOSE / PANIC / CRASH RECOVERY
    # ---------------------------------------------------------

    def close_all(self) -> BotModel:
        position = self.kucoin_api.get_futures_position(self.symbol)

        if position and float(position.currentQty) != 0:
            side = "sell" if float(position.currentQty) > 0 else "buy"

            self.kucoin_api.place_futures_order(
                symbol=self.symbol,
                side=side,
                order_type="market",
                size=abs(float(position.currentQty)),
                reduceOnly=True,
            )

        self.active_bot.status = Status.completed
        self.active_bot.deal.closing_timestamp = int(time() * 1000)

        self.controller.update_logs(
            bot=self.active_bot,
            log_message="Futures position closed",
        )

        self.controller.save(self.active_bot)
        return self.active_bot

    # ---------------------------------------------------------
    # SYNC / CRASH RECOVERY
    # ---------------------------------------------------------

    def sync_from_exchange(self) -> None:
        """
        Reconcile bot state with exchange position.
        """
        position = self.kucoin_api.get_futures_position(self.symbol)

        if not position or float(position.currentQty) == 0:
            self.active_bot.status = Status.completed
            return

        self.active_bot.deal.current_price = float(position.markPrice)
        self.active_bot.deal.unrealised_pnl = float(position.unrealisedPnl)
