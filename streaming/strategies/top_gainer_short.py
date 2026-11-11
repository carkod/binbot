from decimal import ROUND_CEILING, Decimal
from math import isfinite
from typing import ClassVar, NamedTuple

from pybinbot import BinanceKlineIntervals, Position
from pybinbot.shared.price_crossings import price_crossings_six_hours

from streaming.strategies.base import (
    LifecycleContext,
    LifecycleExitIntent,
    LifecycleExitKind,
    LifecycleParameterUpdate,
    LifecyclePolicy,
    LifecycleSignal,
)
from streaming.strategies.default import DefaultLifecycleStrategy


class LowerHighSwing(NamedTuple):
    """Confirmed lower-high peak and the candle swing range that led into it."""

    peak: float
    swing_range_pct: float


class TopGainerShortLifecycleStrategy(DefaultLifecycleStrategy):
    """Manage an open top-gainer short with standard protection.

    After six hours from entry, market-close positions with at least three
    current-price crossings over six hours. Standard protection stays active
    throughout the holding period; entry eligibility belongs to binquant.
    """

    algorithm_names = frozenset({"top_gainer_short"})
    PRICE_CROSSING_EXIT_THRESHOLD = 3
    MIN_CROSSING_EXIT_HOLD_MS = 6 * 60 * 60 * 1000
    LOWER_HIGH_LOOKBACK_BARS = 40
    LOWER_HIGH_FRACTAL_WING = 2
    LOWER_HIGH_MIN_RISE_PCT = 2.0
    LOWER_HIGH_MIN_DROP_PCT = 2.5
    # trailing_profit - trailing_deviation equals the candle swing range, so the
    # deviation never drops below this floor on very large swings.
    MIN_TRAILING_DEVIATION_PCT = 0.5
    # Existing positions retain their original stop policy. This feature only
    # manages positions opened after the 2026-11-01 16:00 UTC rollout boundary.
    STRUCTURAL_TRAIL_MIN_ENTRY_TIMESTAMP_MS = 1_793_548_800_000
    candlestick_interval: ClassVar[BinanceKlineIntervals | None] = (
        BinanceKlineIntervals.fifteen_minutes
    )
    policy = LifecyclePolicy(
        low_price_stop_floor_pct=None,
        recovery_enabled=False,
        stale_position_close_enabled=False,
        strategy_exit_before_sizing=True,
    )

    @classmethod
    def latest_lower_high(cls, context: LifecycleContext) -> LowerHighSwing | None:
        """Match binquant's confirmed 15m lower-high structure on closed bars.

        The swing range is the rise from the preceding swing low to the first
        peak, as binquant's lower-high pattern reports it.
        """
        candles = context.completed_candles[-cls.LOWER_HIGH_LOOKBACK_BARS :]
        if len(candles) < cls.LOWER_HIGH_LOOKBACK_BARS:
            return None
        try:
            timestamps = [int(candle[0]) for candle in candles]
            highs = [float(candle[2]) for candle in candles]
            lows = [float(candle[3]) for candle in candles]
        except IndexError, TypeError, ValueError:
            return None
        if any(
            later - earlier != context.interval_ms
            for earlier, later in zip(timestamps, timestamps[1:])
        ) or any(
            not isfinite(high) or not isfinite(low) or high <= 0 or low <= 0
            for high, low in zip(highs, lows)
        ):
            return None

        wing = cls.LOWER_HIGH_FRACTAL_WING
        swing_highs = [
            index
            for index in range(wing, len(highs) - wing)
            if highs[index] == max(highs[index - wing : index + wing + 1])
            and highs[index - wing : index + wing + 1].count(highs[index]) == 1
        ]
        if len(swing_highs) < 2:
            return None
        earlier, later = swing_highs[-2:]
        if timestamps[later] <= context.bot.deal.opening_timestamp:
            return None
        swing_lows = [
            index
            for index in range(wing, earlier)
            if lows[index] == min(lows[index - wing : index + wing + 1])
            and lows[index - wing : index + wing + 1].count(lows[index]) == 1
        ]
        if not swing_lows:
            return None
        earlier_high = highs[earlier]
        later_high = highs[later]
        swing_low = lows[swing_lows[-1]]
        swing_range_pct = (earlier_high / swing_low - 1) * 100
        if (
            swing_range_pct < cls.LOWER_HIGH_MIN_RISE_PCT
            or (1 - later_high / earlier_high) * 100 < cls.LOWER_HIGH_MIN_DROP_PCT
        ):
            return None
        return LowerHighSwing(peak=later_high, swing_range_pct=swing_range_pct)

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
        default_signal = super().signal(context)
        bot = context.bot
        if (
            default_signal.parameter_update is not None
            or bot.position != Position.short
            or not bot.trailing
            or bot.deal.opening_price <= 0
            or bot.deal.opening_timestamp < self.STRUCTURAL_TRAIL_MIN_ENTRY_TIMESTAMP_MS
            or context.current_price <= 0
        ):
            return default_signal

        lower_high = self.latest_lower_high(context)
        if lower_high is None:
            return default_signal
        stop_price = float(
            Decimal(str(lower_high.peak)).quantize(
                Decimal(1).scaleb(-context.price_precision), rounding=ROUND_CEILING
            )
        )
        current_stop = (
            bot.deal.trailing_stop_loss_price
            if bot.deal.trailing_stop_loss_price > 0
            else bot.deal.stop_loss_price
        )
        # For a short, a lower stop protects more profit. Never arm a trail
        # above entry or replace an existing tighter exchange stop.
        if (
            stop_price <= context.current_price
            or stop_price >= bot.deal.opening_price
            or (current_stop > 0 and stop_price >= current_stop)
        ):
            return default_signal
        # Keep the deviation below trailing profit by the candle swing range
        # instead of the peak-to-price distance, which can exceed 4%.
        trailing_deviation = float(
            max(
                Decimal(str(bot.trailing_profit))
                - Decimal(str(lower_high.swing_range_pct)),
                Decimal(str(self.MIN_TRAILING_DEVIATION_PCT)),
            ).quantize(Decimal("0.0001"), rounding=ROUND_CEILING)
        )
        if not 0 < trailing_deviation < 100:
            return default_signal
        return LifecycleSignal(
            parameter_update=LifecycleParameterUpdate(
                stop_loss=bot.stop_loss,
                trailing_profit=bot.trailing_profit,
                trailing_deviation=trailing_deviation,
                trailing_stop_price=stop_price,
            ),
            log_messages=(
                f"[top_gainer_short] Confirmed lower-high peak {stop_price} is "
                "below entry; tightening the exchange trailing stop with "
                f"{trailing_deviation}% deviation (trailing profit "
                f"{bot.trailing_profit}% minus {lower_high.swing_range_pct:.4f}% "
                "candle swing range).",
            ),
        )
