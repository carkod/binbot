import types
from time import time
from typing import Any, cast
from uuid import uuid4

import pytest
from pandas import DataFrame
from pybinbot import (
    BotModel,
    DealModel,
    MarketType,
    Position,
    RecoveryBotModel,
)

from streaming.context_evaluator import LifecycleContextEvaluator
from streaming.position_market import PositionMarket
from streaming.strategies.base import LifecycleContext, LifecycleExitKind
from streaming.strategies.coinrule.bb_extreme_reversion import (
    BBExtremeReversionLifecycleStrategy,
)
from streaming.strategies.coinrule.price_tracker import PriceTrackerLifecycleStrategy
from streaming.strategies.default import DefaultLifecycleStrategy
from streaming.strategies.liquidation_sweep_pump import (
    LiquidationSweepPumpLifecycleStrategy,
)
from streaming.strategies.mean_reversion_fade import (
    MeanReversionFadeLifecycleStrategy,
)
from streaming.strategies.relative_strength_impulse_rider import (
    RelativeStrengthImpulseRiderLifecycleStrategy,
)


INTERVAL_MS = 15 * 60 * 1000


class FakeApexFlowClose:
    def __init__(self, df: DataFrame, _: DataFrame) -> None:
        self.df = df if not df.empty else DataFrame([{"high": 102.0, "low": 98.0}])

    def get_detectors(self) -> dict[str, bool]:
        return {"vce": False, "mcd": False, "lcrs": False}

    def get_trend_ema(self) -> tuple[float, float]:
        return 101.0, 100.0


def _candles(count: int = 220, *, start: int = 1_800_000_000_000) -> list:
    return [
        [
            start + index * INTERVAL_MS,
            100.0,
            102.0,
            98.0,
            100.0,
            1.0,
            start + (index + 1) * INTERVAL_MS - 1,
        ]
        for index in range(count)
    ]


def _context(
    *,
    name: str = "another_strategy",
    position: Position = Position.long,
    stop_loss: float = 2.0,
    dynamic_trailing: bool = False,
    klines: list | None = None,
    completed_candles: list | None = None,
    opening_timestamp: int = 0,
    current_price: float = 100.0,
    bb_metrics: tuple[float, float] | None = (2.0, 1.5),
    bot_profit: float = 0.0,
) -> LifecycleContext:
    bot = BotModel(
        pair="BEATUSDTM",
        name=name,
        market_type=MarketType.FUTURES,
        position=position,
        stop_loss=stop_loss,
        trailing=True,
        dynamic_trailing=dynamic_trailing,
        trailing_profit=2.0,
        trailing_deviation=1.0,
        deal=DealModel(
            opening_price=100.0,
            opening_timestamp=opening_timestamp,
        ),
    )
    bot.position = position
    rows = klines or _candles()
    return LifecycleContext(
        bot=bot,
        current_price=current_price,
        interval_ms=INTERVAL_MS,
        now_ms=int(time() * 1000),
        klines=rows,
        completed_candles=completed_candles or rows,
        df=DataFrame([{"high": 102.0, "low": 98.0}]),
        btc_df=DataFrame(),
        bb_metrics=bb_metrics,
        bot_profit=bot_profit,
    )


@pytest.mark.parametrize(
    ("algorithm_name", "strategy_type"),
    [
        ("mean_reversion_fade", MeanReversionFadeLifecycleStrategy),
        ("liquidation_sweep_pump", LiquidationSweepPumpLifecycleStrategy),
        (
            "relative_strength_impulse_rider",
            RelativeStrengthImpulseRiderLifecycleStrategy,
        ),
        ("top_gainer_early_momentum", DefaultLifecycleStrategy),
        ("coinrule_price_tracker", PriceTrackerLifecycleStrategy),
        ("coinrule_buy_the_dip", DefaultLifecycleStrategy),
        ("bb_extreme_reversion", BBExtremeReversionLifecycleStrategy),
        ("legacy aggressive momo bot", DefaultLifecycleStrategy),
        ("unknown", DefaultLifecycleStrategy),
    ],
)
def test_context_evaluator_resolves_lifecycle_strategy(
    algorithm_name: str,
    strategy_type: type,
) -> None:
    assert isinstance(LifecycleContextEvaluator.resolve(algorithm_name), strategy_type)


