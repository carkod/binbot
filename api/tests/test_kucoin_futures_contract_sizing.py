import types
from datetime import datetime, timezone
from time import time_ns
from typing import Any, cast
from unittest.mock import Mock
from uuid import uuid4

import pytest
from pybinbot import (
    BinbotErrors,
    BotModel,
    DealType,
    OrderBase,
    OrderModel,
    OrderStatus,
    OrderType,
    Position,
    RecoveryBotModel,
    Status,
)

from api.exchange_apis.kucoin.deals.base import KucoinBaseBalance
from api.exchange_apis.kucoin.futures.futures_deal import KucoinPositionDeal
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
    deal.controller = types.SimpleNamespace(save=lambda bot: bot)
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


def test_constructor_reuses_injected_exchange_dependencies(monkeypatch):

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

    monkeypatch.setattr(KucoinBaseBalance, "__init__", base_balance_init)
    monkeypatch.setattr(
        "api.exchange_apis.kucoin.futures.futures_deal.KucoinFutures",
        DummyFuturesApi,
    )
    monkeypatch.setattr(
        "api.exchange_apis.kucoin.futures.futures_deal.SymbolsCrud",
        DummySymbolsCrud,
    )
    monkeypatch.setattr(
        "api.exchange_apis.kucoin.futures.futures_deal.BotTableCrud",
        DummyBotCrud,
    )
    bot = BotModel(pair="SIRENUSDTM", position=Position.short)
    futures_api = DummyFuturesApi()
    symbols_crud = DummySymbolsCrud()
    controller = DummyBotCrud()

    deal = KucoinPositionDeal(
        bot=bot,
        kucoin_futures_api=cast(Any, futures_api),
        symbols_crud=cast(Any, symbols_crud),
        controller=cast(Any, controller),
        interval_ms=900_000,
    )

    assert deal.kucoin_futures_api is futures_api
    assert deal.symbols_crud is symbols_crud
    assert deal.controller is controller
    assert deal.interval_ms == 900_000


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


def attach_order_book(
    deal,
    *,
    bids: list[list[float]],
    asks: list[list[float]],
    age_ms: int = 0,
) -> None:
    class FuturesMarketApi:
        def get_full_order_book(self, request):
            return types.SimpleNamespace(
                bids=bids,
                asks=asks,
                ts=time_ns() - age_ms * 1_000_000,
            )

    deal.kucoin_futures_api = types.SimpleNamespace(
        futures_market_api=FuturesMarketApi()
    )
    deal.kucoin_symbol = "TESTUSDTM"


def test_entry_liquidity_gate_downsizes_to_contracts_fillable_inside_price_band():
    deal = make_sizing_deal(multiplier=1)
    deal.active_bot.position = Position.long
    attach_order_book(
        deal,
        bids=[[99.99, 100]],
        asks=[[100.01, 3], [100.6, 100]],
    )

    contracts = deal.liquidity_gated_contracts(10)

    assert contracts == 3
    assert any(
        "Futures order downsized from 10 to 3 contracts" in log
        for log in deal.active_bot.logs
    )
    assert any("depth50(bid/ask)" in log for log in deal.active_bot.logs)


def test_entry_liquidity_gate_rejects_excessive_spread_and_records_reason():
    deal = make_sizing_deal(multiplier=1)
    deal.active_bot.position = Position.long
    saved: list[BotModel] = []
    deal.controller = types.SimpleNamespace(save=lambda bot: saved.append(bot))
    attach_order_book(
        deal,
        bids=[[99.8, 100]],
        asks=[[100.2, 100]],
    )

    with pytest.raises(BinbotErrors, match="spread exceeds 20bps"):
        deal.liquidity_gated_contracts(10)

    assert deal.active_bot.status == Status.error
    assert saved == [deal.active_bot]
    assert "spread exceeds 20bps" in deal.active_bot.logs[-1]


def test_entry_liquidity_gate_rejects_excessive_expected_slippage():
    deal = make_sizing_deal(multiplier=1)
    deal.active_bot.position = Position.long
    attach_order_book(
        deal,
        bids=[[99.99, 100]],
        asks=[[100.01, 1], [100.49, 9]],
    )

    with pytest.raises(BinbotErrors, match="expected KuCoin futures slippage"):
        deal.liquidity_gated_contracts(10)

    assert "expected_slippage=44.20bps" in deal.active_bot.logs[-1]


def test_entry_liquidity_gate_rejects_stale_book_data():
    deal = make_sizing_deal(multiplier=1)
    deal.active_bot.position = Position.long
    attach_order_book(
        deal,
        bids=[[99.99, 100]],
        asks=[[100.01, 100]],
        age_ms=3_000,
    )

    with pytest.raises(BinbotErrors, match="order book is stale"):
        deal.liquidity_gated_contracts(10)

    assert "maximum age is 2000ms" in deal.active_bot.logs[-1]


