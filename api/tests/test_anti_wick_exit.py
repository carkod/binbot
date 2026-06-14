"""
Tests for anti-wick exit execution improvements (Phase 1).

Phase 1: reference_price threading through execute_stop_loss / reverse_position
  so that SL closes use the band-capped IOC escalation path instead of a raw
  1-tick cross into a hollow book.

Regression fixture: FHEUSDTM 2026-05-31
  Long opened 0.02343, SL 0.02249 (4% floored).
  14:18 1m candle: low 0.02233, close 0.02235 (wick).
  Actual fill was 0.02235 (the wick low).  With reference_price anchored to the
  last closed 15m candle (0.02252), the band-cap is 0.02247 — a meaningfully
  better fill price.

Note: closed-candle trigger confirmation (Phase 2 / SL_CONFIRM_MODE) was
evaluated via simulation over 14 historical SL exits and found to worsen
aggregate outcomes by ~2.1% (1 clear wick saved, 6 delayed breakdowns).
The phase-2 gate was removed; SL fires on mark-price breach as before.
"""

import types
from typing import Any, cast

import pytest
from bots.models import BotModel, DealModel
from exchange_apis.kucoin.futures.lifecycle import PositionDeal
from pybinbot import MarketType, OrderBase, OrderStatus, DealType, Position


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Raw kline row: [open_time_ms, open, high, low, close, volume, close_time_ms]
# 14:15 15m candle (last fully closed):  close=0.02252 (above SL 0.02249)
_CLOSED_CANDLE_NORMAL = [
    1780236900000,
    0.02279,
    0.02288,
    0.02233,
    0.02252,
    1000,
    1780237799999,
]
# 14:30 15m candle (in-progress at time of SL trigger):
_IN_PROGRESS_CANDLE = [
    1780237800000,
    0.02252,
    0.02255,
    0.02233,
    0.02235,
    500,
    1780238699999,
]

# A klines list where klines[-2] is above the SL (wick scenario)
KLINES_WICK = [_CLOSED_CANDLE_NORMAL, _IN_PROGRESS_CANDLE]

# A klines list where klines[-2] is below the SL (genuine breakdown)
_CLOSED_CANDLE_BREAKDOWN = [
    1780236900000,
    0.02300,
    0.02310,
    0.02200,
    0.02230,
    1000,
    1780237799999,
]
KLINES_BREAKDOWN = [_CLOSED_CANDLE_BREAKDOWN, _IN_PROGRESS_CANDLE]


def _make_fheusdtm_deal(
    *,
    klines=None,
    stop_loss_price: float = 0.02249,
    opening_price: float = 0.02343,
    stop_loss: float = 4.0,
    margin_short_reversal: bool = False,
    position: Position = Position.long,
) -> Any:
    """Minimal PositionDeal stub shaped after the FHEUSDTM production case."""
    deal = cast(Any, PositionDeal.__new__(PositionDeal))
    deal.price_precision = 5
    deal.kucoin_symbol = "FHEUSDTM"
    deal.symbol_info = types.SimpleNamespace(futures_leverage=2)
    deal.active_bot = BotModel(
        pair="FHEUSDTM",
        market_type=MarketType.FUTURES,
        position=position,
        stop_loss=stop_loss,
        take_profit=0.0,
        trailing=False,
        margin_short_reversal=margin_short_reversal,
        deal=DealModel(
            opening_price=opening_price,
            opening_qty=8.0,
            stop_loss_price=stop_loss_price,
            opening_timestamp=1780232436000,  # 14:00 UTC
        ),
    )
    # Pydantic may serialise the enum to its value string; re-assign the
    # enum object so exit() can call .value on it without AttributeError.
    deal.active_bot.position = position
    deal.controller = types.SimpleNamespace(
        save=lambda bot: None,
        update_logs=lambda *args, **kwargs: None,
    )
    deal.klines = klines if klines is not None else KLINES_WICK
    return deal


# ---------------------------------------------------------------------------
# Phase 1 — reference_price flows through to buy/sell in execute_stop_loss
# ---------------------------------------------------------------------------


