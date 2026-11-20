from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pybinbot import (
    BinanceErrors,
    BotModel,
    DealType,
    OrderModel,
    OrderStatus,
    Position,
    RecoveryParams,
    Status,
)

from api.exchange_apis.binance.deals.long import BinanceLongDeal
from api.exchange_apis.binance.deals.short import BinanceShortDeal


def make_deal(deal_class, **parameters):
    deal = deal_class.__new__(deal_class)
    deal.active_bot = BotModel(
        pair="BTCUSDT",
        position=Position.short if deal_class is BinanceShortDeal else Position.long,
        status=Status.active,
        stop_loss=5,
        trailing=True,
        trailing_profit=5,
        trailing_deviation=2,
        take_profit=10,
    )
    for name, value in parameters.items():
        setattr(deal.active_bot, name, value)
    deal.active_bot.deal.opening_price = 100
    deal.price_precision = 4
    deal.qty_precision = 4
    deal.controller = Mock()
    return deal


def test_long_stop_is_below_entry_on_activation():
    deal = make_deal(BinanceLongDeal, status=Status.inactive)

    deal.long_open_deal_trailing_parameters()

    assert deal.active_bot.deal.stop_loss_price == 95
    assert deal.active_bot.status == Status.active


@pytest.mark.parametrize(
    "deal_class, expected", [(BinanceLongDeal, 105), (BinanceShortDeal, 95)]
)
def test_parameter_update_uses_trailing_profit_and_waits_to_arm_stop(
    deal_class, expected
):
    deal = make_deal(deal_class)

    if deal_class is BinanceLongDeal:
        deal.long_update_deal_trailing_parameters()
    else:
        deal.short_update_deal_trailing_parameters()

    assert deal.active_bot.deal.trailing_profit_price == expected
    assert deal.active_bot.deal.trailing_stop_loss_price == 0


@pytest.mark.parametrize(
    "deal_class, expected", [(BinanceLongDeal, 110), (BinanceShortDeal, 90)]
)
def test_parameter_update_refreshes_fixed_take_profit(deal_class, expected):
    deal = make_deal(deal_class, trailing=False)

    if deal_class is BinanceLongDeal:
        deal.long_update_deal_trailing_parameters()
    else:
        deal.short_update_deal_trailing_parameters()

    assert deal.active_bot.deal.take_profit_price == pytest.approx(expected)


def test_short_waits_for_profit_trigger_before_trailing_exit():
    deal = make_deal(BinanceShortDeal)
    deal.active_bot.deal.trailing_profit_price = 95
    deal.close_conditions = Mock()
    deal.execute_take_profit = Mock()

    deal.deal_exit_orchestration(close_price=99)

    assert deal.active_bot.status == Status.active
    deal.execute_take_profit.assert_not_called()


def test_short_with_disabled_stop_loss_stays_open_above_entry():
    deal = make_deal(BinanceShortDeal, stop_loss=0, trailing=False, take_profit=0)
    deal.close_conditions = Mock()
    deal.execute_stop_loss = Mock()

    deal.deal_exit_orchestration(close_price=101)

    deal.execute_stop_loss.assert_not_called()


def test_short_trailing_stop_tracks_price_down_and_closes_on_rebound():
    deal = make_deal(BinanceShortDeal)
    deal.active_bot.deal.trailing_profit_price = 95
    deal.close_conditions = Mock()
    deal.execute_take_profit = Mock()

    deal.deal_exit_orchestration(close_price=94)
    assert deal.active_bot.deal.trailing_stop_loss_price == pytest.approx(95.88)
    assert deal.active_bot.deal.trailing_profit_price == pytest.approx(89.3)
    deal.execute_take_profit.assert_not_called()

    deal.deal_exit_orchestration(close_price=89)
    assert deal.active_bot.deal.trailing_stop_loss_price == pytest.approx(90.78)
    deal.execute_take_profit.assert_not_called()

    deal.deal_exit_orchestration(close_price=91)
    deal.execute_take_profit.assert_called_once_with(DealType.trailing_profit)


@pytest.mark.parametrize("deal_class", [BinanceLongDeal, BinanceShortDeal])
def test_stop_loss_finishes_tick_before_any_other_exit(deal_class):
    deal = make_deal(deal_class)
    deal.active_bot.deal.stop_loss_price = 95 if deal_class is BinanceLongDeal else 105
    deal.active_bot.deal.trailing_stop_loss_price = (
        95 if deal_class is BinanceLongDeal else 105
    )
    deal.close_conditions = Mock()
    deal.check_failed_switch_long_bot = Mock()
    deal.update_spot_orders = Mock()
    deal.trailing_profit = Mock()
    deal.execute_take_profit = Mock()

    def close():
        deal.active_bot.status = Status.completed

    deal.execute_stop_loss = Mock(side_effect=close)
    deal.deal_exit_orchestration(
        close_price=90 if deal_class is BinanceLongDeal else 110,
        open_price=100,
    )

    deal.execute_stop_loss.assert_called_once_with()
    deal.trailing_profit.assert_not_called()
    deal.execute_take_profit.assert_not_called()