def test_base_order_downsizes_when_margin_size_exceeds_available_balance():
    class DummyFuturesApi:
        DEFAULT_MULTIPLIER = 1
        DEFAULT_LEVERAGE = 1

        def __init__(self):
            self.sell_calls: list[dict[str, float]] = []

        def matching_engine(self, symbol, side, size):
            return 10

        def sell(self, symbol, qty, leverage, entry_limit_price=None):
            self.sell_calls.append(
                {
                    "qty": qty,
                    "entry_limit_price": entry_limit_price,
                }
            )
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

        def get_mark_price(self, symbol):
            return 10

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
    deal.body_capped_entry_limit_price = lambda: 10
    deal.liquidity_gated_contracts = lambda contracts: contracts

    opened_bot = KucoinPositionDeal.base_order(deal)

    assert deal.kucoin_futures_api.sell_calls == [{"qty": 9, "entry_limit_price": 10}]
    assert opened_bot.deal.base_order_size == 9
    assert opened_bot.deal.opening_qty == 9
    assert any("Futures order downsized from 15 to 9" in log for log in opened_bot.logs)
    assert any("underpowered_recovery" in log for log in opened_bot.logs)


def test_liquidity_downsized_entry_is_revalidated_with_required_margin():
    order = OrderBase(
        order_id="liquidity-sized-entry",
        order_type="limit",
        pair="TESTUSDTM",
        timestamp=1775008219262,
        order_side="buy",
        qty=4,
        price=10,
        status=OrderStatus.FILLED,
        time_in_force="GTC",
        deal_type=DealType.base_order,
    )
    futures_api = types.SimpleNamespace(
        DEFAULT_MULTIPLIER=1,
        DEFAULT_LEVERAGE=1,
        buy=Mock(return_value=order),
        get_mark_price=Mock(return_value=10),
        retrieve_order=Mock(
            return_value=types.SimpleNamespace(
                filled_size="4",
                avg_deal_price="10",
            )
        ),
    )
    deal = make_sizing_deal(fiat_order_size=100, multiplier=1)
    deal.active_bot.position = Position.long
    deal.active_bot.fiat = "USDT"
    deal.fiat = "USDT"
    deal.kucoin_symbol = "TESTUSDTM"
    deal.kucoin_futures_api = futures_api
    deal.controller = types.SimpleNamespace(
        update_logs=lambda **kwargs: None,
        save=lambda bot: bot,
    )
    deal.compute_available_balance = lambda: 1_000
    deal.body_capped_entry_limit_price = lambda: 10
    deal.max_contracts_for_margin = lambda available_balance, price: 10
    deal.liquidity_gated_contracts = lambda contracts: 4
    margin_checks: list[tuple[float, float]] = []
    required_margin_for_contracts = deal.required_margin_for_contracts

    def record_required_margin(contracts: float, price: float) -> float:
        margin_checks.append((contracts, price))
        return required_margin_for_contracts(contracts, price)

    deal.required_margin_for_contracts = record_required_margin

    opened_bot = KucoinPositionDeal.base_order(deal)

    assert margin_checks == [(4, 10)]
    futures_api.buy.assert_called_once_with(
        symbol="TESTUSDTM",
        qty=4,
        entry_limit_price=10,
    )
    assert opened_bot.deal.base_order_size == 4


def test_unfilled_base_order_logs_pending_wait_queue():
    class DummyFuturesApi:
        DEFAULT_MULTIPLIER = 1
        DEFAULT_LEVERAGE = 1

        def __init__(self):
            self.buy_calls: list[dict[str, float]] = []

        def buy(self, symbol, qty, entry_limit_price=None):
            self.buy_calls.append(
                {
                    "qty": qty,
                    "entry_limit_price": entry_limit_price,
                }
            )
            return OrderBase(
                order_id="pending-entry-1",
                order_type="limit",
                pair=symbol,
                timestamp=1775008219262,
                order_side="buy",
                qty=0,
                price=entry_limit_price,
                status=OrderStatus.NEW,
                time_in_force="GTC",
                deal_type=DealType.base_order,
            )

        def get_mark_price(self, symbol):
            return 10

        def retrieve_order(self, order_id):
            return types.SimpleNamespace(filled_size="0", avg_deal_price="0")

    logged: list[str] = []
    saved: list[BotModel] = []
    deal = make_sizing_deal(fiat_order_size=10, multiplier=1)
    deal.active_bot.position = Position.long
    deal.active_bot.fiat = "USDT"
    deal.fiat = "USDT"
    deal.kucoin_symbol = "TESTUSDTM"
    deal.kucoin_futures_api = DummyFuturesApi()
    deal.controller = types.SimpleNamespace(
        update_logs=lambda **kwargs: logged.append(kwargs["log_message"]),
        save=lambda bot: saved.append(bot),
    )
    deal.compute_available_balance = lambda: 100
    deal.body_capped_entry_limit_price = lambda: 10
    deal.liquidity_gated_contracts = lambda contracts: contracts

    opened_bot = KucoinPositionDeal.base_order(deal)

    assert deal.kucoin_futures_api.buy_calls == [{"qty": 1, "entry_limit_price": 10}]
    assert opened_bot.status == Status.pending
    assert saved == [opened_bot]
    assert any("pending for up to 5 minutes awaiting fill" in log for log in logged)


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
        "api.exchange_apis.kucoin.futures.futures_deal.time",
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


