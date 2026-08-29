from streaming.strategies.default import DefaultLifecycleStrategy


class TopGainerEarlyMomentumLifecycleStrategy(DefaultLifecycleStrategy):
    """Keep volatile top-gainer runners alive long enough to express their edge."""

    algorithm_names = frozenset({"top_gainer_early_momentum"})

    MIN_STOP_LOSS = 2.0
    MIN_TRAILING_PROFIT = 6.0
    MAX_TRAILING_PROFIT = 8.0
    MIN_TRAILING_DEVIATION = 2.5
    MAX_TRAILING_DEVIATION = 4.0
