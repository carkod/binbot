from time import time
from typing import Any, cast
import types

from bots.models import BotModel, DealModel, OrderModel
from exchange_apis.kucoin.futures.futures_deal import KucoinPositionDeal
from exchange_apis.kucoin.futures.position_deal import PositionDeal
from pybinbot import MarketType, OrderBase, OrderStatus, DealType, Position
from kucoin_universal_sdk.generate.futures.order.model_add_order_req import (
    AddOrderReq,
)


def _make_deal(
    *,
    stop_loss: float = 2.0,
    stop_loss_price: float = 98.0,
    trailing_stop_loss_price: float = 0.0,
    margin_short_reversal: bool = False,
    orders: list | None = None,
    position: Position = Position.long,
) -> Any:
    """Build a KucoinPositionDeal stub with no exchange / DB side effects."""
    deal = cast(Any, KucoinPositionDeal.__new__(KucoinPositionDeal))
    deal.price_precision = 2
    deal.kucoin_symbol = "BEATUSDTM"
    deal.symbol_info = types.SimpleNamespace(futures_leverage=1)
    deal.active_bot = BotModel(
        pair="BEATUSDT",
        position=position,
        stop_loss=stop_loss,
        margin_short_reversal=margin_short_reversal,
        deal=DealModel(
            opening_price=100.0,
            opening_qty=1,
            stop_loss_price=stop_loss_price,
            trailing_stop_loss_price=trailing_stop_loss_price,
        ),
    )
    if orders is not None:
        deal.active_bot.orders = orders

    deal.controller = types.SimpleNamespace(update_logs=lambda **kwargs: None)
    deal.kucoin_futures_api = types.SimpleNamespace(
        get_all_stop_loss_orders=lambda symbol: [],
        batch_cancel_stop_loss_orders=lambda ids: None,
        place_futures_order=lambda **kwargs: None,
    )
    return deal


def _make_position_deal(**kwargs) -> Any:
    base_deal = _make_deal(**kwargs)
    deal = cast(Any, PositionDeal.__new__(PositionDeal))
    deal.__dict__.update(base_deal.__dict__)
    return deal


def test_place_stop_loss_for_margin_short_uses_price_above_entry():
    captured: dict[str, Any] = {}

    def fake_place_futures_order(**kwargs):
        captured.update(kwargs)
        return OrderBase(
            order_id="sl-order-1",
            order_type="market",
            pair=kwargs["symbol"],
            timestamp=1775008219262,
            order_side="buy",
            qty=1,
            price=kwargs["stop_price"],
            status=OrderStatus.NEW,
            time_in_force="GTC",
            deal_type=DealType.stop_loss,
        )

    deal = cast(Any, KucoinPositionDeal.__new__(KucoinPositionDeal))
    deal.price_precision = 4
    deal.kucoin_symbol = "BEATUSDTM"
    deal.symbol_info = types.SimpleNamespace(futures_leverage=1)
    deal.kucoin_futures_api = types.SimpleNamespace(
        place_futures_order=fake_place_futures_order
    )
    deal.controller = types.SimpleNamespace(
        update_logs=lambda **kwargs: None,
    )
    deal.active_bot = BotModel(
        pair="BEATUSDT",
        position=Position.short,
        stop_loss=2.0,
        margin_short_reversal=False,
        deal=DealModel(
            opening_price=100.0,
            stop_loss_price=102.0,
            opening_qty=1,
        ),
    )

    KucoinPositionDeal.place_stop_loss(deal)

    assert captured["side"] == AddOrderReq.SideEnum.BUY
    assert captured["stop"] == AddOrderReq.StopEnum.UP
    assert captured["stop_price"] == 102.0
    assert captured["leverage"] == 1


def test_should_replace_stop_loss_order_blocks_immaterial_move():
    deal = _make_deal()
    # Move from 98.0 → 98.05 is well below the 0.15% min-move threshold (0.147)
    assert (
        KucoinPositionDeal.should_replace_stop_loss_order(
            deal,
            current_stop_price=98.0,
            new_stop_price=98.05,
            last_replace_ts_ms=None,
        )
        is False
    )


def test_should_replace_stop_loss_order_blocks_within_cooldown():
    deal = _make_deal()
    now_ms = int(time() * 1000)
    # Material move (98.0 → 99.0) but recent replace timestamp
    assert (
        KucoinPositionDeal.should_replace_stop_loss_order(
            deal,
            current_stop_price=98.0,
            new_stop_price=99.0,
            last_replace_ts_ms=now_ms - 1000,
        )
        is False
    )


def test_should_replace_stop_loss_order_allows_after_cooldown_with_material_move():
    deal = _make_deal()
    stale_ts = int(time() * 1000) - (
        KucoinPositionDeal.STOP_LOSS_REPLACE_COOLDOWN_MS + 1000
    )
    assert (
        KucoinPositionDeal.should_replace_stop_loss_order(
            deal,
            current_stop_price=98.0,
            new_stop_price=99.0,
            last_replace_ts_ms=stale_ts,
        )
        is True
    )


