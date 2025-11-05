import pytest
from unittest.mock import MagicMock
from streaming.streaming_controller import StreamingController, BaseStreaming
from streaming.models import HABollinguerSpread
from tools.enum_definitions import Strategy


class DummyBot:
    def __init__(self, strategy=Strategy.long):
        self.strategy = strategy
        self.trailling = False
        self.trailling_profit = 0
        self.trailling_deviation = 0
        self.stop_loss = 0
        self.deal = MagicMock()
        self.deal.base_order_size = 1
        self.deal.opening_price = 100
        self.deal.closing_price = 0
        self.deal.current_price = 100
        self.pair = "BTCUSDT"
        self.fiat = "USDT"
        self.dynamic_trailling = True


@pytest.fixture
def streaming_controller_with_klines(monkeypatch):
    base = BaseStreaming()
    # Patch binance_api.get_raw_klines to return synthetic klines using monkeypatch to avoid mypy error
    monkeypatch.setattr(
        base.binance_api,
        "get_raw_klines",
        MagicMock(
            return_value=[
                [i * 1000, 100 + i, 101 + i, 99 + i, 100 + i, 1000, (i + 1) * 1000]
                for i in range(200)
            ]
        ),
    )
    # Patch out any bot table queries to avoid hitting the real DB
    # Patch get_active_pairs on both controllers to return an empty list
    monkeypatch.setattr(base.bot_controller, "get_active_pairs", lambda *a, **kw: [])
    monkeypatch.setattr(
        base.paper_trading_controller, "get_active_pairs", lambda *a, **kw: []
    )
    controller = StreamingController(base, symbol="BTCUSDT")
    return controller


def test_calc_quantile_volatility_typical(streaming_controller_with_klines):
    controller = streaming_controller_with_klines
    quantile_vol = controller.calc_quantile_volatility(window=40, quantile=0.8)
    assert isinstance(quantile_vol, float)
    assert quantile_vol >= 0


def test_update_bots_parameters_long(monkeypatch, streaming_controller_with_klines):
    controller = streaming_controller_with_klines
    bot = DummyBot(strategy=Strategy.long)
    bb_spreads = HABollinguerSpread(bb_high=110, bb_mid=105, bb_low=100)
    # Patch compute_single_bot_profit to return a fixed value
    monkeypatch.setattr(controller, "compute_single_bot_profit", lambda bot, price: 2)
    # Patch controller.save and SpotLongDeal
    controller.base_streaming.bot_controller.save = MagicMock()
    monkeypatch.setattr("streaming.streaming_controller.SpotLongDeal", MagicMock())
    controller.update_bots_parameters(
        bot=bot,
        db_table=MagicMock(),
        current_price=110,
        bb_spreads=bb_spreads,
    )
    assert bot.trailling
    assert bot.stop_loss >= 0
    assert bot.trailling_profit >= 0
    assert bot.trailling_deviation >= 0


def test_update_bots_parameters_margin_short(
    monkeypatch, streaming_controller_with_klines
):
    controller = streaming_controller_with_klines
    bot = DummyBot(strategy=Strategy.margin_short)
    bb_spreads = HABollinguerSpread(bb_high=110, bb_mid=105, bb_low=100)
    # Patch compute_single_bot_profit to return a fixed value
    monkeypatch.setattr(controller, "compute_single_bot_profit", lambda bot, price: 2)
    # Patch controller.save and MarginDeal
    controller.base_streaming.paper_trading_controller.save = MagicMock()
    monkeypatch.setattr("streaming.streaming_controller.MarginDeal", MagicMock())
    controller.update_bots_parameters(
        bot=bot,
        db_table=MagicMock(),
        current_price=110,
        bb_spreads=bb_spreads,
    )
    assert bot.trailling
    assert bot.stop_loss >= 0
    assert bot.trailling_profit >= 0
    assert bot.trailling_deviation >= 0


def test_calc_quantile_volatility_insufficient_data(streaming_controller_with_klines):
    controller = streaming_controller_with_klines
    # Patch klines to be too short
    controller.klines = controller.klines[:3]
    quantile_vol = controller.calc_quantile_volatility(window=40, quantile=0.8)
    assert quantile_vol == 0.0