def test_strategy_policies_replace_lifecycle_name_branches() -> None:
    evaluator = LifecycleContextEvaluator()

    mean_reversion = evaluator.evaluate(_context(name="mean_reversion_fade"))
    relative_strength = evaluator.evaluate(
        _context(name="relative_strength_impulse_rider")
    )
    liquidation_sweep = evaluator.evaluate(_context(name="liquidation_sweep_pump"))

    assert mean_reversion.policy.low_price_stop_floor_pct is None
    assert relative_strength.policy.low_price_stop_floor_pct is None
    assert liquidation_sweep.policy.emergency_stop_bounds.minimum_pct == 0.35
    assert liquidation_sweep.policy.emergency_stop_bounds.maximum_pct == 0.75
    assert evaluator.evaluate(_context()).policy.low_price_stop_floor_pct == 4.0


@pytest.mark.parametrize(
    "algorithm_name",
    ["coinrule_price_tracker", "bb_extreme_reversion"],
)
def test_chop_prone_strategies_block_reversal_after_loss(
    algorithm_name: str,
) -> None:
    evaluation = LifecycleContextEvaluator().evaluate(_context(name=algorithm_name))

    assert evaluation.policy.block_reversal_after_loss is True


@pytest.mark.parametrize(
    ("algorithm_name", "position", "expects_exit"),
    [
        ("mean_reversion_fade", Position.short, True),
        ("liquidation_sweep_pump", Position.long, True),
        ("liquidation_sweep_pump", Position.short, False),
        ("coinrule_price_tracker", Position.long, True),
        ("coinrule_price_tracker", Position.short, False),
        ("relative_strength_impulse_rider", Position.long, True),
        ("another_strategy", Position.long, False),
    ],
)
def test_strategy_max_holding_signal_is_direction_scoped(
    algorithm_name: str,
    position: Position,
    expects_exit: bool,
) -> None:
    entry_open = 1_800_000_000_000
    completed = _candles(9, start=entry_open)
    context = _context(
        name=algorithm_name,
        position=position,
        opening_timestamp=entry_open + 1_000,
        klines=completed,
        completed_candles=completed,
    )

    exit_intent = LifecycleContextEvaluator().evaluate(context).signal.exit_intent

    assert (exit_intent is not None) is expects_exit
    if exit_intent is not None:
        assert exit_intent.kind == LifecycleExitKind.algorithmic_close
        assert exit_intent.max_holding_bars == 8


def test_default_dynamic_signal_runs_for_long_and_short(monkeypatch) -> None:
    monkeypatch.setattr(
        "streaming.strategies.default.ApexFlowClose",
        FakeApexFlowClose,
    )

    long_signal = DefaultLifecycleStrategy().signal(
        _context(dynamic_trailing=True, position=Position.long)
    )
    short_signal = DefaultLifecycleStrategy().signal(
        _context(dynamic_trailing=True, position=Position.short)
    )

    assert long_signal.parameter_update is not None
    assert short_signal.parameter_update is not None
    assert long_signal.parameter_update.stop_loss == 1.5
    assert short_signal.parameter_update.stop_loss == 2.0


def test_default_dynamic_signal_preserves_recovery_parameters(monkeypatch) -> None:
    monkeypatch.setattr(
        "streaming.strategies.default.ApexFlowClose",
        FakeApexFlowClose,
    )
    context = _context(dynamic_trailing=True)
    context.bot.recovery_params = RecoveryBotModel(
        id=uuid4(),
        reversal_path="recovery",
        created_at=1,
        updated_at=1,
    )

    assert DefaultLifecycleStrategy().signal(context).parameter_update is None


