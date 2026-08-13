from datetime import datetime
from kucoin_universal_sdk.generate.futures.order.model_get_order_by_order_id_resp import (
    GetOrderByOrderIdResp,
)
from kucoin_universal_sdk.generate.futures.order import CancelOrderByIdReqBuilder
from kucoin_universal_sdk.model.common import RestError
from pybinbot import (
    BotModel,
    DealType,
    ExchangeId,
    OrderModel,
    OrderStatus,
    Status,
    convert_to_kucoin_symbol,
    round_numbers,
)

from api.exchange_apis.kucoin.futures.futures_deal import KucoinPositionDeal
from api.tools.constants import (
    RELATIVE_STRENGTH_IMPULSE_RIDER_ALGO,
    RELATIVE_STRENGTH_IMPULSE_RIDER_PENDING_ENTRY_CANDLES,
    TOP_GAINER_EARLY_MOMENTUM_ALGO,
    TOP_GAINER_EARLY_MOMENTUM_PENDING_ENTRY_CANDLES,
)
from streaming.base import BaseStreaming
from streaming.position_market import PositionMarket


class FuturesPosition(PositionMarket):
    PENDING_ENTRY_TTL_MS = 5 * 60 * 1000
    TERMINAL_ORDER_STATUSES = {
        OrderStatus.FILLED,
        OrderStatus.CANCELED,
        OrderStatus.EXPIRED,
        OrderStatus.REJECTED,
    }

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
        self.base_streaming = base_streaming
        self.price_precision = execution.price_precision
        self.qty_precision = execution.symbol_info.qty_precision
        self.kucoin_benchmark_symbol = "XBTUSDTM"
        self.api = self.base_streaming.kucoin_futures_api

    def is_pending_base_entry_expired(self, order: OrderModel, now_ms: int) -> bool:
        pending_entry_ttl_ms = self.PENDING_ENTRY_TTL_MS
        if self.execution.active_bot.name == RELATIVE_STRENGTH_IMPULSE_RIDER_ALGO:
            pending_entry_ttl_ms = (
                self.base_streaming.interval.get_ms()
                * RELATIVE_STRENGTH_IMPULSE_RIDER_PENDING_ENTRY_CANDLES
            )
        elif self.execution.active_bot.name == TOP_GAINER_EARLY_MOMENTUM_ALGO:
            pending_entry_ttl_ms = (
                self.base_streaming.interval.get_ms()
                * TOP_GAINER_EARLY_MOMENTUM_PENDING_ENTRY_CANDLES
            )
        return (
            self.execution.active_bot.status == Status.pending
            and order.deal_type == DealType.base_order
            and self.execution.active_bot.deal.opening_price == 0
            and now_ms - int(order.timestamp) > pending_entry_ttl_ms
        )

    def should_expire_order_by_age(self, order: OrderModel) -> bool:
        """
        Legacy interval-based expiry is still valid for transient non-position
        orders. Pending futures entries use the explicit 5-minute TTL path so
        they can be cancelled at the exchange before the bot is inactivated.
        Protective orders must remain owned until the exchange reports a
        terminal state.
        """
        return order.deal_type in {
            DealType.algorithmic_close,
            DealType.conversion,
            DealType.margin_short,
        }

    def confirm_close_from_position(self, filled_size: float) -> bool:
        kucoin_symbol = convert_to_kucoin_symbol(self.execution.active_bot)
        position = self.base_streaming.kucoin_futures_api.get_futures_position(
            kucoin_symbol
        )

        if position:
            current_qty = abs(float(position.current_qty))
            if current_qty > 0:
                return False

        elif filled_size > 0:
            self.execution.active_bot = self.execution.backfill_position_from_fills()
            self.execution.controller.save(data=self.execution.active_bot)
            return True

        return True

    def _retrieve_order_or_none(self, order_id: str) -> GetOrderByOrderIdResp | None:
        try:
            return self.base_streaming.kucoin_futures_api.retrieve_order(order_id)
        except RestError as error:
            if float(error.response.code) == 100001:
                return None
            raise error

    @staticmethod
    def _cancel_futures_order_by_id(api, order_id: str) -> bool:
        cancel_by_id = getattr(api, "cancel_futures_order", None)
        if callable(cancel_by_id):
            cancel_by_id(order_id)
            return True

        futures_order_api = getattr(api, "futures_order_api", None)
        sdk_cancel_by_id = getattr(futures_order_api, "cancel_order_by_id", None)
        if callable(sdk_cancel_by_id):
            request = CancelOrderByIdReqBuilder().set_order_id(order_id).build()
            sdk_cancel_by_id(request)
            return True

        return False

    def _cancel_pending_entry_order(
        self, order: OrderModel, kucoin_symbol: str
    ) -> None:
        api = self.base_streaming.kucoin_futures_api
        order_id = str(order.order_id)

        if self._cancel_futures_order_by_id(api, order_id):
            return

        batch_cancel = getattr(api, "batch_cancel_stop_loss_orders", None)
        if callable(batch_cancel):
            batch_cancel([order_id])
            return

        position = api.get_futures_position(kucoin_symbol)
        current_qty = abs(float(getattr(position, "current_qty", 0) or 0))
        live_base_orders = [
            active_order
            for active_order in self.execution.active_bot.orders
            if active_order.deal_type == DealType.base_order
            and active_order.status not in self.TERMINAL_ORDER_STATUSES
        ]
        if current_qty == 0 and len(live_base_orders) == 1:
            api.cancel_all_futures_orders(kucoin_symbol)
            return

        raise RuntimeError(
            f"Refusing symbol-wide cancel for pending entry {order_id}; "
            "position or additional live base orders exist."
        )

    def _apply_system_order_update(
        self,
        order: OrderModel,
        system_order: GetOrderByOrderIdResp,
        status: OrderStatus,
        filled_size: float,
        price_used: float,
    ) -> None:
        system_price = float(system_order.price or 0)
        if system_price > 0:
            order.price = round_numbers(system_price, self.price_precision)

        if status == OrderStatus.FILLED or filled_size > 0:
            order.qty = round_numbers(filled_size, self.qty_precision)
        order.status = status
        order.timestamp = system_order.created_at
        if price_used > 0:
            order.price = round_numbers(price_used, self.price_precision)

    def _activate_filled_base_order(
        self, order: OrderModel, log_message: str | None = None
    ) -> None:
        self.execution.active_bot.deal.opening_price = order.price
        self.execution.active_bot.deal.opening_qty = order.qty
        self.execution.active_bot.deal.opening_timestamp = (
            self.execution.matching_exchange_fill_timestamp(order)
            if self.execution.active_bot.name == RELATIVE_STRENGTH_IMPULSE_RIDER_ALGO
            else order.timestamp
        )
        if log_message:
            self.execution.active_bot.add_log(log_message)
        self.execution.active_bot = self.execution.open_deal()

    def _expire_unfilled_base_order(
        self, order: OrderModel, kucoin_symbol: str
    ) -> None:
        self._cancel_pending_entry_order(order, kucoin_symbol)

        refreshed_order = self._retrieve_order_or_none(str(order.order_id))
        if refreshed_order is not None:
            refreshed_status = OrderStatus.map_from_kucoin_status(
                refreshed_order.status.value
            )
            refreshed_filled_size = float(refreshed_order.filled_size)
            refreshed_price_used = float(refreshed_order.avg_deal_price)
            self._apply_system_order_update(
                order,
                refreshed_order,
                refreshed_status,
                refreshed_filled_size,
                refreshed_price_used,
            )
            if refreshed_filled_size > 0 and refreshed_price_used > 0:
                self.execution.controller.update_order(order)
                self._activate_filled_base_order(
                    order,
                    "Entry order filled while expiry cancellation was being processed. "
                    "Bot activated with confirmed fill.",
                )
                self.execution.controller.save(data=self.execution.active_bot)
                return

        order.status = OrderStatus.EXPIRED
        order.qty = 0
        self.execution.controller.update_order(order)
        self.execution.active_bot.status = Status.inactive
        pending_entry_minutes = self.PENDING_ENTRY_TTL_MS // 60_000
        if self.execution.active_bot.name == RELATIVE_STRENGTH_IMPULSE_RIDER_ALGO:
            pending_entry_minutes = (
                self.base_streaming.interval.get_ms()
                * RELATIVE_STRENGTH_IMPULSE_RIDER_PENDING_ENTRY_CANDLES
                // 60_000
            )
        elif self.execution.active_bot.name == TOP_GAINER_EARLY_MOMENTUM_ALGO:
            pending_entry_minutes = (
                self.base_streaming.interval.get_ms()
                * TOP_GAINER_EARLY_MOMENTUM_PENDING_ENTRY_CANDLES
                // 60_000
            )
        self.execution.active_bot.add_log(
            f"Entry limit order {order.order_id} expired after {pending_entry_minutes} minutes without fill. "
            "Order cancelled and bot set to inactive."
        )
        self.execution.controller.save(data=self.execution.active_bot)

    def backfill_missing_stop_loss(self) -> None:
        """
        Safety net for an active futures position whose emergency stop loss
        order has disappeared from the local order list (cancelled but never
        replaced, or a replace that failed between cancel and place). Rebuilds
        one directly from bot.stop_loss and the entry price rather than
        leaving the position unprotected until the next dynamic-trailing tick.

        Skipped for reversal-eligible bots (they exit bot-side via exit(),
        so a native exchange stop must never be placed for them, per
        reconcile_exchange_sl) and once trailing has armed (the protective
        order there is a trailing_profit order, not a stop_loss order).
        """
        if (
            self.execution.active_bot.status != Status.active
            or self.execution.active_bot.stop_loss <= 0
            or self.execution.active_bot.deal.opening_price <= 0
            or self.execution._reversal_eligible()
            or self.execution.active_bot.deal.trailing_stop_loss_price != 0
        ):
            return

        has_live_stop_loss = any(
            order.deal_type == DealType.stop_loss
            and order.status not in self.TERMINAL_ORDER_STATUSES
            for order in self.execution.active_bot.orders
        )
        if has_live_stop_loss:
            return

        self.execution.active_bot.add_log(
            "No live stop loss order found for active futures position. "
            "Placing emergency stop loss from bot.stop_loss and entry price."
        )
        try:
            self.execution.recompute_derived_prices()
            self.execution.place_stop_loss()
        except Exception as exc:
            self.execution.active_bot.add_log(
                f"Failed to place missing stop loss: {exc}"
            )
        self.execution.controller.save(data=self.execution.active_bot)

    def order_updates(self) -> BotModel:
        """
        Take order id from list of bot.orders
        and fetch order details from exchange
        """
        for order in list(self.execution.active_bot.orders):
            if order.status in self.TERMINAL_ORDER_STATUSES:
                continue

            if self.base_streaming.exchange == ExchangeId.KUCOIN:
                kucoin_symbol = convert_to_kucoin_symbol(self.execution.active_bot)

                # Check if order is expired based on 15m interval
                # this should be a good measure, because candles have closed
                interval_ms = self.base_streaming.interval.get_ms()
                now_ms = int(datetime.now().timestamp() * 1000)
                order_ms = int(order.timestamp)
                is_expired = (now_ms - order_ms) > interval_ms
                is_pending_entry_expired = self.is_pending_base_entry_expired(
                    order, now_ms
                )

                try:
                    # Fetch order details as source of truth for status/fills
                    system_order = (
                        self.base_streaming.kucoin_futures_api.retrieve_order(
                            str(order.order_id)
                        )
                    )
                    if is_expired and self.should_expire_order_by_age(order):
                        self.execution.bot_crud.delete_order(
                            order_id=str(order.order_id),
                            bot_id=str(self.execution.active_bot.id),
                        )
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

                    previous_qty = float(order.qty)
                    previous_status = order.status
                    self._apply_system_order_update(
                        order, system_order, status, filled_size, price_used
                    )

                    if (
                        order.deal_type == DealType.base_order
                        and self.execution.active_bot.deal.opening_price == 0
                        and filled_size > 0
                    ):
                        if status != OrderStatus.FILLED:
                            self._cancel_pending_entry_order(order, kucoin_symbol)
                            order.status = OrderStatus.CANCELED
                        self.execution.controller.update_order(order)
                        self.execution.active_bot.add_log(
                            f"Order {order.order_id} updated from system"
                        )
                        self._activate_filled_base_order(order)
                        self.execution.controller.save(data=self.execution.active_bot)
                        continue

                    if (
                        order.deal_type == DealType.base_order
                        and self.execution.active_bot.deal.opening_price == 0
                        and status
                        in {
                            OrderStatus.CANCELED,
                            OrderStatus.EXPIRED,
                            OrderStatus.REJECTED,
                        }
                    ):
                        self.execution.controller.update_order(order)
                        self.execution.active_bot.status = Status.inactive
                        self.execution.active_bot.add_log(
                            f"Entry limit order {order.order_id} ended with status {status.value} before fill. "
                            "Bot set to inactive."
                        )
                        self.execution.controller.save(data=self.execution.active_bot)
                        continue

                    if is_pending_entry_expired:
                        self._expire_unfilled_base_order(order, kucoin_symbol)
                        continue

                    if order.status == status and (
                        filled_size == 0 or previous_qty == filled_size
                    ):
                        if previous_status == status:
                            continue

                    if previous_status == status and previous_qty == filled_size:
                        continue

                    self.execution.controller.update_order(order)
                    self.execution.active_bot.add_log(
                        f"Order {order.order_id} updated from system"
                    )

                    if (
                        (
                            order.deal_type == DealType.take_profit
                            or order.deal_type == DealType.stop_loss
                            or order.deal_type == DealType.panic_close
                            or order.deal_type == DealType.trailing_profit
                        )
                        and self.execution.active_bot.deal.closing_price == 0
                        and filled_size > 0
                        and self.confirm_close_from_position(filled_size)
                    ):
                        self.execution.active_bot.deal.closing_price = order.price
                        self.execution.active_bot.deal.closing_qty = order.qty
                        self.execution.active_bot.deal.closing_timestamp = (
                            order.timestamp
                        )
                        self.execution.active_bot.status = Status.completed

                    self.execution.controller.save(data=self.execution.active_bot)

                except RestError as e:
                    if float(e.response.code) == 100001:
                        try:
                            if order.deal_type == DealType.base_order:
                                self.execution.cancel_current_sl()
                                self.execution.active_bot.status = Status.inactive
                                self.execution.active_bot.add_log(
                                    f"Order {order.order_id} expired and cancelled. Bot set to inactive.",
                                )
                                self.execution.controller.save(
                                    data=self.execution.active_bot
                                )
                            elif self.should_expire_order_by_age(order):
                                self.execution.cancel_current_sl()
                                self.execution.active_bot.add_log(
                                    f"Order {order.order_id} expired and cancelled.",
                                )
                                self.execution.controller.save(
                                    data=self.execution.active_bot
                                )
                            else:
                                self.execution.bot_crud.delete_order(
                                    order_id=str(order.order_id),
                                    bot_id=str(self.execution.active_bot.id),
                                )
                                self.execution.active_bot.orders = [
                                    active_order
                                    for active_order in self.execution.active_bot.orders
                                    if str(active_order.order_id) != str(order.order_id)
                                ]
                                self.execution.active_bot.add_log(
                                    f"Protective order {order.order_id} was not found on exchange. Removed stale local record.",
                                )
                                self.execution.controller.save(
                                    data=self.execution.active_bot
                                )
                        except Exception as cancel_e:
                            self.execution.active_bot.add_log(
                                f"Failed to cancel all futures orders for {kucoin_symbol}: {str(cancel_e)}"
                            )
                            self.execution.controller.save(
                                data=self.execution.active_bot
                            )
                    else:
                        raise e

        self.backfill_missing_stop_loss()
        return self.execution.active_bot
