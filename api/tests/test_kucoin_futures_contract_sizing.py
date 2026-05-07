from typing import Any, cast
import types

from bots.models import BotModel
from exchange_apis.kucoin.futures.futures_deal import KucoinPositionDeal
from pybinbot import Position


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
    deal.symbol_info = types.SimpleNamespace(qty_precision=qty_precision)
    deal.kucoin_symbol_data = types.SimpleNamespace(multiplier=multiplier)
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
