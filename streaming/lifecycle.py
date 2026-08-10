from math import ceil
from time import time
from typing import Union

from kucoin_universal_sdk.model.common import RestError
from pandas import DataFrame
from pybinbot import (
    BotBase,
    BotModel,
    Candles,
    KucoinApi,
    KucoinFutures,
    MarketType,
    Position,
    RecoveryParams,
    Status,
    round_numbers,
)

from api.databases.crud.autotrade_crud import AutotradeCrud
from api.exchange_apis.kucoin.futures.futures_deal import KucoinPositionDeal
from streaming.context_evaluator import (
    LifecycleContextEvaluator,
    LifecycleEvaluation,
)
from streaming.futures_position import FuturesPosition
from streaming.spot_position import SpotPosition
from streaming.strategies.base import (
    BaseLifecycleStrategy,
    EmergencyStopBounds,
    LifecycleContext,
    LifecycleExitKind,
)


class Lifecycle:
    """
    Position lifecycle for Kucoin futures trading.

    Previously called FuturesLongDeal, but long or short position logic is all handled within this class
    since Kucoin Futures logic allows easy isolated margin and switching positions.

    Happens after open_deal is executed
    formerly known as streaming updates
    these operations are triggered by websockets
    """

    RECOVERY_ATR_WINDOW = 14
    RECOVERY_STRUCTURE_WINDOW = 4
    RECOVERY_STOP_CAP_PCT = 6.5
    RECOVERY_STRUCTURE_ATR_BUFFER = 0.5
    RECOVERY_ATR_FLOOR_MULTIPLIER = 1.5
    RECOVERY_FALLBACK_BUFFER_PCT = 0.75
    RECOVERY_TRAILING_PROFIT_CAP_PCT = 6.0
    RECOVERY_TRAILING_MIN_GAP_PCT = 0.35
    RECOVERY_COOLDOWN_MINUTES = 240
    RECOVERY_EMERGENCY_ATR_MULTIPLIER = 1.0

    def __init__(
        self,
        execution: KucoinPositionDeal,
        base_streaming,
    ) -> None:
        self.execution = execution
        self.base_streaming = base_streaming
        self.api: KucoinApi | KucoinFutures
        self.klines: list | None
        self.btc_klines: list | None
        self.df = DataFrame()
        self.btc_df = DataFrame()
        self.bb_metrics: tuple[float, float] | None = None
        self.context_evaluator = LifecycleContextEvaluator()

    def _evaluate_strategy(
        self,
        *,
        current_price: float,
        completed_candles: list,
        bot_profit: float,
        now_ms: int,
    ) -> LifecycleEvaluation:
        context = LifecycleContext(
            bot=self.execution.active_bot,
            current_price=current_price,
            interval_ms=self.base_streaming.interval.get_ms(),
            now_ms=now_ms,
            klines=self.klines or [],
            completed_candles=completed_candles,
            df=self.df,
            btc_df=self.btc_df,
            bb_metrics=self.bb_metrics,
            bot_profit=bot_profit,
            has_live_stop_loss=BaseLifecycleStrategy.has_live_stop_loss(
                self.execution.active_bot
            ),
        )
        return self.context_evaluator.evaluate(context)

    def _apply_strategy_signal(self, evaluation: LifecycleEvaluation) -> None:
        signal = evaluation.signal
        for message in signal.log_messages:
            self.execution.active_bot.add_log(message)

        update = signal.parameter_update
        if update is None:
            if signal.log_messages:
                self.execution.controller.save(self.execution.active_bot)
            return

        bot = self.execution.active_bot
        if (
            bot.stop_loss == update.stop_loss
            and bot.trailing_profit == update.trailing_profit
            and bot.trailing_deviation == update.trailing_deviation
        ):
            if signal.log_messages:
                self.execution.controller.save(bot)
            return

        bot.stop_loss = update.stop_loss
        bot.trailing_profit = update.trailing_profit
        bot.trailing_deviation = update.trailing_deviation
        self.execution.active_bot = self.execution.update_parameters()
        self.execution.controller.save(self.execution.active_bot)

    def _recovery_atr_pct(self, reference_price: float) -> float | None:
        if reference_price <= 0 or self.klines is None:
            return None

        closed_candles, _ = Candles.partition_closed_candles(
            self.klines,
            now_ms=int(time() * 1000),
        )
        atr = self.execution.closed_candle_atr(closed_candles)
        if atr is None:
            return None

        return (atr / reference_price) * 100

    def compute_recovery_stop_loss_pct(
        self,
        reference_price: float,
        target_position: Position,
    ) -> float | None:
        if reference_price <= 0 or self.klines is None:
            self.execution.active_bot.add_log(
                "Recovery skipped: no valid reference price or kline structure."
            )
            return None

        closed_candles, _ = Candles.partition_closed_candles(
            self.klines,
            now_ms=int(time() * 1000),
        )
        if len(closed_candles) < self.RECOVERY_STRUCTURE_WINDOW:
            self.execution.active_bot.add_log(
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
                self.execution.active_bot.stop_loss,
                buffered_structure_pct,
            )
            self.execution.active_bot.add_log(
                "Recovery ATR unavailable; using four-candle structure plus "
                f"{self.RECOVERY_FALLBACK_BUFFER_PCT:.2f}% fixed buffer."
            )
        else:
            buffered_structure_pct = (
                structure_distance_pct + self.RECOVERY_STRUCTURE_ATR_BUFFER * atr_pct
            )
            recovery_stop_pct = max(
                self.execution.active_bot.stop_loss,
                buffered_structure_pct,
                self.RECOVERY_ATR_FLOOR_MULTIPLIER * atr_pct,
            )

        if buffered_structure_pct > self.RECOVERY_STOP_CAP_PCT:
            self.execution.active_bot.add_log(
                "Recovery skipped: structure invalidation requires "
                f"{buffered_structure_pct:.2f}%, above "
                f"{self.RECOVERY_STOP_CAP_PCT:.2f}% cap."
            )
            return None

        recovery_stop_pct = min(recovery_stop_pct, self.RECOVERY_STOP_CAP_PCT)
        self.execution.active_bot.add_log(
            "Recovery hybrid stop computed at "
            f"{recovery_stop_pct:.2f}% "
            f"(structure distance {structure_distance_pct:.2f}%)."
        )
        return round_numbers(recovery_stop_pct, 2)

    def recovery_body_breakout_confirmed(
        self,
        target_position: Position,
        completed_candles: list,
    ) -> bool:
        if len(completed_candles) < self.RECOVERY_STRUCTURE_WINDOW:
            return False

        structure_candles = completed_candles[-self.RECOVERY_STRUCTURE_WINDOW :]
        latest_candle = structure_candles[-1]
        preceding_candles = structure_candles[:-1]
        latest_open = float(latest_candle[1])
        latest_close = float(latest_candle[4])

        if target_position == Position.short:
            preceding_body_floor = min(
                min(float(candle[1]), float(candle[4])) for candle in preceding_candles
            )
            return latest_close < latest_open and latest_close < preceding_body_floor

        preceding_body_ceiling = max(
            max(float(candle[1]), float(candle[4])) for candle in preceding_candles
        )
        return latest_close > latest_open and latest_close > preceding_body_ceiling

    def recovery_emergency_stop_price(
        self,
        stop_loss_price: float,
        completed_candles: list,
        bounds: EmergencyStopBounds,
    ) -> tuple[float, float]:
        atr = self.execution.closed_candle_atr(completed_candles)
        if atr is None:
            emergency_pct = bounds.minimum_pct
        else:
            atr_pct = (
                self.RECOVERY_EMERGENCY_ATR_MULTIPLIER * atr / stop_loss_price * 100
            )
            emergency_pct = max(
                bounds.minimum_pct,
                min(atr_pct, bounds.maximum_pct),
            )

        direction = self.execution._direction_multiplier()
        emergency_price = round_numbers(
            stop_loss_price - (stop_loss_price * emergency_pct / 100 * direction),
            self.execution.price_precision,
        )
        return emergency_price, emergency_pct

    def _add_recovery_log_once(self, marker: str, message: str) -> None:
        if any(marker in str(log) for log in self.execution.active_bot.logs):
            return
        self.execution.active_bot.add_log(message)
        self.execution.controller.save(self.execution.active_bot)

    def _close_source_without_recovery(
        self,
        message: str,
        reference_price: float | None,
    ) -> BotModel:
        self.execution.active_bot.add_log(message)
        self.execution.active_bot = self.execution.execute_stop_loss(
            reference_price=reference_price
        )
        if self.execution.active_bot.status == Status.completed:
            self._start_recovery_cooldown()
            self.execution.controller.save(self.execution.active_bot)
        return self.execution.active_bot

    def _start_recovery_cooldown(self) -> None:
        configured_symbol_cooldown = int(
            getattr(self.execution.symbol_info, "cooldown", 0) or 0
        )
        bot_cooldown_seconds = self.execution.active_bot.cooldown * 60
        cooldown_seconds = max(
            configured_symbol_cooldown,
            bot_cooldown_seconds,
            self.RECOVERY_COOLDOWN_MINUTES * 60,
        )

        try:
            self.execution.symbols_crud.start_cooldown(
                symbol=self.execution.active_bot.pair,
                cooldown_seconds=cooldown_seconds,
            )
            self.execution.active_bot.add_log(
                f"Recovery cooldown started for {cooldown_seconds // 60} minutes."
            )
        except Exception as exc:
            self.execution.active_bot.add_log(
                f"Failed to start recovery symbol cooldown: {exc}"
            )

    def _source_loss_fiat(
        self,
        source_bot: BotModel,
        closing_price: float,
        contracts: float,
    ) -> float:
        entry_price = source_bot.deal.opening_price
        if entry_price <= 0 or closing_price <= 0 or contracts <= 0:
            return 0

        multiplier = (
            self.execution.kucoin_symbol_data.multiplier
            or self.execution.kucoin_futures_api.DEFAULT_MULTIPLIER
        )
        direction = 1 if source_bot.position == Position.long else -1
        price_pnl = (closing_price - entry_price) * contracts * multiplier * direction
        loss = max(-price_pnl, 0) + source_bot.deal.total_commissions
        return round_numbers(loss, 8)

    def _recovery_trailing_params(
        self,
        source_bot: BotModel,
        recovery_stop_pct: float,
    ) -> tuple[float, float]:
        trailing_profit = min(
            ceil(
                max(
                    source_bot.trailing_profit,
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
                    source_bot.trailing_deviation,
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
        try:
            cooldown_minutes = max(self.execution.active_bot.cooldown, 240)
            window_ms = cooldown_minutes * 60 * 1000
            now_ms = int(time() * 1000)
            candidates = self.execution.controller.get(
                status=Status.completed,
                bot_name=self.execution.active_bot.name,
                start_date=now_ms - window_ms,
                end_date=now_ms,
                limit=20,
            )
        except Exception as exc:
            self.execution.active_bot.add_log(
                f"Reversal circuit-breaker lookup failed ({exc}); allowing reversal."
            )
            return False

        for prev in candidates:
            if prev.pair != self.execution.active_bot.pair:
                continue
            if str(prev.id) == str(self.execution.active_bot.id):
                continue
            op = prev.deal.opening_price
            cp = prev.deal.closing_price
            if op <= 0 or cp <= 0:
                continue
            prev_direction = 1 if prev.position == Position.long else -1
            prev_pct = ((cp - op) / op) * 100 * prev_direction
            if prev_pct < 0:
                return True
        return False

    def reverse_position(self, reference_price: float | None = None) -> BotModel:
        """
        Close the current position with a reduce_only order, mark source bot as
        completed, then create a new opposite-direction bot in Status.pending.
        The next exit() tick promotes pending -> active via open_deal(), which
        places a candle-body-capped base order for recovery-enabled bots.

        When ``reference_price`` is provided the reduce-only close leg is routed
        through the anti-wick escalation path so the reversal close doesn't fill
        into a wick.
        """
        source_bot = self.execution.active_bot
        target_position = (
            Position.short if source_bot.position == Position.long else Position.long
        )

        close_result = self.execution.close_position_for_reversal(
            reference_price=reference_price
        )
        if close_result is None:
            self.execution.active_bot = source_bot
            return source_bot

        closing_order, current_contracts = close_result
        source_bot.orders.append(closing_order)
        source_bot.deal.closing_price = closing_order.price
        source_bot.deal.closing_qty = current_contracts
        source_bot.deal.closing_timestamp = closing_order.timestamp
        source_bot.status = Status.completed
        source_bot.add_log(
            "Reversal: reduce_only source close placed; evaluating opposite "
            f"{target_position.value} entry."
        )

        source_recovery_params = source_bot.recovery_params
        recovery_stop_pct: float | None = None
        recovery_params: RecoveryParams | None = None
        recovery_fiat_order_size = source_bot.fiat_order_size
        recovery_trailing_profit = source_bot.trailing_profit
        recovery_trailing_deviation = source_bot.trailing_deviation
        recovery_margin_short_reversal = source_bot.margin_short_reversal

        if source_recovery_params is not None:
            recovery_stop_pct = self.compute_recovery_stop_loss_pct(
                reference_price=closing_order.price,
                target_position=target_position,
            )
            if recovery_stop_pct is None:
                source_bot.add_log("Source position closed without recovery entry.")
                self._start_recovery_cooldown()
                self.execution.controller.save(source_bot)
                self.execution.active_bot = source_bot
                return source_bot

            recovery_fiat_order_size = AutotradeCrud().get_settings().base_order_size

            (
                recovery_trailing_profit,
                recovery_trailing_deviation,
            ) = self._recovery_trailing_params(source_bot, recovery_stop_pct)
            recovery_margin_short_reversal = False
            recovery_params = RecoveryParams(
                reversal_path="recovery",
                source_contracts=current_contracts,
                source_loss_fiat=self._source_loss_fiat(
                    source_bot,
                    closing_order.price,
                    current_contracts,
                ),
                stop_loss_pct=recovery_stop_pct,
            )
            source_bot.add_log(
                "Recovery entry approved; creating one opposite pending bot."
            )

        self.execution.controller.save(source_bot)
        new_bot = BotBase(
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
        created_bot = self.execution.controller.create(new_bot)
        reversed_bot = BotModel.dump_from_table(created_bot)
        self.execution.active_bot = reversed_bot
        return reversed_bot

    def exit(self, close_price: float) -> BotModel:
        """
        Exit logic for futures positions.
        """
        current_price = round_numbers(close_price, self.execution.price_precision)
        self.execution.active_bot.deal.current_price = current_price
        self.execution.controller.save(self.execution.active_bot)

        if self.execution.active_bot.status == Status.pending:
            self.execution.active_bot.add_log(
                "Pending bot detected on exit tick; calling open_deal to place base_order and activate."
            )
            self.execution.active_bot = self.execution.open_deal()
            return self.execution.active_bot

        direction = self.execution._direction_multiplier()
        position_name = getattr(
            self.execution.active_bot.position,
            "value",
            self.execution.active_bot.position,
        )

        # Anchor exit execution and recovery decisions to timestamp-confirmed
        # completed candles rather than list position.
        completed_candles: list = []
        exit_reference_price: float | None = None
        now_ms = int(time() * 1000)
        if self.klines is not None:
            completed_candles, _ = Candles.partition_closed_candles(
                self.klines,
                now_ms=now_ms,
            )
        if completed_candles:
            closed_close = float(completed_candles[-1][4])
            if closed_close > 0:
                exit_reference_price = closed_close

        # panic close low activity assets
        opening_price = self.execution.active_bot.deal.opening_price
        bot_profit = (
            ((current_price - opening_price) / opening_price) * 100 * direction
            if opening_price > 0
            else 0
        )
        evaluation = self._evaluate_strategy(
            current_price=current_price,
            completed_candles=completed_candles,
            bot_profit=bot_profit,
            now_ms=now_ms,
        )
        self._apply_strategy_signal(evaluation)

        is_1_5_days = (
            self.execution.active_bot.deal.opening_timestamp
            and (now_ms - self.execution.active_bot.deal.opening_timestamp)
            >= 1.5 * 24 * 60 * 60 * 1000
        )
        # Panic close stale low-conviction positions after 1.5 days.
        if -1 <= bot_profit < 1 and is_1_5_days:
            self.execution.controller.update_logs(
                f"Panic close triggered for stale {position_name} position after 1.5 days with profit {bot_profit}. Closing position immediately.",
                self.execution.active_bot,
            )
            self.execution.close_all()
            return self.execution.active_bot

        recovery_params = self.execution.active_bot.recovery_params
        sl_pct = self.execution.active_bot.stop_loss
        is_recovery_bot = self.execution._is_recovery_bot()
        if (
            is_recovery_bot
            and recovery_params is not None
            and recovery_params.stop_loss_pct > 0
        ):
            sl_pct = recovery_params.stop_loss_pct
            self.execution.active_bot.stop_loss = sl_pct

        if self.execution.active_bot.deal.stop_loss_price == 0:
            entry_price = self.execution.active_bot.deal.opening_price
            low_price_stop_floor_pct = evaluation.policy.low_price_stop_floor_pct
            if (
                low_price_stop_floor_pct is not None
                and not is_recovery_bot
                and self.execution.active_bot.market_type == MarketType.FUTURES
                and 0 < entry_price < 0.05
                and sl_pct < low_price_stop_floor_pct
            ):
                self.execution.active_bot.add_log(
                    f"SL floored from {sl_pct:.2f}% to "
                    f"{low_price_stop_floor_pct:.2f}% for low-priced perpetual "
                    f"{self.execution.active_bot.pair} (entry {entry_price})."
                )
                sl_pct = low_price_stop_floor_pct
                self.execution.active_bot.stop_loss = sl_pct
            delta = entry_price * (sl_pct / 100)
            self.execution.active_bot.deal.stop_loss_price = round_numbers(
                entry_price - (delta * direction),
                self.execution.price_precision,
            )

        if (
            sl_pct > 0
            and (
                (current_price - self.execution.active_bot.deal.stop_loss_price)
                * direction
            )
            < 0
        ):
            recovery_source_enabled = (
                recovery_params is not None
                and recovery_params.reversal_path == "source"
            )
            reversal_requires_confirmation = recovery_params is not None

            if reversal_requires_confirmation:
                stop_loss_price = self.execution.active_bot.deal.stop_loss_price
                emergency_price, emergency_pct = self.recovery_emergency_stop_price(
                    stop_loss_price=stop_loss_price,
                    completed_candles=completed_candles,
                    bounds=evaluation.policy.emergency_stop_bounds,
                )
                emergency_breached = (current_price - emergency_price) * direction < 0
                if emergency_breached:
                    self.execution.active_bot = self._close_source_without_recovery(
                        "Recovery emergency threshold breached at "
                        f"{emergency_price} ({emergency_pct:.2f}% beyond stop); "
                        "closing without reversal.",
                        exit_reference_price,
                    )
                    return self.execution.active_bot

                latest_closed_price = (
                    float(completed_candles[-1][4]) if completed_candles else None
                )
                stop_confirmed = (
                    latest_closed_price is not None
                    and (latest_closed_price - stop_loss_price) * direction < 0
                )
                if not stop_confirmed:
                    closed_price_text = (
                        str(latest_closed_price)
                        if latest_closed_price is not None
                        else "unavailable"
                    )
                    self._add_recovery_log_once(
                        "Recovery reversal deferred:",
                        "Recovery reversal deferred: live price breached stop "
                        f"{stop_loss_price}, but latest completed candle close "
                        f"{closed_price_text} did not confirm it; emergency "
                        f"threshold is {emergency_price}.",
                    )
                    return self.execution.active_bot

                target_position = (
                    Position.short
                    if self.execution.active_bot.position == Position.long
                    else Position.long
                )
                if not self.recovery_body_breakout_confirmed(
                    target_position=target_position,
                    completed_candles=completed_candles,
                ):
                    self.execution.active_bot = self._close_source_without_recovery(
                        "Recovery body breakout rejected for opposite "
                        f"{target_position.value}; closing source without reversal.",
                        exit_reference_price,
                    )
                    return self.execution.active_bot

                self.execution.active_bot.add_log(
                    "Recovery candle confirmation approved: completed candle "
                    f"closed beyond {stop_loss_price} with an opposite "
                    f"{target_position.value} body breakout."
                )
                self.execution.active_bot = self.reverse_position(
                    reference_price=exit_reference_price
                )
            elif self.execution.active_bot.margin_short_reversal and (
                recovery_source_enabled
                or not evaluation.policy.block_reversal_after_loss
                or not self._prior_leg_was_loss()
            ):
                self.execution.controller.update_logs(
                    "Margin short reversal enabled; closing source position and "
                    "opening the opposite position.",
                    self.execution.active_bot,
                )
                self.execution.active_bot = self.reverse_position(
                    reference_price=exit_reference_price
                )
            else:
                if (
                    evaluation.policy.exchange_stop_owns_breach
                    and BaseLifecycleStrategy.has_live_stop_loss(
                        self.execution.active_bot
                    )
                ):
                    self.execution.active_bot = (
                        self.execution.close_after_unfilled_bounded_stop(
                            reference_price=exit_reference_price
                        )
                    )
                    return self.execution.active_bot
                if self.execution.active_bot.margin_short_reversal:
                    self.execution.controller.update_logs(
                        f"Reversal circuit-breaker tripped: prior {self.execution.active_bot.name} leg on {self.execution.active_bot.pair} was a loss; closing instead of flipping.",
                        self.execution.active_bot,
                    )
                else:
                    self.execution.controller.update_logs(
                        f"Executing futures {position_name} stop_loss after hitting {self.execution.active_bot.deal.stop_loss_price}",
                        self.execution.active_bot,
                    )
                self.execution.active_bot = self.execution.execute_stop_loss(
                    reference_price=exit_reference_price
                )
            return self.execution.active_bot

        # Trailing profit (price going down)
        if (
            self.execution.active_bot.trailing
            and self.execution.active_bot.deal.opening_price > 0
        ):
            if self.execution.active_bot.deal.trailing_stop_loss_price != 0:
                self.execution.reconcile_trailing_stop_loss()

            # First activation: derive the next trailing trigger from entry or the last trailing stop.
            if self.execution.active_bot.deal.trailing_stop_loss_price == 0:
                trailing_price = self.execution.active_bot.deal.opening_price * (
                    1 + direction * (self.execution.active_bot.trailing_profit / 100)
                )
                trailing_price = round_numbers(
                    trailing_price, self.execution.price_precision
                )
            else:
                # Advance the trailing trigger in the profitable direction.
                trailing_price = (
                    self.execution.active_bot.deal.trailing_stop_loss_price
                    * (
                        1
                        + direction * (self.execution.active_bot.trailing_profit / 100)
                    )
                )
                trailing_price = round_numbers(
                    trailing_price, self.execution.price_precision
                )

            self.execution.active_bot.deal.trailing_profit_price = round_numbers(
                trailing_price, self.execution.price_precision
            )
            if (current_price - trailing_price) * direction >= 0:
                new_take_profit = current_price * (
                    1 + direction * ((self.execution.active_bot.trailing_profit) / 100)
                )
                new_trailing_stop_loss: float = round_numbers(
                    current_price
                    - direction
                    * (
                        current_price
                        * ((self.execution.active_bot.trailing_deviation) / 100)
                    ),
                    self.execution.price_precision,
                )

                # Avoid duplicate logs
                old_trailing_profit_price = (
                    self.execution.active_bot.deal.trailing_profit_price
                )
                old_trailing_stop_loss = (
                    self.execution.active_bot.deal.trailing_stop_loss_price
                )

                # Keep the next trailing trigger ahead of the current price move.
                self.execution.active_bot.deal.trailing_profit_price = round_numbers(
                    new_take_profit, self.execution.price_precision
                )

                # Bot is not able to break ceiling profit
                # so time to close with net profit
                if (
                    new_trailing_stop_loss
                    - self.execution.active_bot.deal.opening_price
                ) * direction > 0 and self.execution.should_refresh_trailing_stop_loss(
                    current_stop_price=self.execution.active_bot.deal.trailing_stop_loss_price,
                    new_stop_price=new_trailing_stop_loss,
                    direction=direction,
                    last_replace_ts_ms=self.execution.last_trailing_stop_replace_ts_ms(),
                ):
                    self.execution.active_bot.deal.trailing_stop_loss_price = (
                        new_trailing_stop_loss
                    )
                    self.execution.place_trailing_stop_loss()

                if (
                    old_trailing_stop_loss
                    != self.execution.active_bot.deal.trailing_stop_loss_price
                ):
                    self.execution.active_bot.add_log(
                        f"Updated trailing_stop_loss_price to {self.execution.active_bot.deal.trailing_stop_loss_price} and set trailing stop loss (stop loss in Kucoin)"
                    )

                if (
                    old_trailing_profit_price
                    != self.execution.active_bot.deal.trailing_profit_price
                ):
                    self.execution.active_bot.add_log(
                        f"Updated trailing_profit_price to {round_numbers(self.execution.active_bot.deal.trailing_profit_price, self.execution.price_precision)} and set trailing profit (profit in Kucoin)"
                    )

                self.execution.controller.save(self.execution.active_bot)

        if (
            self.execution.active_bot.take_profit > 0
            and self.execution.active_bot.deal.take_profit_price
            and self.execution.active_bot.deal.opening_price > 0
        ):
            if (
                current_price - self.execution.active_bot.deal.take_profit_price
            ) * direction >= 0:
                take_profit_result = self.execution.take_profit_order()
                return take_profit_result

        exit_intent = evaluation.signal.exit_intent
        if (
            exit_intent is not None
            and exit_intent.kind == LifecycleExitKind.algorithmic_close
        ):
            self.execution.controller.update_logs(
                exit_intent.log_message,
                self.execution.active_bot,
            )
            return self.execution.close_all(algorithmic_close=True)

        return self.execution.active_bot

    def process_tick(self) -> BotModel:
        close_price = 0.0
        cls: Union[SpotPosition, FuturesPosition]
        if self.execution.active_bot.market_type == MarketType.FUTURES:
            cls = FuturesPosition(
                base_streaming=self.base_streaming,
                execution=self.execution,
            )
            cls.base_streaming.kucoin_benchmark_symbol = "XBTUSDTM"
            self.api = self.base_streaming.kucoin_futures_api
        else:
            cls = SpotPosition(
                base_streaming=self.base_streaming,
                execution=self.execution,
            )
            cls.base_streaming.kucoin_benchmark_symbol = "BTC-USDT"
            self.api = self.base_streaming.kucoin_api
            close_price = self.base_streaming.kucoin_api.get_ticker_price(
                self.execution.active_bot.pair
            )

        klines, btc_klines = cls.dataframe_ops()
        # returns raw klines
        self.klines = klines
        self.btc_klines = btc_klines
        self.df = cls.df
        self.btc_df = cls.btc_df
        self.bb_metrics = cls.build_bb_metrics()

        self.execution.active_bot = cls.order_updates()

        # Fetch position AFTER order_updates so any fill-promotion is already
        # reflected. Same single call as before; close_price stays mark-price.
        position = None
        if self.execution.active_bot.market_type == MarketType.FUTURES:
            position = self.base_streaming.kucoin_futures_api.get_futures_position(
                self.execution.active_bot.pair
            )
            close_price = self.base_streaming.kucoin_futures_api.get_mark_price(
                self.execution.active_bot.pair
            )

        self.execution.active_bot = cls.position_updates(position=position)

        if not close_price or close_price == 0:
            close_price = self.klines[-1][4]

        self.execution.active_bot.deal.current_price = close_price
        self.execution.controller.save(self.execution.active_bot)

        try:
            return self.exit(close_price)
        except RestError as kucoin_error:
            msg = kucoin_error.response.message
            self.execution.controller.update_logs(
                f"Error during deal exit orchestration. Message: {msg}",
                self.execution.active_bot,
            )
            return self.execution.active_bot
