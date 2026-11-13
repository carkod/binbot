from time import sleep, time
from uuid import uuid4

from pybinbot.models.deal import ConditionalCloseOrder
from typing import Any, Callable, Type

from kucoin_universal_sdk.generate.futures.order import GetTradeHistoryReq
from kucoin_universal_sdk.generate.futures.order.model_add_order_req import AddOrderReq
from kucoin_universal_sdk.model.common import RestError
from pybinbot import (
    BinanceKlineIntervals,
    BinbotErrors,
    BotModel,
    DealType,
    EntryMode,
    KucoinFutures,
    OrderBase,
    OrderModel,
    OrderStatus,
    OrderType,
    Position,
    Status,
    ceil_price_to_tick,
    convert_to_kucoin_symbol,
    floor_price_to_tick,
    resolve_tick_size,
    round_numbers,
    round_timestamp,
    stop_limit_price,
)

from api.databases.crud.bot_crud import BotTableCrud
from api.databases.crud.symbols_crud import SymbolsCrud
from api.databases.tables.bot_table import BotTable
from api.exchange_apis.kucoin.deals.base import KucoinBaseBalance
from api.exchange_apis.kucoin.futures.liquidity import load_futures_order_book
from api.tools.utils import submission_guard


def is_order_not_found(exc: RestError) -> bool:
    """KuCoin reports an unknown or purged order id with code 100001."""
    return str(exc.response.code) == "100001" and any(
        phrase in str(exc.response.message).lower()
        for phrase in (
            "order not found",
            "order not exist",
            "order does not exist",
            "getorder.ordernotexist",
        )
    )


