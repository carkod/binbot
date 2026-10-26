from typing import ClassVar

from pybinbot import BinanceKlineIntervals
from pybinbot.shared.price_crossings import price_crossings_six_hours

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

    After six hours from entry, market-close positions with at least three
    current-price crossings over six hours. Standard protection stays active
    throughout the holding period; entry eligibility belongs to binquant.
    """

    algorithm_names = frozenset({"top_gainer_short"})
    PRICE_CROSSING_EXIT_THRESHOLD = 3
    MIN_CROSSING_EXIT_HOLD_MS = 6 * 60 * 60 * 1000
    candlestick_interval: ClassVar[BinanceKlineIntervals | None] = (
        BinanceKlineIntervals.fifteen_minutes
    )
    policy = LifecyclePolicy(
        low_price_stop_floor_pct=None,
        recovery_enabled=False,
        stale_position_close_enabled=False,
        strategy_exit_before_sizing=True,
    )

    def signal(self, context: LifecycleContext) -> LifecycleSignal:
        opening_timestamp = context.bot.deal.opening_timestamp
        if (
            opening_timestamp > 0
            and context.now_ms - opening_timestamp >= self.MIN_CROSSING_EXIT_HOLD_MS
        ):
            crossings = price_crossings_six_hours(
                context.df,
                context.current_price,
                now_ms=context.now_ms,
                interval_ms=context.interval_ms,
            )
            if (
                crossings is not None
                and crossings >= self.PRICE_CROSSING_EXIT_THRESHOLD
            ):
                return LifecycleSignal(
                    exit_intent=LifecycleExitIntent(
                        kind=LifecycleExitKind.algorithmic_close,
                        market_only=True,
                        log_message=(
                            f"[top_gainer_short] {crossings} current-price crossings "
                            "in the last six hours after at least six hours open; "
                            "market-closing the full position."
                        ),
                    )
                )
        return super().signal(context)
