from datetime import datetime, timezone
from typing import Any, cast
import types
from uuid import uuid4

import pytest
from bots.models import BotModel, OrderModel, RecoveryBotModel
from exchange_apis.kucoin.deals.base import KucoinBaseBalance
from exchange_apis.kucoin.futures.futures_deal import KucoinPositionDeal
from pybinbot import BinbotErrors, DealType, OrderBase, OrderStatus, Position
from streaming.base import BaseStreaming
from streaming.futures_position import FuturesPosition


def make_sizing_deal(
    *,
    fiat_order_size: float = 15.0,
    stop_loss: float = 6.43252,
    multiplier: float = 10.0,
    qty_precision: int = 0,
    lot_size: float = 1,
) -> Any:
    deal = cast(Any, KucoinPositionDeal.__new__(KucoinPositionDeal))
    deal.active_bot = BotModel(
        pair="SIRENUSDTM",
        position=Position.short,
        fiat_order_size=fiat_order_size,
        stop_loss=stop_loss,
    )
    deal.symbol_info = types.SimpleNamespace(
        qty_precision=qty_precision,
        futures_leverage=1,
        price_precision=5,
    )
    deal.price_precision = 5
    deal.kucoin_symbol_data = types.SimpleNamespace(
        multiplier=multiplier,
        taker_fee_rate=0.0006,
        lot_size=lot_size,
        mark_price=0.93269,
    )
    deal.kucoin_futures_api = types.SimpleNamespace(
        DEFAULT_MULTIPLIER=1,
        DEFAULT_LEVERAGE=1,
    )
    return deal


def test_calculate_contracts_treats_fiat_order_size_as_initial_margin():
    """
    Margin-spend interpretation: contracts = balance × leverage / (price × mult).
    15 × 1 / (0.93269 × 10) = 1.607 → floored to 1.
    """
    deal = make_sizing_deal()

    assert deal.calculate_contracts(balance=15, price=0.93269) == 1


def test_calculate_contracts_scales_with_per_symbol_leverage():
    """
    Bumping the per-symbol leverage column from 1 to 3 produces a 3x larger
    contract count for the same margin (and thus a 3x larger notional).
    """
    deal = make_sizing_deal()
    deal.symbol_info.futures_leverage = 3

    assert deal.calculate_contracts(balance=15, price=0.93269) == 4


def test_constructor_reuses_injected_base_streaming(monkeypatch):
    """Streaming deal construction must not create another BaseStreaming."""

    def base_balance_init(self):
        self.config = types.SimpleNamespace(
            kucoin_key="key",
            kucoin_secret="secret",
            kucoin_passphrase="passphrase",
        )
        self.autotrade_settings = types.SimpleNamespace(fiat="USDT")
        self.fiat = "USDT"

    class DummyFuturesApi:
        DEFAULT_LEVERAGE = 1

        def __init__(self, *args, **kwargs):
            pass

        def get_symbol_info(self, symbol):
            return types.SimpleNamespace(multiplier=1, lot_size=1)

    class DummySymbolsCrud:
        def get_symbol(self, symbol):
            return types.SimpleNamespace(
                futures_leverage=1,
                price_precision=4,
                qty_precision=0,
            )

    class DummyBotCrud:
        pass

    class ExplodingBaseStreaming:
        def __init__(self):
            raise AssertionError("unexpected BaseStreaming construction")

    monkeypatch.setattr(KucoinBaseBalance, "__init__", base_balance_init)
    monkeypatch.setattr(
        "exchange_apis.kucoin.futures.futures_deal.KucoinFutures",
        DummyFuturesApi,
    )
    monkeypatch.setattr(
        "exchange_apis.kucoin.futures.futures_deal.SymbolsCrud",
        DummySymbolsCrud,
    )
    monkeypatch.setattr(
        "exchange_apis.kucoin.futures.futures_deal.BotTableCrud",
        DummyBotCrud,
    )
    monkeypatch.setattr(
        "exchange_apis.kucoin.futures.futures_deal.BaseStreaming",
        ExplodingBaseStreaming,
    )

    base_streaming = cast(BaseStreaming, types.SimpleNamespace())
    bot = BotModel(pair="SIRENUSDTM", position=Position.short)

    deal = KucoinPositionDeal(bot=bot, base_streaming=base_streaming)

    assert deal.base_streaming is base_streaming


def test_contracts_to_fiat_order_size_inverts_margin_sizing():
    """
    Inverse of margin-spend: 1 contract × 0.93269 price × 10 mult / 1 leverage.
    """
    deal = make_sizing_deal()

    assert deal.contracts_to_fiat_order_size(contracts=1, price=0.93269) == 9.3269


