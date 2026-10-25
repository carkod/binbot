from typing import ClassVar

from pybinbot import BinanceKlineIntervals
from pybinbot.shared.price_crossings import (
    CHOP_LOOKBACK_HOURS,
    price_crossings_six_hours,
)

from streaming.strategies.base import (
    LifecycleContext,
    LifecycleExitIntent,
    LifecycleExitKind,
    LifecyclePolicy,
    LifecycleSignal,
)
from streaming.strategies.default import DefaultLifecycleStrategy


class TopGainerShortLifecycleStrategy(DefaultLifecycleStrategy):
    """Manage an open top-gainer short with standard protection.

    Keep standard protection and market-close choppy positions after three
    current-price crossings in the last six hours of completed candles.
    Position increases belong to dynamic sizing. Recovery follows the bot's
    configuration and cannot be combined with dynamic sizing.
    """

    algorithm_names = frozenset({"top_gainer_short"})
    PRICE_CROSSING_EXIT_THRESHOLD = 3
    candlestick_interval: ClassVar[BinanceKlineIntervals | None] = (
        BinanceKlineIntervals.fifteen_minutes
    )
    policy = LifecyclePolicy(
        low_price_stop_floor_pct=None,
        stale_position_close_enabled=False,
        strategy_exit_before_sizing=True,
    )

    def signal(self, context: LifecycleContext) -> LifecycleSignal:
        crossings = price_crossings_six_hours(
            context.df,
            context.current_price,
            now_ms=context.now_ms,
            interval_ms=context.interval_ms,
        )
        if crossings is not None and crossings >= self.PRICE_CROSSING_EXIT_THRESHOLD:
            return LifecycleSignal(
                exit_intent=LifecycleExitIntent(
                    kind=LifecycleExitKind.algorithmic_close,
                    market_only=True,
                    log_message=(
                        f"[top_gainer_short] {crossings} current-price crossings "
                        f"in the last {CHOP_LOOKBACK_HOURS} hours; "
                        "market-closing the full position."
                    ),
                )
            )
        return super().signal(context)
