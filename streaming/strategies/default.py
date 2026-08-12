from typing import Any, cast

from pybinbot import MarketType, Position, round_numbers

from api.tools.utils import clamp
from streaming.apex_flow_closing import ApexFlowClose
from streaming.strategies.base import (
    BaseLifecycleStrategy,
    LifecycleContext,
    LifecycleParameterUpdate,
    LifecycleSignal,
)


class DefaultLifecycleStrategy(BaseLifecycleStrategy):
    MIN_STOP_LOSS = 0.8
    MAX_STOP_LOSS = 4.0
    MIN_TRAILING_PROFIT = 0.6
    MAX_TRAILING_PROFIT = 3.5
    MIN_TRAILING_DEVIATION = 0.4
    MAX_TRAILING_DEVIATION = 2.5
    MIN_TRAIL_GAP = 0.35
    PULLBACK_ARM_PROFIT = 1.0
    SHALLOW_PULLBACK = 0.75
    DEEP_PULLBACK = 1.5

    @staticmethod
    def _pullback_metrics(
        context: LifecycleContext,
    ) -> dict[str, float] | None:
        entry_price = context.bot.deal.opening_price
        entry_timestamp = context.bot.deal.opening_timestamp
        if entry_price <= 0 or entry_timestamp <= 0:
            return None

        entry_index = next(
            (
                index
                for index, candle in enumerate(context.klines)
                if len(candle) >= 3 and int(float(candle[0])) >= entry_timestamp
            ),
            None,
        )
        if entry_index is None:
            return None

        peak_price_since_entry = max(
            [
                float(candle[2])
                for candle in context.klines[entry_index:]
                if len(candle) >= 3
            ]
            + [context.current_price]
        )
        if peak_price_since_entry <= 0:
            return None

        return {
            "peak_profit_pct": (
                (peak_price_since_entry - entry_price) / entry_price * 100
            ),
            "pullback_pct": max(
                0.0,
                (peak_price_since_entry - context.current_price)
                / peak_price_since_entry
                * 100,
            ),
        }

    def _initial_stop_loss(
        self,
        context: LifecycleContext,
        expansion_range: float,
    ) -> float:
        return 3.0

    def _dynamic_parameter_update(
        self, context: LifecycleContext
    ) -> LifecycleParameterUpdate | None:
        bot = context.bot
        if (
            not bot.dynamic_trailing
            or self.is_recovery_bot(bot)
            or bot.market_type != MarketType.FUTURES
            or bot.position not in {Position.long, Position.short}
            or bot.deal.opening_price <= 0
            or context.bb_metrics is None
        ):
            return None

        top_spread, bottom_spread = context.bb_metrics
        apex_flow_closing = ApexFlowClose(
            cast(Any, context.df),
            cast(Any, context.btc_df),
        )
        row = apex_flow_closing.df.iloc[-1]
        detectors = apex_flow_closing.get_detectors()
        vce_signal = detectors.get("vce", False)
        mcd_signal = detectors.get("mcd", False)
        lcrs_signal = detectors.get("lcrs", False)
        expansion_range = float(row["high"] - row["low"])

        direction = self.direction(bot)
        ema_fast, ema_slow = apex_flow_closing.get_trend_ema()
        trend_up = ema_fast > ema_slow if ema_fast and ema_slow else True
        trend_favorable = trend_up if direction > 0 else not trend_up

        expansion_multiplier = 1.0
        if vce_signal:
            expansion_multiplier += 0.2
        if mcd_signal:
            expansion_multiplier += 0.1
        expansion_multiplier = min(expansion_multiplier, 1.5)

        if context.bot_profit < 2:
            trail_tighten_mult = 1.0
        elif context.bot_profit < 5:
            trail_tighten_mult = 0.7
        else:
            trail_tighten_mult = 0.45
        if (vce_signal or mcd_signal or lcrs_signal) and trend_favorable:
            trail_tighten_mult = max(trail_tighten_mult, 0.7)

        profit_spread, deviation_spread = (
            (top_spread, bottom_spread)
            if direction > 0
            else (bottom_spread, top_spread)
        )
        raw_trailing_profit = profit_spread * trail_tighten_mult * expansion_multiplier
        if context.bot_profit >= 5:
            raw_trailing_profit = min(raw_trailing_profit, 2.0)
        elif context.bot_profit >= 3:
            raw_trailing_profit = min(raw_trailing_profit, 3.0)

        trailing_profit = clamp(
            raw_trailing_profit,
            self.MIN_TRAILING_PROFIT,
            self.MAX_TRAILING_PROFIT,
        )
        trailing_deviation = clamp(
            deviation_spread * trail_tighten_mult,
            self.MIN_TRAILING_DEVIATION,
            self.MAX_TRAILING_DEVIATION,
        )

        pullback_metrics = self._pullback_metrics(context)
        if (
            pullback_metrics
            and pullback_metrics["peak_profit_pct"] >= self.PULLBACK_ARM_PROFIT
        ):
            pullback_pct = pullback_metrics["pullback_pct"]
            if pullback_pct < self.SHALLOW_PULLBACK:
                trailing_profit += 0.25
                trailing_deviation += 0.05
            elif pullback_pct >= self.DEEP_PULLBACK:
                trailing_profit -= 0.30
                trailing_deviation -= 0.10

        existing_stop_loss = bot.stop_loss
        if existing_stop_loss > 0:
            band_stop_loss = clamp(
                deviation_spread,
                self.MIN_STOP_LOSS,
                self.MAX_STOP_LOSS,
            )
            stop_loss = clamp(
                min(existing_stop_loss, band_stop_loss),
                self.MIN_STOP_LOSS,
                self.MAX_STOP_LOSS,
            )
        else:
            stop_loss = self._initial_stop_loss(context, expansion_range)

        stop_loss = clamp(stop_loss, self.MIN_STOP_LOSS, self.MAX_STOP_LOSS)
        trailing_profit = clamp(
            trailing_profit,
            self.MIN_TRAILING_PROFIT,
            self.MAX_TRAILING_PROFIT,
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
        return LifecycleParameterUpdate(
            stop_loss=round_numbers(stop_loss, 2),
            trailing_profit=round_numbers(trailing_profit, 2),
            trailing_deviation=round_numbers(trailing_deviation, 2),
        )

    def signal(self, context: LifecycleContext) -> LifecycleSignal:
        return LifecycleSignal(parameter_update=self._dynamic_parameter_update(context))