def test_non_recovery_entry_uses_body_capped_limit_price(monkeypatch):
    deal = prepare_recovery_entry_deal(
        monkeypatch,
        position=Position.long,
        previous_close=0.00616,
        current_open=0.00619,
        candle_range=0.000135,
    )
    deal.active_bot.recovery_params = None

    limit_price = deal.body_capped_entry_limit_price()

    assert limit_price == 0.00625
    assert any("Body-capped entry" in log for log in deal.active_bot.logs)


def test_relative_strength_impulse_rider_uses_prompt_body_capped_entry_after_reclaim(
    monkeypatch,
):
    deal = prepare_recovery_entry_deal(
        monkeypatch,
        position=Position.long,
        previous_close=100.0,
        current_open=101.0,
        candle_range=2.0,
    )
    deal.active_bot.name = "relative_strength_impulse_rider"
    deal.active_bot.recovery_params = None

    limit_price = deal.body_capped_entry_limit_price()

    assert limit_price == 102.0
    assert any("Body-capped entry" in log for log in deal.active_bot.logs)


def test_top_gainer_early_momentum_waits_for_half_percent_retest(monkeypatch):
    deal = prepare_recovery_entry_deal(
        monkeypatch,
        position=Position.long,
        previous_close=100.0,
        current_open=101.0,
        candle_range=2.0,
    )
    deal.active_bot.name = "top_gainer_early_momentum"
    deal.active_bot.recovery_params = None

    limit_price = deal.body_capped_entry_limit_price()

    assert limit_price == 99.5
    assert any(
        "Top-gainer momentum retest entry" in log for log in deal.active_bot.logs
    )


def test_top_gainer_stop_triggers_early_and_never_falls_back_to_market():
    deal = make_sizing_deal(multiplier=1)
    deal.active_bot.name = "top_gainer_early_momentum"
    deal.active_bot.position = Position.long
    deal.active_bot.deal.opening_price = 100.0
    deal.active_bot.deal.opening_qty = 3
    deal.active_bot.deal.stop_loss_price = 98.0
    deal.kucoin_symbol = "SIRENUSDTM"
    place_order = Mock(
        return_value=OrderBase(
            order_id="bounded-stop",
            order_type="limit",
            pair="SIRENUSDTM",
            timestamp=1,
            order_side="sell",
            qty=3,
            price=98.0,
            status=OrderStatus.NEW,
            time_in_force="GTC",
            deal_type=DealType.stop_loss,
        )
    )
    deal.kucoin_futures_api = types.SimpleNamespace(place_futures_order=place_order)
    deal.controller = types.SimpleNamespace(update_logs=Mock())

    deal.place_stop_loss()

    kwargs = place_order.call_args.kwargs
    assert kwargs["order_type"] == OrderType.limit
    assert kwargs["price"] == 98.0
    assert kwargs["stop_price"] == 98.49
    assert kwargs["allow_market_fallback"] is False
    assert deal.active_bot.deal.stop_loss_price == 98.0


def test_entry_klines_normalizes_kucoin_dashboard_ohlc_order():
    dashboard_candle = [
        1_800_000_000_000,
        "100",
        "105",
        "106",
        "99",
        "1000",
        "5000",
    ]

    normalized = KucoinPositionDeal.normalize_entry_klines([dashboard_candle])

    assert normalized == [
        [
            1_800_000_000_000,
            "100",
            "106",
            "99",
            "105",
            "1000",
            "5000",
        ]
    ]


