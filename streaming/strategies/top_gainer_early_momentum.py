from typing import Any, cast

from pybinbot import MarketType, Position

from streaming.apex_flow_closing import ApexFlowClose
from streaming.strategies.base import (
    LifecycleContext,
    LifecycleParameterUpdate,
    LifecycleSignal,
)
from streaming.strategies.default import DefaultLifecycleStrategy

from api.tools.constants import TOP_MOVER_EARLY_MOMENTUM_ALGOS


class TopGainerEarlyMomentumLifecycleStrategy(DefaultLifecycleStrategy):
    """Keep volatile top-mover runners alive long enough to express their edge."""

    algorithm_names = TOP_MOVER_EARLY_MOMENTUM_ALGOS

    MIN_STOP_LOSS = 2.0
    MIN_TRAILING_PROFIT = 6.0
    MAX_TRAILING_PROFIT = 8.0
    MIN_TRAILING_DEVIATION = 2.5
    MAX_TRAILING_DEVIATION = 4.0

    STRONG_UPTREND_STRUCTURE_BARS = 6
    STRONG_UPTREND_STOP_LOSS = 10.0
    STRONG_UPTREND_TRAILING_PROFIT = 9.0
    STRONG_UPTREND_TRAILING_DEVIATION = 9.0

    @classmethod
    def _has_rising_structure(cls, context: LifecycleContext) -> bool:
        candles = context.completed_candles[-cls.STRONG_UPTREND_STRUCTURE_BARS :]
        if len(candles) < cls.STRONG_UPTREND_STRUCTURE_BARS:
            return False

        midpoint = len(candles) // 2
        earlier_floor = min(float(candle[3]) for candle in candles[:midpoint])
        recent_floor = min(float(candle[3]) for candle in candles[midpoint:])
        first_close = float(candles[0][4])
        latest_close = float(candles[-1][4])
        return recent_floor >= earlier_floor and latest_close > first_close

    def _strong_uptrend(self, context: LifecycleContext) -> bool:
        bot = context.bot
        if (
            bot.market_type != MarketType.FUTURES
            or bot.position != Position.long
            or self.is_recovery_bot(bot)
            or bot.deal.opening_price <= 0
            or context.current_price <= bot.deal.opening_price
            or not self._has_rising_structure(context)
        ):
            return False

        apex_flow_closing = ApexFlowClose(
            cast(Any, context.df),
            cast(Any, context.btc_df),
        )
        ema_fast, ema_slow = apex_flow_closing.get_trend_ema()
        return bool(ema_fast and ema_slow and ema_fast > ema_slow)

    def signal(self, context: LifecycleContext) -> LifecycleSignal:
        if not self._strong_uptrend(context):
            return super().signal(context)

        strong_update = LifecycleParameterUpdate(
            stop_loss=self.STRONG_UPTREND_STOP_LOSS,
            trailing_profit=self.STRONG_UPTREND_TRAILING_PROFIT,
            trailing_deviation=self.STRONG_UPTREND_TRAILING_DEVIATION,
            enable_dynamic_trailing=True,
            allow_stop_loss_widening=True,
            trailing_stop_floor_at_entry=True,
        )
        changed = (
            not context.bot.dynamic_trailing
            or context.bot.stop_loss != strong_update.stop_loss
            or context.bot.trailing_profit != strong_update.trailing_profit
            or context.bot.trailing_deviation != strong_update.trailing_deviation
        )
        return LifecycleSignal(
            parameter_update=strong_update,
            log_messages=(
                (
                    "[top_gainer_early_momentum] Strong uptrend confirmed; "
                    "enabling the loose 10% emergency stop and 9% trailing profile."
                ),
            )
            if changed
            else (),
        )