def test_default_runtime_strategy_preserves_pullback_adjustment(monkeypatch) -> None:
    monkeypatch.setattr(
        "streaming.strategies.default.ApexFlowClose",
        FakeApexFlowClose,
    )
    candles = _candles()
    context = _context(
        name="legacy aggressive momo bot",
        dynamic_trailing=True,
        opening_timestamp=int(candles[0][0]),
        current_price=101.8,
        klines=candles,
    )

    update = DefaultLifecycleStrategy().signal(context).parameter_update

    assert update is not None
    assert update.trailing_profit == 2.25
    assert update.trailing_deviation == 1.55


def test_bb_extreme_reversion_uses_atr_stop_and_bb_trailing() -> None:
    context = _context(
        name="bb_extreme_reversion",
        stop_loss=0.0,
        dynamic_trailing=True,
    )

    update = BBExtremeReversionLifecycleStrategy().signal(context).parameter_update

    assert update is not None
    assert update.stop_loss == 4.0
    assert update.trailing_profit == 2.0
    assert update.trailing_deviation == 1.5


def test_bb_extreme_reversion_pins_existing_stop_for_short() -> None:
    context = _context(
        name="bb_extreme_reversion",
        position=Position.short,
        stop_loss=1.25,
        dynamic_trailing=True,
    )

    update = BBExtremeReversionLifecycleStrategy().signal(context).parameter_update

    assert update is not None
    assert update.stop_loss == 1.25


def test_mean_reversion_uses_conservative_atr_cap() -> None:
    context = _context(
        name="mean_reversion_fade",
        position=Position.short,
        stop_loss=0.0,
        dynamic_trailing=True,
    )

    update = MeanReversionFadeLifecycleStrategy().signal(context).parameter_update

    assert update is not None
    assert update.stop_loss == 3.0
    assert update.trailing_profit == 2.0
    assert update.trailing_deviation == 1.5


def test_mean_reversion_thesis_invalidation_tightens_stop(monkeypatch) -> None:
    strategy = MeanReversionFadeLifecycleStrategy()
    monkeypatch.setattr(strategy, "_thesis_invalidated", lambda context: True)
    context = _context(
        name="mean_reversion_fade",
        position=Position.long,
        stop_loss=3.0,
        dynamic_trailing=True,
        current_price=99.0,
    )

    signal = strategy.signal(context)

    assert signal.parameter_update is not None
    assert signal.parameter_update.stop_loss == 1.0
    assert any("thesis invalidation" in message for message in signal.log_messages)


def test_mean_reversion_rsi_is_100_for_window_without_losses() -> None:
    now_ms = int(time() * 1000)
    start = now_ms - 30 * INTERVAL_MS
    candles = [
        [
            start + index * INTERVAL_MS,
            100.0 + index,
            101.5 + index,
            99.5 + index,
            101.0 + index,
            1.0,
        ]
        for index in range(20)
    ]
    context = _context(
        name="mean_reversion_fade",
        klines=candles,
        completed_candles=candles,
    )
    context = LifecycleContext(
        **{
            **context.__dict__,
            "now_ms": now_ms,
        }
    )

    rsi = MeanReversionFadeLifecycleStrategy()._rsi_series(context)

    assert rsi is not None
    assert float(rsi.iloc[-1]) == 100.0


def test_position_market_generic_helpers_remain_strategy_agnostic() -> None:
    market = cast(Any, PositionMarket.__new__(PositionMarket))
    market.execution = types.SimpleNamespace(
        active_bot=BotModel(
            pair="BEATUSDTM",
            stop_loss=2.0,
            deal=DealModel(opening_price=100.0, opening_timestamp=1),
        )
    )
    market.klines = _candles()
    market.build_pullback_metrics = lambda current_price: None

    long_params = market.derive_dynamic_trailing_params(
        top_spread=2.0,
        bottom_spread=1.5,
        bot_profit=0.0,
        expansion_multiplier=1.0,
        trail_tighten_mult=1.0,
        current_price=100.0,
        direction=1,
    )
    short_params = market.derive_dynamic_trailing_params(
        top_spread=2.0,
        bottom_spread=1.5,
        bot_profit=0.0,
        expansion_multiplier=1.0,
        trail_tighten_mult=1.0,
        current_price=100.0,
        direction=-1,
    )

    assert long_params == (1.5, 2.0, 1.5)
    assert short_params == (2.0, 1.5, 1.14)
