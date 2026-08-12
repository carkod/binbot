from dataclasses import replace

from pybinbot import Position

from streaming.strategies.base import (
    LifecycleContext,
    LifecyclePolicy,
    LifecycleSignal,
)
from streaming.strategies.default import DefaultLifecycleStrategy


class PriceTrackerLifecycleStrategy(DefaultLifecycleStrategy):
    algorithm_names = frozenset({"coinrule_price_tracker"})
    policy = LifecyclePolicy(block_reversal_after_loss=True)
    MAX_HOLDING_BARS = 8

    def signal(self, context: LifecycleContext) -> LifecycleSignal:
        signal = super().signal(context)
        return replace(
            signal,
            exit_intent=self.max_holding_exit(
                context,
                max_holding_bars=self.MAX_HOLDING_BARS,
                positions=frozenset({Position.long}),
            ),
        )
