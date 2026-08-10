from pybinbot import round_numbers

from api.tools.utils import clamp
from streaming.strategies.base import LifecycleContext, LifecycleParameterUpdate
from streaming.strategies.default import DefaultLifecycleStrategy


class AggressiveMomentumLifecycleStrategy(DefaultLifecycleStrategy):
    PULLBACK_ARM_PROFIT = 1.0
    SHALLOW_PULLBACK = 0.75
    DEEP_PULLBACK = 1.5

    @staticmethod
    def matches(algorithm_name: str) -> bool:
        return "aggressive momo" in algorithm_name.lower()

    def _initial_stop_loss(
        self,
        context: LifecycleContext,
        expansion_range: float,
    ) -> float:
        return expansion_range * 0.5 / context.bot.deal.opening_price * 100

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

    def _dynamic_parameter_update(
        self,
        context: LifecycleContext,
    ) -> LifecycleParameterUpdate | None:
        update = super()._dynamic_parameter_update(context)
        if update is None:
            return None

        trailing_profit = update.trailing_profit
        trailing_deviation = update.trailing_deviation
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

        trailing_profit = clamp(
            trailing_profit,
            self.MIN_TRAILING_PROFIT,
            self.MAX_TRAILING_PROFIT,
        )
        maximum_deviation = min(
            self.MAX_TRAILING_DEVIATION,
            trailing_profit - self.MIN_TRAIL_GAP,
        )
        trailing_deviation = clamp(
            trailing_deviation,
            self.MIN_TRAILING_DEVIATION,
            maximum_deviation,
        )
        return LifecycleParameterUpdate(
            stop_loss=update.stop_loss,
            trailing_profit=round_numbers(trailing_profit, 2),
            trailing_deviation=round_numbers(trailing_deviation, 2),
        )
