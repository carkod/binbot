import types
from time import time
from typing import Any, cast
from uuid import uuid4

import pytest
from kucoin_universal_sdk.model.common import RestError
from kucoin_universal_sdk.generate.futures.order.model_add_order_req import (
    AddOrderReq,
)
from kucoin_universal_sdk.generate.futures.order.model_get_stop_order_list_resp import (
    GetStopOrderListItems,
)
from kucoin_universal_sdk.generate.futures.positions.model_get_position_details_resp import (
    GetPositionDetailsResp,
)
from pybinbot import (
    BotModel,
    DealModel,
    DealType,
    MarketType,
    OrderBase,
    OrderModel,
    OrderStatus,
    OrderType,
    Position,
    RecoveryBotModel,
    Status,
)

from api.exchange_apis.kucoin.futures.futures_deal import KucoinPositionDeal
from streaming.base import BaseStreaming
from streaming.lifecycle import Lifecycle


def _stop_order(**kwargs) -> GetStopOrderListItems:
    return GetStopOrderListItems(**kwargs)


def _position(current_qty: int | None = None) -> GetPositionDetailsResp:
    return GetPositionDetailsResp(current_qty=current_qty)


def _make_deal(
    *,
    stop_loss: float = 2.0,
    stop_loss_price: float = 98.0,
    trailing_stop_loss_price: float = 0.0,
    recovery_source: bool = False,
    orders: list | None = None,
    position: Position = Position.long,
) -> Any:
    """Build a KucoinPositionDeal stub with no exchange / DB side effects."""
    deal = cast(Any, KucoinPositionDeal.__new__(KucoinPositionDeal))
    deal.price_precision = 2
    deal.kucoin_symbol = "BEATUSDTM"
    deal.symbol_info = types.SimpleNamespace(futures_leverage=1, qty_precision=0)
    deal.active_bot = BotModel(
        pair="BEATUSDT",
        position=position,
        stop_loss=stop_loss,
        recovery_params=RecoveryBotModel(id=uuid4(), created_at=1, updated_at=1)
        if recovery_source
        else None,
        deal=DealModel(
            opening_price=100.0,
            opening_qty=1,
            stop_loss_price=stop_loss_price,
            trailing_stop_loss_price=trailing_stop_loss_price,
        ),
    )
    if orders is not None:
        deal.active_bot.orders = orders

    deal.controller = types.SimpleNamespace(
        save=lambda *args, **kwargs: None,
        update_logs=lambda *args, **kwargs: None,
    )
    deal.kucoin_futures_api = types.SimpleNamespace(
        get_all_stop_loss_orders=lambda symbol: [],
        batch_cancel_stop_loss_orders=lambda ids: None,
        place_futures_order=lambda **kwargs: None,
        retrieve_order=lambda order_id: types.SimpleNamespace(
            id=order_id,
            is_active=False,
            filled_size=0,
            avg_deal_price=0,
            cancel_exist=True,
            created_at=1,
            status=types.SimpleNamespace(value="done"),
        ),
    )
    return deal


def _make_position_deal(**kwargs) -> Any:
    return _make_deal(**kwargs)


def _make_lifecycle(*, interval_ms: int = 15 * 60 * 1000, **kwargs) -> Lifecycle:
    execution = _make_deal(**kwargs)
    base_streaming = types.SimpleNamespace(
        interval=types.SimpleNamespace(get_ms=lambda: interval_ms),
    )
    return Lifecycle(
        execution=execution, base_streaming=cast(BaseStreaming, base_streaming)
    )


def _make_completed_candles(
    *, entry_candle_open: int, completed_after_entry: int, interval_ms: int
) -> list[list[float]]:
    return [
        [
            entry_candle_open + (index * interval_ms),
            100.0,
            101.0,
            99.0,
            100.0,
            1.0,
            entry_candle_open + ((index + 1) * interval_ms) - 1,
        ]
        for index in range(completed_after_entry + 1)
    ]


