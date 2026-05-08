from typing import Any, cast
import types

import pytest
from bots.models import BotModel
from exchange_apis.kucoin.futures.futures_deal import KucoinPositionDeal
from pybinbot import BinbotErrors, Position


def make_sizing_deal(
    *,
    fiat_order_size: float = 15.0,
    stop_loss: float = 6.43252,
    multiplier: float = 10.0,
    qty_precision: int = 0,
) -> Any:
    deal = cast(Any, KucoinPositionDeal.__new__(KucoinPositionDeal))
    deal.active_bot = BotModel(
        pair="SIRENUSDTM",
        position=Position.short,
        fiat_order_size=fiat_order_size,
        stop_loss=stop_loss,
    )
    deal.symbol_info = types.SimpleNamespace(
        qty_precision=qty_precision,
        futures_leverage=1,
    )
    deal.kucoin_symbol_data = types.SimpleNamespace(
        multiplier=multiplier,
        taker_fee_rate=0.0006,
        lot_size=1,
        mark_price=0.93269,
    )
    deal.kucoin_futures_api = types.SimpleNamespace(
        DEFAULT_MULTIPLIER=1,
        DEFAULT_LEVERAGE=1,
    )
    return deal


def test_calculate_contracts_uses_stop_loss_as_percent_risk_budget():
    deal = make_sizing_deal()

    assert deal.calculate_contracts(balance=15, price=0.93269) == 25


def test_contracts_to_fiat_order_size_is_inverse_risk_budget():
    deal = make_sizing_deal()

    assert deal.contracts_to_fiat_order_size(contracts=25, price=0.93269) == 14.99886769


def test_calculate_contracts_returns_zero_when_risk_budget_is_below_one_contract():
    deal = make_sizing_deal(fiat_order_size=0.5)

    assert deal.calculate_contracts(balance=0.5, price=0.93269) == 0


def test_required_margin_uses_position_notional_and_leverage():
    deal = make_sizing_deal(multiplier=10)

    assert deal.required_margin_for_contracts(contracts=100, price=10) == 10012


def test_base_order_rejects_when_required_margin_exceeds_available_balance():
    class DummyFuturesApi:
        DEFAULT_MULTIPLIER = 1
        DEFAULT_LEVERAGE = 1

        def matching_engine(self, symbol, side, size):
            return 10

        def sell(self, symbol, qty, leverage):
            raise AssertionError("base_order should reject before placing an order")

    deal = make_sizing_deal(fiat_order_size=100, stop_loss=1, multiplier=10)
    deal.active_bot.fiat = "USDT"
    deal.fiat = "USDT"
    deal.kucoin_symbol = "TESTUSDTM"
    deal.kucoin_futures_api = DummyFuturesApi()
    deal.compute_available_balance = lambda: 1000

    with pytest.raises(BinbotErrors, match="Required futures margin"):
        KucoinPositionDeal.base_order(deal)
