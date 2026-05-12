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
    taker_fee_rate: float = 0.0,
) -> Any:
    deal = cast(Any, KucoinPositionDeal.__new__(KucoinPositionDeal))
    deal.active_bot = BotModel(
        pair="SIRENUSDTM",
        position=Position.short,
        fiat_order_size=fiat_order_size,
        stop_loss=stop_loss,
    )
    deal.symbol_info = types.SimpleNamespace(qty_precision=qty_precision)
    deal.kucoin_symbol_data = types.SimpleNamespace(
        multiplier=multiplier,
        taker_fee_rate=taker_fee_rate,
    )
    deal.kucoin_futures_api = types.SimpleNamespace(
        DEFAULT_MULTIPLIER=1,
        DEFAULT_LEVERAGE=1,
    )
    deal.DEFAULT_FUTURES_LEVERAGE = 1
    return deal


def test_calculate_contracts_treats_fiat_order_size_as_initial_margin():
    """
    fiat_order_size is the margin to commit, so contracts = fos*lev/(price*mult).
    round_numbers floors, so 15/9.3269 ≈ 1.61 → 1.
    """
    deal = make_sizing_deal()

    assert deal.calculate_contracts(fiat_order_size=15, price=0.93269) == 1


def test_contracts_to_fiat_order_size_is_inverse_margin():
    """
    Inverse of the new sizing: 1 contract × 0.93269 price × 10 mult / 1 lev.
    """
    deal = make_sizing_deal()

    assert deal.contracts_to_fiat_order_size(contracts=1, price=0.93269) == 9.3269


def test_calculate_contracts_returns_zero_when_margin_is_below_one_contract():
    deal = make_sizing_deal(fiat_order_size=0.05, multiplier=10.0)

    assert deal.calculate_contracts(fiat_order_size=0.05, price=0.93269) == 0


def test_affordable_contracts_caps_when_fiat_order_size_exceeds_balance():
    """
    The margin-based sizing only exceeds wallet capacity when fiat_order_size
    is misconfigured above the available balance. The cap keeps the order
    placeable rather than rejected by the exchange.
    """
    deal = make_sizing_deal(fiat_order_size=100.0, multiplier=1.0)

    desired = deal.calculate_contracts(fiat_order_size=100.0, price=1.0)
    affordable = deal.affordable_contracts(price=1.0, available_balance=56.9)

    assert desired > affordable, (
        "margin sizing must exceed wallet capacity for this regression"
    )
    assert affordable == 56


def test_affordable_contracts_zero_when_one_contract_unaffordable():
    deal = make_sizing_deal(multiplier=1.0)

    assert deal.affordable_contracts(price=100.0, available_balance=10.0) == 0


def test_affordable_contracts_reserves_round_trip_taker_fees():
    """
    With a non-zero taker fee, affordable contracts must leave room for two
    fills (entry + exit). 100 USDT @ 1.0 with 0.06% taker fee → per-contract
    cost = 1 + 2*0.0006 = 1.0012; floor(100/1.0012) = 99.
    """
    deal = make_sizing_deal(multiplier=1.0, taker_fee_rate=0.0006)

    assert deal.affordable_contracts(price=1.0, available_balance=100.0) == 99