def _make_strategy_at_holding_limit(
    *, name: str = "mean_reversion_fade", position: Position = Position.long
) -> Any:
    interval_ms = 15 * 60 * 1000
    current_open = (int(time() * 1000) // interval_ms) * interval_ms
    entry_candle_open = current_open - (9 * interval_ms)
    lifecycle = _make_lifecycle(position=position, interval_ms=interval_ms)
    lifecycle.execution.active_bot.name = name
    lifecycle.execution.active_bot.deal.opening_timestamp = entry_candle_open + 1_000
    lifecycle.klines = _make_completed_candles(
        entry_candle_open=entry_candle_open,
        completed_after_entry=8,
        interval_ms=interval_ms,
    )
    cast(Any, lifecycle.execution).controller = types.SimpleNamespace(
        save=lambda bot: None,
        update_logs=lambda message, bot: None,
    )
    return lifecycle


def test_mean_reversion_fade_closes_at_eight_completed_candles() -> None:
    close_calls: list[bool] = []
    deal = _make_strategy_at_holding_limit()

    def close_all(algorithmic_close: bool = False) -> BotModel:
        close_calls.append(algorithmic_close)
        return deal.execution.active_bot

    deal.execution.close_all = close_all

    result = Lifecycle.exit(deal, close_price=100.0)

    assert result is deal.execution.active_bot
    assert close_calls == [True]


def test_liquidation_sweep_pump_closes_at_eight_completed_candles() -> None:
    close_calls: list[bool] = []
    deal = _make_strategy_at_holding_limit(name="liquidation_sweep_pump")

    def close_all(algorithmic_close: bool = False) -> BotModel:
        close_calls.append(algorithmic_close)
        return deal.execution.active_bot

    deal.execution.close_all = close_all

    result = Lifecycle.exit(deal, close_price=100.0)

    assert result is deal.execution.active_bot
    assert close_calls == [True]


def test_coinrule_price_tracker_closes_at_eight_completed_candles() -> None:
    close_calls: list[bool] = []
    deal = _make_strategy_at_holding_limit(name="coinrule_price_tracker")

    def close_all(algorithmic_close: bool = False) -> BotModel:
        close_calls.append(algorithmic_close)
        return deal.execution.active_bot

    deal.execution.close_all = close_all

    result = Lifecycle.exit(deal, close_price=100.0)

    assert result is deal.execution.active_bot
    assert close_calls == [True]


def test_relative_strength_impulse_rider_closes_at_eight_completed_candles() -> None:
    close_calls: list[bool] = []
    deal = _make_strategy_at_holding_limit(name="relative_strength_impulse_rider")

    def close_all(algorithmic_close: bool = False) -> BotModel:
        close_calls.append(algorithmic_close)
        return deal.execution.active_bot

    deal.execution.close_all = close_all

    result = Lifecycle.exit(deal, close_price=100.0)

    assert result is deal.execution.active_bot
    assert close_calls == [True]


def test_fixed_take_profit_precedes_max_holding_close() -> None:
    for name in (
        "mean_reversion_fade",
        "liquidation_sweep_pump",
        "coinrule_price_tracker",
        "relative_strength_impulse_rider",
    ):
        exit_calls: list[str] = []
        deal = _make_strategy_at_holding_limit(
            name=name,
            position=Position.short,
        )
        deal.execution.active_bot.take_profit = 2.4
        deal.execution.active_bot.deal.stop_loss_price = 102.0
        deal.execution.active_bot.deal.take_profit_price = 97.6

        def take_profit_order() -> BotModel:
            exit_calls.append("take_profit")
            return deal.execution.active_bot

        def close_all(algorithmic_close: bool = False) -> BotModel:  # noqa: ARG001
            exit_calls.append("max_holding")
            return deal.execution.active_bot

        deal.execution.take_profit_order = take_profit_order
        deal.execution.close_all = close_all

        Lifecycle.exit(deal, close_price=97.5)

        assert exit_calls == ["take_profit"]


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
        save=lambda *args, **kwargs: None,
    )
    deal.active_bot = BotModel(
        pair="BEATUSDT",
        position=Position.short,
        stop_loss=2.0,
        recovery_source=False,
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


def test_place_stop_loss_prefers_live_position_quantity():
    deal = _make_deal()
    deal.symbol_info.qty_precision = 0
    deal.active_bot.deal.opening_qty = 4522
    deal.active_bot.deal.current_position_qty = 1800
    captured: dict[str, Any] = {}
    deal.kucoin_futures_api = types.SimpleNamespace(
        get_futures_position=lambda symbol: _position(922),
        get_all_stop_loss_orders=lambda symbol: [],
        place_futures_order=lambda **kwargs: (
            captured.update(kwargs)
            or OrderBase(
                order_id="live-sized-stop",
                order_type="market",
                pair=kwargs["symbol"],
                timestamp=1,
                order_side="sell",
                qty=kwargs["size"],
                price=kwargs["stop_price"],
                status=OrderStatus.NEW,
                time_in_force="GTC",
                deal_type=DealType.stop_loss,
            )
        ),
        retrieve_order=lambda order_id: types.SimpleNamespace(
            id=order_id,
            is_active=False,
            filled_size=0,
            avg_deal_price=0,
            cancel_exist=True,
            created_at=1,
            status=types.SimpleNamespace(value="done"),
        ),
    )

    deal.place_stop_loss()

    assert captured["size"] == 922
    assert deal.active_bot.deal.current_position_qty == 922


def test_place_stop_loss_falls_back_to_historical_position_quantity():
    deal = _make_deal()
    deal.active_bot.deal.opening_qty = 4522
    deal.active_bot.deal.current_position_qty = 922
    captured: dict[str, Any] = {}
    deal.kucoin_futures_api = types.SimpleNamespace(
        get_futures_position=lambda symbol: _position(),
        get_all_stop_loss_orders=lambda symbol: [],
        place_futures_order=lambda **kwargs: (
            captured.update(kwargs)
            or OrderBase(
                order_id="fallback-sized-stop",
                order_type="market",
                pair=kwargs["symbol"],
                timestamp=1,
                order_side="sell",
                qty=kwargs["size"],
                price=kwargs["stop_price"],
                status=OrderStatus.NEW,
                time_in_force="GTC",
                deal_type=DealType.stop_loss,
            )
        ),
        retrieve_order=lambda order_id: types.SimpleNamespace(
            id=order_id,
            is_active=False,
            filled_size=0,
            avg_deal_price=0,
            cancel_exist=True,
            created_at=1,
            status=types.SimpleNamespace(value="done"),
        ),
    )

    deal.place_stop_loss()

    assert captured["size"] == 922


def test_current_position_quantity_treats_exchange_zero_as_confirmed_flat():
    deal = _make_deal()
    deal.symbol_info.qty_precision = 0
    deal.active_bot.deal.opening_qty = 4522
    deal.active_bot.deal.current_position_qty = 922
    deal.kucoin_futures_api = types.SimpleNamespace(
        get_futures_position=lambda symbol: _position(0),
    )

    qty = deal.current_position_quantity()

    assert qty == 0
    assert deal.active_bot.deal.current_position_qty == 0


def test_place_stop_loss_adopts_matching_kucoin_order_without_duplicate():
    deal = _make_deal()
    deal.active_bot.deal.current_position_qty = 1
    place_order = cast(Any, types.SimpleNamespace(calls=0))

    def record_place(**kwargs):
        place_order.calls += 1

    deal.kucoin_futures_api = types.SimpleNamespace(
        get_futures_position=lambda symbol: _position(1),
        get_all_stop_loss_orders=lambda symbol: [
            _stop_order(
                id="existing-kucoin-stop",
                client_oid="kucoin-client-oid",
                stop_price="98",
                size=1,
                side="sell",
                reduce_only=True,
                created_at=1,
            )
        ],
        place_futures_order=record_place,
        retrieve_order=lambda order_id: types.SimpleNamespace(
            id=order_id,
            is_active=False,
            filled_size=0,
            avg_deal_price=0,
            cancel_exist=True,
            created_at=1,
            status=types.SimpleNamespace(value="done"),
        ),
    )

    deal.place_stop_loss()

    assert place_order.calls == 0
    assert deal.active_bot.orders[-1].order_id == "existing-kucoin-stop"


def test_reconcile_exchange_stop_replaces_stale_quantity():
    deal = _make_deal()
    deal.symbol_info.qty_precision = 0
    deal.active_bot.deal.opening_qty = 4522
    deal.active_bot.deal.current_position_qty = 1800
    deal.kucoin_futures_api = types.SimpleNamespace(
        get_futures_position=lambda symbol: _position(922),
        get_all_stop_loss_orders=lambda symbol: [
            _stop_order(id="oversized-stop", stop_price="98", size=1800)
        ],
        retrieve_order=lambda order_id: types.SimpleNamespace(
            id=order_id,
            is_active=False,
            filled_size=0,
            avg_deal_price=0,
            cancel_exist=True,
            created_at=1,
            status=types.SimpleNamespace(value="done"),
        ),
    )
    cancelled: list[bool] = []
    replacements: list[float | None] = []
    deal.cancel_current_sl = lambda **kwargs: cancelled.append(True)
    deal.place_stop_loss = lambda position_qty=None: replacements.append(position_qty)

    deal.reconcile_exchange_sl()

    assert cancelled == [True]
    assert replacements == [922]


def test_place_stop_loss_leaves_immediate_fill_for_position_and_price_reconciliation():
    saved_bots: list[BotModel] = []
    deal = _make_deal()
    deal.active_bot.status = Status.active
    deal.controller = types.SimpleNamespace(
        save=lambda bot: saved_bots.append(bot.model_copy(deep=True)),
        update_logs=lambda **kwargs: None,
    )
    deal.kucoin_futures_api = types.SimpleNamespace(
        place_futures_order=lambda **kwargs: OrderBase(
            order_id="immediate-stop-fill",
            order_type="market",
            pair=kwargs["symbol"],
            timestamp=1_788_529_590_286,
            order_side="sell",
            qty=1,
            price=98.0,
            status=OrderStatus.FILLED,
            time_in_force="GTC",
            deal_type=DealType.stop_loss,
        )
    )

    KucoinPositionDeal.place_stop_loss(deal)

    assert deal.active_bot.status == Status.active
    assert deal.active_bot.deal.closing_price == 0
    assert deal.active_bot.deal.closing_qty == 0
    assert deal.active_bot.orders[-1].status == OrderStatus.FILLED
    assert deal.awaiting_close_confirmation()
    assert saved_bots[-1].status == Status.active


def test_open_deal_does_not_reactivate_an_immediately_filled_stop_loss():
    saved_statuses: list[Status] = []
    deal = _make_deal(
        orders=[
            OrderModel(
                order_id="filled-entry",
                order_type="market",
                pair="BEATUSDTM",
                timestamp=1,
                order_side="buy",
                qty=1,
                price=100.0,
                status=OrderStatus.FILLED,
                time_in_force="GTC",
                deal_type=DealType.base_order,
            )
        ]
    )

    def complete_during_parameter_update() -> BotModel:
        deal.active_bot.status = Status.completed
        deal.active_bot.deal.closing_price = 98.0
        deal.active_bot.deal.closing_qty = 1
        deal.active_bot.deal.closing_timestamp = 2
        return deal.active_bot

    deal.update_parameters = complete_during_parameter_update
    deal.controller = types.SimpleNamespace(
        save=lambda bot: saved_statuses.append(bot.status),
    )

    result = KucoinPositionDeal.open_deal(deal)

    assert result.status == Status.completed
    assert result.deal.closing_price == 98.0
    assert saved_statuses[-1] == Status.completed


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


def test_should_replace_stop_loss_order_allows_explicit_volatility_widening():
    deal = _make_deal()

    assert (
        KucoinPositionDeal.should_replace_stop_loss_order(
            deal,
            current_stop_price=98.0,
            new_stop_price=90.0,
            last_replace_ts_ms=None,
            allow_widening=True,
        )
        is True
    )


def test_reconcile_exchange_sl_delegates_armed_trailing_to_exchange_service():
    calls: list[str] = []
    deal = _make_deal(trailing_stop_loss_price=99.0)
    deal.cancel_current_sl = lambda **kwargs: calls.append("cancel")
    deal.place_stop_loss = lambda **kwargs: calls.append("place")
    deal.reconcile_trailing_stop_loss = lambda **kwargs: calls.append("trailing")

    KucoinPositionDeal.reconcile_exchange_sl(deal)

    assert calls == ["trailing"]


def test_reconcile_exchange_sl_keeps_existing_armed_trailing_stop():
    calls: list[str] = []
    deal = _make_position_deal(trailing_stop_loss_price=99.0)
    deal.kucoin_futures_api = types.SimpleNamespace(
        get_all_stop_loss_orders=lambda symbol: [
            _stop_order(stop_price="99.0", id="trail-1")
        ],
        batch_cancel_stop_loss_orders=lambda ids: None,
        retrieve_order=lambda order_id: types.SimpleNamespace(
            id=order_id,
            is_active=False,
            filled_size=0,
            avg_deal_price=0,
            cancel_exist=True,
            created_at=1,
            status=types.SimpleNamespace(value="done"),
        ),
    )
    deal.cancel_current_sl = lambda **kwargs: calls.append("cancel")
    deal.place_stop_loss = lambda **kwargs: calls.append("place")
    deal.place_trailing_stop_loss = lambda **kwargs: calls.append("trailing")

    KucoinPositionDeal.reconcile_exchange_sl(deal)

    assert calls == []


def test_reconcile_trailing_stop_loss_replaces_worse_exchange_stop():
    calls: list[str] = []
    deal = _make_position_deal(trailing_stop_loss_price=99.0)
    deal.kucoin_futures_api = types.SimpleNamespace(
        get_all_stop_loss_orders=lambda symbol: [
            _stop_order(stop_price="97.0", id="stale-emergency-sl")
        ],
        batch_cancel_stop_loss_orders=lambda ids: None,
        retrieve_order=lambda order_id: types.SimpleNamespace(
            id=order_id,
            is_active=False,
            filled_size=0,
            avg_deal_price=0,
            cancel_exist=True,
            created_at=1,
            status=types.SimpleNamespace(value="done"),
        ),
    )
    deal.place_trailing_stop_loss = lambda **kwargs: calls.append("trailing")

    KucoinPositionDeal.reconcile_trailing_stop_loss(deal)

    assert calls == ["trailing"]


def test_reconcile_trailing_stop_loss_keeps_better_exchange_stop():
    calls: list[str] = []
    deal = _make_position_deal(trailing_stop_loss_price=99.0)
    deal.kucoin_futures_api = types.SimpleNamespace(
        get_all_stop_loss_orders=lambda symbol: [
            _stop_order(stop_price="100.0", id="manual-tighter-sl")
        ],
        batch_cancel_stop_loss_orders=lambda ids: None,
        retrieve_order=lambda order_id: types.SimpleNamespace(
            id=order_id,
            is_active=False,
            filled_size=0,
            avg_deal_price=0,
            cancel_exist=True,
            created_at=1,
            status=types.SimpleNamespace(value="done"),
        ),
    )
    deal.place_trailing_stop_loss = lambda **kwargs: calls.append("trailing")

    KucoinPositionDeal.reconcile_trailing_stop_loss(deal)

    assert calls == []


def test_reconcile_trailing_stop_loss_uses_tracked_trailing_order():
    calls: list[str] = []
    now_ms = int(time() * 1000)
    emergency_order = OrderModel(
        order_id="emergency-sl",
        order_type="market",
        pair="BEATUSDT",
        order_side="sell",
        qty=1,
        price=97.0,
        status=OrderStatus.NEW,
        timestamp=now_ms - 20_000,
        time_in_force="GTC",
        deal_type=DealType.stop_loss,
    )
    trailing_order = OrderModel(
        order_id="trail-1",
        order_type="market",
        pair="BEATUSDT",
        order_side="sell",
        qty=1,
        price=99.0,
        status=OrderStatus.NEW,
        timestamp=now_ms
        - (KucoinPositionDeal.TRAILING_STOP_REPLACE_COOLDOWN_MS + 1_000),
        time_in_force="GTC",
        deal_type=DealType.trailing_profit,
    )
    deal = _make_position_deal(
        trailing_stop_loss_price=99.0,
        orders=[emergency_order, trailing_order],
    )
    deal.kucoin_futures_api = types.SimpleNamespace(
        get_all_stop_loss_orders=lambda symbol: [
            _stop_order(stop_price="97.0", id="emergency-sl"),
            _stop_order(stop_price="99.0", id="trail-1"),
        ],
        batch_cancel_stop_loss_orders=lambda ids: None,
        retrieve_order=lambda order_id: types.SimpleNamespace(
            id=order_id,
            is_active=False,
            filled_size=0,
            avg_deal_price=0,
            cancel_exist=True,
            created_at=1,
            status=types.SimpleNamespace(value="done"),
        ),
    )
    deal.place_trailing_stop_loss = lambda **kwargs: calls.append("trailing")

    KucoinPositionDeal.reconcile_trailing_stop_loss(deal)

    assert calls == []


def test_place_trailing_stop_loss_keeps_existing_exchange_stop_without_cancel():
    calls: list[str] = []
    deal = _make_position_deal(trailing_stop_loss_price=99.0)
    deal.controller = types.SimpleNamespace(
        update_logs=lambda *args, **kwargs: None,
        save=lambda bot: None,
    )
    deal.kucoin_futures_api = types.SimpleNamespace(
        get_futures_position=lambda symbol: _position(1),
        get_all_stop_loss_orders=lambda symbol: [
            _stop_order(stop_price="99.0", id="trail-1")
        ],
        batch_cancel_stop_loss_orders=lambda ids: calls.append("cancel"),
        place_futures_order=lambda **kwargs: calls.append("place"),
        retrieve_order=lambda order_id: types.SimpleNamespace(
            id=order_id,
            is_active=False,
            filled_size=0,
            avg_deal_price=0,
            cancel_exist=True,
            created_at=1,
            status=types.SimpleNamespace(value="done"),
        ),
    )

    KucoinPositionDeal.place_trailing_stop_loss(deal)

    assert calls == []
    assert deal.active_bot.orders == []


def test_place_trailing_stop_loss_cancels_only_tracked_trailing_order():
    cancelled_ids: list[str] = []
    now_ms = int(time() * 1000)
    emergency_order = OrderModel(
        order_id="emergency-sl",
        order_type="market",
        pair="BEATUSDT",
        order_side="sell",
        qty=1,
        price=97.0,
        status=OrderStatus.NEW,
        timestamp=now_ms - 20_000,
        time_in_force="GTC",
        deal_type=DealType.stop_loss,
    )
    trailing_order = OrderModel(
        order_id="trail-1",
        order_type="market",
        pair="BEATUSDT",
        order_side="sell",
        qty=1,
        price=98.0,
        status=OrderStatus.NEW,
        timestamp=now_ms
        - (KucoinPositionDeal.TRAILING_STOP_REPLACE_COOLDOWN_MS + 1_000),
        time_in_force="GTC",
        deal_type=DealType.trailing_profit,
    )

    def fake_place_futures_order(**kwargs):
        return OrderBase(
            order_id="trail-2",
            order_type="market",
            pair=kwargs["symbol"],
            timestamp=now_ms,
            order_side="sell",
            qty=1,
            price=kwargs["stop_price"],
            status=OrderStatus.NEW,
            time_in_force="GTC",
            deal_type=DealType.trailing_profit,
        )

    deal = _make_position_deal(
        trailing_stop_loss_price=99.0,
        orders=[emergency_order, trailing_order],
    )
    deal.controller = types.SimpleNamespace(
        update_logs=lambda *args, **kwargs: None,
        save=lambda bot: None,
    )
    deal.kucoin_futures_api = types.SimpleNamespace(
        get_futures_position=lambda symbol: _position(1),
        get_all_stop_loss_orders=lambda symbol: [
            _stop_order(stop_price="97.0", id="emergency-sl"),
            _stop_order(stop_price="98.0", id="trail-1"),
        ],
        batch_cancel_stop_loss_orders=lambda ids: cancelled_ids.extend(ids),
        place_futures_order=fake_place_futures_order,
        retrieve_order=lambda order_id: types.SimpleNamespace(
            id=order_id,
            is_active=False,
            filled_size=0,
            avg_deal_price=0,
            cancel_exist=True,
            created_at=1,
            status=types.SimpleNamespace(value="done"),
        ),
    )

    KucoinPositionDeal.place_trailing_stop_loss(deal)

    assert cancelled_ids == ["trail-1"]
    assert [order.order_id for order in deal.active_bot.orders] == [
        "emergency-sl",
        "trail-1",
        "trail-2",
    ]


def test_place_trailing_stop_loss_blocks_recent_trailing_replace():
    calls: list[str] = []
    now_ms = int(time() * 1000)
    recent_trailing_order = OrderModel(
        order_id="trail-1",
        order_type="market",
        pair="BEATUSDT",
        order_side="sell",
        qty=1,
        price=98.0,
        status=OrderStatus.NEW,
        timestamp=now_ms - 1000,
        time_in_force="GTC",
        deal_type=DealType.trailing_profit,
    )
    deal = _make_position_deal(
        trailing_stop_loss_price=99.0,
        orders=[recent_trailing_order],
    )
    deal.controller = types.SimpleNamespace(
        update_logs=lambda *args, **kwargs: None,
        save=lambda bot: None,
    )
    deal.kucoin_futures_api = types.SimpleNamespace(
        get_futures_position=lambda symbol: _position(1),
        get_all_stop_loss_orders=lambda symbol: [
            _stop_order(stop_price="98.0", id="trail-1")
        ],
        batch_cancel_stop_loss_orders=lambda ids: calls.append("cancel"),
        place_futures_order=lambda **kwargs: calls.append("place"),
        retrieve_order=lambda order_id: types.SimpleNamespace(
            id=order_id,
            is_active=False,
            filled_size=0,
            avg_deal_price=0,
            cancel_exist=True,
            created_at=1,
            status=types.SimpleNamespace(value="done"),
        ),
    )

    KucoinPositionDeal.place_trailing_stop_loss(deal)

    assert calls == []
    assert deal.active_bot.orders == [recent_trailing_order]


def test_last_trailing_stop_replace_ignores_emergency_and_terminal_trailing_orders():
    now_ms = int(time() * 1000)
    emergency_order = OrderModel(
        order_id="emergency-sl",
        order_type="market",
        pair="BEATUSDT",
        order_side="sell",
        qty=1,
        price=97.0,
        status=OrderStatus.NEW,
        timestamp=now_ms,
        time_in_force="GTC",
        deal_type=DealType.stop_loss,
    )
    closed_trailing_order = OrderModel(
        order_id="trail-closed",
        order_type="market",
        pair="BEATUSDT",
        order_side="sell",
        qty=1,
        price=98.0,
        status=OrderStatus.CANCELED,
        timestamp=now_ms - 1_000,
        time_in_force="GTC",
        deal_type=DealType.trailing_profit,
    )
    active_trailing_order = OrderModel(
        order_id="trail-active",
        order_type="market",
        pair="BEATUSDT",
        order_side="sell",
        qty=1,
        price=98.5,
        status=OrderStatus.NEW,
        timestamp=now_ms - 2_000,
        time_in_force="GTC",
        deal_type=DealType.trailing_profit,
    )
    deal = _make_position_deal(
        orders=[emergency_order, closed_trailing_order, active_trailing_order],
    )

    assert KucoinPositionDeal.last_trailing_stop_replace_ts_ms(deal) == now_ms - 2_000


def test_place_trailing_stop_loss_logs_new_status_as_armed_stop():
    calls: list[dict] = []

    def fake_place_futures_order(**kwargs):
        calls.append(kwargs)
        return OrderBase(
            order_id="trail-1",
            order_type="market",
            pair=kwargs["symbol"],
            timestamp=1775008219262,
            order_side="sell",
            qty=1,
            price=kwargs["stop_price"],
            status=OrderStatus.NEW,
            time_in_force="GTC",
            deal_type=DealType.trailing_profit,
        )

    deal = _make_position_deal(trailing_stop_loss_price=99.0)
    deal.controller = types.SimpleNamespace(
        update_logs=lambda *args, **kwargs: None,
        save=lambda bot: None,
    )
    deal.kucoin_futures_api = types.SimpleNamespace(
        get_futures_position=lambda symbol: _position(1),
        get_all_stop_loss_orders=lambda symbol: [],
        batch_cancel_stop_loss_orders=lambda ids: None,
        place_futures_order=fake_place_futures_order,
        retrieve_order=lambda order_id: types.SimpleNamespace(
            id=order_id,
            is_active=False,
            filled_size=0,
            avg_deal_price=0,
            cancel_exist=True,
            created_at=1,
            status=types.SimpleNamespace(value="done"),
        ),
    )

    KucoinPositionDeal.place_trailing_stop_loss(deal)

    assert len(calls) == 1
    assert calls[0]["order_type"] == OrderType.market
    assert "price" not in calls[0]
    assert any(
        "Trailing stop armed on exchange with status" in log
        for log in deal.active_bot.logs
    )
    assert not any("not filled immediately" in log for log in deal.active_bot.logs)


def test_should_refresh_trailing_stop_loss_allows_first_stop():
    deal = _make_position_deal()

    assert (
        KucoinPositionDeal.should_refresh_trailing_stop_loss(
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
        KucoinPositionDeal.should_refresh_trailing_stop_loss(
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
        KucoinPositionDeal.should_refresh_trailing_stop_loss(
            deal,
            current_stop_price=100.0,
            new_stop_price=100.2,
            direction=1,
        )
        is True
    )


def test_should_refresh_trailing_stop_loss_blocks_recent_replace():
    deal = _make_position_deal()
    now_ms = int(time() * 1000)

    assert (
        KucoinPositionDeal.should_refresh_trailing_stop_loss(
            deal,
            current_stop_price=100.0,
            new_stop_price=101.0,
            direction=1,
            last_replace_ts_ms=now_ms - 1000,
        )
        is False
    )


def test_should_refresh_trailing_stop_loss_blocks_recent_replace_without_local_stop():
    deal = _make_position_deal()
    now_ms = int(time() * 1000)

    assert (
        KucoinPositionDeal.should_refresh_trailing_stop_loss(
            deal,
            current_stop_price=0.0,
            new_stop_price=101.0,
            direction=1,
            last_replace_ts_ms=now_ms - 1000,
        )
        is False
    )


def test_should_refresh_trailing_stop_loss_blocks_small_short_improvement():
    deal = _make_position_deal()

    assert (
        KucoinPositionDeal.should_refresh_trailing_stop_loss(
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
        KucoinPositionDeal.should_refresh_trailing_stop_loss(
            deal,
            current_stop_price=100.0,
            new_stop_price=99.8,
            direction=-1,
        )
        is True
    )


@pytest.mark.parametrize(
    ("algorithm_name", "position"),
    [
        ("top_gainer_early_momentum", Position.long),
        ("top_loser_early_momentum", Position.short),
        ("top_gainer_short", Position.short),
    ],
)
def test_reconcile_exchange_sl_places_native_backstop_for_strategy(
    algorithm_name: str,
    position: Position,
):
    calls: list[str] = []
    deal = _make_deal(position=position)
    deal.active_bot.name = algorithm_name
    deal.cancel_current_sl = lambda **kwargs: calls.append("cancel")
    deal.place_stop_loss = lambda **kwargs: calls.append("place")

    KucoinPositionDeal.reconcile_exchange_sl(deal)

    assert calls == ["cancel", "place"]


@pytest.mark.parametrize("recovery_enabled", [False, True])
def test_top_gainer_short_ignores_recovery_configuration_for_native_stop(
    recovery_enabled: bool,
):
    calls: list[str] = []
    deal = _make_deal(
        recovery_source=not recovery_enabled,
        position=Position.short,
    )
    deal.active_bot.name = "top_gainer_short"
    if recovery_enabled:
        recovery_id = uuid4()
        deal.active_bot.recovery_mode_id = recovery_id
        deal.active_bot.recovery_params = RecoveryBotModel(
            id=recovery_id,
            reversal_path="recovery",
            source_contracts=1,
            source_loss_fiat=1.0,
            stop_loss_pct=2.0,
            created_at=1,
            updated_at=1,
        )
    deal.cancel_current_sl = lambda **kwargs: calls.append("cancel")
    deal.place_stop_loss = lambda **kwargs: calls.append("place")

    KucoinPositionDeal.reconcile_exchange_sl(deal)

    assert calls == ["cancel", "place"]


def test_top_gainer_short_with_recovery_waits_for_native_stop_confirmation():
    deal = _make_lifecycle(
        stop_loss=2.0,
        stop_loss_price=102.0,
        recovery_source=True,
        position=Position.short,
    )
    deal.execution.active_bot.name = "top_gainer_short"
    deal.execution.active_bot.trailing = False
    recovery_id = uuid4()
    deal.execution.active_bot.recovery_mode_id = recovery_id
    deal.execution.active_bot.recovery_params = RecoveryBotModel(
        id=recovery_id,
        reversal_path="source",
        source_contracts=0,
        source_loss_fiat=0,
        stop_loss_pct=0,
        created_at=1,
        updated_at=1,
    )
    deal.klines = None
    stop_calls: list[float | None] = []
    reconcile_calls: list[bool] = []

    def execute_stop_loss(reference_price: float | None = None) -> BotModel:
        stop_calls.append(reference_price)
        return deal.execution.active_bot

    def reconcile_exchange_sl() -> None:
        reconcile_calls.append(True)

    cast(Any, deal.execution).execute_stop_loss = execute_stop_loss
    cast(Any, deal.execution).reconcile_exchange_sl = reconcile_exchange_sl

    Lifecycle.exit(deal, 103.0)

    assert stop_calls == []
    assert reconcile_calls == [True]


def test_top_gainer_short_low_price_stop_is_not_widened():
    deal = _make_lifecycle(
        stop_loss=2.0,
        stop_loss_price=0.0,
        position=Position.short,
    )
    deal.execution.active_bot.name = "top_gainer_short"
    deal.execution.active_bot.trailing = False
    deal.execution.active_bot.deal.opening_price = 0.04
    deal.execution.price_precision = 5
    deal.klines = None

    Lifecycle.exit(deal, 0.04)

    assert deal.execution.active_bot.deal.stop_loss_price == 0.0408


def test_top_gainer_hard_stop_executes_without_liquidity_precheck():
    deal = _make_lifecycle(stop_loss=2.0, stop_loss_price=98.0)
    deal.execution.active_bot.name = "top_gainer_early_momentum"
    now_ms = int(time() * 1000)
    deal.klines = [
        [
            now_ms - 120_000,
            100.0,
            101.0,
            98.0,
            99.0,
            1.0,
            now_ms - 60_001,
        ],
        [
            now_ms - 60_000,
            99.0,
            99.0,
            97.0,
            97.5,
            1.0,
            now_ms + 1,
        ],
    ]
    stop_calls: list[float | None] = []

    def execute_stop_loss(reference_price: float | None = None) -> BotModel:
        stop_calls.append(reference_price)
        return deal.execution.active_bot

    cast(Any, deal.execution).execute_stop_loss = execute_stop_loss

    Lifecycle.exit(deal, 97.5)

    assert stop_calls == [99.0]


def test_top_mover_hard_stop_cleans_native_backstop_after_reduce_only_close():
    events: list[str] = []
    deal = _make_deal()
    deal.active_bot.name = "top_gainer_early_momentum"
    deal.current_position_quantity = lambda: 1
    deal.cancel_current_sl = lambda **kwargs: events.append("cancel_backstop")

    def sell(**kwargs) -> OrderBase:
        events.append("sell")
        return OrderBase(
            order_id="bot-side-hard-stop",
            order_type="limit",
            pair=kwargs["symbol"],
            timestamp=1,
            order_side="sell",
            qty=kwargs["qty"],
            price=97.9,
            status=OrderStatus.FILLED,
            time_in_force="IOC",
            deal_type=DealType.stop_loss,
        )

    deal.kucoin_futures_api = types.SimpleNamespace(sell=sell)

    result = deal.execute_stop_loss(reference_price=99.0)

    assert events == ["sell", "cancel_backstop"]
    assert result.status == Status.completed
    assert result.deal.closing_price == 97.9


def test_top_mover_hard_stop_keeps_native_backstop_when_position_lookup_fails():
    events: list[str] = []
    deal = _make_deal()
    deal.active_bot.name = "top_gainer_early_momentum"
    deal.cancel_current_sl = lambda **kwargs: events.append("cancel_backstop")
    deal.current_position_quantity = lambda: (_ for _ in ()).throw(
        RuntimeError("position lookup failed")
    )

    with pytest.raises(RuntimeError, match="position lookup failed"):
        deal.execute_stop_loss(reference_price=99.0)

    assert events == []


def test_top_mover_hard_stop_keeps_native_backstop_when_close_fails():
    events: list[str] = []
    deal = _make_deal()
    deal.active_bot.name = "top_gainer_early_momentum"
    deal.current_position_quantity = lambda: 1
    deal.cancel_current_sl = lambda **kwargs: events.append("cancel_backstop")

    def sell(**kwargs):
        events.append("sell")
        raise RestError(
            msg="close failed",
            response=types.SimpleNamespace(code=400100, message="close failed"),
        )

    deal.kucoin_futures_api = types.SimpleNamespace(sell=sell)

    result = deal.execute_stop_loss(reference_price=99.0)

    assert events == ["sell"]
    assert result.status == Status.error


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
    deal.cancel_current_sl = lambda **kwargs: calls.append("cancel")
    deal.place_stop_loss = lambda **kwargs: calls.append("place")

    KucoinPositionDeal.reconcile_exchange_sl(deal)

    assert calls == ["cancel", "place"]


def test_exit_panic_closes_stale_mild_loser_after_three_days(monkeypatch):
    deal = _make_lifecycle(stop_loss=0)
    deal.klines = None
    deal.execution.active_bot = BotModel(
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
    deal.execution.active_bot.position = Position.long
    cast(Any, deal.execution).controller = types.SimpleNamespace(
        save=lambda bot: None,
        update_logs=lambda *args, **kwargs: None,
    )
    closed: list[bool] = []
    cast(Any, deal.execution).close_all = lambda: closed.append(True)

    monkeypatch.setattr(
        "streaming.lifecycle.time",
        lambda: (1_000 + (4 * 24 * 60 * 60 * 1000)) / 1000,
    )

    Lifecycle.exit(deal, 99.5)

    assert closed == [True]


def test_top_gainer_short_is_not_closed_by_stale_position_rule(monkeypatch):
    deal = _make_lifecycle(stop_loss=0, position=Position.short)
    deal.klines = None
    deal.execution.active_bot.name = "top_gainer_short"
    deal.execution.active_bot.trailing = False
    deal.execution.active_bot.deal.opening_price = 100.0
    deal.execution.active_bot.deal.opening_timestamp = 1_000
    cast(Any, deal.execution).controller = types.SimpleNamespace(
        save=lambda bot: None,
        update_logs=lambda *args, **kwargs: None,
    )
    closed: list[bool] = []
    cast(Any, deal.execution).close_all = lambda: closed.append(True)

    monkeypatch.setattr(
        "streaming.lifecycle.time",
        lambda: (1_000 + (4 * 24 * 60 * 60 * 1000)) / 1000,
    )

    Lifecycle.exit(deal, 100.5)

    assert closed == []


def test_exit_keeps_stale_loser_below_panic_close_band(monkeypatch):
    deal = _make_lifecycle(stop_loss=0)
    deal.klines = None
    deal.execution.active_bot = BotModel(
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
    deal.execution.active_bot.position = Position.long
    cast(Any, deal.execution).controller = types.SimpleNamespace(
        save=lambda bot: None,
        update_logs=lambda *args, **kwargs: None,
    )
    closed: list[bool] = []
    cast(Any, deal.execution).close_all = lambda: closed.append(True)

    monkeypatch.setattr(
        "streaming.lifecycle.time",
        lambda: (1_000 + (4 * 24 * 60 * 60 * 1000)) / 1000,
    )

    Lifecycle.exit(deal, 98.9)

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
        retrieve_order=lambda order_id: types.SimpleNamespace(
            id=order_id,
            is_active=False,
            filled_size=0,
            avg_deal_price=0,
            cancel_exist=True,
            created_at=1,
            status=types.SimpleNamespace(value="done"),
        ),
    )
    deal.cancel_current_sl = lambda **kwargs: calls.append("cancel")
    deal.place_stop_loss = lambda **kwargs: calls.append("place")

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
            _stop_order(stop_price="97.5", id="x-1")
        ],
        batch_cancel_stop_loss_orders=lambda ids: None,
        retrieve_order=lambda order_id: types.SimpleNamespace(
            id=order_id,
            is_active=False,
            filled_size=0,
            avg_deal_price=0,
            cancel_exist=True,
            created_at=1,
            status=types.SimpleNamespace(value="done"),
        ),
    )
    deal.cancel_current_sl = lambda **kwargs: calls.append("cancel")
    deal.place_stop_loss = lambda **kwargs: calls.append("place")

    KucoinPositionDeal.reconcile_exchange_sl(deal)

    assert calls == []
    # Exchange price was adopted as truth
    assert deal.active_bot.deal.stop_loss_price == 97.5


def test_reconcile_exchange_sl_replaces_after_drift_once_ratchet_is_material():
    """
    Regression for the ratchet going permanently dead after the first drift:
    real KuCoin stop-market orders report price=0 (only stop_price lives on
    the exchange), so _bot_known_stop_order always falls back to
    deal.stop_loss_price — the bot's freshly-ratcheted target. Case 2 used to
    overwrite that target with the exchange's stale price before Case 3 could
    compare them, so current == new and the ratchet could never fire again
    for the life of the deal. It must still replace once the ratcheted
    target is materially tighter and the cooldown has elapsed.
    """
    calls: list[str] = []
    old_timestamp = int(time() * 1000) - 60_000  # past the 30s cooldown
    deal = _make_deal(stop_loss_price=98.5)
    deal.active_bot.name = "top_gainer_early_momentum"
    deal.active_bot.orders = [
        OrderModel(
            order_id="sl-1",
            order_type="market",
            pair="BEATUSDT",
            order_side="sell",
            qty=1,
            price=0.0,
            status=OrderStatus.NEW,
            timestamp=old_timestamp,
            time_in_force="GTC",
            deal_type=DealType.stop_loss,
        )
    ]
    # Exchange still has the stale SL from placement time.
    deal.kucoin_futures_api = types.SimpleNamespace(
        get_all_stop_loss_orders=lambda symbol: [
            _stop_order(stop_price="97.5", id="x-1")
        ],
        batch_cancel_stop_loss_orders=lambda ids: None,
        retrieve_order=lambda order_id: types.SimpleNamespace(
            id=order_id,
            is_active=False,
            filled_size=0,
            avg_deal_price=0,
            cancel_exist=True,
            created_at=1,
            status=types.SimpleNamespace(value="done"),
        ),
    )
    deal.cancel_current_sl = lambda **kwargs: calls.append("cancel")
    deal.place_stop_loss = lambda **kwargs: calls.append("place")

    KucoinPositionDeal.reconcile_exchange_sl(deal)

    assert calls == ["cancel", "place"]


def test_reconcile_exchange_sl_replaces_tighter_live_stop_for_favorable_trend():
    calls: list[str] = []
    old_timestamp = int(time() * 1000) - 60_000
    deal = _make_deal(stop_loss_price=90.0)
    deal.active_bot.orders = [
        OrderModel(
            order_id="sl-1",
            order_type="market",
            pair="BEATUSDT",
            order_side="sell",
            qty=1,
            price=0.0,
            status=OrderStatus.NEW,
            timestamp=old_timestamp,
            time_in_force="GTC",
            deal_type=DealType.stop_loss,
        )
    ]
    deal.kucoin_futures_api = types.SimpleNamespace(
        get_all_stop_loss_orders=lambda symbol: [
            _stop_order(stop_price="98.0", id="sl-1")
        ],
        batch_cancel_stop_loss_orders=lambda ids: None,
        retrieve_order=lambda order_id: types.SimpleNamespace(
            id=order_id,
            is_active=False,
            filled_size=0,
            avg_deal_price=0,
            cancel_exist=True,
            created_at=1,
            status=types.SimpleNamespace(value="done"),
        ),
    )
    deal.cancel_current_sl = lambda **kwargs: calls.append("cancel")
    deal.place_stop_loss = lambda **kwargs: calls.append("place")

    KucoinPositionDeal.reconcile_exchange_sl(deal, allow_widening=True)

    assert calls == ["cancel", "place"]
    assert any(
        "volatility expansion widened" in message for message in deal.active_bot.logs
    )


@pytest.mark.parametrize("position", [Position.long, Position.short])
def test_trailing_stop_resizes_after_scale_in_even_during_replace_cooldown(position):
    short = position == Position.short
    intended_price = 96.0 if short else 104.0
    exchange_price = 95.5 if short else 104.5
    now_ms = int(time() * 1000)
    trailing_order = OrderModel(
        order_id="trail-before-increase",
        order_type="market",
        pair="BEATUSDTM",
        order_side="buy" if short else "sell",
        qty=100,
        price=exchange_price,
        status=OrderStatus.NEW,
        timestamp=now_ms,
        time_in_force="GTC",
        deal_type=DealType.trailing_profit,
    )
    deal = _make_deal(
        position=position,
        trailing_stop_loss_price=intended_price,
        orders=[trailing_order],
    )
    cancelled = []
    placed = []

    def place(**kwargs):
        placed.append(kwargs)
        return OrderBase(
            order_id="trail-after-increase",
            deal_type=DealType.trailing_profit,
            order_type="market",
            pair=kwargs["symbol"],
            order_side=kwargs["side"].value,
            qty=kwargs["size"],
            price=kwargs["stop_price"],
            timestamp=now_ms,
            time_in_force="GTC",
            status=OrderStatus.NEW,
        )

    deal.kucoin_futures_api = types.SimpleNamespace(
        get_futures_position=lambda symbol: _position(-125 if short else 125),
        get_all_stop_loss_orders=lambda symbol: [
            _stop_order(
                id="trail-before-increase", stop_price=str(exchange_price), size=100
            )
        ],
        batch_cancel_stop_loss_orders=lambda ids: cancelled.extend(ids),
        place_futures_order=place,
        retrieve_order=lambda order_id: types.SimpleNamespace(
            id=order_id,
            is_active=False,
            filled_size=0,
            avg_deal_price=0,
            cancel_exist=True,
            created_at=1,
            status=types.SimpleNamespace(value="done"),
        ),
    )
    deal.reconcile_trailing_stop_loss()
    assert cancelled == ["trail-before-increase"]
    assert len(placed) == 1
    assert placed[0]["size"] == 125
    assert placed[0]["reduce_only"] is True
    assert placed[0]["order_type"] == OrderType.market
    # Quantity replacement preserves a tighter manually adjusted stop.
    assert placed[0]["stop_price"] == exchange_price
    assert deal.active_bot.deal.trailing_stop_loss_price == exchange_price


def test_dynamic_sizing_keeps_native_full_position_stop_loss():
    deal = _make_deal()
    deal.active_bot.dynamic_position_sizing = True
    placed = []
    deal.cancel_current_sl = lambda **kwargs: None
    deal.place_stop_loss = lambda **kwargs: placed.append(True)
    deal.reconcile_exchange_sl()
    assert placed == [True]


@pytest.mark.parametrize("fill_price", [0, 104])
def test_immediately_filled_trailing_stop_waits_for_execution_reconciliation(
    fill_price,
):
    from unittest.mock import Mock

    deal = _make_deal(trailing_stop_loss_price=104)
    deal.active_bot.status = Status.active
    deal.active_bot.dynamic_position_sizing = True
    deal.active_bot.deal.opening_qty = 100
    filled = OrderBase(
        order_id="immediate-trailing-fill",
        pair=deal.kucoin_symbol,
        order_type="market",
        order_side="sell",
        qty=100,
        price=fill_price,
        timestamp=1775008219262,
        time_in_force="GTC",
        status=OrderStatus.FILLED,
        deal_type=DealType.trailing_profit,
    )
    deal.kucoin_futures_api = types.SimpleNamespace(
        get_futures_position=Mock(side_effect=[_position(100), _position(0)]),
        get_all_stop_loss_orders=lambda symbol: [],
        place_futures_order=lambda **kwargs: filled,
        retrieve_order=lambda order_id: types.SimpleNamespace(
            id=order_id,
            is_active=False,
            filled_size=0,
            avg_deal_price=0,
            cancel_exist=True,
            created_at=1,
            status=types.SimpleNamespace(value="done"),
        ),
    )
    deal.place_trailing_stop_loss()
    assert deal.active_bot.status == Status.active
    assert deal.active_bot.deal.closing_qty == 0
    assert deal.active_bot.deal.closing_price == 0
    assert deal.active_bot.orders[-1].price == fill_price
    assert deal.awaiting_close_confirmation()


@pytest.mark.parametrize("position", [Position.long, Position.short])
@pytest.mark.parametrize(
    "protection",
    ["emergency", "emergency_unknown_quantity", "trailing", "missing_trailing"],
)
def test_active_partial_increase_protects_confirmed_size_despite_stale_position(
    position, protection
):
    from unittest.mock import Mock
    from pybinbot.models.deal import PositionSizeOrder
    from api.exchange_apis.kucoin.futures.position_sizing import DynamicPositionSizing

    short = position == Position.short
    trailing = protection in {"trailing", "missing_trailing"}
    stop_price = (96 if short else 104) if trailing else (105 if short else 95)
    deal = _make_deal(
        position=position,
        stop_loss_price=stop_price if not trailing else (105 if short else 95),
        trailing_stop_loss_price=stop_price if trailing else 0,
    )
    bot = deal.active_bot
    bot.status = Status.active
    bot.dynamic_position_sizing = True
    bot.deal.opening_qty = 100
    bot.deal.current_position_qty = 100
    bot.deal.position_size_order = PositionSizeOrder(
        client_oid="active-partial-scale-in",
        reducing=False,
        quantity_before=100,
        entry_price_before=100,
        requested_qty=25,
        signal_price=90 if short else 110,
    )
    now_ms = int(time() * 1000)
    bot.orders = [
        OrderModel(
            order_id="original-stop",
            pair=bot.pair,
            order_type="market",
            order_side="buy" if short else "sell",
            qty=100,
            price=stop_price,
            timestamp=now_ms,
            status=OrderStatus.NEW,
            time_in_force="GTC",
            deal_type=DealType.trailing_profit if trailing else DealType.stop_loss,
        )
    ]
    stops = (
        []
        if protection == "missing_trailing"
        else [
            _stop_order(
                id="original-stop",
                stop_price=str(stop_price),
                size=None if protection == "emergency_unknown_quantity" else 100,
            )
        ]
    )
    fill = types.SimpleNamespace(
        is_active=True, filled_size=5, avg_deal_price=90 if short else 110
    )
    stale_position = Mock(return_value=_position(-100 if short else 100))
    placed = []

    def place(**kwargs):
        placed.append(kwargs)
        return OrderBase(
            order_id="resized-stop",
            pair=bot.pair,
            order_type="market",
            order_side=kwargs["side"].value,
            qty=kwargs["size"],
            price=kwargs["stop_price"],
            timestamp=now_ms,
            status=OrderStatus.NEW,
            time_in_force="GTC",
            deal_type=DealType.trailing_profit if trailing else DealType.stop_loss,
        )

    deal.kucoin_futures_api = types.SimpleNamespace(
        futures_order_api=types.SimpleNamespace(
            get_order_by_client_oid=lambda request: fill
        ),
        get_futures_position=stale_position,
        get_all_stop_loss_orders=lambda symbol: stops,
        batch_cancel_stop_loss_orders=lambda ids: None,
        place_futures_order=place,
        retrieve_order=lambda order_id: types.SimpleNamespace(
            id=order_id,
            is_active=False,
            filled_size=0,
            avg_deal_price=0,
            cancel_exist=True,
            created_at=1,
            status=types.SimpleNamespace(value="done"),
        ),
    )
    DynamicPositionSizing(deal).reconcile()
    assert bot.deal.current_position_qty == 105
    assert bot.deal.position_size_order is not None
    assert len(placed) == 1
    assert placed[0]["size"] == 105
    assert placed[0]["reduce_only"] is True
    assert placed[0]["stop_price"] == stop_price
    stale_position.assert_not_called()
