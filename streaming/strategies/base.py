from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar, Protocol

from pandas import DataFrame
from pybinbot import BotModel, DealType, OrderStatus, Position


@dataclass(frozen=True)
class EmergencyStopBounds:
    minimum_pct: float = 0.75
    maximum_pct: float = 1.5


@dataclass(frozen=True)
class LifecyclePolicy:
    low_price_stop_floor_pct: float | None = 4.0
    emergency_stop_bounds: EmergencyStopBounds = field(
        default_factory=EmergencyStopBounds
    )
    block_reversal_after_loss: bool = False
    exchange_stop_owns_breach: bool = False


class LifecycleExitKind(str, Enum):
    algorithmic_close = "algorithmic_close"


@dataclass(frozen=True)
class LifecycleExitIntent:
    kind: LifecycleExitKind
    log_message: str
    max_holding_bars: int | None = None


@dataclass(frozen=True)
class LifecycleParameterUpdate:
    stop_loss: float
    trailing_profit: float
    trailing_deviation: float


@dataclass(frozen=True)
class LifecycleSignal:
    parameter_update: LifecycleParameterUpdate | None = None
    exit_intent: LifecycleExitIntent | None = None
    log_messages: tuple[str, ...] = ()


@dataclass(frozen=True)
class LifecycleContext:
    bot: BotModel
    current_price: float
    interval_ms: int
    now_ms: int
    klines: list
    completed_candles: list
    df: DataFrame
    btc_df: DataFrame
    bb_metrics: tuple[float, float] | None
    bot_profit: float
    has_live_stop_loss: bool


class LifecycleStrategy(Protocol):
    algorithm_names: ClassVar[frozenset[str]]
    policy: ClassVar[LifecyclePolicy]

    def signal(self, context: LifecycleContext) -> LifecycleSignal: ...


class BaseLifecycleStrategy:
    algorithm_names: ClassVar[frozenset[str]] = frozenset()
    policy: ClassVar[LifecyclePolicy] = LifecyclePolicy()

    @staticmethod
    def direction(bot: BotModel) -> int:
        return -1 if bot.position == Position.short else 1

    @staticmethod
    def is_recovery_bot(bot: BotModel) -> bool:
        recovery_params = bot.recovery_params
        return (
            recovery_params is not None and recovery_params.reversal_path == "recovery"
        )

    @staticmethod
    def max_holding_exit(
        context: LifecycleContext,
        *,
        max_holding_bars: int,
        positions: frozenset[Position] | None = None,
    ) -> LifecycleExitIntent | None:
        if positions is not None and context.bot.position not in positions:
            return None

        opening_timestamp = context.bot.deal.opening_timestamp
        if opening_timestamp <= 0:
            return None

        entry_candle_open = opening_timestamp - (
            opening_timestamp % context.interval_ms
        )
        completed_after_entry = sum(
            1
            for candle in context.completed_candles
            if len(candle) >= 1 and int(float(candle[0])) > entry_candle_open
        )
        if completed_after_entry < max_holding_bars:
            return None

        return LifecycleExitIntent(
            kind=LifecycleExitKind.algorithmic_close,
            max_holding_bars=max_holding_bars,
            log_message=(
                f"[{context.bot.name}] Maximum holding period reached after "
                f"{max_holding_bars} completed candles; closing position."
            ),
        )

    @staticmethod
    def atr_pct(context: LifecycleContext, window: int) -> float | None:
        if len(context.klines) < window + 1 or context.current_price <= 0:
            return None

        true_ranges: list[float] = []
        for index in range(len(context.klines) - window, len(context.klines)):
            if index <= 0:
                continue
            previous_close = float(context.klines[index - 1][4])
            high = float(context.klines[index][2])
            low = float(context.klines[index][3])
            true_ranges.append(
                max(
                    high - low,
                    abs(high - previous_close),
                    abs(low - previous_close),
                )
            )

        if not true_ranges:
            return None
        return (sum(true_ranges) / len(true_ranges)) / context.current_price * 100

    @staticmethod
    def has_live_stop_loss(bot: BotModel) -> bool:
        terminal_statuses = {
            OrderStatus.FILLED,
            OrderStatus.CANCELED,
            OrderStatus.EXPIRED,
            OrderStatus.REJECTED,
        }
        return any(
            order.deal_type == DealType.stop_loss
            and order.status not in terminal_statuses
            for order in bot.orders
        )
