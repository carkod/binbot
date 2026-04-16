from typing import Any, cast
import types

from bots.models import BotModel, DealModel
from exchange_apis.kucoin.futures.futures_deal import KucoinPositionDeal
from pybinbot import OrderBase, OrderStatus, DealType, Position
from kucoin_universal_sdk.generate.futures.order.model_add_order_req import (
    AddOrderReq,
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
