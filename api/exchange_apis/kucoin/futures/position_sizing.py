"""Fill-confirmed position increases at trailing-profit triggers."""

from decimal import Decimal, ROUND_DOWN
from time import time
from uuid import uuid4

from kucoin_universal_sdk.generate.account.account import GetFuturesAccountReqBuilder
from kucoin_universal_sdk.generate.futures.order import (
    AddOrderReq,
    AddOrderReqBuilder,
    GetOrderByClientOidReqBuilder,
)
from kucoin_universal_sdk.model.common import RestError
from pybinbot import DealType, MarketType, OrderModel, OrderStatus, Position, Status
from pybinbot.models.deal import PositionSizeOrder

from api.exchange_apis.kucoin.futures.futures_deal import KucoinPositionDeal


class DynamicPositionSizing:
    """Increase position size without taking ownership of protective exits.

    Persist an intent before submitting. After an ambiguous response, look up
    that same client ID on subsequent ticks. Recovery reuses the original ID
    so exchange deduplication prevents a second adjustment.
    """

    def __init__(self, execution: KucoinPositionDeal) -> None:
        self.execution = execution

    NOT_FOUND_RETRY_COUNT = 3
    NOT_FOUND_GRACE_MS = 60_000

    @staticmethod
    def adjustment_quantity(quantity: float, percentage: float, lot_size: int) -> int:
        lots = (
            Decimal(str(quantity)) * Decimal(str(percentage)) / 100 / lot_size
        ).to_integral_value(rounding=ROUND_DOWN)
        return int(lots) * lot_size

    def fallback(self, reason: str) -> None:
        bot = self.execution.active_bot
        bot.dynamic_position_sizing = False
        bot.trailing = True
        # A fixed TP must not close the position on the very tick that the
        # failed scale-in hands control back to trailing profit.
        bot.take_profit = 0
        bot.deal.take_profit_price = 0
        bot.deal.position_size_reference_price = 0
        bot.add_log(
            f"Dynamic position sizing disabled: {reason}. Using normal trailing profit."
        )
        self.execution.recompute_derived_prices()
        self.execution.controller.save(bot)
        self.execution.reconcile_exchange_sl()

    def reconcile(self) -> None:
        bot = self.execution.active_bot
        deal = bot.deal
        pending = deal.position_size_order
        if pending is None:
            return
        request = (
            GetOrderByClientOidReqBuilder().set_client_oid(pending.client_oid).build()
        )
        try:
            order = self.execution.kucoin_futures_api.futures_order_api.get_order_by_client_oid(
                request
            )
        except RestError as exc:
            # 100001 is also used for invalid parameters. Only an explicit
            # missing-order response is evidence for submission recovery.
            message = str(exc.response.message).lower()
            if str(exc.response.code) != "100001" or not any(
                phrase in message
                for phrase in (
                    "order not found",
                    "order does not exist",
                    "order not exist",
                    "error.getorder.ordernotexist",
                )
            ):
                raise
            now_ms = int(time() * 1000)
            if pending.not_found_count == 0:
                pending.not_found_since_ms = now_ms
            pending.not_found_count += 1
            self.execution.controller.save(bot)
            direction = 1 if bot.position == Position.long else -1
            if (
                bot.dynamic_position_sizing
                and bot.status == Status.active
                and not pending.reducing
                and (
                    deal.stop_loss_price == 0
                    or (deal.current_price - deal.stop_loss_price) * direction > 0
                )
                and (
                    deal.trailing_stop_loss_price == 0
                    or (deal.current_price - deal.trailing_stop_loss_price) * direction
                    > 0
                )
                and pending.not_found_count >= self.NOT_FOUND_RETRY_COUNT
                and now_ms - pending.not_found_since_ms >= self.NOT_FOUND_GRACE_MS
            ):
                bot.add_log(
                    f"Recovering missing dynamic sizing order {pending.client_oid} "
                    "by resubmitting the same client ID."
                )
                self.submit(pending, deal.current_price)
            return
        if pending.not_found_count:
            pending.not_found_count = 0
            pending.not_found_since_ms = 0
            self.execution.controller.save(bot)
        quantity = float(order.filled_size or 0)
        price = float(order.avg_deal_price or 0)
        fill_complete = not order.is_active and (quantity == 0 or price > 0)
        remaining = deal.current_position_qty
        if quantity > 0:
            # KuCoin reports cumulative fills. Always derive from the persisted
            # pre-order snapshot, including after a restart; never add the same
            # partial fill to an already updated position a second time.
            signed_quantity = -quantity if pending.reducing else quantity
            remaining = max(0, pending.quantity_before + signed_quantity)
            if not pending.reducing and price > 0:
                deal.opening_price = (
                    pending.entry_price_before * pending.quantity_before
                    + price * quantity
                ) / remaining
            deal.current_position_qty = remaining
            deal.base_order_size = remaining
            # Protect observed contracts even when the fill price is delayed.
            # Keep lifecycle triggers and protective prices intact.
            if fill_complete:
                timestamp = int(order.end_at or order.updated_at or order.created_at)
                side = (
                    "sell"
                    if (bot.position == Position.long) == pending.reducing
                    else "buy"
                )
                bot.orders.append(
                    OrderModel(
                        order_id=order.id,
                        pair=bot.pair,
                        order_side=side,
                        order_type="MARKET",
                        time_in_force="GTC",
                        timestamp=timestamp,
                        qty=quantity,
                        price=price,
                        status=OrderStatus.FILLED,
                        deal_type=DealType.stop_loss
                        if pending.reducing
                        else DealType.base_order,
                    )
                )
                if remaining == 0:
                    bot.status = Status.completed
                    deal.closing_qty = quantity
                    deal.closing_price = price
                    deal.closing_timestamp = timestamp
                bot.add_log(
                    f"Dynamic position {'reduced' if pending.reducing else 'increased'} "
                    f"by {quantity} contracts at {price}; remaining {remaining}."
                )
        elif fill_complete:
            bot.add_log(
                "Dynamic position adjustment ended without a fill; thresholds unchanged."
            )
        else:
            return
        if fill_complete:
            deal.position_size_order = None
        self.execution.controller.save(bot)
        if quantity > 0 and remaining > 0 and bot.status == Status.active:
            # The position endpoint can lag these confirmed fills. Pass the
            # observed quantity through to protection instead of shrinking it
            # back to a stale position response.
            self.execution.reconcile_exchange_sl(position_qty=remaining)

    def process(
        self, current_price: float, *, trailing_profit_reached: bool = False
    ) -> bool:
        """Reconcile a pending intent or increase once at a trailing-profit trigger."""
        bot = self.execution.active_bot
        deal = bot.deal
        if current_price > 0:
            deal.current_price = current_price
        if deal.position_size_order is not None:
            if deal.position_size_order.submission_phase == "prepared":
                # No API call is allowed before the submitting phase is saved.
                # This intent can therefore be discarded without guessing
                # whether an exchange order exists or replaying a stale signal.
                deal.position_size_order = None
                self.fallback("recovered an intent interrupted before order submission")
                return False
            try:
                self.reconcile()
            except RestError:
                if bot.dynamic_position_sizing:
                    raise
                # A disabled sizing mode must not hold normal exits hostage
                # to an unresolved lookup retained for bookkeeping.
                bot.add_log(
                    "Pending sizing order lookup failed; continuing normal exits."
                )
                self.execution.controller.save(bot)
            return bot.dynamic_position_sizing
        if (
            not bot.dynamic_position_sizing
            or bot.status != Status.active
            or not trailing_profit_reached
        ):
            return False
        # Validate again because table hydration and model_construct bypass
        # BotBase validation, and strategy/API updates can mutate parameters.
        if (
            bot.market_type != MarketType.FUTURES
            or bot.trailing_profit <= 0
            or not 0 < bot.trailing_deviation < 100
            or not 0 < deal.position_size_pct <= 100
        ):
            raise ValueError("Invalid dynamic position sizing configuration")
        if current_price <= 0 or deal.opening_price <= 0:
            return False
        direction = 1 if bot.position == Position.long else -1

        position = self.execution.kucoin_futures_api.get_futures_position(
            self.execution.kucoin_symbol
        )
        signed_quantity = float(position.current_qty)
        if signed_quantity * direction <= 0:
            return False
        quantity = abs(signed_quantity)
        lot_size = self.execution.kucoin_symbol_data.lot_size or 1
        adjustment = self.adjustment_quantity(
            quantity, deal.position_size_pct, lot_size
        )
        if adjustment == 0:
            self.fallback("increase is smaller than the exchange lot size")
            return False

        request = GetFuturesAccountReqBuilder().set_currency(bot.fiat).build()
        account = (
            self.execution.kucoin_futures_api.futures_account_api.get_futures_account(
                request
            )
        )
        available = float(account.available_balance or 0)
        required = self.execution.required_margin_for_contracts(
            adjustment, current_price
        )
        if required > available:
            self.fallback(
                f"insufficient futures funds (requires {required}, available {available})"
            )
            return False

        pending = PositionSizeOrder(
            client_oid=str(uuid4()),
            submission_phase="prepared",
            reducing=False,
            quantity_before=quantity,
            entry_price_before=deal.opening_price,
            requested_qty=adjustment,
            signal_price=current_price,
        )
        deal.position_size_order = pending
        # Commit before any exchange side effect, including a possible timeout.
        self.execution.controller.save(bot)
        if not self.submit(pending, current_price):
            return False
        self.reconcile()
        return True

    def submit(self, pending: PositionSizeOrder, current_price: float) -> bool:
        """Submit or replay one persisted intent using its original client ID."""
        bot = self.execution.active_bot
        retrying = pending.submission_phase == "submitting"
        if retrying and not pending.reducing:
            # A retry must not rely on the wallet snapshot before the crash.
            request = GetFuturesAccountReqBuilder().set_currency(bot.fiat).build()
            account = self.execution.kucoin_futures_api.futures_account_api.get_futures_account(
                request
            )
            available = float(account.available_balance or 0)
            required = self.execution.required_margin_for_contracts(
                pending.requested_qty, current_price
            )
            if current_price <= 0 or required > available:
                # Preserve the uncertain identity for reconciliation, restore
                # normal protection, and never replay after falling back.
                self.fallback("missing order recovery has insufficient futures funds")
                return False

        pending.submission_phase = "submitting"
        pending.not_found_count = 0
        pending.not_found_since_ms = 0
        # A crash on either side of add_order now leaves a recoverable intent.
        self.execution.controller.save(bot)
        side = (
            AddOrderReq.SideEnum.SELL
            if (bot.position == Position.long) == pending.reducing
            else AddOrderReq.SideEnum.BUY
        )
        request = (
            AddOrderReqBuilder()
            .set_client_oid(pending.client_oid)
            .set_symbol(self.execution.kucoin_symbol)
            .set_side(side)
            .set_type(AddOrderReq.TypeEnum.MARKET)
            .set_size(int(pending.requested_qty))
            .set_leverage(str(self.execution.active_bot.futures_leverage))
            .set_reduce_only(pending.reducing)
            .build()
        )
        try:
            self.execution.kucoin_futures_api.futures_order_api.add_order(request)
        except RestError as exc:
            code = str(exc.response.code)
            message = str(exc.response.message).lower()
            if code == "300018":
                # An accepted order can lag the lookup endpoint. Never replace
                # its ID or infer that this duplicate response is a fill.
                return True
            if not pending.reducing and (
                code == "300003"
                or (code == "400100" and "account.available.amount" in message)
            ):
                if not retrying:
                    bot.deal.position_size_order = None
                self.fallback("exchange rejected increase for insufficient funds")
                return False
            raise
        return True
