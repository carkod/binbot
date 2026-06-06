from math import ceil
from time import time
from typing import Type, Union

from bots.models import (
    BotCreateRequest,
    BotModel,
    OrderModel,
    RecoveryParamsRequest,
)
from databases.crud.bot_crud import BotTableCrud
from databases.crud.paper_trading_crud import PaperTradingTableCrud
from databases.tables.bot_table import BotTable, PaperTradingTable
from exchange_apis.kucoin.futures.futures_deal import KucoinPositionDeal
from kucoin_universal_sdk.generate.futures.order.model_add_order_req import AddOrderReq
from kucoin_universal_sdk.model.common import RestError
from pybinbot import (
    DealType,
    KucoinApi,
    KucoinFutures,
    MarketType,
    OrderBase,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    Status,
    convert_to_kucoin_symbol,
    round_numbers,
    round_timestamp,
)
from streaming.futures_position import FuturesPosition
from streaming.spot_position import SpotPosition


class PositionDeal(KucoinPositionDeal):
    """
    Position-based implementation for Kucoin futures trading.

    Previously called FuturesLongDeal, but long or short position logic is all handled within this class
    since Kucoin Futures logic allows easy isolated margin and switching positions.

    Happens after open_deal is executed
    formerly known as streaming updates
    these operations are triggered by websockets
    """

    TRAILING_STOP_REFRESH_MIN_IMPROVEMENT_RATIO = 0.002
    RECOVERY_ATR_WINDOW = 14
    RECOVERY_STRUCTURE_WINDOW = 4
    RECOVERY_STOP_CAP_PCT = 6.5
    RECOVERY_STRUCTURE_ATR_BUFFER = 0.5
    RECOVERY_ATR_FLOOR_MULTIPLIER = 1.5
    RECOVERY_FALLBACK_BUFFER_PCT = 0.75
    RECOVERY_TRAILING_PROFIT_CAP_PCT = 6.0
    RECOVERY_TRAILING_MIN_GAP_PCT = 0.35
    RECOVERY_COOLDOWN_MINUTES = 240

    def __init__(
        self,
        bot: BotModel,
        db_table: Type[BotTable] | Type[PaperTradingTable] = BotTable,
        base_streaming=None,
    ) -> None:
        super().__init__(bot=bot, db_table=db_table, base_streaming=base_streaming)
        self.active_bot = bot
        self.price_precision = self.symbol_info.price_precision
        self.qty_precision = self.symbol_info.qty_precision
        self.kucoin_symbol = convert_to_kucoin_symbol(bot)
        # Inherited variables for mypy
        self.api: KucoinApi | KucoinFutures
        self.controller: BotTableCrud | PaperTradingTableCrud
        self.klines: list | None

    def should_refresh_trailing_stop_loss(
        self,
        current_stop_price: float,
        new_stop_price: float,
        direction: int,
    ) -> bool:
        if new_stop_price <= 0:
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

    def place_reversal_reentry_order(
        self,
        contracts: float,
        repurchase_multiplier: float = 1,
    ) -> OrderBase | None:
        """
        Second order for reverse_position,
        if first order succeeds, we want to use as much balance as possible
        in the case we can't fulfill fiat_order_size with original number of contracts
        before reversal
        """
        adjusted_contracts = round_numbers(
            float(contracts) * float(repurchase_multiplier),
            self.qty_precision,
        )

        if adjusted_contracts <= 0:
            self.active_bot.add_log(
                "Failed to place repurchase order during reversal. Repurchase size reached 0 contracts."
            )
            return None

        try:
            if self.active_bot.position == Position.short:
                return self.kucoin_futures_api.sell(
                    symbol=self.kucoin_symbol,
                    qty=adjusted_contracts,
                    reduce_only=False,
                    leverage=self.symbol_info.futures_leverage,
                )

            return self.kucoin_futures_api.buy(
                symbol=self.kucoin_symbol,
                qty=adjusted_contracts,
                reduce_only=False,
            )
        except RestError as kucoin_error:
            code = int(kucoin_error.response.code)
            if code not in (400100, 200005, 200004):
                raise kucoin_error

            next_multiplier = round_numbers(repurchase_multiplier - 0.25, 2)
            self.active_bot.add_log(
                f"Repurchase order hit insufficient balance with multiplier {repurchase_multiplier}. Retrying with {next_multiplier}."
            )

            if next_multiplier <= 0:
                self.active_bot.add_log(
                    "Failed to place repurchase order during reversal after reducing contracts to 0."
                )
                return None

            return self.place_reversal_reentry_order(
                contracts=contracts,
                repurchase_multiplier=next_multiplier,
            )

    def take_profit_order(self) -> BotModel:
        """
        Futures take profit:
        - Closes the current futures position with a reduce-only order
          (SELL for longs, BUY for shorts).
        """
        deal_buy_price = self.active_bot.deal.opening_price
        buy_total_qty = self.active_bot.deal.opening_qty
        take_profit_pct = float(self.active_bot.take_profit or 0) / 100
        take_profit_multiplier = (
            1 - take_profit_pct
            if self.active_bot.position == Position.short
            else 1 + take_profit_pct
        )
        self.active_bot.deal.take_profit_price = take_profit_multiplier * float(
            deal_buy_price
        )
        close_side = (
            OrderSide.buy
            if self.active_bot.position == Position.short
            else OrderSide.sell
        )

        # Paper trading: do not hit the exchange, just simulate an order
        if isinstance(self.controller, PaperTradingTableCrud):
            price = float(self.active_bot.deal.current_price or deal_buy_price)
            qty = round_numbers(buy_total_qty, 8)
            order_data = OrderModel(
                timestamp=int(time() * 1000),
                order_id="paper-futures-tp",
                deal_type=DealType.take_profit,
                pair=self.kucoin_symbol,
                order_side=close_side,
                order_type="MARKET",
                price=price,
                qty=float(qty),
                time_in_force="GTC",
                status=OrderStatus.FILLED,
            )
        else:
            # Real futures: close current LONG position via reduce-only SELL
            position = self.kucoin_futures_api.get_futures_position(self.kucoin_symbol)
            if not position or float(position.current_qty) == 0:
                self.active_bot = self.backfill_position_from_fills()
                return self.active_bot

            qty = round_numbers(abs(float(position.current_qty)), 8)
            if self.active_bot.position == Position.short:
                self.controller.update_logs(
                    "Dispatching futures buy order for take profit...",
                    self.active_bot,
                )
                order_base = self.kucoin_futures_api.buy(
                    symbol=self.kucoin_symbol,
                    qty=qty,
                    reduce_only=True,
                )
            else:
                self.controller.update_logs(
                    "Dispatching futures sell order for take profit...",
                    self.active_bot,
                )
                order_base = self.kucoin_futures_api.place_futures_order(
                    symbol=self.kucoin_symbol,
                    side=AddOrderReq.SideEnum.SELL,
                    size=qty,
                    order_type=OrderType.market,
                    reduce_only=True,
                    leverage=self.symbol_info.futures_leverage,
                )

            order_base.deal_type = DealType.take_profit
            # Convert OrderBase to OrderModel using model_dump/model_construct
            order_data = OrderModel.model_construct(**order_base.model_dump())

        self.active_bot.orders.append(order_data)
        self.active_bot.deal.closing_price = float(order_data.price)
        self.active_bot.deal.closing_qty = float(order_data.qty)
        self.active_bot.deal.closing_timestamp = round_timestamp(order_data.timestamp)
        self.active_bot.status = Status.completed

        self.active_bot.add_log("Completed futures take profit.")
        self.controller.save(self.active_bot)

        return self.active_bot

    def execute_stop_loss(self, reference_price: float | None = None) -> BotModel:
        """
        Place a stop loss limit order, since we've hit the threshold

        - Hard sell (order status="FILLED" immediately) initial amount crypto in deal
        - Close current opened take profit order
        - Deactivate bot

        When ``reference_price`` is provided the close order is routed through the
        anti-wick escalation path (band-capped IOC → market fallback) so the fill
        stays within a sane slippage band off the last-closed-candle price.
        """
        self.controller.update_logs("Placing Futures stop loss...", self.active_bot)

        # Paper trading: simulate without hitting the exchange
        if isinstance(self.controller, PaperTradingTableCrud):
            qty = self.active_bot.deal.opening_qty
            if qty <= 0:
                return self.active_bot

            # Use reference_price as the simulated fill price when available so
            # paper-trade results reflect the anti-wick capped behaviour.
            price = float(
                reference_price
                if reference_price is not None
                else (self.active_bot.deal.current_price or 0)
            )
            close_side = (
                OrderSide.buy
                if self.active_bot.position == Position.short
                else OrderSide.sell
            )
            stop_loss_order = OrderModel(
                timestamp=int(time() * 1000),
                order_id="paper-futures-sl",
                deal_type=DealType.stop_loss,
                pair=self.kucoin_symbol,
                order_side=close_side,
                order_type=OrderType.limit,
                price=price,
                qty=float(qty),
                time_in_force="GTC",
                status=OrderStatus.FILLED,
            )
        else:
            qty = self.active_bot.deal.opening_qty
            try:
                if self.active_bot.position == Position.short:
                    order_base = self.kucoin_futures_api.buy(
                        symbol=self.kucoin_symbol,
                        qty=qty,
                        reduce_only=True,
                        reference_price=reference_price,
                    )
                else:
                    order_base = self.kucoin_futures_api.sell(
                        symbol=self.kucoin_symbol,
                        qty=qty,
                        reduce_only=True,
                        leverage=self.symbol_info.futures_leverage,
                        reference_price=reference_price,
                    )

            except RestError as e:
                if float(e.response.code) == 300009:
                    self.controller.update_logs(
                        bot=self.active_bot,
                        log_message=f"{str(e.response.message)}",
                    )
                    self.active_bot.status = Status.completed
                    self.controller.save(self.active_bot)
                    return self.active_bot
                else:
                    self.controller.update_logs(
                        bot=self.active_bot,
                        log_message=f"Failed to execute stop loss order: {str(e.response.message)}",
                    )
                    self.active_bot.status = Status.error
                    return self.active_bot

            order_base.deal_type = DealType.stop_loss
            stop_loss_order = OrderModel.model_construct(**order_base.model_dump())

        self.active_bot.orders.append(stop_loss_order)
        self.active_bot.deal.closing_price = float(stop_loss_order.price)
        self.active_bot.deal.closing_qty = float(stop_loss_order.qty)
        self.active_bot.deal.closing_timestamp = stop_loss_order.timestamp
        self.active_bot.add_log("Completed futures Stop loss.")

        if stop_loss_order.status != OrderStatus.FILLED:
            self.controller.update_logs(
                bot=self.active_bot,
                log_message=f"Stop loss order not filled immediately, got status {stop_loss_order.status}. Manual intervention may be required.",
            )
        else:
            self.active_bot.status = Status.completed

        self.controller.save(self.active_bot)

        return self.active_bot

    def place_trailing_stop_loss(
        self, repurchase_multiplier: float = 1
    ) -> BotModel | None:
        """
        Place the closing position (stop loss in Kucoin) when the bot (long or short) is
        in a profitable position

        This only places the stop loss order at the exchange, the actual bot status and deal parameters will be updated when the order is filled and the system receives the update via websocket (handled in futures_position.order_updates)
        """

        if isinstance(self.controller, PaperTradingTableCrud):
            # all qty simulated
            qty = self.active_bot.deal.opening_qty or 1.0
            price = float(self.active_bot.deal.current_price or 0)
            close_side = (
                OrderSide.buy
                if self.active_bot.position == Position.short
                else OrderSide.sell
            )
            order_data = OrderModel(
                timestamp=int(time() * 1000),
                order_id="paper-futures-trail",
                deal_type=DealType.trailing_profit,
                pair=self.kucoin_symbol,
                order_side=close_side,
                order_type="MARKET",
                price=price,
                qty=float(qty),
                time_in_force="GTC",
                status=OrderStatus.FILLED,
            )
        else:
            position = self.kucoin_futures_api.get_futures_position(self.kucoin_symbol)
            if not position or float(position.current_qty) == 0:
                # If position doesn't exist, there's no point in trailing anymore
                # so we backfill orders and finish
                self.active_bot = self.backfill_position_from_fills()
                return self.active_bot

            qty = round_numbers(
                abs(float(position.current_qty)) * repurchase_multiplier, 8
            )
            action = "buy" if self.active_bot.position == Position.short else "sell"
            self.controller.update_logs(
                f"Dispatching futures {action} order for trailing profit...",
                self.active_bot,
            )

            # since trailing_profit only runs when trail is broken
            # we can assume stop loss needs to be replaced
            # if it constantly runs, then we need to add conditional logic
            # to avoid cancelling constantly
            self.cancel_current_sl()

            if self.active_bot.position == Position.short:
                order_base: OrderBase = self.kucoin_futures_api.place_futures_order(
                    side=AddOrderReq.SideEnum.BUY,
                    symbol=self.kucoin_symbol,
                    size=qty,
                    reduce_only=True,
                    order_type=OrderType.market,
                    stop_price_type=AddOrderReq.StopPriceTypeEnum.MARK_PRICE,
                    stop=AddOrderReq.StopEnum.UP,
                    stop_price=self.active_bot.deal.trailing_stop_loss_price,
                    leverage=self.symbol_info.futures_leverage,
                )
            else:
                order_base = self.kucoin_futures_api.place_futures_order(
                    side=AddOrderReq.SideEnum.SELL,
                    symbol=self.kucoin_symbol,
                    size=qty,
                    reduce_only=True,
                    order_type=OrderType.market,
                    stop_price_type=AddOrderReq.StopPriceTypeEnum.MARK_PRICE,
                    stop=AddOrderReq.StopEnum.DOWN,
                    stop_price=self.active_bot.deal.trailing_stop_loss_price,
                    leverage=self.symbol_info.futures_leverage,
                )

            order_base.deal_type = DealType.trailing_profit
            order_data = OrderModel(**order_base.model_dump())

        self.remove_stale_orders()
        self.active_bot.orders.append(order_data)

        if order_data.status != OrderStatus.FILLED:
            self.active_bot.add_log(
                f"Trailing profit order not filled immediately, got status {order_data.status}"
            )
        else:
            self.active_bot.add_log(
                "Completed futures take profit after failing to break trailing"
            )

        self.controller.save(self.active_bot)
        return self.active_bot

    def reconcile_trailing_stop_loss(self) -> None:
        """
        Re-place an armed futures trailing stop if the exchange no longer has
        a stop order. The bot-side trailing price is the intended exit once
        trailing has armed.
        """
        intended_price = float(self.active_bot.deal.trailing_stop_loss_price)
        if intended_price <= 0:
            return

        exchange_ok, exchange_price = self._exchange_stop_loss_price()
        if not exchange_ok:
            return

        if exchange_price is not None and not self.should_replace_stop_loss_order(
            current_stop_price=exchange_price,
            new_stop_price=intended_price,
            last_replace_ts_ms=None,
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
        self.place_trailing_stop_loss()

    # Strategies whose reversal chain has historically compounded losses on chop;
    # for these, a second SL on the same pair within the cooldown closes instead of flipping.
    _NO_REVERSAL_AFTER_LOSS_NAMES = {
        "coinrule_buy_the_dip",
        "coinrule_price_tracker",
        "bb_extreme_reversion",
    }

    def _is_recovery_bot(self) -> bool:
        recovery_params = getattr(self.active_bot, "recovery_params", None)
        return (
            recovery_params is not None and recovery_params.reversal_path == "recovery"
        )

    def _recovery_atr_pct(self, reference_price: float) -> float | None:
        if reference_price <= 0 or self.klines is None:
            return None

        closed_candles = self.klines[:-1]
        if len(closed_candles) < self.RECOVERY_ATR_WINDOW + 1:
            return None

        true_ranges: list[float] = []
        start_index = len(closed_candles) - self.RECOVERY_ATR_WINDOW
        for index in range(start_index, len(closed_candles)):
            previous_close = float(closed_candles[index - 1][4])
            high = float(closed_candles[index][2])
            low = float(closed_candles[index][3])
            true_ranges.append(
                max(
                    high - low,
                    abs(high - previous_close),
                    abs(low - previous_close),
                )
            )

        if not true_ranges:
            return None

        return (sum(true_ranges) / len(true_ranges) / reference_price) * 100

    def compute_recovery_stop_loss_pct(
        self,
        reference_price: float,
        target_position: Position,
    ) -> float | None:
        if reference_price <= 0 or self.klines is None:
            self.active_bot.add_log(
                "Recovery skipped: no valid reference price or kline structure."
            )
            return None

        closed_candles = self.klines[:-1]
        if len(closed_candles) < self.RECOVERY_STRUCTURE_WINDOW:
            self.active_bot.add_log(
                "Recovery skipped: fewer than four closed candles available for structure invalidation."
            )
            return None

        structure_candles = closed_candles[-self.RECOVERY_STRUCTURE_WINDOW :]
        if target_position == Position.short:
            structure_price = max(float(candle[2]) for candle in structure_candles)
            structure_distance_pct = (
                max(structure_price - reference_price, 0) / reference_price * 100
            )
        else:
            structure_price = min(float(candle[3]) for candle in structure_candles)
            structure_distance_pct = (
                max(reference_price - structure_price, 0) / reference_price * 100
            )

        atr_pct = self._recovery_atr_pct(reference_price)
        if atr_pct is None:
            buffered_structure_pct = (
                structure_distance_pct + self.RECOVERY_FALLBACK_BUFFER_PCT
            )
            recovery_stop_pct = max(
                float(self.active_bot.stop_loss),
                buffered_structure_pct,
            )
            self.active_bot.add_log(
                "Recovery ATR unavailable; using four-candle structure plus "
                f"{self.RECOVERY_FALLBACK_BUFFER_PCT:.2f}% fixed buffer."
            )
        else:
            buffered_structure_pct = (
                structure_distance_pct + self.RECOVERY_STRUCTURE_ATR_BUFFER * atr_pct
            )
            recovery_stop_pct = max(
                float(self.active_bot.stop_loss),
                buffered_structure_pct,
                self.RECOVERY_ATR_FLOOR_MULTIPLIER * atr_pct,
            )

        if buffered_structure_pct > self.RECOVERY_STOP_CAP_PCT:
            self.active_bot.add_log(
                "Recovery skipped: structure invalidation requires "
                f"{buffered_structure_pct:.2f}%, above "
                f"{self.RECOVERY_STOP_CAP_PCT:.2f}% cap."
            )
            return None

        recovery_stop_pct = min(recovery_stop_pct, self.RECOVERY_STOP_CAP_PCT)
        self.active_bot.add_log(
            "Recovery hybrid stop computed at "
            f"{recovery_stop_pct:.2f}% "
            f"(structure distance {structure_distance_pct:.2f}%)."
        )
        return round_numbers(recovery_stop_pct, 2)

    def _start_recovery_cooldown(self) -> None:
        configured_symbol_cooldown = int(getattr(self.symbol_info, "cooldown", 0) or 0)
        bot_cooldown_seconds = int(self.active_bot.cooldown or 0) * 60
        cooldown_seconds = max(
            configured_symbol_cooldown,
            bot_cooldown_seconds,
            self.RECOVERY_COOLDOWN_MINUTES * 60,
        )

        try:
            self.symbols_crud.start_cooldown(
                symbol=self.active_bot.pair,
                cooldown_seconds=cooldown_seconds,
            )
            self.active_bot.add_log(
                f"Recovery cooldown started for {cooldown_seconds // 60} minutes."
            )
        except Exception as exc:
            self.active_bot.add_log(f"Failed to start recovery symbol cooldown: {exc}")

    def _source_loss_fiat(
        self,
        source_bot: BotModel,
        closing_price: float,
        contracts: float,
    ) -> float:
        entry_price = float(source_bot.deal.opening_price)
        if entry_price <= 0 or closing_price <= 0 or contracts <= 0:
            return 0

        multiplier = float(
            getattr(self.kucoin_symbol_data, "multiplier", 0)
            or getattr(self.kucoin_futures_api, "DEFAULT_MULTIPLIER", 1)
            or 1
        )
        direction = 1 if source_bot.position == Position.long else -1
        price_pnl = (closing_price - entry_price) * contracts * multiplier * direction
        loss = max(-price_pnl, 0) + float(source_bot.deal.total_commissions)
        return round_numbers(loss, 8)

    def _recovery_trailing_params(
        self,
        source_bot: BotModel,
        recovery_stop_pct: float,
    ) -> tuple[float, float]:
        trailing_profit = min(
            ceil(
                max(
                    float(source_bot.trailing_profit),
                    0.9 * recovery_stop_pct,
                )
                * 100
            )
            / 100,
            self.RECOVERY_TRAILING_PROFIT_CAP_PCT,
        )
        trailing_deviation = min(
            ceil(
                max(
                    float(source_bot.trailing_deviation),
                    0.45 * recovery_stop_pct,
                )
                * 100
            )
            / 100,
            trailing_profit - self.RECOVERY_TRAILING_MIN_GAP_PCT,
        )
        return (
            trailing_profit,
            max(
                round_numbers(trailing_deviation, 2),
                0,
            ),
        )

    def _prior_leg_was_loss(self) -> bool:
        """
        True when the most recent completed bot for this pair+name (within the
        active bot's cooldown window) closed at a loss. Used by the reversal
        circuit-breaker to avoid the loss → flip → loss → flip chain on
        chop-prone strategies.
        """
        if self.active_bot.name not in self._NO_REVERSAL_AFTER_LOSS_NAMES:
            return False
        try:
            cooldown_minutes = max(int(self.active_bot.cooldown or 0), 240)
            window_ms = cooldown_minutes * 60 * 1000
            now_ms = int(time() * 1000)
            candidates = self.controller.get(
                status=Status.completed,
                bot_name=self.active_bot.name,
                start_date=now_ms - window_ms,
                end_date=now_ms,
                limit=20,
            )
        except Exception as exc:
            self.active_bot.add_log(
                f"Reversal circuit-breaker lookup failed ({exc}); allowing reversal."
            )
            return False

        for prev in candidates:
            if prev.pair != self.active_bot.pair:
                continue
            if str(prev.id) == str(self.active_bot.id):
                continue
            deal = getattr(prev, "deal", None)
            if deal is None:
                continue
            op = float(getattr(deal, "opening_price", 0) or 0)
            cp = float(getattr(deal, "closing_price", 0) or 0)
            if op <= 0 or cp <= 0:
                continue
            prev_position = getattr(prev, "position", None)
            prev_position_value = getattr(prev_position, "value", prev_position)
            prev_direction = 1 if str(prev_position_value).lower() == "long" else -1
            prev_pct = ((cp - op) / op) * 100 * prev_direction
            if prev_pct < 0:
                return True
        return False

    def reverse_position(self, reference_price: float | None = None) -> BotModel:
        """
        Close the current position with a reduce_only order, mark source bot as
        completed, then create a new opposite-direction bot in Status.pending.
        The next exit() tick promotes pending -> active via open_deal(), which
        places the base_order at fresh market price.

        When ``reference_price`` is provided the reduce-only close leg is routed
        through the anti-wick escalation path so the reversal close doesn't fill
        into a wick.  The new bot's re-entry (open_deal) always uses fresh market
        price and is unaffected.
        """
        if self._is_recovery_bot():
            self.active_bot.add_log(
                "Recovery stop loss reached; closing without another reversal."
            )
            self.active_bot = self.execute_stop_loss(reference_price=reference_price)
            if self.active_bot.status == Status.completed:
                self._start_recovery_cooldown()
                self.controller.save(self.active_bot)
            return self.active_bot

        source_bot = self.active_bot
        target_position = (
            Position.short if source_bot.position == Position.long else Position.long
        )

        current_position = self.kucoin_futures_api.get_futures_position(
            self.kucoin_symbol
        )
        if not current_position or abs(current_position.current_qty) == 0:
            source_bot.add_log("No open futures position to reverse; aborting.")
            source_bot.status = Status.error
            self.controller.save(source_bot)
            self.active_bot = source_bot
            return source_bot

        current_contracts = abs(float(current_position.current_qty))

        try:
            if source_bot.position == Position.long:
                close_order = self.kucoin_futures_api.sell(
                    symbol=self.kucoin_symbol,
                    qty=current_contracts,
                    reduce_only=True,
                    leverage=self.symbol_info.futures_leverage,
                    reference_price=reference_price,
                )
            else:
                close_order = self.kucoin_futures_api.buy(
                    symbol=self.kucoin_symbol,
                    qty=current_contracts,
                    reduce_only=True,
                    reference_price=reference_price,
                )
        except RestError as kucoin_error:
            msg = kucoin_error.response.message
            source_bot.add_log(f"Reduce-only close failed during reversal: {msg}")
            source_bot.status = Status.error
            self.controller.save(source_bot)
            self.active_bot = source_bot
            return source_bot

        closing_order = OrderModel(
            timestamp=int(time() * 1000),
            order_id=str(close_order.order_id),
            deal_type=DealType.margin_short,
            pair=self.kucoin_symbol,
            order_side=close_order.order_side,
            order_type=close_order.order_type,
            price=close_order.price,
            qty=close_order.qty,
            time_in_force=close_order.time_in_force,
            status=close_order.status,
        )
        source_bot.orders.append(closing_order)
        source_bot.deal.closing_price = closing_order.price
        source_bot.deal.closing_qty = current_contracts
        source_bot.deal.closing_timestamp = closing_order.timestamp
        source_bot.status = Status.completed
        source_bot.add_log(
            "Reversal: reduce_only source close placed; evaluating opposite "
            f"{target_position.value} entry."
        )

        source_recovery_params = getattr(source_bot, "recovery_params", None)
        recovery_stop_pct: float | None = None
        recovery_params: RecoveryParamsRequest | None = None
        recovery_fiat_order_size = float(source_bot.fiat_order_size)
        recovery_trailing_profit = float(source_bot.trailing_profit)
        recovery_trailing_deviation = float(source_bot.trailing_deviation)
        recovery_margin_short_reversal = source_bot.margin_short_reversal

        if (
            source_recovery_params is not None
            and source_recovery_params.reversal_path == "source"
        ):
            recovery_stop_pct = self.compute_recovery_stop_loss_pct(
                reference_price=float(closing_order.price),
                target_position=target_position,
            )
            if recovery_stop_pct is None:
                source_bot.add_log("Source position closed without recovery entry.")
                self._start_recovery_cooldown()
                self.controller.save(source_bot)
                self.active_bot = source_bot
                return source_bot

            recovery_fiat_order_size = self.contracts_to_fiat_order_size(
                current_contracts,
                float(closing_order.price),
            )
            if recovery_fiat_order_size <= 0:
                recovery_fiat_order_size = float(source_bot.fiat_order_size)

            (
                recovery_trailing_profit,
                recovery_trailing_deviation,
            ) = self._recovery_trailing_params(source_bot, recovery_stop_pct)
            recovery_margin_short_reversal = False
            recovery_params = RecoveryParamsRequest(
                reversal_path="recovery",
                source_contracts=current_contracts,
                source_loss_fiat=self._source_loss_fiat(
                    source_bot,
                    float(closing_order.price),
                    current_contracts,
                ),
                stop_loss_pct=recovery_stop_pct,
            )
            source_bot.add_log(
                "Recovery entry approved; creating one opposite pending bot."
            )

        self.controller.save(source_bot)
        new_bot = BotCreateRequest(
            pair=source_bot.pair,
            fiat=source_bot.fiat,
            fiat_order_size=recovery_fiat_order_size,
            quote_asset=source_bot.quote_asset,
            candlestick_interval=source_bot.candlestick_interval,
            market_type=source_bot.market_type,
            close_condition=source_bot.close_condition,
            cooldown=source_bot.cooldown,
            dynamic_trailing=source_bot.dynamic_trailing,
            margin_short_reversal=recovery_margin_short_reversal,
            name=source_bot.name,
            position=target_position,
            mode=source_bot.mode,
            status=Status.pending,
            stop_loss=(
                recovery_stop_pct
                if recovery_stop_pct is not None
                else source_bot.stop_loss
            ),
            take_profit=source_bot.take_profit,
            trailing=source_bot.trailing,
            trailing_deviation=recovery_trailing_deviation,
            trailing_profit=recovery_trailing_profit,
            logs=[],
            recovery_params=recovery_params,
        )
        created_bot = self.controller.create(new_bot)
        reversed_bot = BotModel.dump_from_table(created_bot)
        self.active_bot = reversed_bot
        return reversed_bot

    def exit(self, close_price: float, _: float | None = None) -> BotModel:
        """
        Exit logic for futures positions.
        """
        current_price = round_numbers(close_price, self.price_precision)
        self.active_bot.deal.current_price = current_price
        self.controller.save(self.active_bot)

        if self.active_bot.status == Status.pending:
            self.active_bot.add_log(
                "Pending bot detected on exit tick; calling open_deal to place base_order and activate."
            )
            self.active_bot = self.open_deal()
            return self.active_bot

        direction = self._direction_multiplier()
        position_name = getattr(
            self.active_bot.position,
            "value",
            self.active_bot.position,
        )

        # ---------------------------------------------------------------------------
        # Reference price for anti-wick exit execution (Phase 1).
        # Anchors the slippage band to the last *closed* candle close so that
        # reduce-only limit orders don't chase a transient wick below the book.
        # self.klines[-1] is the in-progress candle; [-2] is last fully closed.
        # ---------------------------------------------------------------------------
        exit_reference_price: float | None = None
        if self.klines is not None and len(self.klines) >= 2:
            closed_close = float(self.klines[-2][4])
            if closed_close > 0:
                exit_reference_price = closed_close

        # panic close low activity assets
        opening_price = float(self.active_bot.deal.opening_price)
        bot_profit = (
            ((current_price - opening_price) / opening_price) * 100 * direction
            if opening_price > 0
            else 0
        )
        is_1_5_days = (
            self.active_bot.deal.opening_timestamp
            and (int(time() * 1000) - self.active_bot.deal.opening_timestamp)
            >= 1.5 * 24 * 60 * 60 * 1000
        )
        # Panic close stale low-conviction positions after 1.5 days.
        if -1 <= bot_profit < 1 and is_1_5_days:
            self.controller.update_logs(
                f"Panic close triggered for stale {position_name} position after 1.5 days with profit {bot_profit}. Closing position immediately.",
                self.active_bot,
            )
            self.close_all()
            return self.active_bot

        recovery_params = getattr(self.active_bot, "recovery_params", None)
        sl_pct = float(self.active_bot.stop_loss)
        is_recovery_bot = self._is_recovery_bot()
        if (
            is_recovery_bot
            and recovery_params is not None
            and recovery_params.stop_loss_pct > 0
        ):
            sl_pct = float(recovery_params.stop_loss_pct)
            self.active_bot.stop_loss = sl_pct

        if self.active_bot.deal.stop_loss_price == 0:
            entry_price = float(self.active_bot.deal.opening_price)
            # ATR-equivalent floor for low-priced perpetuals: tick-noise on
            # sub-$0.05 contracts routinely exceeds the configured 2.5% SL,
            # so we widen the band to 4% to avoid pure-noise stop-outs.
            if (
                not is_recovery_bot
                and self.active_bot.market_type == MarketType.FUTURES
                and 0 < entry_price < 0.05
                and sl_pct < 4.0
            ):
                self.active_bot.add_log(
                    f"SL floored from {sl_pct:.2f}% to 4.00% for low-priced perpetual {self.active_bot.pair} (entry {entry_price})."
                )
                sl_pct = 4.0
                self.active_bot.stop_loss = sl_pct
            delta = entry_price * (sl_pct / 100)
            self.active_bot.deal.stop_loss_price = round_numbers(
                entry_price - (delta * direction),
                self.price_precision,
            )

        if (
            sl_pct > 0
            and ((current_price - self.active_bot.deal.stop_loss_price) * direction) < 0
        ):
            recovery_source_enabled = (
                recovery_params is not None
                and recovery_params.reversal_path == "source"
            )
            if is_recovery_bot:
                self.controller.update_logs(
                    "Recovery stop loss reached; closing and starting symbol cooldown.",
                    self.active_bot,
                )
                self.active_bot = self.reverse_position(
                    reference_price=exit_reference_price
                )
            elif self.active_bot.margin_short_reversal and (
                recovery_source_enabled or not self._prior_leg_was_loss()
            ):
                self.controller.update_logs(
                    "Margin short reversal enabled; closing source position and "
                    "opening the opposite position.",
                    self.active_bot,
                )
                self.active_bot = self.reverse_position(
                    reference_price=exit_reference_price
                )
            else:
                if self.active_bot.margin_short_reversal:
                    self.controller.update_logs(
                        f"Reversal circuit-breaker tripped: prior {self.active_bot.name} leg on {self.active_bot.pair} was a loss; closing instead of flipping.",
                        self.active_bot,
                    )
                else:
                    self.controller.update_logs(
                        f"Executing futures {position_name} stop_loss after hitting {self.active_bot.deal.stop_loss_price}",
                        self.active_bot,
                    )
                self.active_bot = self.execute_stop_loss(
                    reference_price=exit_reference_price
                )
            return self.active_bot

        # Trailing profit (price going down)
        if self.active_bot.trailing and self.active_bot.deal.opening_price > 0:
            if self.active_bot.deal.trailing_stop_loss_price != 0:
                self.reconcile_trailing_stop_loss()

            # First activation: derive the next trailing trigger from entry or the last trailing stop.
            if self.active_bot.deal.trailing_stop_loss_price == 0:
                trailing_price = float(self.active_bot.deal.opening_price) * (
                    1 + direction * (float(self.active_bot.trailing_profit) / 100)
                )
                trailing_price = round_numbers(trailing_price, self.price_precision)
            else:
                # Advance the trailing trigger in the profitable direction.
                trailing_price = float(
                    self.active_bot.deal.trailing_stop_loss_price
                ) * (1 + direction * (self.active_bot.trailing_profit / 100))
                trailing_price = round_numbers(trailing_price, self.price_precision)

            self.active_bot.deal.trailing_profit_price = round_numbers(
                trailing_price, self.price_precision
            )
            if (current_price - trailing_price) * direction >= 0:
                new_take_profit = current_price * (
                    1 + direction * ((self.active_bot.trailing_profit) / 100)
                )
                new_trailing_stop_loss: float = round_numbers(
                    current_price
                    - direction
                    * (current_price * ((self.active_bot.trailing_deviation) / 100)),
                    self.price_precision,
                )

                # Avoid duplicate logs
                old_trailing_profit_price = self.active_bot.deal.trailing_profit_price
                old_trailing_stop_loss = self.active_bot.deal.trailing_stop_loss_price

                # Keep the next trailing trigger ahead of the current price move.
                self.active_bot.deal.trailing_profit_price = round_numbers(
                    new_take_profit, self.price_precision
                )

                # Bot is not able to break ceiling profit
                # so time to close with net profit
                if (
                    new_trailing_stop_loss - self.active_bot.deal.opening_price
                ) * direction > 0 and self.should_refresh_trailing_stop_loss(
                    current_stop_price=self.active_bot.deal.trailing_stop_loss_price,
                    new_stop_price=new_trailing_stop_loss,
                    direction=direction,
                ):
                    self.active_bot.deal.trailing_stop_loss_price = (
                        new_trailing_stop_loss
                    )
                    self.place_trailing_stop_loss()

                if (
                    old_trailing_stop_loss
                    != self.active_bot.deal.trailing_stop_loss_price
                ):
                    self.active_bot.add_log(
                        f"Updated trailing_stop_loss_price to {self.active_bot.deal.trailing_stop_loss_price} and set trailing stop loss (stop loss in Kucoin)"
                    )

                if (
                    old_trailing_profit_price
                    != self.active_bot.deal.trailing_profit_price
                ):
                    self.active_bot.add_log(
                        f"Updated trailing_profit_price to {round_numbers(self.active_bot.deal.trailing_profit_price, self.price_precision)} and set trailing profit (profit in Kucoin)"
                    )

                self.controller.save(self.active_bot)

        if (
            self.active_bot.take_profit > 0
            and self.active_bot.deal.take_profit_price
            and self.active_bot.deal.opening_price > 0
        ):
            if (
                current_price - self.active_bot.deal.take_profit_price
            ) * direction >= 0:
                self.take_profit_order()

        return self.active_bot

    def update_short_trailing(self, close_price: float) -> None:
        deal = self.active_bot.deal
        opening_price = float(deal.opening_price)
        if opening_price <= 0:
            return

        if close_price > 0:
            self.close_price = close_price
            self.active_bot.deal.current_price = close_price

        take_profit_pct = float(self.active_bot.take_profit) / 100
        deviation_pct = float(self.active_bot.trailing_deviation) / 100

        if deal.trailing_stop_loss_price == 0:
            price_reference = (
                close_price if close_price < opening_price else opening_price
            )
            trailing_take_profit = price_reference - (price_reference * take_profit_pct)
            stop_loss_trailing_price = trailing_take_profit - (
                trailing_take_profit * deviation_pct
            )
            if stop_loss_trailing_price < opening_price:
                deal.trailing_profit_price = trailing_take_profit
                deal.trailing_stop_loss_price = stop_loss_trailing_price
                self.active_bot.add_log(
                    f"{self.kucoin_symbol} below opening_price, setting futures short trailing_stop_loss"
                )
                self.controller.save(self.active_bot)

        if (
            deal.trailing_stop_loss_price > 0
            and deal.trailing_profit_price > 0
            and deal.trailing_stop_loss_price < close_price
        ):
            deal.trailing_stop_loss_price = deal.trailing_profit_price * (
                1 + deviation_pct
            )
            deal.stop_loss_price = 0
            self.controller.update_logs(
                f"{self.kucoin_symbol} Updating after broken first trailing_profit (futures short)",
                self.active_bot,
            )

        if deal.trailing_profit_price == 0:
            return

        if close_price <= deal.trailing_profit_price:
            new_take_profit: float = close_price - (close_price * take_profit_pct)
            new_trailing_stop_loss = close_price * (1 + deviation_pct)
            deal.trailing_profit_price = new_take_profit

            if new_trailing_stop_loss < close_price:
                deal.trailing_stop_loss_price = new_trailing_stop_loss

        self.controller.save(self.active_bot)

    def deal_exit_orchestration(
        self, close_price: float, open_price: float
    ) -> BotModel:
        cls: Union[SpotPosition, FuturesPosition]
        if self.active_bot.market_type == MarketType.FUTURES:
            cls = FuturesPosition(
                base_streaming=self.base_streaming,
                bot=self.active_bot,
                price_precision=self.price_precision,
                qty_precision=self.qty_precision,
                db_table=self.db_table,
            )
            cls.base_streaming.kucoin_benchmark_symbol = "XBTUSDTM"
            self.api = self.base_streaming.kucoin_futures_api
        else:
            cls = SpotPosition(
                base_streaming=self.base_streaming,
                bot=self.active_bot,
                price_precision=self.price_precision,
                qty_precision=self.qty_precision,
                db_table=self.db_table,
            )
            cls.base_streaming.kucoin_benchmark_symbol = "BTC-USDT"
            self.api = self.base_streaming.kucoin_api
            close_price = self.base_streaming.kucoin_api.get_ticker_price(
                self.active_bot.pair
            )

        klines, btc_klines = cls.dataframe_ops()
        # returns raw klines
        self.klines = klines
        self.btc_klines = btc_klines

        self.active_bot = cls.order_updates()
        cls.active_bot = self.active_bot

        # Fetch position AFTER order_updates so any fill-promotion is already
        # reflected. Same single call as before; close_price stays mark-price.
        position = None
        if self.active_bot.market_type == MarketType.FUTURES:
            position = self.base_streaming.kucoin_futures_api.get_futures_position(
                self.active_bot.pair
            )
            if position is not None:
                close_price = position.mark_price

        self.active_bot = cls.position_updates(position=position)
        cls.active_bot = self.active_bot

        open_price = float(self.klines[-1][1])
        if not close_price or close_price == 0:
            close_price = self.klines[-1][4]

        self.active_bot.deal.current_price = close_price
        self.controller.save(self.active_bot)

        if self.active_bot.dynamic_trailing:
            cls.market_trailing_analytics(current_price=close_price)

        try:
            return self.exit(close_price, open_price)
        except RestError as kucoin_error:
            msg = kucoin_error.response.message
            self.controller.update_logs(
                f"Error during deal exit orchestration. Message: {msg}", self.active_bot
            )
            return self.active_bot