def test_calculate_contracts_returns_zero_when_margin_is_below_one_contract():
    deal = make_sizing_deal(fiat_order_size=0.5)

    assert deal.calculate_contracts(balance=0.5, price=0.93269) == 0


def test_notional_stays_within_thirty_at_autotrade_default_and_two_x_leverage():
    """
    Product invariant: with the autotrade default fiat_order_size of 15 USDT
    and a per-symbol futures_leverage of 2x, notional must not exceed 30 USDT.
    Guards against accidental drift back to a risk-budget interpretation or
    silently raising the model's `le=3` leverage cap.
    """
    deal = make_sizing_deal(fiat_order_size=15.0, multiplier=1.0)
    deal.symbol_info.futures_leverage = 2

    contracts = deal.calculate_contracts(balance=15.0, price=1.0)
    notional = deal.notional_for_contracts(contracts, price=1.0)

    assert notional <= 30.0


def test_required_margin_uses_position_notional_and_leverage():
    deal = make_sizing_deal(multiplier=10)

    assert deal.required_margin_for_contracts(contracts=100, price=10) == 10012


def test_reversal_margin_check_does_not_double_count_lot_size():
    deal = make_sizing_deal(multiplier=1, lot_size=5)
    deal.compute_available_balance = lambda: 60

    assert deal._is_reversal_possible(mark_price=10, current_contracts=10) == 15


def test_base_order_downsizes_when_margin_size_exceeds_available_balance():
    class DummyFuturesApi:
        DEFAULT_MULTIPLIER = 1
        DEFAULT_LEVERAGE = 1

        def __init__(self):
            self.sell_calls: list[int] = []

        def matching_engine(self, symbol, side, size):
            return 10

        def sell(self, symbol, qty, leverage, entry_limit_price=None):
            self.sell_calls.append(qty)
            return OrderBase(
                order_id="base-order-1",
                order_type="limit",
                pair=symbol,
                timestamp=1775008219262,
                order_side="sell",
                qty=qty,
                price=10,
                status=OrderStatus.FILLED,
                time_in_force="GTC",
                deal_type=DealType.base_order,
            )

        def get_futures_position(self, symbol):
            return types.SimpleNamespace(mark_price=10)

        def retrieve_order(self, order_id):
            # Simulate an already-filled entry so base_order() activates immediately.
            return types.SimpleNamespace(filled_size="9", avg_deal_price="10")

    # margin_sized at 1x: 1500 / (10*10) = 15 contracts (notional 1500, margin 1500).
    # affordable: per-contract margin (100*1 + 2*100*0.0006) = 100.12 → floor(1000/100.12) = 9.
    # min(15, 9) = 9, downsized from 15 to 9.
    deal = make_sizing_deal(fiat_order_size=1500, stop_loss=1, multiplier=10)
    recovery_id = uuid4()
    deal.active_bot.recovery_mode_id = recovery_id
    deal.active_bot.recovery_params = RecoveryBotModel(
        id=recovery_id,
        reversal_path="recovery",
        source_contracts=20,
        source_loss_fiat=4,
        stop_loss_pct=3,
        created_at=1,
        updated_at=1,
    )
    deal.active_bot.fiat = "USDT"
    deal.fiat = "USDT"
    deal.kucoin_symbol = "TESTUSDTM"
    deal.kucoin_futures_api = DummyFuturesApi()
    deal.controller = types.SimpleNamespace(
        update_logs=lambda **kwargs: None,
        save=lambda bot: bot,
    )
    deal.compute_available_balance = lambda: 1000
    deal.recovery_entry_limit_price = lambda: 10

    opened_bot = KucoinPositionDeal.base_order(deal)

    assert deal.kucoin_futures_api.sell_calls == [9]
    assert opened_bot.deal.base_order_size == 9
    assert opened_bot.deal.opening_qty == 9
    assert any("Futures order downsized from 15 to 9" in log for log in opened_bot.logs)
    assert any("underpowered_recovery" in log for log in opened_bot.logs)


def entry_klines(
    *,
    event_time: datetime,
    previous_close: float,
    current_open: float,
    candle_range: float,
    completed_count: int = 15,
) -> list[list[float]]:
    interval_ms = 15 * 60 * 1000
    current_open_ms = int(
        event_time.replace(minute=0, second=0, microsecond=0).timestamp() * 1000
    )
    rows: list[list[float]] = []
    for offset in range(completed_count, 0, -1):
        open_time_ms = current_open_ms - offset * interval_ms
        rows.append(
            [
                open_time_ms,
                previous_close,
                previous_close + candle_range / 2,
                previous_close - candle_range / 2,
                previous_close,
                100,
                open_time_ms + interval_ms - 1,
            ]
        )
    rows.append(
        [
            current_open_ms,
            current_open,
            current_open,
            current_open,
            current_open,
            100,
            current_open_ms + interval_ms - 1,
        ]
    )
    return rows


