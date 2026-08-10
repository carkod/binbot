from __future__ import annotations


from pandas import Series
from pybinbot import MarketType, Position, round_numbers

from api.tools.utils import clamp
from streaming.strategies.base import (
    LifecycleContext,
    LifecycleParameterUpdate,
    LifecyclePolicy,
    LifecycleSignal,
)
from streaming.strategies.default import DefaultLifecycleStrategy


class MeanReversionFadeLifecycleStrategy(DefaultLifecycleStrategy):
    algorithm_names = frozenset({"mean_reversion_fade"})
    policy = LifecyclePolicy(low_price_stop_floor_pct=None)
    ATR_WINDOW = 14
    ATR_STOP_MULTIPLIER = 2.0
    RSI_WINDOW = 14
    INVALIDATION_BARS = 3
    MIN_STOP_LOSS = 0.8
    MAX_STOP_LOSS = 3.0
    MAX_HOLDING_BARS = 8

    @staticmethod
    def _closed_candles(context: LifecycleContext) -> list:
        return [
            candle
            for candle in context.klines
            if len(candle) >= 5
            and int(float(candle[0])) + context.interval_ms <= context.now_ms
        ]

    def _rsi_series(self, context: LifecycleContext) -> Series | None:
        closed_candles = self._closed_candles(context)
        if len(closed_candles) < self.RSI_WINDOW + 1:
            return None

        closes = Series([float(candle[4]) for candle in closed_candles])
        delta = closes.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        average_gain = gain.ewm(
            alpha=1 / self.RSI_WINDOW,
            min_periods=self.RSI_WINDOW,
            adjust=False,
        ).mean()
        average_loss = loss.ewm(
            alpha=1 / self.RSI_WINDOW,
            min_periods=self.RSI_WINDOW,
            adjust=False,
        ).mean()
        denominator = average_gain + average_loss
        return (100 * average_gain / denominator).where(denominator != 0, 50.0)

    def _thesis_invalidated(self, context: LifecycleContext) -> bool:
        bot = context.bot
        entry_price = bot.deal.opening_price
        entry_timestamp = bot.deal.opening_timestamp
        if entry_price <= 0 or entry_timestamp <= 0:
            return False

        closed_candles = self._closed_candles(context)
        if len(closed_candles) < self.RSI_WINDOW + 1:
            return False

        entry_index = next(
            (
                index
                for index, candle in enumerate(closed_candles)
                if int(float(candle[0])) >= entry_timestamp
            ),
            None,
        )
        if entry_index is None:
            return False

        bars_since_entry = len(closed_candles) - 1 - entry_index
        if not (0 < bars_since_entry <= self.INVALIDATION_BARS):
            return False

        direction = self.direction(bot)
        if (context.current_price - entry_price) * direction > 0:
            return False

        rsi_series = self._rsi_series(context)
        if rsi_series is None or entry_index >= len(rsi_series):
            return False
        rsi_since_entry = rsi_series.iloc[entry_index:]
        if rsi_since_entry.isnull().any():
            return False

        rsi_now = float(rsi_since_entry.iloc[-1])
        rsi_at_entry = float(rsi_since_entry.iloc[0])
        if direction > 0:
            return rsi_now <= rsi_since_entry.min() + 1e-9 and rsi_now < rsi_at_entry
        return rsi_now >= rsi_since_entry.max() - 1e-9 and rsi_now > rsi_at_entry

    def _dynamic_parameter_update_with_logs(
        self, context: LifecycleContext
    ) -> tuple[LifecycleParameterUpdate | None, tuple[str, ...]]:
        bot = context.bot
        if (
            not bot.dynamic_trailing
            or self.is_recovery_bot(bot)
            or bot.market_type != MarketType.FUTURES
            or bot.position not in {Position.long, Position.short}
            or bot.deal.opening_price <= 0
        ):
            return None, ()

        if bot.stop_loss > 0:
            stop_loss = clamp(
                bot.stop_loss,
                self.MIN_STOP_LOSS,
                self.MAX_STOP_LOSS,
            )
        else:
            atr_pct = self.atr_pct(context, self.ATR_WINDOW)
            stop_loss = (
                self.MAX_STOP_LOSS
                if atr_pct is None
                else clamp(
                    self.ATR_STOP_MULTIPLIER * atr_pct,
                    self.MIN_STOP_LOSS,
                    self.MAX_STOP_LOSS,
                )
            )

        logs: tuple[str, ...] = ()
        if self._thesis_invalidated(context):
            direction = self.direction(bot)
            adverse_move_pct = (
                (bot.deal.opening_price - context.current_price)
                / bot.deal.opening_price
                * 100
                * direction
            )
            early_stop_loss = clamp(
                max(adverse_move_pct, self.MIN_STOP_LOSS),
                self.MIN_STOP_LOSS,
                stop_loss,
            )
            if early_stop_loss < stop_loss:
                stop_loss = early_stop_loss
                logs = (
                    "[mean_reversion_fade] thesis invalidation: RSI resumed "
                    "moving against the position within the first "
                    f"{self.INVALIDATION_BARS} bars; tightening stop_loss "
                    f"to {stop_loss:.2f}% for an early, smaller exit.",
                )

        if context.bb_metrics is None:
            trailing_profit = bot.trailing_profit if bot.trailing_profit > 0 else 2.3
            trailing_deviation = (
                bot.trailing_deviation if bot.trailing_deviation > 0 else 1.63
            )
        else:
            top_spread, bottom_spread = context.bb_metrics
            trailing_profit = clamp(
                top_spread,
                self.MIN_TRAILING_PROFIT,
                self.MAX_TRAILING_PROFIT,
            )
            trailing_deviation = clamp(
                bottom_spread,
                self.MIN_TRAILING_DEVIATION,
                self.MAX_TRAILING_DEVIATION,
            )
            max_deviation = min(
                self.MAX_TRAILING_DEVIATION,
                trailing_profit - self.MIN_TRAIL_GAP,
            )
            trailing_deviation = clamp(
                trailing_deviation,
                self.MIN_TRAILING_DEVIATION,
                max_deviation,
            )

        return (
            LifecycleParameterUpdate(
                stop_loss=round_numbers(stop_loss, 2),
                trailing_profit=round_numbers(trailing_profit, 2),
                trailing_deviation=round_numbers(trailing_deviation, 2),
            ),
            logs,
        )

    def signal(self, context: LifecycleContext) -> LifecycleSignal:
        parameter_update, logs = self._dynamic_parameter_update_with_logs(context)
        return LifecycleSignal(
            parameter_update=parameter_update,
            exit_intent=self.max_holding_exit(
                context,
                max_holding_bars=self.MAX_HOLDING_BARS,
            ),
            log_messages=logs,
        )
