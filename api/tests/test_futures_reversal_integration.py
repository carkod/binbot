from typing import Any, cast

from bots.models import BotModel, OrderModel
from exchange_apis.kucoin.futures.position_deal import PositionDeal
from kucoin_universal_sdk.model.common import RestError
from pybinbot import MarketType, OrderStatus, QuoteAssets, Status, DealType, Position
from tests.fixtures.mock_bot_table import make_mock_bot_active_model


class DummyController:
    def __init__(self):
        self.saved: list[BotModel] = []
        self.created: list[BotModel] = []

    def save(self, bot: BotModel) -> BotModel:
        snapshot = BotModel.model_validate(bot.model_dump())
        self.saved.append(snapshot)
        return snapshot

    def create(self, new_bot) -> BotModel:
        created = BotModel.model_validate(new_bot.model_dump())
        self.created.append(created)
        return created


class DummyFuturesApi:
    def __init__(self, current_qty: float = 68):
        self._position = type(
            "pos", (object,), {"current_qty": current_qty, "mark_price": 1.27}
        )()
        self.sell_calls: list[dict] = []
        self.buy_calls: list[dict] = []

    def get_futures_position(self, symbol):
        return self._position

    def sell(self, symbol, qty, reduce_only, leverage=None):
        self.sell_calls.append({"qty": qty, "reduce_only": reduce_only})
        return OrderModel(
            order_id="close-order-1",
            order_type="market",
            pair=symbol,
            timestamp=1774770587226,
            order_side="sell",
            qty=qty,
            price=1.267,
            status=OrderStatus.FILLED,
            time_in_force="GTC",
            deal_type=DealType.margin_short,
        )

    def buy(self, symbol, qty, reduce_only, leverage=None):
        self.buy_calls.append({"qty": qty, "reduce_only": reduce_only})
        return OrderModel(
            order_id="close-order-1",
            order_type="market",
            pair=symbol,
            timestamp=1774770587226,
            order_side="buy",
            qty=qty,
            price=1.267,
            status=OrderStatus.FILLED,
            time_in_force="GTC",
            deal_type=DealType.margin_short,
        )


class DummyResponse:
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


def make_position_deal(bot, futures_api):
    controller = DummyController()
    position_deal = cast(Any, PositionDeal.__new__(PositionDeal))
    position_deal.active_bot = bot
    position_deal.controller = controller
    position_deal.kucoin_futures_api = futures_api
    position_deal.kucoin_symbol = "BTCUSDTM"
    position_deal.symbol_info = type("SymbolInfo", (), {"futures_leverage": 1})()
    position_deal.price_precision = 4
    position_deal.qty_precision = 0
    return position_deal, controller


def make_long_bot():
    bot = make_mock_bot_active_model()
    bot.market_type = MarketType.FUTURES
    bot.position = Position.long
    bot.margin_short_reversal = True
    bot.pair = "BTCUSDT"
    bot.quote_asset = QuoteAssets.USDT
    bot.fiat = "USDT"
    bot.orders = []
    bot.deal.base_order_size = 68
    bot.deal.opening_price = 1.31
    bot.deal.opening_qty = 68
    bot.deal.opening_timestamp = 1774751364351
    return bot


def test_reverse_position_closes_source_with_reduce_only_and_creates_pending_bot():
    bot = make_long_bot()
    futures_api = DummyFuturesApi(current_qty=68)
    position_deal, controller = make_position_deal(bot, futures_api)

    reversed_bot = PositionDeal.reverse_position(position_deal)

    # New bot is pending with flipped direction and no orders/deal
    assert reversed_bot.position == Position.short
    assert reversed_bot.status == Status.pending
    assert reversed_bot.orders == []
    assert reversed_bot.deal.opening_price == 0

    # Exactly one reduce_only sell was placed to close the long position
    assert len(futures_api.sell_calls) == 1
    assert futures_api.sell_calls[0]["reduce_only"] is True
    assert futures_api.sell_calls[0]["qty"] == 68

    # Source bot was marked completed with closing fields populated
    completed = [s for s in controller.saved if s.status == Status.completed]
    assert len(completed) == 1
    assert completed[0].deal.closing_qty == 68
    assert completed[0].deal.closing_price > 0


def test_reverse_position_short_closes_with_buy():
    bot = make_long_bot()
    bot.position = Position.short
    futures_api = DummyFuturesApi(current_qty=-68)
    position_deal, controller = make_position_deal(bot, futures_api)

    reversed_bot = PositionDeal.reverse_position(position_deal)

    assert reversed_bot.position == Position.long
    assert reversed_bot.status == Status.pending
    assert len(futures_api.buy_calls) == 1
    assert futures_api.buy_calls[0]["reduce_only"] is True
    assert futures_api.buy_calls[0]["qty"] == 68


def test_reverse_position_errors_when_no_position():
    bot = make_long_bot()

    class NoPositionApi(DummyFuturesApi):
        def get_futures_position(self, symbol):
            return None

    futures_api = NoPositionApi()
    position_deal, controller = make_position_deal(bot, futures_api)

    result = PositionDeal.reverse_position(position_deal)

    assert result.status == Status.error
    assert len(futures_api.sell_calls) == 0


def test_reverse_position_errors_when_reduce_only_fails():
    bot = make_long_bot()

    class FailingApi(DummyFuturesApi):
        def sell(self, symbol, qty, reduce_only, leverage=None):
            raise RestError(
                msg="insufficient balance",
                response=DummyResponse(400100, "insufficient balance"),
            )

    futures_api = FailingApi()
    position_deal, controller = make_position_deal(bot, futures_api)

    result = PositionDeal.reverse_position(position_deal)

    assert result.status == Status.error
    # Source bot is NOT marked completed — close failed
    completed = [s for s in controller.saved if s.status == Status.completed]
    assert len(completed) == 0