def test_should_replace_stop_loss_order_blocks_worse_move():
    deal = _make_deal()
    # Long position: lower SL is worse — never replace toward a worse stop.
    assert (
        KucoinPositionDeal.should_replace_stop_loss_order(
            deal,
            current_stop_price=99.0,
            new_stop_price=97.0,
            last_replace_ts_ms=None,
        )
        is False
    )


def test_reconcile_exchange_sl_skips_armed_trailing_in_base_deal():
    calls: list[str] = []
    deal = _make_deal(trailing_stop_loss_price=99.0)
    deal.cancel_current_sl = lambda: calls.append("cancel")
    deal.place_stop_loss = lambda: calls.append("place")

    KucoinPositionDeal.reconcile_exchange_sl(deal)

    assert calls == []


def test_reconcile_exchange_sl_keeps_existing_armed_trailing_stop():
    calls: list[str] = []
    deal = _make_position_deal(trailing_stop_loss_price=99.0)
    deal.kucoin_futures_api = types.SimpleNamespace(
        get_all_stop_loss_orders=lambda symbol: [
            types.SimpleNamespace(stop_price="99.0", id="trail-1")
        ],
        batch_cancel_stop_loss_orders=lambda ids: None,
    )
    deal.cancel_current_sl = lambda: calls.append("cancel")
    deal.place_stop_loss = lambda: calls.append("place")
    deal.place_trailing_stop_loss = lambda: calls.append("trailing")

    KucoinPositionDeal.reconcile_exchange_sl(deal)

    assert calls == []


def test_reconcile_trailing_stop_loss_replaces_worse_exchange_stop():
    calls: list[str] = []
    deal = _make_position_deal(trailing_stop_loss_price=99.0)
    deal.kucoin_futures_api = types.SimpleNamespace(
        get_all_stop_loss_orders=lambda symbol: [
            types.SimpleNamespace(stop_price="97.0", id="stale-emergency-sl")
        ],
        batch_cancel_stop_loss_orders=lambda ids: None,
    )
    deal.place_trailing_stop_loss = lambda: calls.append("trailing")

    PositionDeal.reconcile_trailing_stop_loss(deal)

    assert calls == ["trailing"]


def test_reconcile_trailing_stop_loss_keeps_better_exchange_stop():
    calls: list[str] = []
    deal = _make_position_deal(trailing_stop_loss_price=99.0)
    deal.kucoin_futures_api = types.SimpleNamespace(
        get_all_stop_loss_orders=lambda symbol: [
            types.SimpleNamespace(stop_price="100.0", id="manual-tighter-sl")
        ],
        batch_cancel_stop_loss_orders=lambda ids: None,
    )
    deal.place_trailing_stop_loss = lambda: calls.append("trailing")

    PositionDeal.reconcile_trailing_stop_loss(deal)

    assert calls == []


def test_should_refresh_trailing_stop_loss_allows_first_stop():
    deal = _make_position_deal()

    assert (
        PositionDeal.should_refresh_trailing_stop_loss(
            deal,
            current_stop_price=0.0,
            new_stop_price=99.0,
            direction=1,
        )
        is True
    )


def test_should_refresh_trailing_stop_loss_blocks_small_long_improvement():
    deal = _make_position_deal()

    assert (
        PositionDeal.should_refresh_trailing_stop_loss(
            deal,
            current_stop_price=100.0,
            new_stop_price=100.1,
            direction=1,
        )
        is False
    )


def test_should_refresh_trailing_stop_loss_allows_material_long_improvement():
    deal = _make_position_deal()

    assert (
        PositionDeal.should_refresh_trailing_stop_loss(
            deal,
            current_stop_price=100.0,
            new_stop_price=100.2,
            direction=1,
        )
        is True
    )


def test_should_refresh_trailing_stop_loss_blocks_small_short_improvement():
    deal = _make_position_deal()

    assert (
        PositionDeal.should_refresh_trailing_stop_loss(
            deal,
            current_stop_price=100.0,
            new_stop_price=99.9,
            direction=-1,
        )
        is False
    )


def test_should_refresh_trailing_stop_loss_allows_material_short_improvement():
    deal = _make_position_deal()

    assert (
        PositionDeal.should_refresh_trailing_stop_loss(
            deal,
            current_stop_price=100.0,
            new_stop_price=99.8,
            direction=-1,
        )
        is True
    )


def test_reconcile_exchange_sl_skips_for_margin_short_reversal():
    calls: list[str] = []
    deal = _make_deal(margin_short_reversal=True)
    deal.cancel_current_sl = lambda: calls.append("cancel")
    deal.place_stop_loss = lambda: calls.append("place")

    KucoinPositionDeal.reconcile_exchange_sl(deal)

    assert calls == []


