from streaming.strategies.base import LifecyclePolicy
from streaming.strategies.default import DefaultLifecycleStrategy


class TopGainerEarlyMomentumLifecycleStrategy(DefaultLifecycleStrategy):
    algorithm_names = frozenset({"top_gainer_early_momentum"})
    policy = LifecyclePolicy(exchange_stop_owns_breach=True)
