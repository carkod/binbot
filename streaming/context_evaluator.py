from __future__ import annotations

import logging
from dataclasses import dataclass

from streaming.strategies.aggressive_momentum import (
    AggressiveMomentumLifecycleStrategy,
)
from streaming.strategies.base import (
    LifecycleContext,
    LifecyclePolicy,
    LifecycleSignal,
    LifecycleStrategy,
)
from streaming.strategies.coinrule.bb_extreme_reversion import (
    BBExtremeReversionLifecycleStrategy,
)
from streaming.strategies.coinrule.buy_the_dip import BuyTheDipLifecycleStrategy
from streaming.strategies.coinrule.price_tracker import PriceTrackerLifecycleStrategy
from streaming.strategies.default import DefaultLifecycleStrategy
from streaming.strategies.liquidation_sweep_pump import (
    LiquidationSweepPumpLifecycleStrategy,
)
from streaming.strategies.mean_reversion_fade import (
    MeanReversionFadeLifecycleStrategy,
)
from streaming.strategies.relative_strength_impulse_rider import (
    RelativeStrengthImpulseRiderLifecycleStrategy,
)
from streaming.strategies.top_gainer_early_momentum import (
    TopGainerEarlyMomentumLifecycleStrategy,
)


@dataclass(frozen=True)
class LifecycleEvaluation:
    policy: LifecyclePolicy
    signal: LifecycleSignal


class LifecycleContextEvaluator:
    STRATEGY_TYPES = (
        MeanReversionFadeLifecycleStrategy,
        LiquidationSweepPumpLifecycleStrategy,
        RelativeStrengthImpulseRiderLifecycleStrategy,
        TopGainerEarlyMomentumLifecycleStrategy,
        PriceTrackerLifecycleStrategy,
        BuyTheDipLifecycleStrategy,
        BBExtremeReversionLifecycleStrategy,
    )
    STRATEGY_REGISTRY = {
        algorithm_name: strategy_type
        for strategy_type in STRATEGY_TYPES
        for algorithm_name in strategy_type.algorithm_names
    }

    @classmethod
    def resolve(cls, algorithm_name: str) -> LifecycleStrategy:
        strategy_type = cls.STRATEGY_REGISTRY.get(algorithm_name)
        if strategy_type is not None:
            return strategy_type()
        if AggressiveMomentumLifecycleStrategy.matches(algorithm_name):
            return AggressiveMomentumLifecycleStrategy()
        return DefaultLifecycleStrategy()

    def evaluate(self, context: LifecycleContext) -> LifecycleEvaluation:
        strategy = self.resolve(context.bot.name)
        try:
            signal = strategy.signal(context)
        except Exception:
            logging.exception(
                "Lifecycle strategy %s raised while processing %s; "
                "continuing without strategy mutations for this tick.",
                context.bot.name,
                context.bot.pair,
            )
            signal = LifecycleSignal(
                log_messages=(
                    f"Lifecycle strategy {context.bot.name} failed; "
                    "skipping strategy-specific mutations for this tick.",
                )
            )
        return LifecycleEvaluation(policy=strategy.policy, signal=signal)
