from typing import Type
from datetime import datetime
from databases.tables.bot_table import BotTable, PaperTradingTable
from exchange_apis.kucoin.futures.position_market import PositionMarket
from streaming.base import BaseStreaming
from bots.models import BotModel
from pybinbot import (
    OrderStatus,
    Status,
    ExchangeId,
    round_numbers,
    convert_to_kucoin_symbol,
)
from tools.enum_definitions import DealType


class SpotPosition(PositionMarket):
    def __init__(
        self,
        base_streaming: BaseStreaming,
        bot: BotModel,
        price_precision: int,
        qty_precision: int,
        db_table: Type[BotTable] | Type[PaperTradingTable],
    ):
        super().__init__(
            base_streaming=base_streaming,
            bot=bot,
            api=base_streaming.kucoin_futures_api,
            symbol=bot.pair,
            db_table=db_table,
        )
        self.kucoin_benchmark_symbol = "USDT-BTC"
        self.api = self.base_streaming.kucoin_api
        self.price_precision = price_precision
        self.qty_precision = qty_precision

    def order_updates(self) -> BotModel:
        """
        Take order id from list of bot.orders
        and fetch order details from exchange

        Fill incomplete orders first
        """
        kucoin_symbol = convert_to_kucoin_symbol(self.active_bot)
        stop_orders = self.base_streaming.kucoin_futures_api.get_all_stop_loss_orders(
            kucoin_symbol
        )
        # assuming there can only be one
        if len(stop_orders) > 1:
            self.active_bot.add_log(
                f"Warning: More than one stop loss order found for bot {self.active_bot.id}. Check system orders for discrepancies."
            )

        if len(stop_orders) == 0:
            self.active_bot.add_log(
                "No stop loss orders found, this indicates stop loss has been executed. Retrieving order details from system to update bot accordingly."
            )

        for order in self.active_bot.orders:
            if (
                self.base_streaming.exchange == ExchangeId.KUCOIN
                and order.status != OrderStatus.FILLED
            ):
                kucoin_symbol = convert_to_kucoin_symbol(self.active_bot)
                system_order = self.base_streaming.kucoin_api.get_order(
                    symbol=kucoin_symbol,
                    order_id=str(order.order_id),
                )

                # Check if order is expired based on 15m interval
                # this should be a good measure, because candles have closed
                interval_ms = self.base_streaming.interval.get_ms()
                now_ms = int(datetime.now().timestamp() * 1000)
                order_ms = int(order.timestamp * 1000)
                is_expired = (now_ms - order_ms) > interval_ms

                if system_order and float(system_order.funds) > 0:
                    if float(system_order.price) > 0:
                        order.price = round_numbers(
                            system_order.price, self.price_precision
                        )

                    order.qty = round_numbers(system_order.funds, self.qty_precision)
                    order.status = (
                        OrderStatus.NEW if system_order.active else OrderStatus.FILLED
                    )
                    order.timestamp = system_order.created_at
                    self.base_streaming.bot_controller.update_order(order)
                    self.active_bot.add_log(
                        f"Order {order.order_id} updated from system"
                    )

                    if (
                        order.deal_type == DealType.base_order
                        and self.active_bot.deal.opening_price == 0
                        and order.price > 0
                    ):
                        self.active_bot.deal.opening_price = order.price
                        self.active_bot.deal.opening_qty = order.qty
                        self.active_bot.deal.opening_timestamp = order.timestamp
                        self.active_bot.status = Status.active

                    if (
                        (
                            order.deal_type == DealType.take_profit
                            or order.deal_type == DealType.stop_loss
                            or order.deal_type == DealType.panic_close
                            or order.deal_type == DealType.trailing_profit
                        )
                        and self.active_bot.deal.closing_price == 0
                        and order.price > 0
                    ):
                        self.active_bot.deal.closing_price = order.price
                        self.active_bot.deal.closing_qty = order.qty
                        self.active_bot.deal.closing_timestamp = order.timestamp
                        self.active_bot.status = Status.completed

                if not system_order or is_expired:
                    try:
                        self.base_streaming.kucoin_api.cancel_order_by_order_id_sync(
                            order_id=str(order.order_id)
                        )
                    except Exception as e:
                        # Order may already be cancelled or doesn't exist
                        self.active_bot.add_log(
                            f"Failed to cancel order {order.order_id}: {str(e)}"
                        )
                    if order.deal_type == DealType.base_order:
                        self.active_bot.status = Status.inactive
                        self.active_bot.add_log(
                            f"Order {order.order_id} expired and cancelled. Bot set to inactive.",
                        )
                    else:
                        self.active_bot.add_log(
                            f"Order {order.order_id} expired and cancelled.",
                        )

                    self.base_streaming.bot_controller.update_order(order)

            self.base_streaming.bot_controller.save(data=self.active_bot)

        return self.active_bot
