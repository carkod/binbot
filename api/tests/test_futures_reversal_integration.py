from typing import Any, cast

from bots.models import BotModel, OrderModel
from exchange_apis.kucoin.futures.position_deal import PositionDeal
from pybinbot import DealType, MarketType, OrderStatus, QuoteAssets, Status, Strategy
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
    def __init__(self):
        self._positions = [
            type("pos", (object,), {"current_qty": 68, "mark_price": 1.27})(),
            type("pos", (object,), {"current_qty": -12, "mark_price": 1.267})(),
            type("pos", (object,), {"current_qty": -68, "mark_price": 1.267})(),
        ]
        self.sell_calls: list[float] = []

    def get_futures_position(self, symbol):
        if self._positions:
            return self._positions.pop(0)
        return None

    def sell(self, symbol, qty, reduce_only):
        self.sell_calls.append(qty)
        return OrderModel(
            order_id=f"flip-order-{len(self.sell_calls)}",
            order_type="market",
            pair=symbol,
            timestamp=1774770587226,
            order_side="sell",
            qty=qty,
            price=1.267,
            status=OrderStatus.FILLED,
            time_in_force="GTC",
            deal_type=DealType.base_order,
        )

    def buy(self, symbol, qty, reduce_only):
        return self.sell(symbol=symbol, qty=qty, reduce_only=reduce_only)

    def retrieve_order(self, order_id):
        return type(
            "order",
            (object,),
            {
                "filled_size": 56,
                "avg_deal_price": 1.267,
                "created_at": 1774770587227,
                "type": "market",
                "time_in_force": "GTC",
                "side": "sell",
                "symbol": "BTCUSDTM",
            },
        )()

    def get_fills(self, symbol, start_at, end_at):
        return type("fills", (object,), {"items": []})()


def test_reverse_position_closes_previous_and_opens_new_bot(monkeypatch):
    bot = make_mock_bot_active_model()
    bot.market_type = MarketType.FUTURES
    bot.strategy = Strategy.long
    bot.margin_short_reversal = True
    bot.pair = "BTCUSDT"
    bot.quote_asset = QuoteAssets.USDT
    bot.fiat = "USDT"
    bot.orders = []
    bot.deal.base_order_size = 68
    bot.deal.opening_price = 1.31
    bot.deal.opening_qty = 68
    bot.deal.opening_timestamp = 1774751364351

    controller = DummyController()
    futures_api = DummyFuturesApi()

    position_deal = cast(Any, PositionDeal.__new__(PositionDeal))
    position_deal.active_bot = bot
    position_deal.controller = controller
    position_deal.kucoin_futures_api = futures_api
    position_deal.kucoin_symbol = "BTCUSDTM"
    position_deal.price_precision = 4
    position_deal.qty_precision = 0
    position_deal._is_reversal_possible = lambda mark, current: 80
    position_deal.backfill_position_from_fills = lambda: position_deal.active_bot
    position_deal.update_parameters = lambda: position_deal.active_bot

    monkeypatch.setattr(
        "exchange_apis.kucoin.futures.position_deal.sleep", lambda _: None
    )

    reversed_bot = PositionDeal.reverse_position(position_deal)

    assert reversed_bot.strategy == Strategy.margin_short
    assert reversed_bot.status == Status.active
    assert reversed_bot.deal.base_order_size == 68
    assert reversed_bot.deal.opening_qty == 68
    assert reversed_bot.fiat_order_size == 2.58467999
    assert len(reversed_bot.orders) == 1
    assert reversed_bot.orders[0].qty == 56
    assert reversed_bot.orders[0].deal_type == DealType.base_order
    assert futures_api.sell_calls == [80, 56]

    completed_previous = [
        saved
        for saved in controller.saved
        if saved.id == bot.id and saved.status == Status.completed
    ]
    assert len(completed_previous) > 0
    assert completed_previous[-1].deal.closing_qty == 68
