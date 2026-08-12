from datetime import datetime
from pybinbot import (
    BotModel,
    DealType,
    ExchangeId,
    OrderStatus,
    Status,
    convert_to_kucoin_symbol,
    round_numbers,
)

from api.exchange_apis.kucoin.futures.futures_deal import KucoinPositionDeal
from streaming.base import BaseStreaming
from streaming.position_market import PositionMarket


class SpotPosition(PositionMarket):
    def __init__(
        self,
        base_streaming: BaseStreaming,
        execution: KucoinPositionDeal,
    ):
        super().__init__(
            execution=execution,
            base_streaming=base_streaming,
            api=base_streaming.kucoin_futures_api,
            symbol=execution.active_bot.pair,
        )
        self.kucoin_benchmark_symbol = "USDT-BTC"
        self.api = self.base_streaming.kucoin_api
        self.price_precision = execution.price_precision
        self.qty_precision = execution.symbol_info.qty_precision

    def order_updates(self) -> BotModel:
        """
        Take order id from list of bot.orders
        and fetch order details from exchange

        Fill incomplete orders first
        """
        kucoin_symbol = convert_to_kucoin_symbol(self.execution.active_bot)
        stop_orders = self.base_streaming.kucoin_futures_api.get_all_stop_loss_orders(
            kucoin_symbol
        )
        # assuming there can only be one
        if len(stop_orders) > 1:
            self.execution.active_bot.add_log(
                f"Warning: More than one stop loss order found for bot {self.execution.active_bot.id}. Check system orders for discrepancies."
            )

        if len(stop_orders) == 0:
            self.execution.active_bot.add_log(
                "No stop loss orders found, this indicates stop loss has been executed. Retrieving order details from system to update bot accordingly."
            )

        for order in self.execution.active_bot.orders:
            if (
                self.base_streaming.exchange == ExchangeId.KUCOIN
                and order.status != OrderStatus.FILLED
            ):
                kucoin_symbol = convert_to_kucoin_symbol(self.execution.active_bot)
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
                    self.execution.active_bot.add_log(
                        f"Order {order.order_id} updated from system"
                    )

                    if (
                        order.deal_type == DealType.base_order
                        and self.execution.active_bot.deal.opening_price == 0
                        and order.price > 0
                    ):
                        self.execution.active_bot.deal.opening_price = order.price
                        self.execution.active_bot.deal.opening_qty = order.qty
                        self.execution.active_bot.deal.opening_timestamp = (
                            order.timestamp
                        )
                        self.execution.active_bot.status = Status.active

                    if (
                        (
                            order.deal_type == DealType.take_profit
                            or order.deal_type == DealType.stop_loss
                            or order.deal_type == DealType.panic_close
                            or order.deal_type == DealType.trailing_profit
                        )
                        and self.execution.active_bot.deal.closing_price == 0
                        and order.price > 0
                    ):
                        self.execution.active_bot.deal.closing_price = order.price
                        self.execution.active_bot.deal.closing_qty = order.qty
                        self.execution.active_bot.deal.closing_timestamp = (
                            order.timestamp
                        )
                        self.execution.active_bot.status = Status.completed

                if not system_order or is_expired:
                    try:
                        self.base_streaming.kucoin_api.cancel_order_by_order_id_sync(
                            order_id=str(order.order_id)
                        )
                    except Exception as e:
                        # Order may already be cancelled or doesn't exist
                        self.execution.active_bot.add_log(
                            f"Failed to cancel order {order.order_id}: {str(e)}"
                        )
                    if order.deal_type == DealType.base_order:
                        self.execution.active_bot.status = Status.inactive
                        self.execution.active_bot.add_log(
                            f"Order {order.order_id} expired and cancelled. Bot set to inactive.",
                        )
                    else:
                        self.execution.active_bot.add_log(
                            f"Order {order.order_id} expired and cancelled.",
                        )

                    self.base_streaming.bot_controller.update_order(order)

            self.execution.controller.save(data=self.execution.active_bot)

        return self.execution.active_bot