def test_unfilled_capped_base_order_uses_pending_entry_ttl_not_legacy_age_expiry():
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
    bot = types.SimpleNamespace(
        name="another_strategy",
        status=Status.pending,
        deal=types.SimpleNamespace(opening_price=0),
    )
    position.execution = types.SimpleNamespace(active_bot=bot)

    assert position.should_expire_order_by_age(order) is False
    assert (
        position.is_pending_base_entry_expired(order, now_ms=5 * 60 * 1000 + 2) is True
    )


@pytest.mark.parametrize("interval_minutes", [5, 15, 60])
def test_relative_strength_impulse_rider_pending_entry_waits_one_candle(
    interval_minutes,
):
    position = cast(Any, FuturesPosition.__new__(FuturesPosition))
    order = OrderModel(
        order_id="impulse-retest-entry",
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
    position.execution = types.SimpleNamespace(
        active_bot=BotModel(
            pair="KATUSDTM",
            name="relative_strength_impulse_rider",
            status=Status.pending,
        )
    )
    interval_ms = interval_minutes * 60 * 1000
    position.base_streaming = types.SimpleNamespace(
        interval=types.SimpleNamespace(get_ms=lambda: interval_ms)
    )

    assert position.is_pending_base_entry_expired(order, now_ms=interval_ms) is False
    assert position.is_pending_base_entry_expired(order, now_ms=interval_ms + 2) is True


@pytest.mark.parametrize("interval_minutes", [5, 15, 60])
def test_top_gainer_retest_entry_waits_one_configured_candle(interval_minutes):
    position = cast(Any, FuturesPosition.__new__(FuturesPosition))
    order = OrderModel(
        order_id="top-gainer-retest-entry",
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
    position.execution = types.SimpleNamespace(
        active_bot=BotModel(
            pair="KATUSDTM",
            name="top_gainer_early_momentum",
            status=Status.pending,
        )
    )
    interval_ms = interval_minutes * 60 * 1000
    position.base_streaming = types.SimpleNamespace(
        interval=types.SimpleNamespace(get_ms=lambda: interval_ms)
    )

    assert position.is_pending_base_entry_expired(order, now_ms=interval_ms) is False
    assert position.is_pending_base_entry_expired(order, now_ms=interval_ms + 2) is True


def test_relative_strength_impulse_rider_delayed_fill_starts_holding_clock_at_fill(
    monkeypatch,
):
    fill_time = datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc)
    observation_time = datetime(2026, 8, 6, 15, 0, tzinfo=timezone.utc)
    fill_timestamp_ms = int(fill_time.timestamp() * 1000)
    monkeypatch.setattr(
        "streaming.futures_position.datetime",
        types.SimpleNamespace(now=lambda: observation_time),
    )
    position = cast(Any, FuturesPosition.__new__(FuturesPosition))
    execution = cast(Any, KucoinPositionDeal.__new__(KucoinPositionDeal))
    execution.active_bot = BotModel(
        pair="KATUSDTM",
        name="relative_strength_impulse_rider",
        status=Status.pending,
    )
    position.execution = execution
    execution.kucoin_futures_api = types.SimpleNamespace(
        get_fills=lambda **kwargs: types.SimpleNamespace(
            items=[
                types.SimpleNamespace(
                    order_id="another-order",
                    trade_time=int(observation_time.timestamp() * 1_000_000_000),
                    created_at=int(observation_time.timestamp() * 1000),
                ),
                types.SimpleNamespace(
                    order_id="filled-impulse-retest-entry",
                    trade_time=fill_timestamp_ms * 1_000_000,
                    created_at=fill_timestamp_ms,
                ),
            ]
        )
    )
    execution.open_deal = lambda: execution.active_bot
    order = OrderModel(
        order_id="filled-impulse-retest-entry",
        order_type="limit",
        pair="KATUSDTM",
        timestamp=1,
        order_side="buy",
        qty=150,
        price=0.00625,
        status=OrderStatus.FILLED,
        time_in_force="GTC",
        deal_type=DealType.base_order,
    )

    position._activate_filled_base_order(order)

    assert execution.active_bot.deal.opening_timestamp == fill_timestamp_ms


@pytest.mark.parametrize(
    "deal_type",
    [
        DealType.algorithmic_close,
        DealType.conversion,
        DealType.margin_short,
    ],
)
def test_non_protective_futures_orders_remain_subject_to_age_expiry(deal_type):
    position = cast(Any, FuturesPosition.__new__(FuturesPosition))
    order = OrderModel(
        order_id="non-protective-order",
        order_type="limit",
        pair="KATUSDTM",
        timestamp=1,
        order_side="sell",
        qty=150,
        price=0.00625,
        status=OrderStatus.NEW,
        time_in_force="GTC",
        deal_type=deal_type,
    )

    assert position.should_expire_order_by_age(order) is True
