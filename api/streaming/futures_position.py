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
        self.price_precision = price_precision
        self.qty_precision = qty_precision
        self.kucoin_benchmark_symbol = "ETHBTCUSDTM"
        self.api = self.base_streaming.kucoin_futures_api

    def confirm_close_from_position(self, filled_size: float) -> bool:
        kucoin_symbol = convert_to_kucoin_symbol(self.active_bot)
        position = self.base_streaming.kucoin_futures_api.get_futures_position(
            kucoin_symbol
        )

        if position:
            current_qty = abs(float(position.current_qty))
            if current_qty > 0:
                return False

        elif filled_size > 0:
            self.active_bot = self.backfill_position_from_fills()
            self.base_streaming.bot_controller.save(data=self.active_bot)
            return True

        return True

    def order_updates(self) -> BotModel:
        """
        Take order id from list of bot.orders
        and fetch order details from exchange
        """
        for order in list(self.active_bot.orders):
            if order.status == OrderStatus.FILLED:
                continue

            if self.base_streaming.exchange == ExchangeId.KUCOIN:
                kucoin_symbol = convert_to_kucoin_symbol(self.active_bot)

                # Check if order is expired based on 15m interval
                # this should be a good measure, because candles have closed
                interval_ms = self.base_streaming.interval.get_ms()
                now_ms = int(datetime.now().timestamp() * 1000)
                order_ms = int(order.timestamp)
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
                            msg=f"Order {order.order_id} is expired based on time threshold. Marking as expired.",
                            response=type(
                                "obj",
                                (object,),
                                {"code": 100001, "message": "Order expired"},
                            )(),
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

                    previous_qty = float(order.qty)
                    if order.status == status and previous_qty == filled_size:
                        continue

                    order.qty = round_numbers(filled_size, self.qty_precision)
                    order.status = status
                    order.timestamp = timestamp
                    order.price = round_numbers(price_used, self.price_precision)

                    self.base_streaming.bot_controller.update_order(order)
                    self.active_bot.add_log(
                        f"Order {order.order_id} updated from system"
                    )

                    if (
                        order.deal_type == DealType.base_order
                        and self.active_bot.deal.opening_price == 0
                        and float(system_order.price) > 0
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
                            or order.deal_type == DealType.trailling_profit
                        )
                        and self.active_bot.deal.closing_price == 0
                        and filled_size > 0
                        and self.confirm_close_from_position(filled_size)
                    ):
                        self.active_bot.deal.closing_price = order.price
                        self.active_bot.deal.closing_qty = order.qty
                        self.active_bot.deal.closing_timestamp = order.timestamp
                        self.active_bot.status = Status.completed

                    self.base_streaming.bot_controller.save(data=self.active_bot)

                except RestError as e:
                    if float(e.response.code) == 100001:
                        try:
                            self.cancel_current_sl()
                            if order.deal_type == DealType.base_order:
                                self.active_bot.status = Status.inactive
                                self.active_bot.add_log(
                                    f"Order {order.order_id} expired and cancelled. Bot set to inactive.",
                                )
                                self.base_streaming.bot_controller.save(
                                    data=self.active_bot
                                )
                            else:
                                self.active_bot.add_log(
                                    f"Order {order.order_id} expired and cancelled.",
                                )
                                self.base_streaming.bot_controller.save(
                                    data=self.active_bot
                                )
                        except Exception as cancel_e:
                            self.active_bot.add_log(
                                f"Failed to cancel all futures orders for {kucoin_symbol}: {str(cancel_e)}"
                            )
                            self.base_streaming.bot_controller.save(
                                data=self.active_bot
                            )
                    else:
                        raise e

        return self.active_bot
