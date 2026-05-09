from typing import Any, cast
import types

from bots.models import BotModel
from exchange_apis.kucoin.deals.base import KucoinBaseBalance
from exchange_apis.kucoin.futures.futures_deal import KucoinPositionDeal
from pybinbot import DealType, OrderBase, OrderStatus, Position
from streaming.base import BaseStreaming


def make_sizing_deal(
    *,
    fiat_order_size: float = 15.0,
    stop_loss: float = 6.43252,
    multiplier: float = 10.0,
    qty_precision: int = 0,
    lot_size: float = 1,
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
        lot_size=lot_size,
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


def test_constructor_reuses_injected_base_streaming(monkeypatch):
    """Streaming deal construction must not create another BaseStreaming."""

    def base_balance_init(self):
        self.config = types.SimpleNamespace(
            kucoin_key="key",
            kucoin_secret="secret",
            kucoin_passphrase="passphrase",
        )
        self.autotrade_settings = types.SimpleNamespace(fiat="USDT")
        self.fiat = "USDT"

    class DummyFuturesApi:
        DEFAULT_LEVERAGE = 1

        def __init__(self, *args, **kwargs):
            pass

        def get_symbol_info(self, symbol):
            return types.SimpleNamespace(multiplier=1, lot_size=1)

    class DummySymbolsCrud:
        def get_symbol(self, symbol):
            return types.SimpleNamespace(
                futures_leverage=1,
                price_precision=4,
                qty_precision=0,
            )

    class DummyBotCrud:
        pass

    class ExplodingBaseStreaming:
        def __init__(self):
            raise AssertionError("unexpected BaseStreaming construction")

    monkeypatch.setattr(KucoinBaseBalance, "__init__", base_balance_init)
    monkeypatch.setattr(
        "exchange_apis.kucoin.futures.futures_deal.KucoinFutures",
        DummyFuturesApi,
    )
    monkeypatch.setattr(
        "exchange_apis.kucoin.futures.futures_deal.SymbolsCrud",
        DummySymbolsCrud,
    )
    monkeypatch.setattr(
        "exchange_apis.kucoin.futures.futures_deal.BotTableCrud",
        DummyBotCrud,
    )
    monkeypatch.setattr(
        "exchange_apis.kucoin.futures.futures_deal.BaseStreaming",
        ExplodingBaseStreaming,
    )

    base_streaming = cast(BaseStreaming, types.SimpleNamespace())
    bot = BotModel(pair="SIRENUSDTM", position=Position.short)

    deal = KucoinPositionDeal(bot=bot, base_streaming=base_streaming)

    assert deal.base_streaming is base_streaming


def test_contracts_to_fiat_order_size_is_inverse_risk_budget():
    deal = make_sizing_deal()

    assert deal.contracts_to_fiat_order_size(contracts=25, price=0.93269) == 14.99886769


def test_calculate_contracts_returns_zero_when_risk_budget_is_below_one_contract():
    deal = make_sizing_deal(fiat_order_size=0.5)

    assert deal.calculate_contracts(balance=0.5, price=0.93269) == 0


def test_required_margin_uses_position_notional_and_leverage():
    deal = make_sizing_deal(multiplier=10)

    assert deal.required_margin_for_contracts(contracts=100, price=10) == 10012


def test_reversal_margin_check_does_not_double_count_lot_size():
    deal = make_sizing_deal(multiplier=1, lot_size=5)
    deal.compute_available_balance = lambda: 60

    assert deal._is_reversal_possible(mark_price=10, current_contracts=10) == 15


def test_base_order_downsizes_when_risk_size_exceeds_available_margin():
    class DummyFuturesApi:
        DEFAULT_MULTIPLIER = 1
        DEFAULT_LEVERAGE = 1

        def __init__(self):
            self.sell_calls: list[int] = []

        def matching_engine(self, symbol, side, size):
            return 10

        def sell(self, symbol, qty, leverage):
            self.sell_calls.append(qty)
            return OrderBase(
                order_id="base-order-1",
                order_type="limit",
                pair=symbol,
                timestamp=1775008219262,
                order_side="sell",
                qty=qty,
                price=10,
                status=OrderStatus.FILLED,
                time_in_force="GTC",
                deal_type=DealType.base_order,
            )

        def get_futures_position(self, symbol):
            return types.SimpleNamespace(mark_price=10)

    deal = make_sizing_deal(fiat_order_size=100, stop_loss=1, multiplier=10)
    deal.active_bot.fiat = "USDT"
    deal.fiat = "USDT"
    deal.kucoin_symbol = "TESTUSDTM"
    deal.kucoin_futures_api = DummyFuturesApi()
    deal.controller = types.SimpleNamespace(
        update_logs=lambda **kwargs: None,
        save=lambda bot: bot,
    )
    deal.compute_available_balance = lambda: 1000

    opened_bot = KucoinPositionDeal.base_order(deal)

    assert deal.kucoin_futures_api.sell_calls == [9]
    assert opened_bot.deal.base_order_size == 9
    assert opened_bot.deal.opening_qty == 9
    assert any(
        "Futures order downsized from 100 to 9" in log for log in opened_bot.logs
    )
