from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import Mock

import pytest
from pybinbot import BotModel, DealType, OrderStatus, Position, Status

from api.exchange_apis.kucoin.deals.short_deal import KucoinShortDeal


@pytest.mark.parametrize(
    ("deal_type", "completion_log"),
    [
        (DealType.stop_loss, "Completed Stop loss order"),
        (DealType.take_profit, "Completed Take profit!"),
        (DealType.trailing_profit, "Completed Take profit!"),
    ],
)
def test_margin_close_records_buyback_and_commission(deal_type, completion_log):
    deal = cast(Any, KucoinShortDeal.__new__(KucoinShortDeal))
    deal.active_bot = BotModel(pair="BTCUSDT", position=Position.short)
    deal.controller = Mock()
    order = SimpleNamespace(
        created_at=1_700_000_000_000,
        id="order-1",
        symbol="BTC-USDT",
        side="buy",
        type="market",
        price="99",
        size="2",
        time_in_force="GTC",
        active=False,
        fee="0.2",
    )
    deal.margin_liquidation = Mock(return_value=order)

    if deal_type == DealType.stop_loss:
        result = deal.execute_stop_loss()
    else:
        result = deal.execute_take_profit(deal_type)

    assert result is deal.active_bot
    assert result.status == Status.completed
    assert result.orders[-1].deal_type == deal_type
    assert result.orders[-1].status == OrderStatus.FILLED
    assert result.deal.closing_price == 99
    assert result.deal.closing_qty == 2
    assert result.deal.total_commissions == 0.2
    assert any(completion_log in log for log in result.logs)
    deal.controller.save.assert_called_once_with(result)


def test_active_short_updates_stop_and_trailing_prices():
    deal = cast(Any, KucoinShortDeal.__new__(KucoinShortDeal))
    deal.active_bot = BotModel(
        pair="BTCUSDT",
        position=Position.short,
        stop_loss=5,
        trailing=True,
        trailing_profit=6,
        trailing_deviation=2,
    )
    deal.active_bot.deal.opening_price = 100
    deal.price_precision = 2

    result = deal.short_update_deal_trailing_parameters()

    assert result.deal.stop_loss_price == 105
    assert result.deal.trailing_profit_price == 94
    assert result.deal.trailing_stop_loss_price == 102
