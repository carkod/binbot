from types import SimpleNamespace
from unittest.mock import Mock
from typing import Any, cast

import pytest
from kucoin_universal_sdk.generate.futures.order import (
    BatchCancelOrdersData,
    BatchCancelOrdersResp,
    CancelOrderByIdResp,
    GetStopOrderListItems,
)
from kucoin_universal_sdk.model.common import RestError
from pybinbot import (
    BinbotErrors,
    BotModel,
    DealType,
    MarketType,
    OrderBase,
    OrderModel,
    OrderStatus,
    OrderType,
    Position,
    Status,
)
from pybinbot.models.deal import ConditionalCloseOrder

from api.exchange_apis.kucoin.futures.futures_deal import KucoinPositionDeal


@pytest.fixture(params=[Position.long, Position.short])
def replacement(request):
    position = request.param
    engine = cast(Any, KucoinPositionDeal.__new__(KucoinPositionDeal))
    engine.active_bot = BotModel(
        pair="APLDUSDTM",
        market_type=MarketType.FUTURES,
        status=Status.active,
        position=position,
        stop_loss=4,
    )
    engine.kucoin_symbol = "APLDUSDTM"
    engine.price_precision = 2
    engine.kucoin_symbol_data = SimpleNamespace(tick_size=0.01, multiplier=1)
    engine.symbol_info = SimpleNamespace(qty_precision=0)
    engine.active_bot.deal.opening_price = 100
    engine.active_bot.deal.opening_qty = 18
    engine.active_bot.deal.current_position_qty = 18
    old_price = 102 if position == Position.short else 98
    target = 101 if position == Position.short else 99
    engine.active_bot.deal.trailing_stop_loss_price = target
    engine.active_bot.deal.conditional_close_order = ConditionalCloseOrder(
        client_oid="old-client",
        requested_qty=18,
        stop_price=old_price,
        order_id="old-stop",
        deal_type=DealType.trailing_profit,
    )
    engine.active_bot.orders = [
        OrderModel(
            order_id="old-stop",
            client_oid="old-client",
            pair="APLDUSDTM",
            order_type="market",
            order_side="buy" if position == Position.short else "sell",
            time_in_force="GTC",
            timestamp=1,
            qty=0,
            price=0,
            requested_qty=18,
            stop_price=old_price,
            status=OrderStatus.NEW,
            deal_type=DealType.trailing_profit,
        )
    ]
    snapshots = []
    engine.controller = Mock()
    engine.controller.save.side_effect = lambda bot: snapshots.append(bot.model_dump())
    live = [GetStopOrderListItems(id="old-stop", stop_price=str(old_price), size=18)]
    api = engine.kucoin_futures_api = Mock()
    api.get_futures_position.return_value = SimpleNamespace(
        current_qty=-18 if position == Position.short else 18
    )
    api.get_all_stop_loss_orders.side_effect = lambda symbol: live[:]

    def cancel(order_ids):
        assert order_ids == ["old-stop"]
        assert snapshots[-1]["deal"]["trailing_stop_loss_price"] == target
        live.clear()
        return BatchCancelOrdersResp(
            data=[BatchCancelOrdersData(order_id="old-stop", code="200000")]
        )

    api.batch_cancel_stop_loss_orders.side_effect = cancel
    api.retrieve_order.side_effect = RestError(
        msg="temporarily unavailable",
        response=SimpleNamespace(code="100001", message="error.getOrder.orderNotExist"),
    )
    api.get_order_execution.return_value = (0, 0, 0)

    def place(**kwargs):
        live.append(
            GetStopOrderListItems(
                id="new-stop", stop_price=str(kwargs["stop_price"]), size=kwargs["size"]
            )
        )
        return OrderBase(
            order_id="new-stop",
            pair=kwargs["symbol"],
            order_type="market",
            order_side=kwargs["side"].value,
            time_in_force="GTC",
            timestamp=1,
            qty=0,
            price=0,
            status=OrderStatus.NEW,
            deal_type=DealType.trailing_profit,
        )

    api.place_futures_order.side_effect = place
    return engine, api, live, snapshots, target


def test_missing_cancelled_order_preserves_tighter_native_stop_without_recreation_loop(
    replacement,
):
    engine, api, live, snapshots, target = replacement
    engine.place_trailing_stop_loss()

    assert engine.active_bot.orders[0].status == OrderStatus.CANCELED
    assert engine.active_bot.deal.conditional_close_order.order_id == "new-stop"
    assert engine.active_bot.deal.trailing_stop_loss_price == target
    submitted = api.place_futures_order.call_args.kwargs
    assert submitted["stop_price"] == target
    assert submitted["size"] == 18
    assert submitted["reduce_only"] is True
    assert submitted["order_type"] == OrderType.limit
    assert submitted["price"] > 0
    api.get_order_execution.assert_called_once_with("old-stop")

    # Restart with persisted state and repeat after the replacement cooldown.
    # A pending stop's zero executed quantity must not be mistaken for its size.
    engine.active_bot = BotModel.model_validate(snapshots[-1])
    engine.reconcile_trailing_stop_loss(position_qty=18)
    engine.place_trailing_stop_loss()
    api.batch_cancel_stop_loss_orders.assert_called_once()
    api.place_futures_order.assert_called_once()
    assert len(live) == 1


