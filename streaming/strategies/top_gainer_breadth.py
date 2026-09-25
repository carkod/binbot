from streaming.strategies.base import LifecyclePolicy
from streaming.strategies.default import DefaultLifecycleStrategy


class TopGainerBreadthLifecycleStrategy(DefaultLifecycleStrategy):
    """Manage an open top-gainer breadth short with standard protection.

    Entry belongs to binquant. Once the short is open, this strategy only
    derives bounded stop-loss and trailing parameters from the live market.
    It deliberately emits no breadth-based algorithmic exit.
    """

    algorithm_names = frozenset({"top_gainer_breadth"})
    policy = LifecyclePolicy(
        low_price_stop_floor_pct=None,
        reversal_enabled=False,
        recovery_enabled=False,
        stale_position_close_enabled=False,
    )
