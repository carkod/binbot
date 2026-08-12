from dataclasses import replace

from pybinbot import Position

from streaming.strategies.base import (
    LifecycleContext,
    LifecyclePolicy,
    LifecycleSignal,
)
from streaming.strategies.default import DefaultLifecycleStrategy


class RelativeStrengthImpulseRiderLifecycleStrategy(DefaultLifecycleStrategy):
    algorithm_names = frozenset({"relative_strength_impulse_rider"})
    policy = LifecyclePolicy(low_price_stop_floor_pct=None)
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