def prepare_recovery_entry_deal(
    monkeypatch,
    *,
    position: Position,
    previous_close: float,
    current_open: float,
    candle_range: float,
    completed_count: int = 15,
) -> Any:
    event_time = datetime(2026, 6, 9, 23, 4, 7, tzinfo=timezone.utc)
    monkeypatch.setattr(
        "exchange_apis.kucoin.futures.futures_deal.time",
        lambda: event_time.timestamp(),
    )
    deal = make_sizing_deal(multiplier=1)
    deal.active_bot.position = position
    recovery_id = uuid4()
    deal.active_bot.recovery_mode_id = recovery_id
    deal.active_bot.recovery_params = RecoveryBotModel(
        id=recovery_id,
        reversal_path="source",
        source_contracts=0,
        source_loss_fiat=0,
        stop_loss_pct=0,
        created_at=1,
        updated_at=1,
    )
    klines = entry_klines(
        event_time=event_time,
        previous_close=previous_close,
        current_open=current_open,
        candle_range=candle_range,
        completed_count=completed_count,
    )
    deal.kucoin_symbol = "KATUSDTM"
    deal.kucoin_futures_api = types.SimpleNamespace(
        DEFAULT_MULTIPLIER=1,
        DEFAULT_LEVERAGE=1,
        get_ui_klines=lambda **kwargs: klines,
    )
    return deal


def test_recovery_long_entry_caps_kat_wick_with_atr_allowance(monkeypatch):
    deal = prepare_recovery_entry_deal(
        monkeypatch,
        position=Position.long,
        previous_close=0.00616,
        current_open=0.00619,
        candle_range=0.000135,
    )

    limit_price = deal.recovery_entry_limit_price()

    assert limit_price == 0.00625
    assert any("Recovery body-capped entry" in log for log in deal.active_bot.logs)
    assert any("(ATR)" in log for log in deal.active_bot.logs)


def test_recovery_short_entry_uses_lower_body_anchor(monkeypatch):
    deal = prepare_recovery_entry_deal(
        monkeypatch,
        position=Position.short,
        previous_close=0.00616,
        current_open=0.00613,
        candle_range=0.00001,
    )

    limit_price = deal.recovery_entry_limit_price()

    assert limit_price == 0.00609
    assert any("allowance=0.50%" in log for log in deal.active_bot.logs)


def test_recovery_entry_atr_allowance_is_capped_at_one_and_a_half_percent(
    monkeypatch,
):
    deal = prepare_recovery_entry_deal(
        monkeypatch,
        position=Position.long,
        previous_close=0.00616,
        current_open=0.00619,
        candle_range=0.001,
    )

    limit_price = deal.recovery_entry_limit_price()

    assert limit_price == 0.00628
    assert any("allowance=1.50%" in log for log in deal.active_bot.logs)


def test_recovery_entry_uses_fallback_allowance_without_enough_atr_data(
    monkeypatch,
):
    deal = prepare_recovery_entry_deal(
        monkeypatch,
        position=Position.long,
        previous_close=0.00616,
        current_open=0.00619,
        candle_range=0.00001,
        completed_count=2,
    )

    limit_price = deal.recovery_entry_limit_price()

    assert limit_price == 0.00623
    assert any("allowance=0.75% (fallback)" in log for log in deal.active_bot.logs)


def test_recovery_entry_rejects_activation_without_current_candle(monkeypatch):
    deal = prepare_recovery_entry_deal(
        monkeypatch,
        position=Position.long,
        previous_close=0.00616,
        current_open=0.00619,
        candle_range=0.00001,
    )
    completed_only = deal.kucoin_futures_api.get_ui_klines()[:-1]
    deal.kucoin_futures_api.get_ui_klines = lambda **kwargs: completed_only

    with pytest.raises(BinbotErrors, match="Reliable current and completed candles"):
        deal.recovery_entry_limit_price()


def test_non_recovery_entry_keeps_legacy_market_matching_path():
    deal = make_sizing_deal()
    deal.kucoin_futures_api.get_ui_klines = lambda **kwargs: (_ for _ in ()).throw(
        AssertionError("non-recovery entry should not request klines")
    )

    assert deal.recovery_entry_limit_price() is None


def test_unfilled_capped_base_order_remains_subject_to_candle_age_expiry():
    position = cast(Any, FuturesPosition.__new__(FuturesPosition))
    order = OrderModel(
        order_id="capped-entry",
        order_type="limit",
        pair="KATUSDTM",
        timestamp=1,
        order_side="buy",
        qty=150,
        price=0.00625,
        status=OrderStatus.NEW,
        time_in_force="GTC",
        deal_type=DealType.base_order,
    )

    assert position.should_expire_order_by_age(order) is True
