from streaming.strategies.base import LifecyclePolicy
from streaming.strategies.default import DefaultLifecycleStrategy


class TopGainerBreadthLifecycleStrategy(DefaultLifecycleStrategy):
    """Manage a top-gainer breadth short and its recovery long.

    Entry belongs to binquant. The source short uses bounded stop-loss and
    trailing parameters from the live market. A confirmed stop breakout may
    reverse it into one protected recovery long. This strategy deliberately
    emits no breadth-based algorithmic exit.
    """

    algorithm_names = frozenset({"top_gainer_breadth"})
    policy = LifecyclePolicy(
        low_price_stop_floor_pct=None,
        reversal_enabled=True,
        recovery_enabled=True,
        stale_position_close_enabled=False,
    )