def test_reconcile_exchange_sl_places_when_exchange_missing():
    """Drift case: bot expected an SL, exchange has none — re-place it."""
    calls: list[str] = []
    deal = _make_deal()
    # Bot has a recorded SL order that should be on the exchange
    deal.active_bot.orders = [
        OrderModel(
            order_id="sl-1",
            order_type="market",
            pair="BEATUSDT",
            order_side="sell",
            qty=1,
            price=98.0,
            status=OrderStatus.NEW,
            timestamp=int(time() * 1000)
            - (KucoinPositionDeal.STOP_LOSS_REPLACE_COOLDOWN_MS + 1000),
            time_in_force="GTC",
            deal_type=DealType.stop_loss,
        )
    ]
    deal.cancel_current_sl = lambda: calls.append("cancel")
    deal.place_stop_loss = lambda: calls.append("place")

    KucoinPositionDeal.reconcile_exchange_sl(deal)

    assert calls == ["cancel", "place"]


def test_exit_panic_closes_stale_mild_loser_after_three_days(monkeypatch):
    deal = cast(Any, PositionDeal.__new__(PositionDeal))
    deal.price_precision = 2
    deal.klines = None
    deal.active_bot = BotModel(
        pair="BEATUSDTM",
        market_type=MarketType.FUTURES,
        position=Position.long,
        stop_loss=0,
        trailing=False,
        take_profit=0,
        deal=DealModel(
            opening_price=100.0,
            opening_timestamp=1_000,
        ),
    )
    deal.active_bot.position = Position.long
    deal.controller = types.SimpleNamespace(
        save=lambda bot: None,
        update_logs=lambda *args, **kwargs: None,
    )
    closed: list[bool] = []
    deal.close_all = lambda: closed.append(True)

    monkeypatch.setattr(
        "exchange_apis.kucoin.futures.position_deal.time",
        lambda: (1_000 + (4 * 24 * 60 * 60 * 1000)) / 1000,
    )

    PositionDeal.exit(deal, 99.5)

    assert closed == [True]


def test_exit_keeps_stale_loser_below_panic_close_band(monkeypatch):
    deal = cast(Any, PositionDeal.__new__(PositionDeal))
    deal.price_precision = 2
    deal.klines = None
    deal.active_bot = BotModel(
        pair="BEATUSDTM",
        market_type=MarketType.FUTURES,
        position=Position.long,
        stop_loss=0,
        trailing=False,
        take_profit=0,
        deal=DealModel(
            opening_price=100.0,
            opening_timestamp=1_000,
        ),
    )
    deal.active_bot.position = Position.long
    deal.controller = types.SimpleNamespace(
        save=lambda bot: None,
        update_logs=lambda *args, **kwargs: None,
    )
    closed: list[bool] = []
    deal.close_all = lambda: closed.append(True)

    monkeypatch.setattr(
        "exchange_apis.kucoin.futures.position_deal.time",
        lambda: (1_000 + (4 * 24 * 60 * 60 * 1000)) / 1000,
    )

    PositionDeal.exit(deal, 98.9)

    assert closed == []


def test_reconcile_exchange_sl_skips_on_api_failure():
    """API blip must not cancel/replace a possibly-still-valid SL."""
    calls: list[str] = []
    deal = _make_deal()
    deal.active_bot.orders = [
        OrderModel(
            order_id="sl-1",
            order_type="market",
            pair="BEATUSDT",
            order_side="sell",
            qty=1,
            price=98.0,
            status=OrderStatus.NEW,
            timestamp=int(time() * 1000),
            time_in_force="GTC",
            deal_type=DealType.stop_loss,
        )
    ]

    def boom(symbol):
        raise RuntimeError("transient 5xx")

    deal.kucoin_futures_api = types.SimpleNamespace(
        get_all_stop_loss_orders=boom,
        batch_cancel_stop_loss_orders=lambda ids: None,
    )
    deal.cancel_current_sl = lambda: calls.append("cancel")
    deal.place_stop_loss = lambda: calls.append("place")

    KucoinPositionDeal.reconcile_exchange_sl(deal)

    assert calls == []


def test_reconcile_exchange_sl_adopts_exchange_drift_without_replacing():
    """If exchange SL drifts but is still valid, adopt the exchange price as truth."""
    calls: list[str] = []
    deal = _make_deal(stop_loss_price=98.0)
    deal.active_bot.orders = [
        OrderModel(
            order_id="sl-1",
            order_type="market",
            pair="BEATUSDT",
            order_side="sell",
            qty=1,
            price=98.0,
            status=OrderStatus.NEW,
            timestamp=int(time() * 1000),
            time_in_force="GTC",
            deal_type=DealType.stop_loss,
        )
    ]
    # Exchange shows an SL at 97.5 (not 98.0). Within cooldown — should not replace.
    deal.kucoin_futures_api = types.SimpleNamespace(
        get_all_stop_loss_orders=lambda symbol: [
            types.SimpleNamespace(stop_price="97.5", id="x-1")
        ],
        batch_cancel_stop_loss_orders=lambda ids: None,
    )
    deal.cancel_current_sl = lambda: calls.append("cancel")
    deal.place_stop_loss = lambda: calls.append("place")

    KucoinPositionDeal.reconcile_exchange_sl(deal)

    assert calls == []
    # Exchange price was adopted as truth
    assert deal.active_bot.deal.stop_loss_price == 97.5
