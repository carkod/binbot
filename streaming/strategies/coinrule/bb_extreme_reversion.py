from pybinbot import MarketType, Position, round_numbers

from api.tools.utils import clamp
from streaming.strategies.base import (
    LifecycleContext,
    LifecycleParameterUpdate,
    LifecyclePolicy,
    LifecycleSignal,
)
from streaming.strategies.default import DefaultLifecycleStrategy


class BBExtremeReversionLifecycleStrategy(DefaultLifecycleStrategy):
    algorithm_names = frozenset({"bb_extreme_reversion"})
    policy = LifecyclePolicy(block_reversal_after_loss=True)
    ATR_WINDOW = 14
    ATR_STOP_MULTIPLIER = 2.0

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
        ):
            return None

        if bot.stop_loss > 0:
            stop_loss = clamp(
                bot.stop_loss,
                self.MIN_STOP_LOSS,
                self.MAX_STOP_LOSS,
            )
        else:
            atr_pct = self.atr_pct(context, self.ATR_WINDOW)
            stop_loss = (
                3.0
                if atr_pct is None
                else clamp(
                    self.ATR_STOP_MULTIPLIER * atr_pct,
                    self.MIN_STOP_LOSS,
                    self.MAX_STOP_LOSS,
                )
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

        return LifecycleParameterUpdate(
            stop_loss=round_numbers(stop_loss, 2),
            trailing_profit=round_numbers(trailing_profit, 2),
            trailing_deviation=round_numbers(trailing_deviation, 2),
        )

    def signal(self, context: LifecycleContext) -> LifecycleSignal:
        return LifecycleSignal(parameter_update=self._dynamic_parameter_update(context))