class OrderExecution(KucoinBaseBalance):
    """
    KuCoin futures order execution for one bot: native stop-limit and
    trailing protection, position closes, and fill reconciliation.

    KucoinPositionDeal extends this class with deal and position logic.
    """

    # SL replacement gating — stop loss is "emergency only", we only
    # touch the on-exchange order when it materially changes, and even
    # then no more often than the cooldown.
    STOP_LOSS_REPLACE_MIN_MOVE_RATIO = 0.0015  # 0.15% of price
    STOP_LOSS_REPLACE_MIN_TICKS = 2
    STOP_LOSS_REPLACE_COOLDOWN_MS = 30_000
    TRAILING_STOP_REFRESH_MIN_IMPROVEMENT_RATIO = 0.002
    TRAILING_STOP_REPLACE_COOLDOWN_MS = 5 * 60 * 1000
    TERMINAL_STOP_ORDER_STATUSES = (
        OrderStatus.FILLED,
        OrderStatus.CANCELED,
        OrderStatus.EXPIRED,
        OrderStatus.REJECTED,
    )
    # How long to wait after the first (limit) close leg before checking its
    # fill status: KuCoin's order/position endpoints can lag fill processing.
    CLOSE_ALL_FILL_CHECK_SLEEP_S = 5.0

    def __init__(
        self,
        bot: BotModel,
        db_table: Type[BotTable] = BotTable,
        kucoin_futures_api: KucoinFutures | None = None,
        controller: BotTableCrud | None = None,
        symbols_crud: SymbolsCrud | None = None,
        interval_ms: int | None = None,
    ) -> None:
        super().__init__()
        self.active_bot = bot
        self.db_table = db_table
        self.kucoin_futures_api = kucoin_futures_api or KucoinFutures(
            key=self.config.kucoin_key,
            secret=self.config.kucoin_secret,
            passphrase=self.config.kucoin_passphrase,
        )
        if controller is not None:
            self.controller = controller
        else:
            self.controller = BotTableCrud()

        self.symbols_crud = symbols_crud or SymbolsCrud()
        self.interval_ms = (
            interval_ms or BinanceKlineIntervals(bot.candlestick_interval).get_ms()
        )
        self.symbol_info = self.symbols_crud.get_symbol(bot.pair)
        self.kucoin_futures_api.DEFAULT_LEVERAGE = self.active_bot.futures_leverage
        self.kucoin_symbol = convert_to_kucoin_symbol(bot)
        self.kucoin_symbol_data = self.kucoin_futures_api.get_symbol_info(
            self.kucoin_symbol
        )
        self.price_precision = self.symbol_info.price_precision

    def _direction_multiplier(self) -> int:
        return -1 if self.active_bot.position == Position.short else 1

    def matching_exchange_fill_timestamp(
        self,
        order: OrderModel,
        fallback_timestamp: int | None = None,
        *,
        last_fill: bool = False,
    ) -> int:
        """Return the first exchange fill time for an order, in milliseconds."""
        resolved_fallback = fallback_timestamp or order.timestamp
        try:
            fills = self.kucoin_futures_api.get_fills(order_id=str(order.order_id))
        except Exception as exc:
            self.active_bot.add_log(
                f"Unable to load fill timestamp for order {order.order_id}: {exc}. "
                "Using the exchange update timestamp."
            )
            return resolved_fallback

        matching_fills = [
            fill
            for fill in (fills.items or [])
            if str(fill.order_id) == str(order.order_id)
        ]
        trade_timestamps = [
            int(fill.trade_time) // 1_000_000
            for fill in matching_fills
            if fill.trade_time is not None
        ]
        if trade_timestamps:
            return max(trade_timestamps) if last_fill else min(trade_timestamps)

        created_timestamps = [
            int(fill.created_at)
            for fill in matching_fills
            if fill.created_at is not None
        ]
        if created_timestamps:
            return max(created_timestamps) if last_fill else min(created_timestamps)

        self.active_bot.add_log(
            f"No matching exchange fill timestamp found for order {order.order_id}. "
            "Using the exchange update timestamp."
        )
        return resolved_fallback

    def recovery_source_enabled(self) -> bool:
        params = self.active_bot.recovery_params
        return (
            params is not None
            and params.reversal_path == "source"
            and not self.active_bot.dynamic_position_sizing
        )

    def awaiting_close_confirmation(self) -> bool:
        """A complete native fill can precede the exchange position snapshot."""
        return self.active_bot.deal.closing_qty == 0 and any(
            order.deal_type
            in {DealType.stop_loss, DealType.trailing_profit, DealType.take_profit}
            and order.status == OrderStatus.FILLED
            and order.requested_qty > 0
            and order.qty >= order.requested_qty
            for order in self.active_bot.orders
        )

    def _cleanup_native_protection_after_close(self) -> None:
        """Remove exchange-native protection after a confirmed bot-side close."""

        try:
            self.cancel_current_sl()
        except Exception as exc:
            # The position is already confirmed closed. A stale reduce-only
            # stop cannot reopen it, so cleanup failure is safe to retry later.
            self.active_bot.add_log(
                "Could not clean up exchange-native protection after the "
                f"confirmed bot-side close ({exc})."
            )

    def backfill_position_from_fills(self) -> BotModel:
        self.active_bot.add_log(
            "Position not found in exchange, cannot update size. ADL might have happened, or position might have been closed without bot's knowledge."
        )
        side = (
            GetTradeHistoryReq.SideEnum.BUY
            if self.active_bot.position == Position.short
            else GetTradeHistoryReq.SideEnum.SELL
        )

        start_at = self.active_bot.deal.opening_timestamp
        now_ms = int(time() * 1000)

        fills = self.kucoin_futures_api.get_fills(
            side=side,
            symbol=self.kucoin_symbol,
            start_at=start_at,
            end_at=now_ms,
        )
        self.active_bot.add_log(
            f"Fetched fills history to check for position updates. Number of fills found: {len(fills.items)}."
        )
        if len(fills.items) > 0:
            total_qty = sum(abs(float(fill.size)) for fill in fills.items)
            order_resp = fills.items[0]
            total_notional = sum(
                abs(float(fill.size)) * float(fill.price) for fill in fills.items
            )
            closing_price = (
                round_numbers(total_notional / total_qty, self.price_precision)
                if total_qty > 0
                else float(order_resp.price)
            )
            if self.active_bot.position == Position.short:
                deal_type = (
                    DealType.take_profit
                    if (closing_price < self.active_bot.deal.opening_price)
                    else DealType.stop_loss
                )
            else:
                deal_type = (
                    DealType.take_profit
                    if (closing_price > self.active_bot.deal.opening_price)
                    else DealType.stop_loss
                )

            exit_order = OrderModel(
                order_id=order_resp.order_id,
                order_type=order_resp.order_type.value,
                pair=order_resp.symbol,
                timestamp=order_resp.created_at,
                order_side=order_resp.side.value,
                qty=total_qty,
                price=closing_price,
                status=OrderStatus.FILLED,
                # no data, assumed
                time_in_force="GTC",
                deal_type=deal_type,
            )
            self.active_bot.orders.append(exit_order)
            self.active_bot.deal.closing_price = closing_price
            self.active_bot.deal.closing_qty = total_qty
            self.active_bot.deal.closing_timestamp = order_resp.created_at
            self.active_bot.deal.total_commissions += float(order_resp.fee)
            self.active_bot.deal.current_position_qty = 0
            self.active_bot.status = Status.completed
            self.active_bot.add_log(
                f"Position size updated from fills history. New size: {total_qty}."
            )
            return self.active_bot

        else:
            self.active_bot.add_log(
                "No fills found in history, cannot update position size. ADL might have happened, or position might have been closed without bot's knowledge."
            )
            self.active_bot.status = Status.error

        return self.active_bot

    def remove_stale_orders(self) -> None:
        stale_orders = [
            order
            for order in self.active_bot.orders
            if order.deal_type == DealType.trailing_profit
            and order.status == OrderStatus.FILLED
            and order.price == 0
            and order.qty == 0
        ]
        for stale_order in stale_orders:
            try:
                self.controller.delete_order(
                    str(stale_order.order_id), str(self.active_bot.id)
                )
            except BinbotErrors:
                pass

        self.active_bot.orders = [
            order
            for order in self.active_bot.orders
            if not (
                order.deal_type == DealType.trailing_profit
                and order.status == OrderStatus.FILLED
                and order.price == 0
                and order.qty == 0
            )
        ]

    def cancel_current_sl(self, *, deal_type: DealType | None = None) -> None:
        """Cancel only this bot's protection, retaining execution history."""
        # A replacement target can have been tightened in memory. Persist it
        # before cancelling protection so a delayed lookup cannot roll it back.
        self.controller.save(self.active_bot)
        intent = self.active_bot.deal.conditional_close_order
        if intent is not None and intent.order_id is None:
            details = self.kucoin_futures_api.retrieve_order_by_client_oid(
                intent.client_oid
            )
            intent.order_id = str(details.id)
        owned: dict[str, OrderModel | None] = {
            str(order.order_id): order
            for order in self.active_bot.orders
            if order.deal_type in {DealType.stop_loss, DealType.trailing_profit}
            and (deal_type is None or order.deal_type == deal_type)
            and order.status not in self.TERMINAL_STOP_ORDER_STATUSES
        }
        if intent is not None and intent.order_id is not None:
            recorded = next(
                (
                    row
                    for row in self.active_bot.orders
                    if str(row.order_id) == intent.order_id
                ),
                None,
            )
            if (
                recorded is None
                or recorded.status not in self.TERMINAL_STOP_ORDER_STATUSES
            ):
                owned.setdefault(intent.order_id, recorded)
        if not owned:
            self.active_bot.deal.conditional_close_order = None
            return
        untriggered = {
            str(order.id)
            for order in self.kucoin_futures_api.get_all_stop_loss_orders(
                self.kucoin_symbol
            )
        }
        for order_id, local_order in owned.items():
            # Fills that order_updates already reconciled into the deal. A
            # triggered stop-limit can rest partially filled; those fills are
            # accounted for and must not block cancelling the remainder.
            recorded_filled_quantity = 0.0
            if local_order is not None and (
                local_order.requested_qty > 0
                or local_order.status == OrderStatus.PARTIALLY_FILLED
            ):
                # Older NEW rows used qty for the requested stop size.
                recorded_filled_quantity = local_order.qty
            known_filled_quantity = recorded_filled_quantity
            stop_cancellation = None
            standard_cancellation = None
            if order_id in untriggered:
                stop_cancellation = (
                    self.kucoin_futures_api.batch_cancel_stop_loss_orders([order_id])
                )
            else:
                details = self.kucoin_futures_api.retrieve_order(order_id)
                known_filled_quantity = max(
                    known_filled_quantity, float(details.filled_size or 0)
                )
                if details.is_active:
                    standard_cancellation = (
                        self.kucoin_futures_api.cancel_futures_order(order_id)
                    )
            try:
                details = self.kucoin_futures_api.retrieve_order(order_id)
            except RestError as exc:
                missing = is_order_not_found(exc)
                acknowledged = (
                    stop_cancellation is not None
                    and any(
                        str(result.order_id) == order_id
                        and str(result.code) == "200000"
                        for result in stop_cancellation.data or []
                    )
                ) or (
                    standard_cancellation is not None
                    and order_id in (standard_cancellation.cancelled_order_ids or [])
                )
                if not missing or not acknowledged:
                    raise
                # The detail endpoint can temporarily lose an untriggered stop
                # after cancellation. An acknowledgement alone is insufficient:
                # verify removal and check history for a fill racing the cancel.
                if any(
                    str(order.id) == order_id
                    for order in self.kucoin_futures_api.get_all_stop_loss_orders(
                        self.kucoin_symbol
                    )
                ):
                    raise BinbotErrors(
                        "Conditional close cancellation is not confirmed; deferring replacement/exit"
                    ) from exc
                filled_quantity, _, _ = self.kucoin_futures_api.get_order_execution(
                    order_id
                )
            else:
                if details.is_active:
                    raise BinbotErrors(
                        "Conditional close cancellation is not confirmed; deferring replacement/exit"
                    )
                filled_quantity = float(details.filled_size or 0)
            if max(known_filled_quantity, filled_quantity) > recorded_filled_quantity:
                raise BinbotErrors(
                    "Conditional close filled during cancellation; reconcile its fills before another exit"
                )
            if local_order is not None:
                local_order.status = OrderStatus.CANCELED
                if recorded_filled_quantity == 0:
                    local_order.qty = 0
                    local_order.price = 0
        self.active_bot.deal.conditional_close_order = None
        self.controller.save(self.active_bot)

    def _bot_known_stop_order(
        self,
        deal_type: DealType,
        fallback_price: float,
    ) -> tuple[float | None, int | None, str | None]:
        """
        Source of truth from the bot's local order list:
        return (price, timestamp_ms, order_id) of the most recent open stop
        order matching the requested deal type, or (None, None, None) if
        there is no matching local order.
        """
        for order in reversed(self.active_bot.orders):
            if order.deal_type != deal_type:
                continue
            if order.status in self.TERMINAL_STOP_ORDER_STATUSES:
                continue
            order_price = order.stop_price if order.stop_price > 0 else order.price
            ts = order.timestamp
            order_id = str(order.order_id) if order.order_id else None
            if order_price > 0:
                return order_price, ts, order_id
            if fallback_price > 0:
                return fallback_price, ts, order_id
            return None, ts, order_id
        return None, None, None

    def _bot_known_stop_loss(self) -> tuple[float | None, int | None]:
        stop_price, ts, _ = self._bot_known_stop_order(
            DealType.stop_loss,
            self.active_bot.deal.stop_loss_price,
        )
        return stop_price, ts

    def _bot_known_trailing_stop_loss(
        self,
    ) -> tuple[float | None, int | None, str | None]:
        return self._bot_known_stop_order(
            DealType.trailing_profit,
            self.active_bot.deal.trailing_stop_loss_price,
        )

    def _exchange_stop_loss_details(
        self, order_id: str | None = None
    ) -> tuple[bool, float | None, float | None]:
        """
        Source of truth from the exchange.

        Returns ``(ok, price, qty)``:
          - ``ok=True, price=float``  → exchange has an SL at this price
          - ``ok=True, price=None``   → exchange confirmed no SL exists
            for the requested order id, or no stop exists when no id is passed
          - ``ok=False, price=None``  → query failed; caller must NOT treat
            this as "no SL", or it will cancel/replace a still-valid one.
        Quantity is ``None`` when KuCoin omits it.
        """
        try:
            stop_orders = self.kucoin_futures_api.get_all_stop_loss_orders(
                self.kucoin_symbol
            )
        except Exception as exc:
            self.active_bot.add_log(f"Could not query exchange stop orders: {exc}")
            return False, None, None

        if not stop_orders:
            return True, None, None

        matching_orders: list[Any] = stop_orders
        if order_id is not None:
            matching_orders = [
                order for order in stop_orders if str(order.id or "") == order_id
            ]

        if not matching_orders:
            return True, None, None

        for order in matching_orders:
            stop_price = float(order.stop_price or 0)
            if stop_price > 0:
                raw_qty = order.size
                qty = abs(float(raw_qty)) if raw_qty is not None else None
                return True, stop_price, qty
        return True, None, None

    def _exchange_stop_loss_price(
        self, order_id: str | None = None
    ) -> tuple[bool, float | None]:
        exchange_ok, exchange_price, _ = self._exchange_stop_loss_details(order_id)
        return exchange_ok, exchange_price

    def should_replace_stop_loss_order(
        self,
        current_stop_price: float | None,
        new_stop_price: float,
        last_replace_ts_ms: int | None = None,
        cooldown_ms: int | None = None,
        allow_widening: bool = False,
    ) -> bool:
        """
        Decide whether the on-exchange SL needs replacing.

        Replace only when:
          - we have a meaningful new price, and
          - either there's no current SL, the new one is *better*, or the
            caller has explicitly allowed favorable-trend widening, and
          - the move exceeds the min-move threshold, and
          - the cooldown since the last replace has elapsed.
        """
        if new_stop_price <= 0:
            return False

        if current_stop_price is None or current_stop_price <= 0:
            return True

        direction = self._direction_multiplier()
        directional_move = (new_stop_price - current_stop_price) * direction
        if directional_move == 0 or (directional_move < 0 and not allow_widening):
            return False

        tick_size = 10 ** (-self.price_precision)
        min_replace_move = max(
            abs(current_stop_price) * self.STOP_LOSS_REPLACE_MIN_MOVE_RATIO,
            tick_size * self.STOP_LOSS_REPLACE_MIN_TICKS,
        )
        if abs(directional_move) < min_replace_move:
            return False

        if last_replace_ts_ms and last_replace_ts_ms > 0:
            cooldown = (
                self.STOP_LOSS_REPLACE_COOLDOWN_MS
                if cooldown_ms is None
                else cooldown_ms
            )
            now_ms = int(time() * 1000)
            if now_ms - last_replace_ts_ms < cooldown:
                return False

        return True

    def reconcile_exchange_sl(
        self, *, allow_widening: bool = False, position_qty: float | None = None
    ) -> None:
        """
        Reconcile the on-exchange emergency stop loss with what the bot
        thinks should be there.

        Cases handled:
          1. Bot expects SL but exchange has none — re-place (it was cancelled
             externally, expired, or never made it through).
          2. Exchange has an SL at a price that disagrees with the bot's
             local record — adopt the exchange price as truth (someone moved
             it manually) and only replace if it's now unsafe.
          3. Bot wants to ratchet SL closer to entry — only replace if the
             move is material and the cooldown has elapsed.
          4. A favorable-trend strategy explicitly permits widening — use
             the same material-move and cooldown protection before replacing.

        Skipped when:
          - trailing has armed (trailing_stop_loss_price != 0); in that mode
            the broad emergency stop has been replaced by the exchange-native
            trailing stop and its dedicated reconciler owns further updates.
        """
        intent = self.active_bot.deal.conditional_close_order
        if intent is not None and intent.order_id is None:
            self.place_conditional_close(
                intent.stop_price, intent.requested_qty, intent.deal_type
            )
            return

        if self.active_bot.stop_loss <= 0:
            return
        if self.awaiting_close_confirmation():
            return
        if self.active_bot.deal.trailing_stop_loss_price != 0:
            self.reconcile_trailing_stop_loss(position_qty=position_qty)
            return

        if (
            self.active_bot.deal.closing_qty > 0
            and self.active_bot.deal.current_position_qty == 0
        ):
            return
        if any(
            order.deal_type == DealType.stop_loss
            and order.qty > 0
            and order.client_oid is not None
            and order.status not in self.TERMINAL_STOP_ORDER_STATUSES
            for order in self.active_bot.orders
        ):
            return
        # Intended price
        if self.active_bot.deal.stop_loss_price <= 0:
            return

        exchange_ok, exchange_price, exchange_qty = self._exchange_stop_loss_details()
        if not exchange_ok:
            # API blip — we don't know what's on the exchange. Bail out and
            # try again next tick rather than risk cancelling/duplicating
            # a still-valid emergency SL.
            return

        bot_known_price, last_replace_ts_ms = self._bot_known_stop_loss()
        expected_qty = (
            position_qty
            if position_qty is not None
            else self.current_position_quantity()
        )

        # Case 1: exchange confirmed no SL exists — re-place.
        if exchange_price is None:
            if self.stop_limit_awaiting_fill():
                return
            if bot_known_price is not None:
                self.active_bot.add_log(
                    "Exchange SL missing — re-placing emergency stop."
                )
            self.cancel_current_sl()  # cleans local stale records, no-op on empty
            self.place_stop_loss(position_qty=position_qty)
            return

        quantity_changed = (
            exchange_qty is not None and exchange_qty != expected_qty
        ) or (
            position_qty is not None
            and any(
                order.deal_type == DealType.stop_loss
                and order.status not in self.TERMINAL_STOP_ORDER_STATUSES
                and (order.requested_qty if order.requested_qty > 0 else order.qty)
                != expected_qty
                for order in self.active_bot.orders
            )
        )
        if expected_qty > 0 and quantity_changed:
            self.active_bot.add_log(
                f"Exchange SL quantity drift detected: stop={exchange_qty} "
                f"contracts, current position={expected_qty}; replacing."
            )
            self.cancel_current_sl()
            self.place_stop_loss(position_qty=expected_qty)
            return

        # Case 2: exchange disagrees with our local record. Log the drift,
        # but keep the bot's freshly-ratcheted target (already computed into
        # deal.stop_loss_price by recompute_derived_prices) intact so Case 3
        # can judge it against the exchange price below. Overwriting it here
        # would make current_stop_price == new_stop_price in Case 3 and
        # permanently disable the ratchet the first time drift is seen.
        ratcheted_target = self.active_bot.deal.stop_loss_price
        if bot_known_price is not None and abs(exchange_price - bot_known_price) > (
            10**-self.price_precision
        ):
            self.active_bot.add_log(
                f"Exchange SL drift detected: bot={bot_known_price} exchange={exchange_price}; trusting exchange."
            )

        # Case 3: ratchet — replace only if materially better and not on cooldown.
        if self.should_replace_stop_loss_order(
            current_stop_price=exchange_price,
            new_stop_price=ratcheted_target,
            last_replace_ts_ms=last_replace_ts_ms,
            allow_widening=allow_widening,
        ):
            if (ratcheted_target - exchange_price) * self._direction_multiplier() < 0:
                self.active_bot.add_log(
                    "Favorable-trend volatility expansion widened the exchange "
                    f"stop from {exchange_price} to {ratcheted_target}."
                )
            self.cancel_current_sl()
            self.place_stop_loss()
        else:
            # Not replacing — the exchange price is what's actually
            # protecting the position, so adopt it as truth.
            self.active_bot.deal.stop_loss_price = round_numbers(
                exchange_price, self.price_precision
            )

    def current_position_quantity(self) -> float:
        """Return live contracts, falling back to the latest known quantity.

        KuCoin occasionally omits or temporarily reports no position quantity
        immediately after a market fill. In that case current_position_qty is
        safer than the historical opening quantity after partial exits or ADL.
        """
        try:
            position = self.kucoin_futures_api.get_futures_position(self.kucoin_symbol)
        except Exception as exc:
            self.active_bot.add_log(
                f"Could not refresh current position quantity from KuCoin: {exc}. "
                "Using the last confirmed quantity."
            )
        else:
            raw_position_qty = position.current_qty
            if raw_position_qty is not None:
                live_qty = round_numbers(
                    abs(float(raw_position_qty)), self.symbol_info.qty_precision
                )
                self.active_bot.deal.current_position_qty = live_qty
                if live_qty > 0:
                    self.active_bot.deal.base_order_size = live_qty
                return live_qty

        if self.active_bot.deal.current_position_qty > 0:
            return self.active_bot.deal.current_position_qty
        return self.active_bot.deal.opening_qty

    def stop_limit_awaiting_fill(self) -> bool:
        """The native stop triggered and its limit order still rests unfilled.

        KuCoin removes a triggered stop from the stop-order list, so the
        reconcilers must not read its absence as missing protection.
        """
        intent = self.active_bot.deal.conditional_close_order
        if intent is None or intent.order_id is None:
            return False
        try:
            details = self.kucoin_futures_api.retrieve_order(intent.order_id)
        except RestError as exc:
            if is_order_not_found(exc):
                return False
            raise
        return bool(details.stop_triggered and details.is_active)

    def stop_limit_missed(
        self, closed_candle_close: float, closed_candle_close_time_ms: int
    ) -> bool:
        """A closed candle settled beyond the native stop's limit price.

        The stop-limit then cannot fill until the price comes back, so the
        position needs a market close. Wicks alone never count: only a closed
        candle beyond the limit does, and only one that closed after KuCoin
        accepted the stop. A candle that closed before the stop existed (for
        example before a breakout entry or a fresh trailing stop) says
        nothing about this order.
        """
        intent = self.active_bot.deal.conditional_close_order
        if intent is None or intent.order_id is None or closed_candle_close <= 0:
            return False
        stop_order = next(
            (
                order
                for order in self.active_bot.orders
                if str(order.order_id) == intent.order_id
            ),
            None,
        )
        if stop_order is None or closed_candle_close_time_ms <= stop_order.timestamp:
            return False
        limit_price = stop_limit_price(
            intent.stop_price,
            self.active_bot.position,
            resolve_tick_size(self.kucoin_symbol_data.tick_size, self.price_precision),
        )
        return (closed_candle_close - limit_price) * self._direction_multiplier() < 0

    def place_conditional_close(
        self, stop_price: float, quantity: float, deal_type: DealType
    ) -> OrderModel | None:
        """Persist identity; resolve lost acknowledgements before conditional retry."""
        intent = self.active_bot.deal.conditional_close_order
        details = None
        if intent is not None:
            try:
                details = (
                    self.kucoin_futures_api.retrieve_order(intent.order_id)
                    if intent.order_id is not None
                    else self.kucoin_futures_api.retrieve_order_by_client_oid(
                        intent.client_oid
                    )
                )
            except RestError as exc:
                missing = is_order_not_found(exc)
                if not missing:
                    raise
                now_ms = int(time() * 1000)
                if intent.not_found_count == 0:
                    intent.not_found_since_ms = now_ms
                intent.not_found_count += 1
                self.controller.save(self.active_bot)
                if (
                    intent.order_id is not None
                    or intent.not_found_count < 3
                    or now_ms - intent.not_found_since_ms < 60_000
                ):
                    self.active_bot.add_log(
                        "Conditional acknowledgement unresolved; retaining the same clientOid and trigger."
                    )
                    return None
        else:
            intent = ConditionalCloseOrder(
                client_oid=str(uuid4()),
                requested_qty=quantity,
                stop_price=stop_price,
                deal_type=deal_type,
            )
            self.active_bot.deal.conditional_close_order = intent
            self.controller.save(self.active_bot)
        if details is not None:
            response = OrderBase(
                order_id=str(details.id),
                client_oid=intent.client_oid,
                requested_qty=intent.requested_qty,
                stop_price=intent.stop_price,
                pair=self.kucoin_symbol,
                order_type=OrderType.limit,
                time_in_force="GTC",
                order_side="buy"
                if self.active_bot.position == Position.short
                else "sell",
                price=float(details.avg_deal_price or 0),
                qty=float(details.filled_size or 0),
                timestamp=int(details.created_at or 0),
                status=OrderStatus.map_from_kucoin_status(details.status.value),
                deal_type=intent.deal_type,
            )
        else:
            intent.not_found_count = 0
            intent.not_found_since_ms = 0
            self.controller.save(self.active_bot)
            short = self.active_bot.position == Position.short
            response = self.kucoin_futures_api.place_futures_order(
                symbol=self.kucoin_symbol,
                side=AddOrderReq.SideEnum.BUY if short else AddOrderReq.SideEnum.SELL,
                order_type=OrderType.limit,
                price=stop_limit_price(
                    intent.stop_price,
                    self.active_bot.position,
                    resolve_tick_size(
                        self.kucoin_symbol_data.tick_size, self.price_precision
                    ),
                ),
                size=intent.requested_qty,
                leverage=self.active_bot.futures_leverage,
                stop=AddOrderReq.StopEnum.UP if short else AddOrderReq.StopEnum.DOWN,
                stop_price=intent.stop_price,
                stop_price_type=AddOrderReq.StopPriceTypeEnum.MARK_PRICE,
                reduce_only=True,
                client_oid=intent.client_oid,
            )
        intent.order_id = str(response.order_id)
        response.deal_type = intent.deal_type
        response.client_oid = intent.client_oid
        response.requested_qty = intent.requested_qty
        response.stop_price = intent.stop_price
        if response.status == OrderStatus.FILLED and response.qty <= 0:
            response.status = OrderStatus.CANCELED
        order = OrderModel(**response.model_dump())
        existing = next(
            (
                row
                for row in self.active_bot.orders
                if str(row.order_id) == str(order.order_id)
            ),
            None,
        )
        if existing is None:
            self.active_bot.orders.append(order)
        else:
            existing.__dict__.update(order.__dict__)
            order = existing
        self.controller.save(self.active_bot)
        return order

    def place_stop_loss(self, position_qty: float | None = None) -> None:
        if self.active_bot.stop_loss <= 0 or self.awaiting_close_confirmation():
            return

        direction = self._direction_multiplier()
        stop_price = self.active_bot.deal.stop_loss_price
        if stop_price <= 0:
            stop_price = round_numbers(
                self.active_bot.deal.opening_price
                - (
                    self.active_bot.deal.opening_price
                    * (self.active_bot.stop_loss / 100)
                    * direction
                ),
                self.price_precision,
            )

        if self.active_bot.position == Position.short:
            side = AddOrderReq.SideEnum.BUY
        else:
            side = AddOrderReq.SideEnum.SELL

        qty = (
            position_qty
            if position_qty is not None and position_qty > 0
            else self.current_position_quantity()
        )
        if qty <= 0:
            self.active_bot.add_log(
                "Stop loss was not placed because no current or historical "
                "position quantity is available."
            )
            return

        intent = self.active_bot.deal.conditional_close_order
        if (
            intent is not None
            and intent.order_id is not None
            and any(
                str(order.order_id) == intent.order_id
                and order.status in self.TERMINAL_STOP_ORDER_STATUSES
                for order in self.active_bot.orders
            )
        ):
            self.active_bot.deal.conditional_close_order = None
            self.controller.save(self.active_bot)

        # Adopt matching protection already on the exchange. New submissions
        # persist their clientOid before placing an order, so a lost response
        # can be recovered without creating another identity.
        try:
            exchange_stop_orders = self.kucoin_futures_api.get_all_stop_loss_orders(
                self.kucoin_symbol
            )
        except Exception:
            exchange_stop_orders = []
        for exchange_order in exchange_stop_orders:
            exchange_price = float(exchange_order.stop_price or 0)
            raw_exchange_qty = exchange_order.size
            exchange_qty = (
                abs(float(raw_exchange_qty)) if raw_exchange_qty is not None else None
            )
            if abs(exchange_price - stop_price) > 10**-self.price_precision:
                continue
            # An explicit fill quantity must not adopt a stop whose size the
            # exchange has omitted; that does not confirm full protection.
            if exchange_qty is None and position_qty is not None:
                continue
            if exchange_qty is not None and exchange_qty != qty:
                continue
            if (
                exchange_order.side is not None
                and exchange_order.side.lower() != side.value
            ):
                continue
            if exchange_order.reduce_only is False:
                continue

            exchange_order_id = str(exchange_order.id or "")
            if not exchange_order_id:
                continue
            if not any(
                str(local_order.order_id) == exchange_order_id
                and local_order.status not in self.TERMINAL_STOP_ORDER_STATUSES
                for local_order in self.active_bot.orders
            ):
                self.active_bot.orders.append(
                    OrderModel(
                        timestamp=int(exchange_order.created_at or time() * 1000),
                        order_id=exchange_order_id,
                        deal_type=DealType.stop_loss,
                        pair=self.kucoin_symbol,
                        order_side=side.value,
                        order_type=OrderType.limit,
                        price=0,
                        stop_price=stop_price,
                        requested_qty=exchange_qty if exchange_qty is not None else qty,
                        qty=0,
                        client_oid=exchange_order.client_oid,
                        time_in_force="GTC",
                        status=OrderStatus.NEW,
                    )
                )
            client_oid = exchange_order.client_oid
            identifier = (
                f"{exchange_order_id} (clientOid {client_oid})"
                if client_oid
                else exchange_order_id
            )
            self.active_bot.add_log(
                f"Reused matching KuCoin stop order {identifier} instead of "
                "placing a duplicate."
            )
            self.active_bot.deal.stop_loss_price = stop_price
            return

        order_model = self.place_conditional_close(stop_price, qty, DealType.stop_loss)
        if order_model is None:
            return
        self.active_bot.deal.stop_loss_price = stop_price

        if order_model.status == OrderStatus.FILLED:
            self.active_bot.add_log(
                "Native stop has execution activity; awaiting position/fill reconciliation."
            )
            self.controller.save(self.active_bot)
            return

        limit_price = stop_limit_price(
            stop_price,
            self.active_bot.position,
            resolve_tick_size(self.kucoin_symbol_data.tick_size, self.price_precision),
        )
        self.controller.update_logs(
            bot=self.active_bot,
            log_message=f"Stop-limit set @ {stop_price}, limit {limit_price}",
        )

    def should_refresh_trailing_stop_loss(
        self,
        current_stop_price: float,
        new_stop_price: float,
        direction: int,
        last_replace_ts_ms: int | None = None,
    ) -> bool:
        if new_stop_price <= 0:
            return False

        if self.trailing_stop_replace_on_cooldown(last_replace_ts_ms):
            return False

        if current_stop_price <= 0:
            return True

        improvement = (new_stop_price - current_stop_price) * direction
        if improvement <= 0:
            return False

        min_improvement = (
            abs(current_stop_price) * self.TRAILING_STOP_REFRESH_MIN_IMPROVEMENT_RATIO
        )
        return improvement >= min_improvement

    def trailing_stop_replace_on_cooldown(self, last_replace_ts_ms: int | None) -> bool:
        if not last_replace_ts_ms or last_replace_ts_ms <= 0:
            return False

        now_ms = int(time() * 1000)
        return now_ms - last_replace_ts_ms < self.TRAILING_STOP_REPLACE_COOLDOWN_MS

    def last_trailing_stop_replace_ts_ms(self) -> int | None:
        _, ts, _ = self._bot_known_trailing_stop_loss()
        return ts

    def take_profit_order(self) -> BotModel:
        """
        Futures take profit:
        - Closes the current futures position with a reduce-only order
          (SELL for longs, BUY for shorts).
        """
        deal_buy_price = self.active_bot.deal.opening_price
        take_profit_pct = self.active_bot.take_profit / 100
        take_profit_multiplier = (
            1 - take_profit_pct
            if self.active_bot.position == Position.short
            else 1 + take_profit_pct
        )
        self.active_bot.deal.take_profit_price = take_profit_multiplier * deal_buy_price

        position = self.kucoin_futures_api.get_futures_position(self.kucoin_symbol)
        if not position or float(position.current_qty) == 0:
            self.active_bot = self.backfill_position_from_fills()
            return self.active_bot

        qty = round_numbers(abs(float(position.current_qty)), 8)
        side = (
            AddOrderReq.SideEnum.BUY
            if self.active_bot.position == Position.short
            else AddOrderReq.SideEnum.SELL
        )
        self.controller.update_logs(
            f"Dispatching futures {side.value} order for take profit...",
            self.active_bot,
        )
        order_base = self.kucoin_futures_api.place_futures_order(
            symbol=self.kucoin_symbol,
            side=side,
            size=qty,
            order_type=OrderType.market,
            reduce_only=True,
            leverage=self.active_bot.futures_leverage,
        )

        order_base.deal_type = DealType.take_profit
        # Convert OrderBase to OrderModel using model_dump/model_construct
        order_data = OrderModel.model_construct(**order_base.model_dump())

        self.active_bot.orders.append(order_data)
        self.active_bot.deal.closing_price = float(order_data.price)
        self.active_bot.deal.closing_qty = float(order_data.qty)
        self.active_bot.deal.closing_timestamp = round_timestamp(order_data.timestamp)
        self.active_bot.deal.current_position_qty = 0
        self.active_bot.status = Status.completed

        if order_data.status == OrderStatus.FILLED:
            self._cleanup_native_protection_after_close()

        self.active_bot.add_log("Completed futures take profit.")
        self.controller.save(self.active_bot)

        return self.active_bot

    def place_trailing_stop_loss(
        self, repurchase_multiplier: float = 1, *, position_qty: float | None = None
    ) -> BotModel | None:
        """
        Place the closing position (stop loss in Kucoin) when the bot (long or short) is
        in a profitable position

        This only places the stop loss order at the exchange, the actual bot status and deal parameters will be updated when the order is filled and the streaming worker reconciles the actual fills (futures_position.order_updates)
        """

        intent = self.active_bot.deal.conditional_close_order
        if intent is not None and intent.order_id is None:
            self.place_conditional_close(
                intent.stop_price, intent.requested_qty, intent.deal_type
            )
            return self.active_bot

        if position_qty is None:
            position = self.kucoin_futures_api.get_futures_position(self.kucoin_symbol)
            if not position or float(position.current_qty) == 0:
                self.active_bot = self.backfill_position_from_fills()
                return self.active_bot
            position_qty = abs(float(position.current_qty))

        qty = round_numbers(position_qty * repurchase_multiplier, 8)
        intended_price = self.active_bot.deal.trailing_stop_loss_price
        _, last_replace_ts_ms, trailing_order_id = self._bot_known_trailing_stop_loss()
        exchange_ok, exchange_price, exchange_qty = self._exchange_stop_loss_details(
            order_id=trailing_order_id
        )
        if not exchange_ok:
            return self.active_bot
        if exchange_price is None and self.stop_limit_awaiting_fill():
            return self.active_bot
        quantity_changed = (exchange_qty is not None and exchange_qty != qty) or any(
            str(order.order_id) == trailing_order_id
            and (order.requested_qty if order.requested_qty > 0 else order.qty) != qty
            for order in self.active_bot.orders
        )
        if quantity_changed and exchange_price is not None:
            # Resizing protection must never loosen a tighter exchange stop.
            direction = self._direction_multiplier()
            if (exchange_price - intended_price) * direction > 0:
                intended_price = exchange_price
                self.active_bot.deal.trailing_stop_loss_price = exchange_price
        if exchange_ok and not quantity_changed:
            if exchange_price is None and self.trailing_stop_replace_on_cooldown(
                last_replace_ts_ms
            ):
                return self.active_bot
            if exchange_price is not None and not self.should_replace_stop_loss_order(
                current_stop_price=exchange_price,
                new_stop_price=intended_price,
                last_replace_ts_ms=last_replace_ts_ms,
                cooldown_ms=self.TRAILING_STOP_REPLACE_COOLDOWN_MS,
            ):
                direction = self._direction_multiplier()
                if (exchange_price - intended_price) * direction > 0:
                    self.active_bot.deal.trailing_stop_loss_price = exchange_price
                    self.controller.save(self.active_bot)
                return self.active_bot

        action = "buy" if self.active_bot.position == Position.short else "sell"
        self.controller.update_logs(
            f"Dispatching futures {action} order for trailing profit...",
            self.active_bot,
        )

        self.cancel_current_sl(
            deal_type=DealType.trailing_profit
            if trailing_order_id is not None
            else None
        )

        order_data = self.place_conditional_close(
            self.active_bot.deal.trailing_stop_loss_price, qty, DealType.trailing_profit
        )
        if order_data is None:
            return self.active_bot

        if order_data.status == OrderStatus.FILLED:
            self.active_bot.add_log(
                "Trailing stop filled; waiting for position and execution reconciliation"
            )
        elif order_data.status == OrderStatus.NEW:
            self.active_bot.add_log(
                f"Trailing stop armed on exchange with status {order_data.status}"
            )
        else:
            self.active_bot.add_log(
                f"Trailing stop placement returned status {order_data.status}; verify exchange order state"
            )

        self.controller.save(self.active_bot)
        return self.active_bot

    def reconcile_trailing_stop_loss(
        self, *, position_qty: float | None = None
    ) -> None:
        """
        Re-place an armed futures trailing stop if the exchange no longer has
        a stop order. The bot-side trailing price is the intended exit once
        trailing has armed.
        """
        intended_price = self.active_bot.deal.trailing_stop_loss_price
        if intended_price <= 0:
            return

        _, last_replace_ts_ms, trailing_order_id = self._bot_known_trailing_stop_loss()
        exchange_ok, exchange_price, exchange_qty = self._exchange_stop_loss_details(
            order_id=trailing_order_id
        )
        if not exchange_ok:
            return
        if exchange_price is None and self.stop_limit_awaiting_fill():
            return

        quantity_changed = (
            exchange_qty is not None
            and exchange_qty
            != (
                position_qty
                if position_qty is not None
                else self.current_position_quantity()
            )
        ) or (
            position_qty is not None
            and any(
                str(order.order_id) == trailing_order_id
                and (order.requested_qty if order.requested_qty > 0 else order.qty)
                != position_qty
                for order in self.active_bot.orders
            )
        )
        if quantity_changed:
            self.active_bot.add_log(
                "Exchange trailing SL quantity changed; resizing full-position protection."
            )
            self.place_trailing_stop_loss(position_qty=position_qty)
            return

        if exchange_price is None and self.trailing_stop_replace_on_cooldown(
            last_replace_ts_ms
        ):
            return

        if exchange_price is not None and not self.should_replace_stop_loss_order(
            current_stop_price=exchange_price,
            new_stop_price=intended_price,
            last_replace_ts_ms=last_replace_ts_ms,
            cooldown_ms=self.TRAILING_STOP_REPLACE_COOLDOWN_MS,
        ):
            return

        reason = (
            "missing"
            if exchange_price is None
            else f"at {exchange_price}, expected {intended_price}"
        )
        self.active_bot.add_log(
            f"Exchange trailing SL {reason} — re-placing trailing stop."
        )
        self.place_trailing_stop_loss(position_qty=position_qty)

    def _actual_fill(self, order: OrderBase | None) -> tuple[float, float]:
        """Best-effort real (filled_qty, avg_price) for a just-placed order.

        place_futures_order()'s own response doesn't reliably carry fill
        details, so query the order and then its fills to get the real numbers.
        Returns zero filled quantity when confirmation is unavailable; callers
        decide how to handle an unconfirmed fill.
        """
        if not order or not order.order_id:
            return 0.0, 0.0
        try:
            details = self.kucoin_futures_api.retrieve_order(str(order.order_id))
            filled_qty = float(details.filled_size or 0)
            avg_price = float(details.avg_deal_price or 0)
            if filled_qty > 0 and avg_price > 0:
                return filled_qty, avg_price
        except Exception:
            pass

        try:
            fills = self.kucoin_futures_api.get_fills(order_id=str(order.order_id))
            matching_fills = [
                fill
                for fill in (fills.items or [])
                if str(fill.order_id) == str(order.order_id)
                and float(fill.size or 0) > 0
                and float(fill.price or 0) > 0
            ]
            filled_qty = sum(float(fill.size) for fill in matching_fills)
            if filled_qty > 0:
                fill_notional = sum(
                    float(fill.size) * float(fill.price) for fill in matching_fills
                )
                return filled_qty, fill_notional / filled_qty
        except Exception:
            pass

        if order.status == OrderStatus.FILLED and order.qty > 0 and order.price > 0:
            return order.qty, order.price
        return 0.0, float(order.price or 0)

    def _close_with_market_fallback(
        self, side: AddOrderReq.SideEnum, qty: int, *, market_only: bool = False
    ) -> list[tuple[OrderBase, float, float]]:
        """Cross the spread with an IOC limit at the 1-tick matching-engine
        price first (better fill than a market order when the book has the
        depth); whatever doesn't fill immediately is guaranteed closed with
        a market order for the residual qty, so this always fully closes.

        Market-only exits skip the IOC leg and use the same fill confirmation.
        Returns every leg that actually filled as (order, filled_qty,
        avg_price) — both legs when the IOC only partially fills — so the
        caller can record every fill and compute a true weighted-average
        close price instead of only the last order placed.
        """
        fills: list[tuple[OrderBase, float, float]] = []
        limit_filled_qty = 0.0
        if not market_only:
            try:
                book = load_futures_order_book(
                    self.kucoin_futures_api, self.kucoin_symbol
                )
                tick_size = resolve_tick_size(
                    self.kucoin_symbol_data.tick_size, self.price_precision
                )
                # Cross the spread by one tick from the best opposite level.
                limit_price = (
                    ceil_price_to_tick(book.asks[0].price + tick_size, tick_size)
                    if side == AddOrderReq.SideEnum.BUY
                    else floor_price_to_tick(book.bids[0].price - tick_size, tick_size)
                )
                limit_order = self.kucoin_futures_api.place_futures_order(
                    symbol=self.kucoin_symbol,
                    side=side,
                    size=qty,
                    price=limit_price,
                    leverage=self.active_bot.futures_leverage,
                    order_type=OrderType.limit,
                    reduce_only=True,
                    time_in_force=AddOrderReq.TimeInForceEnum.IMMEDIATE_OR_CANCEL,
                )
                sleep(self.CLOSE_ALL_FILL_CHECK_SLEEP_S)
                limit_filled_qty, limit_avg_price = self._actual_fill(limit_order)
                limit_filled_qty = min(limit_filled_qty, float(qty))
                if limit_filled_qty > 0:
                    fills.append((limit_order, limit_filled_qty, limit_avg_price))
            except Exception as error:
                self.active_bot.add_log(
                    "IOC close leg unavailable; sending the full residual as a "
                    f"reduce-only market order ({error})."
                )

        remaining_qty = qty - limit_filled_qty
        if remaining_qty <= 0:
            return fills

        market_order = self.kucoin_futures_api.place_futures_order(
            symbol=self.kucoin_symbol,
            side=side,
            size=int(round(remaining_qty)),
            leverage=self.active_bot.futures_leverage,
            order_type=OrderType.market,
            reduce_only=True,
        )
        sleep(self.CLOSE_ALL_FILL_CHECK_SLEEP_S)
        market_filled_qty, market_avg_price = self._actual_fill(market_order)
        if market_filled_qty <= 0:
            raise RuntimeError(
                "Reduce-only market close was submitted but its fill could not be "
                "confirmed; leaving the bot open for exchange-fill reconciliation."
            )
        market_filled_qty = min(market_filled_qty, remaining_qty)
        fills.append((market_order, market_filled_qty, market_avg_price))
        return fills

    def close_all(
        self,
        algorithmic_close: bool = False,
        *,
        deal_type: DealType = DealType.panic_close,
        market_only: bool = False,
        progress: Callable[[int, str], None] | None = None,
    ) -> BotModel:
        """
        Closes all open positions and cancels all orders.
        To be used also for panic selling from terminal.

        Tries a spread-crossing limit order first for a better fill; any
        amount that doesn't fill immediately is closed with a market order
        for whatever qty is left. ``market_only`` skips the limit leg.
        """
        if self.active_bot.entry_mode == EntryMode.conditional_limit:
            # Reload under the same lock as submission before claiming that a
            # waiting candidate is stopped. A stale request may have lost the race.
            with submission_guard(self.active_bot.id) as (bot, _session):
                self.active_bot = bot
                if (
                    bot.entry_mode == EntryMode.conditional_limit
                    and bot.deal.entry_client_oid is None
                    and not bot.orders
                    and bot.deal.opening_timestamp == 0
                    and bot.deal.opening_qty == 0
                    and bot.deal.current_position_qty == 0
                ):
                    bot.status = Status.closed
                    bot.deal.recovery_cancelled = True
                    bot.add_log(
                        "Conditional entry closed: deactivated before submission"
                    )
                    self.controller.save(bot)
                    if progress:
                        progress(95, "Waiting conditional entry closed")
                    return bot
                if bot.status == Status.pending:
                    raise BinbotErrors(
                        "Conditional entry submission has started; deactivation is "
                        "not confirmed. Reconcile the entry order before retrying."
                    )
        if algorithmic_close:
            deal_type = DealType.algorithmic_close
        if progress:
            progress(35, "Cancelling protective and pending orders")
        if (
            deal_type != DealType.stop_loss
            and self.active_bot.recovery_params is not None
        ):
            self.active_bot.deal.recovery_cancelled = True
            self.controller.save(self.active_bot)
        intent = self.active_bot.deal.conditional_close_order
        conditional_order_id = intent.order_id if intent is not None else None
        if self.active_bot.deal.conditional_close_order is not None or any(
            order.deal_type in {DealType.stop_loss, DealType.trailing_profit}
            and order.status not in self.TERMINAL_STOP_ORDER_STATUSES
            for order in self.active_bot.orders
        ):
            self.cancel_current_sl()
        if self.active_bot.deal.position_size_order is not None:
            # Stop recovery before cancelling: a restart must never replay an
            # uncertain increase after the position's protective exit.
            self.active_bot.dynamic_position_sizing = False
            self.controller.save(self.active_bot)
            self.kucoin_futures_api.cancel_all_futures_orders(self.kucoin_symbol)
        position = self.kucoin_futures_api.get_futures_position(self.kucoin_symbol)
        if progress:
            progress(55, "Checking the exchange position")

        if position and float(position.current_qty) != 0:
            if progress:
                progress(65, "Closing the exchange position")
            position_qty = float(position.current_qty)
            qty = abs(int(position_qty))
            close_side = (
                AddOrderReq.SideEnum.BUY
                if position_qty < 0
                else AddOrderReq.SideEnum.SELL
            )
            fills = self._close_with_market_fallback(
                close_side, qty, market_only=market_only
            )

            total_filled_qty = 0.0
            weighted_notional = 0.0
            for order, filled_qty, avg_price in fills:
                order_dict = order.model_dump()
                order_dict["qty"] = filled_qty
                order_dict["price"] = avg_price
                order_model = OrderModel(**order_dict)
                order_model.deal_type = deal_type
                self.active_bot.orders.append(order_model)
                total_filled_qty += filled_qty
                weighted_notional += filled_qty * avg_price

            if total_filled_qty < qty:
                raise RuntimeError(
                    "Futures close did not confirm the full exchange position: "
                    f"confirmed={total_filled_qty}, expected={qty}."
                )
            if progress:
                progress(85, "Close fills confirmed")

            # A stop-limit that partially filled before this close is part of
            # the same exit; blend it in so closing_price reflects every fill.
            partial_stop_fill = next(
                (
                    row
                    for row in self.active_bot.orders
                    if conditional_order_id is not None
                    and str(row.order_id) == conditional_order_id
                    and row.qty > 0
                    and row.price > 0
                ),
                None,
            )
            if partial_stop_fill is not None:
                total_filled_qty += partial_stop_fill.qty
                weighted_notional += partial_stop_fill.qty * partial_stop_fill.price

            # Both legs recorded and blended into a single weighted-average
            # close — a partial IOC fill plus market-fallback residual must
            # not be reported (and downstream-PnL'd) as if the entire
            # position closed at only the last order's price.
            self.active_bot.deal.closing_qty = (
                total_filled_qty if total_filled_qty > 0 else qty
            )
            self.active_bot.deal.closing_price = (
                weighted_notional / total_filled_qty if total_filled_qty > 0 else 0.0
            )
            self.active_bot.deal.closing_timestamp = max(
                order.timestamp for order, _, _ in fills
            )
            self.active_bot.deal.current_position_qty = 0
            # Same rule as a native stop fill: a recovery source stays open so
            # the streaming lifecycle can open its recovery leg.
            if not (
                deal_type == DealType.stop_loss
                and self.active_bot.recovery_params is not None
                and self.recovery_source_enabled()
            ):
                self.active_bot.status = Status.completed
            self._cleanup_native_protection_after_close()
            self.controller.update_logs(
                bot=self.active_bot,
                log_message=f"Futures position closed successfully ({deal_type.value})",
            )

        elif (
            self.active_bot.status == Status.completed
            and self.active_bot.deal.closing_price > 0
        ):
            # A native stop already recorded the close; do not aggregate old
            # partial reductions into it when retiring a pending increase.
            self._cleanup_native_protection_after_close()
        elif (
            not self.active_bot.orders
            and self.active_bot.deal.opening_timestamp == 0
            and self.active_bot.deal.opening_qty == 0
        ):
            self.active_bot.add_log(
                "No futures position, entry order, or opening fill exists; "
                "skipping fill-history reconciliation."
            )
        else:
            self.active_bot = self.backfill_position_from_fills()

        self.controller.save(self.active_bot)
        if progress:
            progress(95, "Bot state saved")
        return self.active_bot
