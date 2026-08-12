from dataclasses import replace

from pybinbot import Position

from streaming.strategies.base import (
    EmergencyStopBounds,
    LifecycleContext,
    LifecyclePolicy,
    LifecycleSignal,
)
from streaming.strategies.default import DefaultLifecycleStrategy


class LiquidationSweepPumpLifecycleStrategy(DefaultLifecycleStrategy):
    algorithm_names = frozenset({"liquidation_sweep_pump"})
    policy = LifecyclePolicy(
        emergency_stop_bounds=EmergencyStopBounds(
            minimum_pct=0.35,
            maximum_pct=0.75,
        )
    )
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
