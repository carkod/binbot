from typing import Any, cast

from pybinbot import BotModel, DealModel, MarketType, Position

from streaming.base import BaseStreaming


def make_streaming() -> BaseStreaming:
    return cast(Any, BaseStreaming.__new__(BaseStreaming))


def make_futures_bot(position: Position, opening_price: float = 100.0) -> BotModel:
    return BotModel(
        pair="BTCUSDTM",
        name="test bot",
        market_type=MarketType.FUTURES,
        position=position,
        deal=DealModel(
            opening_price=opening_price,
            opening_qty=1.0,
            base_order_size=1.0,
        ),
    )


def test_compute_single_bot_profit_positive_for_long_when_price_rises():
    streaming = make_streaming()
    bot = make_futures_bot(Position.long)

    profit = streaming.compute_single_bot_profit(bot, current_price=110.0)

    assert profit == 10.0


def test_compute_single_bot_profit_negative_for_long_when_price_falls():
    streaming = make_streaming()
    bot = make_futures_bot(Position.long)

    profit = streaming.compute_single_bot_profit(bot, current_price=90.0)

    assert profit == -10.0


def test_compute_single_bot_profit_positive_for_short_when_price_falls():
    """A futures short profits when price falls — before the direction fix,
    this returned the raw (unflipped) negative return here, which would have
    silently broken the profit-based trailing-tighten schedule once shorts
    started running through market_trailing_analytics."""
    streaming = make_streaming()
    bot = make_futures_bot(Position.short)

    profit = streaming.compute_single_bot_profit(bot, current_price=90.0)

    assert profit == 10.0


def test_compute_single_bot_profit_negative_for_short_when_price_rises():
    streaming = make_streaming()
    bot = make_futures_bot(Position.short)

    profit = streaming.compute_single_bot_profit(bot, current_price=110.0)

    assert profit == -10.0
