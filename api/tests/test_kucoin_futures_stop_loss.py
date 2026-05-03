from typing import Any, cast
import types

from bots.models import BotModel, DealModel, OrderModel
from exchange_apis.kucoin.futures.futures_deal import KucoinPositionDeal
from pybinbot import OrderBase, OrderStatus, DealType, Position
from kucoin_universal_sdk.generate.futures.order.model_add_order_req import (
    AddOrderReq,
)


def make_stop_loss_order(price: float = 97.5) -> OrderModel:
    return OrderModel(
        order_id="existing-sl",
        order_type="market",
        pair="BEATUSDTM",
        timestamp=1775008219262,
        order_side="sell",
        qty=1,
        price=price,
        status=OrderStatus.NEW,
        time_in_force="GTC",
        deal_type=DealType.stop_loss,
    )


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


def test_should_replace_stop_loss_order_only_for_material_protective_moves():
    deal = cast(Any, KucoinPositionDeal.__new__(KucoinPositionDeal))
    deal.price_precision = 4
    deal.active_bot = BotModel(pair="BEATUSDT", position=Position.long)

    assert deal.should_replace_stop_loss_order(None, 97.5) is True
    assert deal.should_replace_stop_loss_order(97.5, 97.0) is False
    assert deal.should_replace_stop_loss_order(97.5, 97.55) is False
    assert deal.should_replace_stop_loss_order(97.5, 97.7) is True

    deal.active_bot.position = Position.short
    assert deal.should_replace_stop_loss_order(102.0, 102.5) is False
    assert deal.should_replace_stop_loss_order(102.0, 101.95) is False
    assert deal.should_replace_stop_loss_order(102.0, 101.8) is True


def test_update_parameters_keeps_exchange_stop_when_new_long_stop_is_less_protective():
    calls: list[str] = []
    deal = cast(Any, KucoinPositionDeal.__new__(KucoinPositionDeal))
    deal.price_precision = 2
    deal.cancel_current_sl = lambda: calls.append("cancel")
    deal.place_stop_loss = lambda: calls.append("place")
    deal.active_bot = BotModel(
        pair="BEATUSDT",
        position=Position.long,
        stop_loss=3.0,
        margin_short_reversal=False,
        orders=[make_stop_loss_order(price=97.5)],
        deal=DealModel(
            opening_price=100.0,
            opening_qty=1,
            stop_loss_price=97.5,
        ),
    )

    updated_bot = KucoinPositionDeal.update_parameters(deal)

    assert updated_bot.deal.stop_loss_price == 97.0
    assert calls == []


def test_update_parameters_replaces_exchange_stop_when_new_long_stop_improves_enough():
    calls: list[str] = []
    deal = cast(Any, KucoinPositionDeal.__new__(KucoinPositionDeal))
    deal.price_precision = 2
    deal.cancel_current_sl = lambda: calls.append("cancel")
    deal.place_stop_loss = lambda: calls.append("place")
    deal.active_bot = BotModel(
        pair="BEATUSDT",
        position=Position.long,
        stop_loss=2.0,
        margin_short_reversal=False,
        orders=[make_stop_loss_order(price=97.5)],
        deal=DealModel(
            opening_price=100.0,
            opening_qty=1,
            stop_loss_price=97.5,
        ),
    )

    updated_bot = KucoinPositionDeal.update_parameters(deal)

    assert updated_bot.deal.stop_loss_price == 98.0
    assert calls == ["cancel", "place"]


def test_update_parameters_places_stop_loss_when_no_exchange_stop_is_tracked():
    calls: list[str] = []
    deal = cast(Any, KucoinPositionDeal.__new__(KucoinPositionDeal))
    deal.price_precision = 2
    deal.cancel_current_sl = lambda: calls.append("cancel")
    deal.place_stop_loss = lambda: calls.append("place")
    deal.active_bot = BotModel(
        pair="BEATUSDT",
        position=Position.long,
        stop_loss=2.5,
        margin_short_reversal=False,
        deal=DealModel(
            opening_price=100.0,
            opening_qty=1,
            stop_loss_price=97.5,
        ),
    )

    updated_bot = KucoinPositionDeal.update_parameters(deal)

    assert updated_bot.deal.stop_loss_price == 97.5
    assert calls == ["cancel", "place"]


def test_update_parameters_recreates_stop_loss_when_local_order_is_stale():
    calls: list[str] = []
    deal = cast(Any, KucoinPositionDeal.__new__(KucoinPositionDeal))
    deal.price_precision = 2
    deal.kucoin_symbol = "BEATUSDTM"
    deal.kucoin_futures_api = types.SimpleNamespace(
        get_all_stop_loss_orders=lambda symbol: []
    )
    deal.cancel_current_sl = lambda: calls.append("cancel")
    deal.place_stop_loss = lambda: calls.append("place")
    deal.active_bot = BotModel(
        pair="BEATUSDT",
        position=Position.long,
        stop_loss=3.0,
        margin_short_reversal=False,
        orders=[make_stop_loss_order(price=97.5)],
        deal=DealModel(
            opening_price=100.0,
            opening_qty=1,
            stop_loss_price=97.5,
        ),
    )

    updated_bot = KucoinPositionDeal.update_parameters(deal)

    assert updated_bot.deal.stop_loss_price == 97.0
    assert calls == ["cancel", "place"]
