from pybinbot import Position, breadth_momentum_reversal, btc_trend_confirms

from streaming.strategies.base import (
    LifecycleContext,
    LifecycleExitIntent,
    LifecycleExitKind,
    LifecycleSignal,
)
from streaming.strategies.default import DefaultLifecycleStrategy


class TopGainerBreadthLifecycleStrategy(DefaultLifecycleStrategy):
    """Live-tick mirror of binquant's top_gainer_breadth exit.

    binquant closes this bot when market-breadth momentum reverses off an
    extended bullish reading and BTC confirms a downtrend, but only checks
    on its own signal-generation cadence. This gives the same exit a faster,
    tick-by-tick check inside streaming, using the exact same shared
    pybinbot math (breadth_momentum_reversal / btc_trend_confirms) so the
    two surfaces can't drift out of calibration with each other.
    """

    algorithm_names = frozenset({"top_gainer_breadth"})

    def _breadth_reversal_exit(
        self, context: LifecycleContext
    ) -> LifecycleExitIntent | None:
        if context.bot.position != Position.long:
            return None

        exit_values, _ = breadth_momentum_reversal(context.market_breadth, direction=-1)
        if exit_values is None:
            return None

        breadth_timestamp_ms = int(exit_values["breadth_timestamp"] * 1000)
        if breadth_timestamp_ms < max(
            context.now_ms - context.interval_ms,
            context.bot.deal.opening_timestamp,
        ):
            return None

        if btc_trend_confirms(context.btc_df, direction=-1) is None:
            return None

        return LifecycleExitIntent(
            kind=LifecycleExitKind.algorithmic_close,
            log_message=(
                "[top_gainer_breadth] breadth momentum reversed off an "
                f"extended bullish reading (market_breadth="
                f"{exit_values['market_breadth']:.4f}) and BTC confirmed a "
                "downtrend; closing position."
            ),
        )

    def signal(self, context: LifecycleContext) -> LifecycleSignal:
        base_signal = super().signal(context)
        exit_intent = self._breadth_reversal_exit(context)
        if exit_intent is None:
            return base_signal

        return LifecycleSignal(
            parameter_update=base_signal.parameter_update,
            exit_intent=exit_intent,
            log_messages=base_signal.log_messages,
        )
