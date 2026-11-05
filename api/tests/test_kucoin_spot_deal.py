from typing import Any, cast
from unittest.mock import Mock, sentinel

from pybinbot import BotModel, Position, QuoteAssets

from api.exchange_apis.kucoin.deals.spot_deal import SpotDeal


def test_buy_quote_uses_available_trade_balance():
    deal = cast(Any, SpotDeal.__new__(SpotDeal))
    deal.active_bot = BotModel(
        pair="BTCUSDT", position=Position.long, quote_asset=QuoteAssets.USDT
    )
    deal.symbol = "BTC-USDT"
    deal.qty_precision = 2
    deal.compute_balance = Mock(return_value=({"trade": {"USDT": 20.0}}, 20.0, 0.0))
    deal.kucoin_api = Mock()
    deal.kucoin_api.get_ticker_price.return_value = 10.0
    deal.kucoin_api.buy_order.return_value = sentinel.order

    assert deal.buy_quote_with_available_balance() is sentinel.order
    deal.kucoin_api.buy_order.assert_called_once_with(symbol="BTC-USDT", qty=2.0)
