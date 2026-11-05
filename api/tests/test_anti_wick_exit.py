"""
Stop losses are KuCoin-native stop-limit orders; the bot never exits on a wick.

Regression fixture: FHEUSDTM 2026-05-31
  Long opened 0.02343, SL 0.02249 (4% floored), tick 0.00001.
  A 1m wick traded down to 0.02233 and the old stop-market filled at 0.02235
  (the wick low). With a 0.5% stop-limit, KuCoin rests the close at 0.02237,
  so no fill can land deeper in the wick than that.

The trigger itself stays on KuCoin's mark price, inside the candle. An earlier
simulation over 14 historical SL exits found that delaying the *trigger* to a
closed candle worsened outcomes (~2.1%), so only the market fallback for a
stop-limit that the price ran past waits for a closed candle.
"""

import types
from time import time
from typing import Any, cast

import pytest
from kucoin_universal_sdk.generate.futures.order.model_add_order_req import (
    AddOrderReq,
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
)
from pybinbot.models.deal import ConditionalCloseOrder

from api.exchange_apis.kucoin.futures.futures_deal import KucoinPositionDeal
from streaming.base import BaseStreaming
from streaming.lifecycle import Lifecycle

FHEU_STOP = 0.02249
FHEU_STOP_LIMIT = 0.02237  # floor(0.02249 * 0.995) on a 0.00001 tick
WICK_LOW = 0.02233
INTERVAL_MS = 15 * 60 * 1000


def _klines(closed_close: float) -> list[list[float]]:
    """One closed 15m candle and the forming candle that holds the wick."""
    current_open = (int(time() * 1000) // INTERVAL_MS) * INTERVAL_MS
    return [
        [
            current_open - INTERVAL_MS,
            0.02279,
            0.02288,
            0.02233,
            closed_close,
            1000,
            current_open - 1,
        ],
        [
            current_open,
            closed_close,
            0.02255,
            WICK_LOW,
            0.02235,
            500,
            current_open + INTERVAL_MS - 1,
        ],
    ]


def _make_fheusdtm_lifecycle(*, closed_close: float) -> Lifecycle:
    execution = cast(Any, KucoinPositionDeal.__new__(KucoinPositionDeal))
    execution.price_precision = 5
    execution.kucoin_symbol = "FHEUSDTM"
    execution.kucoin_symbol_data = types.SimpleNamespace(
        tick_size=0.00001, multiplier=1
    )
    execution.symbol_info = types.SimpleNamespace(
        futures_leverage=2,
        qty_precision=0,
    )
    execution.active_bot = BotModel(
        pair="FHEUSDTM",
        market_type=MarketType.FUTURES,
        position=Position.long,
        stop_loss=4.0,
        take_profit=0.0,
        trailing=False,
        deal=DealModel(
            opening_price=0.02343,
            opening_qty=8.0,
            current_position_qty=8.0,
            stop_loss_price=FHEU_STOP,
            opening_timestamp=int(time() * 1000) - 2 * INTERVAL_MS,
            conditional_close_order=ConditionalCloseOrder(
                client_oid="native-stop",
                order_id="native-stop-id",
                requested_qty=8,
                stop_price=FHEU_STOP,
                deal_type=DealType.stop_loss,
            ),
        ),
    )
    execution.controller = types.SimpleNamespace(
        save=lambda *args, **kwargs: None,
        update_logs=lambda *args, **kwargs: None,
    )
    lifecycle = Lifecycle(
        execution=execution,
        base_streaming=cast(
            BaseStreaming,
            types.SimpleNamespace(
                interval=types.SimpleNamespace(get_ms=lambda: INTERVAL_MS)
            ),
        ),
    )
    # KuCoin accepted the stop when the closed candle opened.
    execution.active_bot.orders = [
        OrderModel(
            order_id="native-stop-id",
            client_oid="native-stop",
            pair="FHEUSDTM",
            order_type=OrderType.limit,
            order_side="sell",
            time_in_force="GTC",
            timestamp=_klines(closed_close)[0][0],
            qty=0,
            price=0,
            requested_qty=8,
            stop_price=FHEU_STOP,
            status=OrderStatus.NEW,
            deal_type=DealType.stop_loss,
        )
    ]
    lifecycle.klines = _klines(closed_close)
    return lifecycle


def test_native_stop_is_a_stop_limit_capped_above_the_wick():
    lifecycle = _make_fheusdtm_lifecycle(closed_close=0.02252)
    execution = cast(Any, lifecycle.execution)
    execution.active_bot.deal.conditional_close_order = None
    submitted: dict[str, Any] = {}

    def place_futures_order(**kwargs) -> OrderBase:
        submitted.update(kwargs)
        return OrderBase(
            order_id="native-stop-id",
            order_type="limit",
            pair="FHEUSDTM",
            timestamp=1,
            order_side="sell",
            qty=0,
            price=0,
            status=OrderStatus.NEW,
            time_in_force="GTC",
            deal_type=DealType.stop_loss,
        )

    execution.kucoin_futures_api = types.SimpleNamespace(
        place_futures_order=place_futures_order
    )

    execution.place_conditional_close(FHEU_STOP, 8, DealType.stop_loss)

    assert submitted["order_type"] == OrderType.limit
    assert submitted["stop"] == AddOrderReq.StopEnum.DOWN
    assert submitted["stop_price"] == FHEU_STOP
    assert submitted["price"] == FHEU_STOP_LIMIT
    assert submitted["price"] > WICK_LOW
    assert submitted["reduce_only"] is True


def test_wick_through_stop_with_closed_candle_above_limit_keeps_native_stop():
    lifecycle = _make_fheusdtm_lifecycle(closed_close=0.02252)
    close_calls: list[Any] = []
    cast(Any, lifecycle.execution).close_all = lambda **kwargs: close_calls.append(
        kwargs
    )

    Lifecycle.exit(lifecycle, 0.02235)

    assert close_calls == []


@pytest.mark.parametrize("closed_close", [0.02236, 0.02230])
def test_closed_candle_below_stop_limit_closes_at_market(closed_close):
    lifecycle = _make_fheusdtm_lifecycle(closed_close=closed_close)
    close_calls: list[Any] = []

    def close_all(**kwargs) -> BotModel:
        close_calls.append(kwargs)
        return lifecycle.execution.active_bot

    cast(Any, lifecycle.execution).close_all = close_all

    Lifecycle.exit(lifecycle, closed_close)

    assert close_calls == [{"deal_type": DealType.stop_loss, "market_only": True}]
