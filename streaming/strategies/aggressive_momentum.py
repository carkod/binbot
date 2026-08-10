from streaming.strategies.base import LifecycleContext
from streaming.strategies.default import DefaultLifecycleStrategy


class AggressiveMomentumLifecycleStrategy(DefaultLifecycleStrategy):
    @staticmethod
    def matches(algorithm_name: str) -> bool:
        return "aggressive momo" in algorithm_name.lower()

    def _initial_stop_loss(
        self,
        context: LifecycleContext,
        expansion_range: float,
    ) -> float:
        return expansion_range * 0.5 / context.bot.deal.opening_price * 100