def test_execute_stop_loss_passes_reference_price_to_sell():
    """
    Phase 1: execute_stop_loss(reference_price=X) must pass reference_price
    through to kucoin_futures_api.sell() for a long position.
    """
    captured: dict = {}

    def fake_sell(symbol, qty, reduce_only, leverage, reference_price=None):
        captured["reference_price"] = reference_price
        return OrderBase(
            order_id="sl-test",
            order_type="limit",
            pair=symbol,
            timestamp=1780237000000,
            order_side="sell",
            qty=qty,
            price=0.02247,
            status=OrderStatus.FILLED,
            time_in_force="IOC",
            deal_type=DealType.stop_loss,
        )

    deal = _make_fheusdtm_deal()
    deal.kucoin_futures_api = types.SimpleNamespace(sell=fake_sell)

    PositionDeal.execute_stop_loss(deal, reference_price=0.02252)

    assert captured.get("reference_price") == pytest.approx(0.02252, abs=1e-6)


def test_execute_stop_loss_passes_reference_price_to_buy_for_short():
    """
    Phase 1: execute_stop_loss(reference_price=X) for a SHORT position must
    pass reference_price through to kucoin_futures_api.buy().
    """
    captured: dict = {}

    def fake_buy(symbol, qty, reduce_only, reference_price=None):
        captured["reference_price"] = reference_price
        return OrderBase(
            order_id="sl-test",
            order_type="limit",
            pair=symbol,
            timestamp=1780237000000,
            order_side="buy",
            qty=qty,
            price=0.02260,
            status=OrderStatus.FILLED,
            time_in_force="IOC",
            deal_type=DealType.stop_loss,
        )

    deal = _make_fheusdtm_deal(position=Position.short, stop_loss_price=0.02334)
    deal.kucoin_futures_api = types.SimpleNamespace(buy=fake_buy)

    PositionDeal.execute_stop_loss(deal, reference_price=0.02245)

    assert captured.get("reference_price") == pytest.approx(0.02245, abs=1e-6)


def test_paper_trading_execute_stop_loss_uses_reference_price_as_fill():
    """
    Paper-trading branch: when reference_price is provided the simulated fill
    price should be reference_price, not the current mark price.
    """
    from databases.crud.paper_trading_crud import PaperTradingTableCrud
    from databases.tables.bot_table import PaperTradingTable

    saved: list[BotModel] = []

    # Subclass PaperTradingTableCrud so isinstance() checks pass, but override
    # the DB-touching methods to avoid any real database calls.
    class PaperCtrlStub(PaperTradingTableCrud):
        def __init__(self) -> None:
            pass  # skip real __init__ that opens a DB session

        def save(self, bot: BotModel) -> PaperTradingTable:
            saved.append(bot)
            return cast(PaperTradingTable, None)

        def update_logs(self, *args: Any, **kwargs: Any) -> PaperTradingTable:
            return cast(PaperTradingTable, None)

    deal = _make_fheusdtm_deal()
    deal.controller = PaperCtrlStub()
    deal.active_bot.deal.current_price = 0.0224  # the wick low

    PositionDeal.execute_stop_loss(deal, reference_price=0.02252)

    assert len(saved) > 0
    closing_price = saved[-1].deal.closing_price
    # Should use reference_price (0.02252) not the wick mark (0.0224)
    assert closing_price == pytest.approx(0.02252, abs=1e-5)


def test_reverse_position_passes_reference_price_to_close_leg():
    """
    Phase 1: reverse_position(reference_price=X) must pass reference_price
    through to the reduce-only sell/buy call that closes the current position.
    """
    captured: dict = {}

    def fake_sell(symbol, qty, reduce_only, leverage, reference_price=None):
        captured["reference_price"] = reference_price
        return OrderBase(
            order_id="rev-close",
            order_type="limit",
            pair=symbol,
            timestamp=1780247000000,
            order_side="sell",
            qty=qty,
            price=0.02247,
            status=OrderStatus.FILLED,
            time_in_force="IOC",
            deal_type=DealType.margin_short,
        )

    deal = _make_fheusdtm_deal()
    # Stub the exchange position query
    deal.kucoin_futures_api = types.SimpleNamespace(
        sell=fake_sell,
        get_futures_position=lambda symbol: types.SimpleNamespace(current_qty=8.0),
    )
    # Stub the DB create so the new pending bot is created without a real DB
    deal.controller = types.SimpleNamespace(
        save=lambda bot: None,
        update_logs=lambda *a, **kw: None,
        create=lambda bot: BotModel(**bot.model_dump()),
    )

    PositionDeal.reverse_position(deal, reference_price=0.02252)

    assert captured.get("reference_price") == pytest.approx(0.02252, abs=1e-6)