@pytest.mark.parametrize(
    "outcome",
    [
        "not_acknowledged",
        "still_open",
        "filled",
        "unrelated_error",
        "history_unavailable",
        "unrecorded_partial_fill",
    ],
)
def test_ambiguous_cancellation_cannot_submit_another_stop(replacement, outcome):
    engine, api, live, snapshots, target = replacement
    if outcome == "not_acknowledged":
        api.batch_cancel_stop_loss_orders.side_effect = None
        api.batch_cancel_stop_loss_orders.return_value = BatchCancelOrdersResp(
            data=[BatchCancelOrdersData(order_id="another-stop", code="200000")]
        )
    elif outcome == "still_open":
        api.batch_cancel_stop_loss_orders.side_effect = None
        api.batch_cancel_stop_loss_orders.return_value = BatchCancelOrdersResp(
            data=[BatchCancelOrdersData(order_id="old-stop", code="200000")]
        )
    elif outcome == "filled":
        api.get_order_execution.return_value = (18, target, 1000)
    elif outcome == "unrelated_error":
        api.retrieve_order.side_effect = RestError(
            msg="invalid parameters",
            response=SimpleNamespace(code="100001", message="Invalid parameter"),
        )
    elif outcome == "history_unavailable":
        api.get_order_execution.side_effect = TimeoutError("history unavailable")
    else:
        # The stop executed 6 contracts that order_updates has not recorded.
        api.get_order_execution.return_value = (6, target, 1000)

    with pytest.raises((RestError, BinbotErrors, TimeoutError)):
        engine.place_trailing_stop_loss()
    api.place_futures_order.assert_not_called()
    assert engine.active_bot.orders[0].status == OrderStatus.NEW
    assert snapshots[0]["deal"]["trailing_stop_loss_price"] == target
    if outcome == "unrelated_error":
        api.get_order_execution.assert_not_called()


def test_tighter_trailing_target_survives_failure_before_cancel_acknowledgement(
    replacement,
):
    engine, api, live, snapshots, target = replacement
    api.batch_cancel_stop_loss_orders.side_effect = TimeoutError(
        "lost cancellation response"
    )
    with pytest.raises(TimeoutError):
        engine.place_trailing_stop_loss()
    restarted = BotModel.model_validate(snapshots[-1])
    assert restarted.deal.trailing_stop_loss_price == target
    assert restarted.orders[0].status == OrderStatus.NEW
    api.place_futures_order.assert_not_called()
    assert len(live) == 1


def test_stop_list_outage_never_cancels_working_native_protection(replacement):
    engine, api, live, snapshots, target = replacement
    api.get_all_stop_loss_orders.side_effect = TimeoutError("temporary outage")
    engine.place_trailing_stop_loss()
    api.batch_cancel_stop_loss_orders.assert_not_called()
    api.place_futures_order.assert_not_called()
    assert len(live) == 1


def test_triggered_stop_limit_waiting_at_its_limit_is_not_replaced(replacement):
    """KuCoin drops a triggered stop from the stop list; it still protects."""
    engine, api, live, snapshots, target = replacement
    live.clear()
    api.retrieve_order.side_effect = None
    api.retrieve_order.return_value = SimpleNamespace(
        stop_triggered=True, is_active=True, filled_size=6
    )

    engine.place_trailing_stop_loss()
    engine.reconcile_trailing_stop_loss(position_qty=12)

    api.batch_cancel_stop_loss_orders.assert_not_called()
    api.cancel_futures_order.assert_not_called()
    api.place_futures_order.assert_not_called()
    assert engine.active_bot.orders[0].status == OrderStatus.NEW


def test_recorded_partial_stop_fill_does_not_block_cancelling_the_rest(replacement):
    """A missed stop-limit must stay closable after a partial fill."""
    engine, api, live, snapshots, target = replacement
    live.clear()
    engine.active_bot.orders[0].qty = 6
    engine.active_bot.orders[0].price = target
    engine.active_bot.orders[0].status = OrderStatus.PARTIALLY_FILLED
    api.retrieve_order.side_effect = [
        SimpleNamespace(is_active=True, filled_size=6),
        SimpleNamespace(is_active=False, filled_size=6),
    ]
    api.cancel_futures_order.return_value = CancelOrderByIdResp(
        cancelled_order_ids=["old-stop"]
    )

    engine.cancel_current_sl()

    api.cancel_futures_order.assert_called_once_with("old-stop")
    stop = engine.active_bot.orders[0]
    assert stop.status == OrderStatus.CANCELED
    assert (stop.qty, stop.price) == (6, target)
    assert engine.active_bot.deal.conditional_close_order is None


def test_fill_racing_the_cancel_beyond_recorded_quantity_still_blocks(replacement):
    engine, api, live, snapshots, target = replacement
    live.clear()
    engine.active_bot.orders[0].qty = 6
    engine.active_bot.orders[0].status = OrderStatus.PARTIALLY_FILLED
    api.retrieve_order.side_effect = [
        SimpleNamespace(is_active=True, filled_size=6),
        SimpleNamespace(is_active=False, filled_size=8),
    ]
    api.cancel_futures_order.return_value = CancelOrderByIdResp(
        cancelled_order_ids=["old-stop"]
    )

    with pytest.raises(BinbotErrors, match="filled during cancellation"):
        engine.cancel_current_sl()
