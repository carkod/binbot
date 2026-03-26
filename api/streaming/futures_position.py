from datetime import datetime
from typing import Type

from bots.models import BotModel
from databases.tables.bot_table import BotTable, PaperTradingTable
from exchange_apis.kucoin.futures.position_market import PositionMarket
from kucoin_universal_sdk.model.common import RestError
from pybinbot import (
    DealType,
    ExchangeId,
    OrderStatus,
    Status,
    convert_to_kucoin_symbol,
    round_numbers,
)
from streaming.base import BaseStreaming


class FuturesPosition(PositionMarket):
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
        self.base_streaming = base_streaming
        self.bot = bot
        self.price_precision = price_precision
        self.qty_precision = qty_precision
        self.kucoin_benchmark_symbol = "ETHBTCUSDTM"
        self.api = self.base_streaming.kucoin_futures_api

    def futures_stop_loss_updates(self) -> BotModel:
        """
        Take stop loss order id from list of bot.orders
        and fetch order details from exchange
        """
        kucoin_symbol = convert_to_kucoin_symbol(self.bot)
        stop_orders = self.base_streaming.kucoin_futures_api.get_all_stop_loss_orders(
            kucoin_symbol
        )
        # assuming there can only be one
        if len(stop_orders) > 1:
            self.bot.add_log(
                f"Warning: More than one stop loss order found for bot {self.bot.id}. Check system orders for discrepancies."
            )

        if len(stop_orders) == 0:
            self.bot.add_log(
                "No stop loss orders found, this indicates stop loss has been executed. Retrieving order details from system to update bot accordingly."
            )

        for order in self.bot.orders:
            if (
                order.deal_type == DealType.stop_loss
                and order.status != OrderStatus.FILLED
            ):
                system_order = self.base_streaming.kucoin_futures_api.retrieve_order(
                    str(order.order_id)
                )

                if system_order and float(system_order.filled_size) > 0:
                    if float(system_order.avg_deal_price) > 0:
                        order.price = round_numbers(
                            system_order.avg_deal_price, self.price_precision
                        )

                    order.qty = round_numbers(
                        float(system_order.filled_size), self.qty_precision
                    )
                    order.status = OrderStatus.map_from_kucoin_status(
                        system_order.status.value
                    )
                    order.timestamp = system_order.created_at
                    self.base_streaming.bot_controller.update_order(order)
                    self.bot.add_log(
                        f"Stop loss order {order.order_id} updated from system"
                    )
                else:
                    self.bot.add_log(
                        f"Stop loss order {order.order_id} not found in system, marking as filled based on absence and updating bot status to completed."
                    )
                    order.status = OrderStatus.FILLED
                    order.price = self.bot.deal.closing_price
                    order.qty = self.bot.deal.opening_qty
                    order.timestamp = int(datetime.now().timestamp() * 1000)
                    self.base_streaming.bot_controller.update_order(order)
                    self.bot.deal.closing_price = order.price
                    self.bot.deal.closing_qty = order.qty
                    self.bot.deal.closing_timestamp = order.timestamp
                    self.bot.status = Status.completed

        self.base_streaming.bot_controller.save(data=self.bot)
        return self.bot

    def order_updates(self) -> BotModel:
        """
        Take order id from list of bot.orders
        and fetch order details from exchange
        """
        for order in self.bot.orders:
            if order.status == OrderStatus.FILLED:
                continue

            if self.base_streaming.exchange == ExchangeId.KUCOIN:
                kucoin_symbol = convert_to_kucoin_symbol(self.bot)

                # Check if order is expired based on 15m interval
                # this should be a good measure, because candles have closed
                interval_ms = self.base_streaming.interval.get_ms()
                now_ms = int(datetime.now().timestamp() * 1000)
                order_ms = int(order.timestamp * 1000)
                is_expired = (now_ms - order_ms) > interval_ms

                try:
                    # Fetch order details as source of truth for status/fills
                    system_order = (
                        self.base_streaming.kucoin_futures_api.retrieve_order(
                            str(order.order_id)
                        )
                    )
                    if is_expired:
                        raise RestError(
                            response=type(
                                "obj",
                                (object,),
                                {"code": 100001, "message": "Order expired"},
                            )()
                        )
                    status = OrderStatus.map_from_kucoin_status(
                        system_order.status.value
                    )
                    filled_size = float(system_order.filled_size)
                    price_used = float(system_order.avg_deal_price)
                    timestamp = system_order.created_at

                    if float(float(system_order.price)) > 0:
                        order.price = round_numbers(
                            float(system_order.price), self.price_precision
                        )

                    if order.status == status and float(system_order.price) == 0:
                        continue

                    order.qty = round_numbers(filled_size, self.qty_precision)
                    order.status = status
                    order.timestamp = timestamp
                    order.price = round_numbers(price_used, self.price_precision)

                    self.base_streaming.bot_controller.update_order(order)
                    self.bot.add_log(f"Order {order.order_id} updated from system")

                    if (
                        order.deal_type == DealType.base_order
                        and self.bot.deal.opening_price == 0
                        and float(system_order.price) > 0
                    ):
                        self.bot.deal.opening_price = order.price
                        self.bot.deal.opening_qty = order.qty
                        self.bot.deal.opening_timestamp = order.timestamp
                        self.bot.status = Status.active

                    if (
                        (
                            order.deal_type == DealType.take_profit
                            or order.deal_type == DealType.stop_loss
                            or order.deal_type == DealType.panic_close
                            or order.deal_type == DealType.trailling_profit
                        )
                        and self.bot.deal.closing_price == 0
                        and float(system_order.price) > 0
                    ):
                        self.bot.deal.closing_price = order.price
                        self.bot.deal.closing_qty = order.qty
                        self.bot.deal.closing_timestamp = order.timestamp
                        self.bot.status = Status.completed

                    self.base_streaming.bot_controller.save(data=self.bot)

                except RestError as e:
                    if float(e.response.code) == 100001:
                        try:
                            self.cancel_current_sl()
                            if order.deal_type == DealType.base_order:
                                self.bot.status = Status.inactive
                                self.bot.add_log(
                                    f"Order {order.order_id} expired and cancelled. Bot set to inactive.",
                                )
                                self.base_streaming.bot_controller.save(data=self.bot)
                            else:
                                self.bot.add_log(
                                    f"Order {order.order_id} expired and cancelled.",
                                )
                                self.base_streaming.bot_controller.save(data=self.bot)
                        except Exception as cancel_e:
                            self.bot.add_log(
                                f"Failed to cancel all futures orders for {kucoin_symbol}: {str(cancel_e)}"
                            )
                            self.base_streaming.bot_controller.save(data=self.bot)
                    else:
                        raise e

        return self.bot
