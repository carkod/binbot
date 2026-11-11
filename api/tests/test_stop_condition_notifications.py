from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import Mock

import pytest
from pybinbot import DataFrame
from pybinbot import (
    BinanceKlineIntervals,
    BotModel,
    DealModel,
    DealType,
    MarketType,
    OrderModel,
    OrderStatus,
    Position,
    Status,
)

from streaming.futures_position import FuturesPosition
from streaming.lifecycle import Lifecycle


def make_position(
    *,
    position: Position = Position.long,
    deal_type: DealType = DealType.stop_loss,
    threshold: float = 98,
    status: Status = Status.active,
    order_status: OrderStatus = OrderStatus.NEW,
) -> Any:
    bot = BotModel(
        name="any_strategy",
        pair="BTCUSDTM",
        position=position,
        status=status,
        market_type=MarketType.FUTURES,
        deal=DealModel(opening_price=100, current_position_qty=1),
        orders=[
            OrderModel(
                order_id="protective-order",
                pair="BTCUSDTM",
                order_type="LIMIT",
                time_in_force="GTC",
                order_side="sell" if position == Position.long else "buy",
                qty=0,
                price=0,
                stop_price=threshold,
                requested_qty=1,
                status=order_status,
                deal_type=deal_type,
            )
        ],
    )
    instance = cast(Any, object.__new__(FuturesPosition))
    instance.execution = SimpleNamespace(active_bot=bot)
    instance.base_streaming = SimpleNamespace(
        config=SimpleNamespace(frontend_domain="https://terminal.example/"),
        telegram_delivery=SimpleNamespace(send_once=Mock()),
    )
    return instance


@pytest.mark.parametrize(
    "position,threshold", [(Position.long, 98), (Position.short, 102)]
)
@pytest.mark.parametrize("deal_type", [DealType.stop_loss, DealType.trailing_profit])
def test_armed_stop_notifies_at_threshold_for_any_strategy(
    position, threshold, deal_type
):
    instance = make_position(
        position=position, threshold=threshold, deal_type=deal_type
    )
    bot = instance.execution.active_bot
    stop_type = (
        "Trailing stop loss" if deal_type == DealType.trailing_profit else "Stop loss"
    )

    instance.notify_stop_condition_hits(threshold)

    instance.base_streaming.telegram_delivery.send_once.assert_called_once_with(
        f"<strong>any_strategy</strong> #BTCUSDTM\n"
        f"{stop_type} condition hit @ {bot.orders[0].stop_price}\n"
        f'<a href="https://terminal.example/bots/futures/edit/{bot.id}">Dashboard</a>'
    )


@pytest.mark.parametrize(
    "position,threshold,price", [(Position.long, 98, 97), (Position.short, 102, 103)]
)
def test_repeated_breaches_notify_until_bot_is_completed(position, threshold, price):
    instance = make_position(position=position, threshold=threshold)
    instance.notify_stop_condition_hits(price)
    instance.notify_stop_condition_hits(price)
    instance.execution.active_bot.status = Status.completed
    instance.notify_stop_condition_hits(price)
    assert instance.base_streaming.telegram_delivery.send_once.call_count == 2


@pytest.mark.parametrize(
    "status", [Status.pending, Status.inactive, Status.error, Status.completed]
)
def test_non_active_bots_do_not_notify(status):
    instance = make_position(status=status)
    instance.notify_stop_condition_hits(97)
    instance.base_streaming.telegram_delivery.send_once.assert_not_called()


@pytest.mark.parametrize(
    "order_status",
    [
        OrderStatus.CANCELED,
        OrderStatus.EXPIRED,
        OrderStatus.REJECTED,
        OrderStatus.FILLED,
    ],
)
def test_old_protective_orders_do_not_notify(order_status):
    instance = make_position(order_status=order_status)
    instance.notify_stop_condition_hits(97)
    instance.base_streaming.telegram_delivery.send_once.assert_not_called()


@pytest.mark.parametrize("position,price", [(Position.long, 99), (Position.short, 97)])
def test_stop_not_reached_does_not_notify(position, price):
    instance = make_position(position=position)
    instance.notify_stop_condition_hits(price)
    instance.base_streaming.telegram_delivery.send_once.assert_not_called()


def test_arming_or_tightening_a_stop_is_not_a_hit():
    instance = make_position(deal_type=DealType.trailing_profit, threshold=105)
    instance.execution.active_bot.deal.trailing_stop_loss_price = 110
    instance.notify_stop_condition_hits(108)
    instance.base_streaming.telegram_delivery.send_once.assert_not_called()


def test_legacy_stop_order_uses_deal_trigger_price():
    instance = make_position(threshold=0)
    instance.execution.active_bot.deal.stop_loss_price = 98
    instance.notify_stop_condition_hits(97)
    instance.base_streaming.telegram_delivery.send_once.assert_called_once()


def test_lifecycle_notifies_before_reconciliation_completes_bot(monkeypatch):
    instance = make_position()
    bot = instance.execution.active_bot
    events = []
    base = instance.base_streaming
    base.kucoin_futures_api = SimpleNamespace(get_mark_price=Mock(return_value=97))
    base.telegram_delivery.send_once.side_effect = lambda message: events.append(
        "notify"
    )
    instance.df = DataFrame()
    instance.btc_df = DataFrame()
    instance.dataframe_ops = Mock(return_value=([], []))
    instance.build_bb_metrics = Mock(return_value=None)

    def order_updates():
        events.append("reconcile")
        bot.status = Status.completed
        return bot

    instance.order_updates = order_updates
    monkeypatch.setattr(FuturesPosition, "__new__", lambda cls, **kwargs: instance)
    monkeypatch.setattr(FuturesPosition, "__init__", lambda self, **kwargs: None)
    lifecycle = cast(Any, object.__new__(Lifecycle))
    lifecycle.execution = instance.execution
    lifecycle.base_streaming = base
    lifecycle.lifecycle_candle_intervals = Mock(
        return_value=(BinanceKlineIntervals.fifteen_minutes,) * 2
    )

    assert lifecycle.process_tick() is bot
    assert events == ["notify", "reconcile"]
    # Completed bots also skip the upstream price lookup on another tick.
    lifecycle.process_tick()
    base.kucoin_futures_api.get_mark_price.assert_called_once_with("BTCUSDTM")
    assert events == ["notify", "reconcile", "reconcile"]
