from streaming.strategies.base import LifecyclePolicy
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
    policy = LifecyclePolicy(wait_for_exit_liquidity=True)