@pytest.mark.parametrize("deal_class", [BinanceLongDeal, BinanceShortDeal])
def test_market_reversal_close_finishes_tick(deal_class):
    deal = make_deal(deal_class)
    deal.check_failed_switch_long_bot = Mock()
    deal.update_spot_orders = Mock()
    deal.execute_stop_loss = Mock()
    deal.execute_take_profit = Mock()
    deal.trailing_profit = Mock()

    def close(_):
        deal.active_bot.status = Status.completed

    deal.close_conditions = Mock(side_effect=close)
    deal.deal_exit_orchestration(close_price=110, open_price=111)

    deal.execute_stop_loss.assert_not_called()
    deal.execute_take_profit.assert_not_called()
    deal.trailing_profit.assert_not_called()


@pytest.mark.parametrize("balance", [0, 0.00001])
def test_long_panic_close_persists_error_when_no_sellable_quantity(balance):
    deal = make_deal(BinanceLongDeal)
    deal.symbols_crud = SimpleNamespace(base_asset=Mock(return_value="BTC"))
    deal.get_single_spot_balance = Mock(return_value=balance)
    deal.sell_order = Mock()

    result = deal.close_all()

    assert result.status == Status.error
    deal.controller.save.assert_called_once_with(result)
    deal.sell_order.assert_not_called()


@pytest.mark.parametrize(
    "result", [None, {"code": -2010, "msg": "Insufficient balance"}]
)
def test_short_stop_preserves_position_when_liquidation_has_no_fill(result):
    deal = make_deal(BinanceShortDeal)
    deal.margin_liquidation = Mock(return_value=result)

    returned = deal.execute_stop_loss()

    assert returned.status == Status.active
    assert returned.deal.closing_price == 0
    assert returned.orders == []
    deal.controller.save.assert_called_once_with(returned)


def test_short_panic_close_records_failed_liquidation():
    deal = make_deal(BinanceShortDeal)
    deal.symbols_crud = SimpleNamespace(base_asset=Mock(return_value="BTC"))
    deal.get_single_raw_balance = Mock(return_value=1)
    deal.margin_liquidation = Mock(return_value=None)

    result = deal.close_all()

    assert result.status == Status.error
    assert result.deal.closing_price == 0
    deal.controller.save.assert_called_once_with(result)


def test_long_panic_close_propagates_exchange_errors():
    deal = make_deal(BinanceLongDeal)
    deal.symbols_crud = SimpleNamespace(base_asset=Mock(return_value="BTC"))
    deal.get_single_spot_balance = Mock(return_value=1)
    error = BinanceErrors("Exchange unavailable", -1000)
    deal.sell_order = Mock(side_effect=error)

    with pytest.raises(BinanceErrors) as raised:
        deal.close_all()

    assert raised.value is error


def test_cancel_open_order_removes_matching_model_with_exchange_integer_id():
    deal = make_deal(BinanceLongDeal)
    order = OrderModel(
        order_id="123",
        pair="BTCUSDT",
        order_side="BUY",
        order_type="LIMIT",
        time_in_force="GTC",
        timestamp=1_700_000_000_000,
        qty=1,
        price=100,
        status=OrderStatus.NEW,
        deal_type=DealType.base_order,
    )
    deal.active_bot.orders.append(order)
    deal.query_open_orders = Mock(return_value=[{"orderId": 123, "status": "NEW"}])
    deal.signed_request = Mock()
    deal.order_url = "/order"

    assert deal.close_open_orders("BTCUSDT") is True
    assert deal.active_bot.orders == []
    assert deal.active_bot.status == Status.error
    deal.controller.save.assert_called_once_with(deal.active_bot)


@pytest.mark.parametrize("completed", [False, True])
def test_short_reversal_requires_confirmed_source_close(completed):
    deal = make_deal(BinanceShortDeal, recovery_params=RecoveryParams())
    deal.active_bot.deal.stop_loss_price = 105
    deal.close_conditions = Mock()
    deal.switch_to_long_bot = Mock()
    deal.symbol_info = SimpleNamespace(is_margin_trading_allowed=True)

    def close():
        if completed:
            deal.active_bot.status = Status.completed

    deal.execute_stop_loss = Mock(side_effect=close)
    deal.deal_exit_orchestration(close_price=106)

    assert deal.switch_to_long_bot.call_count == int(completed)


@pytest.mark.parametrize(
    "deal_class, price", [(BinanceLongDeal, 95), (BinanceShortDeal, 105)]
)
def test_stop_triggers_at_exact_stop_price(deal_class, price):
    deal = make_deal(deal_class)
    deal.active_bot.deal.stop_loss_price = price
    deal.close_conditions = Mock()
    deal.check_failed_switch_long_bot = Mock()
    deal.update_spot_orders = Mock()
    deal.execute_stop_loss = Mock()

    deal.deal_exit_orchestration(close_price=price, open_price=100)

    deal.execute_stop_loss.assert_called_once_with()


def test_short_trailing_stop_never_moves_up():
    deal = make_deal(BinanceShortDeal)
    deal.active_bot.deal.trailing_profit_price = 95
    deal.active_bot.deal.trailing_stop_loss_price = 90

    deal.update_trailing_profit(92)

    assert deal.active_bot.deal.trailing_stop_loss_price == 90


def test_margin_entry_preserves_original_exchange_error():
    deal = make_deal(BinanceShortDeal, fiat_order_size=100)
    deal.get_ticker_price = Mock(return_value=100)
    deal.init_margin_short = Mock()
    error = BinanceErrors("Exchange unavailable", -1000)
    deal.sell_margin_order = Mock(side_effect=error)

    with pytest.raises(BinanceErrors) as raised:
        deal.margin_short_base_order()

    assert raised.value is error
