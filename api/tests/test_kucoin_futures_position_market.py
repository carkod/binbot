from typing import Any, cast
import types

import pandas as pd

from bots.models import BotModel, DealModel
from exchange_apis.kucoin.futures.futures_deal import KucoinPositionDeal
from exchange_apis.kucoin.futures.position_market import PositionMarket
from pybinbot import MarketType, Position


class FakeApexFlowClose:
    def __init__(self, df, btc_df):
        self.df = df
        self.btc_df = btc_df

    def get_detectors(self) -> dict[str, bool]:
        return {"vce": False, "mcd": False, "lcrs": False}

    def get_trend_ema(self) -> tuple[float, float]:
        return 0.0, 0.0


def make_position_market(
    *,
    bot_profit: float = 4.0,
    opening_timestamp: int = 2_000,
    name: str = "test bot",
):
    market = cast(Any, PositionMarket.__new__(PositionMarket))
    market.active_bot = BotModel(
        pair="BTCUSDT",
        name=name,
        market_type=MarketType.FUTURES,
        position=Position.long,
        dynamic_trailing=True,
        trailing=True,
        trailing_profit=0.0,
        trailing_deviation=0.0,
        stop_loss=0.0,
        deal=DealModel(
            opening_price=100.0,
            opening_timestamp=opening_timestamp,
            opening_qty=1.0,
            base_order_size=1.0,
        ),
    )
    market.klines = [
        [1_000, 99.0, 101.0, 98.0, 100.0],
        [2_000, 100.0, 102.0, 99.0, 101.0],
        [3_000, 101.0, 106.0, 100.0, 105.0],
    ]
    market.df = pd.DataFrame(
        [
            {
                "bb_upper": 106.0,
                "bb_mid": 100.0,
                "bb_lower": 98.0,
                "high": 110.0,
                "low": 100.0,
            }
        ]
    )
    market.btc_df = pd.DataFrame([{"close": 1.0}])
    market.base_streaming = types.SimpleNamespace(
        compute_single_bot_profit=lambda bot, price: bot_profit
    )
    market.controller = types.SimpleNamespace(save=lambda data: None)
    market.symbol_data = types.SimpleNamespace(price_precision=2)
    market.build_bb_spreads = lambda: types.SimpleNamespace(
        bb_high=106.0,
        bb_mid=100.0,
        bb_low=98.0,
    )
    market.update_parameters = lambda: market.active_bot
    return market


def test_market_trailing_analytics_keeps_stop_loss_percent_when_pullback_missing(
    monkeypatch,
):
    monkeypatch.setattr(
        "exchange_apis.kucoin.futures.position_market.ApexFlowClose",
        FakeApexFlowClose,
    )
    market = make_position_market(
        bot_profit=1.5,
        opening_timestamp=9_999,
        name="aggressive momo bot",
    )

    market.market_trailing_analytics(current_price=104.0)

    assert market.active_bot.stop_loss == 4.0
    assert market.active_bot.trailing_profit == 3.5
    assert market.active_bot.trailing_deviation == 2.0


def test_derive_dynamic_trailing_params_widens_gap_on_shallow_pullback():
    market = make_position_market(bot_profit=4.0)

    stop_loss, trailing_profit, trailing_deviation = (
        market.derive_dynamic_trailing_params(
            top_spread=5.66,
            bottom_spread=2.0,
            bot_profit=4.0,
            expansion_multiplier=1.0,
            is_aggressive_momo=False,
            expansion_range=10.0,
            trail_tighten_mult=0.7,
            current_price=105.6,
        )
    )

    assert stop_loss == 3.25
    assert trailing_profit == 3.25
    assert trailing_deviation == 1.45
    assert trailing_deviation < trailing_profit


def test_derive_dynamic_trailing_params_tightens_on_deep_pullback():
    market = make_position_market(bot_profit=4.0)

    stop_loss, trailing_profit, trailing_deviation = (
        market.derive_dynamic_trailing_params(
            top_spread=5.66,
            bottom_spread=2.0,
            bot_profit=4.0,
            expansion_multiplier=1.0,
            is_aggressive_momo=False,
            expansion_range=10.0,
            trail_tighten_mult=0.7,
            current_price=104.0,
        )
    )

    assert stop_loss == 2.5
    assert trailing_profit == 2.7
    assert trailing_deviation == 1.29
    assert trailing_deviation < trailing_profit


def test_update_parameters_translates_percent_values_into_prices():
    deal = cast(Any, KucoinPositionDeal.__new__(KucoinPositionDeal))
    deal.price_precision = 2
    deal.cancel_current_sl = lambda: None
    deal.place_stop_loss = lambda: None
    deal.active_bot = BotModel(
        pair="BEATUSDT",
        market_type=MarketType.FUTURES,
        position=Position.long,
        stop_loss=2.5,
        take_profit=2.3,
        trailing=True,
        trailing_profit=2.7,
        trailing_deviation=1.3,
        margin_short_reversal=False,
        deal=DealModel(
            opening_price=100.0,
            opening_qty=1.0,
            trailing_stop_loss_price=95.0,
        ),
    )

    updated_bot = KucoinPositionDeal.update_parameters(deal)

    assert updated_bot.deal.stop_loss_price == 97.5
    assert updated_bot.deal.trailing_profit_price == 102.69
    assert updated_bot.deal.trailing_stop_loss_price == 0
