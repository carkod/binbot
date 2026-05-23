from uuid import uuid4

import pytest
from pydantic import ValidationError
from pybinbot import ExchangeId, GridLadderStatus, MarketType
from sqlmodel import Session, delete

from databases.tables.grid_ladder_table import (
    GridLadderTable,
    GridLevelTable,
    GridOrderTable,
)
from grid_ladders.calculations import calculate_grid_levels
from grid_ladders.capital import evaluate_grid_capital
from grid_ladders.models import GridLadderCreate
from grid_ladders.routes import GridContractMeta
from grid_ladders.sizing import KucoinGridMarginRules


def _fake_meta(
    multiplier: float = 1.0,
    lot_size: float = 1.0,
    qty_precision: int = 0,
    taker_fee_rate: float = 0.0,
    min_notional: float = 0.0,
) -> GridContractMeta:
    return GridContractMeta(
        multiplier=multiplier,
        lot_size=lot_size,
        qty_precision=qty_precision,
        taker_fee_rate=taker_fee_rate,
        min_notional=min_notional,
    )


def _patch_contract_meta(monkeypatch, meta: GridContractMeta | None = None) -> None:
    monkeypatch.setattr(
        "grid_ladders.routes._fetch_kucoin_futures_contract_meta",
        lambda symbol_row: meta or _fake_meta(),
    )


def _patch_balance(monkeypatch, fiat_available: float) -> None:
    balance = type("Balance", (), {"fiat_available": fiat_available})()

    class Accounts:
        def __init__(self, *args, **kwargs):
            pass

        def get_balance(self):
            return balance

    monkeypatch.setattr("grid_ladders.routes.ConsolidatedAccounts", Accounts)


@pytest.fixture(autouse=True)
def clean_grid_ladders(create_test_tables):
    with Session(create_test_tables) as session:
        session.exec(delete(GridOrderTable))
        session.exec(delete(GridLevelTable))
        session.exec(delete(GridLadderTable))
        session.commit()
    yield
    with Session(create_test_tables) as session:
        session.exec(delete(GridOrderTable))
        session.exec(delete(GridLevelTable))
        session.exec(delete(GridLadderTable))
        session.commit()


def _payload(symbol: str = "ADAUSDC", total_margin: float = 1000) -> dict:
    return {
        "symbol": symbol,
        "fiat": "USDC",
        "exchange": "kucoin",
        "algorithm_name": "fixed_grid",
        "range_low": 90,
        "range_high": 110,
        "level_count": 5,
        "total_margin": total_margin,
        "breakout_low": 85,
        "breakout_high": 115,
        "context": {"note": "test grid"},
    }


def _active_ladder(symbol: str, reserved_margin: float = 100) -> GridLadderTable:
    return GridLadderTable(
        id=uuid4(),
        symbol=symbol,
        fiat="USDC",
        exchange=ExchangeId.KUCOIN,
        market_type=MarketType.FUTURES,
        algorithm_name="fixed_grid",
        status=GridLadderStatus.active,
        range_low=90,
        range_high=110,
        grid_step=5,
        level_count=5,
        total_margin=reserved_margin,
        reserved_margin=reserved_margin,
        breakout_low=85,
        breakout_high=115,
    )


@pytest.mark.parametrize(
    "field,value,error_text",
    [
        ("level_count", 2, "greater than or equal to 3"),
        ("range_low", 110, "range_low must be less than range_high"),
        ("total_margin", 0, "greater than 0"),
        ("breakout_low", 90, "breakout_low must be less than range_low"),
        ("breakout_high", 110, "breakout_high must be greater than range_high"),
    ],
)
def test_grid_ladder_create_rejects_invalid_business_rules(field, value, error_text):
    data = _payload()
    data[field] = value

    with pytest.raises(ValidationError) as exc_info:
        GridLadderCreate(**data)

    assert error_text in str(exc_info.value)


def test_rejects_fourth_active_ladder_when_hard_max_is_used():
    active_ladders = [
        _active_ladder("BTCUSDC"),
        _active_ladder("ETHUSDC"),
        _active_ladder("SOLUSDC"),
    ]

    with pytest.raises(ValueError, match="max_active_ladders=3"):
        evaluate_grid_capital(
            active_ladders,
            available_fiat_balance=10_000,
            requested_margin=100,
            max_active_ladders=3,
        )


def test_allows_full_grid_budget_while_keeping_per_ladder_cap():
    active_ladders = [_active_ladder("BTCUSDC", reserved_margin=100)]

    decision = evaluate_grid_capital(
        active_ladders,
        available_fiat_balance=1_000,
        requested_margin=200,
    )

    assert decision.available_after_cash_reserve == 1000
    assert decision.allowed_grid_margin == 1000
    assert decision.allowed_margin_for_new_ladder == 250

    with pytest.raises(ValueError, match="exceeds allowed margin 250"):
        evaluate_grid_capital(
            active_ladders,
            available_fiat_balance=1_000,
            requested_margin=251,
        )


def test_calculates_fixed_grid_levels_correctly():
    sizer = KucoinGridMarginRules(futures_leverage=1)

    calculated = calculate_grid_levels(90, 110, 5, 1000, sizer)

    assert calculated.grid_step == 5
    assert [level.price for level in calculated.levels] == [90, 95, 100, 105, 110]
    assert [level.side for level in calculated.levels] == [
        "buy",
        "buy",
        "neutral",
        "sell",
        "sell",
    ]
    assert [level.take_profit_price for level in calculated.levels] == [
        95,
        100,
        None,
        100,
        105,
    ]


def test_sizes_level_contracts_using_margin_spend_interpretation():
    sizer = KucoinGridMarginRules(futures_leverage=2, multiplier=1, lot_size=1)

    calculated = calculate_grid_levels(90, 110, 5, 1000, sizer)

    buy_level = calculated.levels[0]
    assert buy_level.contracts == 5
    assert buy_level.margin_required == 225


def test_rejects_ladder_when_per_level_margin_is_too_small():
    sizer = KucoinGridMarginRules(futures_leverage=1, multiplier=1, lot_size=1)

    with pytest.raises(
        ValueError, match="cannot afford the exchange minimum contract size"
    ):
        calculate_grid_levels(90, 110, 5, 10, sizer)


def test_post_grid_ladder_persists_ladder_and_levels(client, monkeypatch):
    _patch_balance(monkeypatch, 10_000)
    _patch_contract_meta(monkeypatch)

    response = client.post("/grid-ladders", json=_payload())

    assert response.status_code == 200
    body = response.json()
    ladder = body["detail"]
    assert ladder["symbol"] == "ADAUSDC"
    assert ladder["status"] == "pending"
    assert ladder["grid_step"] == 5
    assert len(ladder["levels"]) == 5
    assert [level["side"] for level in ladder["levels"]] == [
        "buy",
        "buy",
        "neutral",
        "sell",
        "sell",
    ]


def test_post_grid_ladder_rejects_second_active_ladder_for_same_symbol(
    client, monkeypatch
):
    _patch_balance(monkeypatch, 10_000)
    _patch_contract_meta(monkeypatch)

    first = client.post("/grid-ladders", json=_payload())
    second = client.post("/grid-ladders", json=_payload())

    assert first.status_code == 200
    assert second.status_code == 400
    assert "already exists" in second.json()["detail"]


def test_post_grid_ladder_rejects_default_third_active_ladder(client, monkeypatch):
    _patch_balance(monkeypatch, 20_000)
    _patch_contract_meta(monkeypatch)

    first = client.post("/grid-ladders", json=_payload("ADAUSDC", 1000))
    second = client.post("/grid-ladders", json=_payload("ADXUSDC", 1000))
    third = client.post("/grid-ladders", json=_payload("EPICUSDC", 1000))

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 400
    assert "max_active_ladders=2" in third.json()["detail"]


def test_post_grid_ladder_uses_per_symbol_contract_metadata(client, monkeypatch):
    """
    The sizer must use the real lot_size / multiplier from the symbol,
    not hard-coded 1's — otherwise contract sizing is off by 10–100x
    on KuCoin futures pairs.
    """
    _patch_balance(monkeypatch, 40_000)
    _patch_contract_meta(
        monkeypatch,
        _fake_meta(multiplier=10.0, lot_size=1.0),
    )

    # total_margin=5000 → per_level_margin=1250. With multiplier=10,
    # leverage=1, the most-expensive level (price 110) needs 1100 margin
    # per contract → 1 contract per active level.
    response = client.post("/grid-ladders", json=_payload(total_margin=5000))

    assert response.status_code == 200, response.json()
    levels = response.json()["detail"]["levels"]
    buy_level = next(level for level in levels if level["side"] == "buy")
    # Notional reflects the multiplier (1 contract * 90 price * 10 mult = 900).
    assert buy_level["contracts"] == 1
    assert buy_level["margin_required"] == 900


def test_sizer_snaps_contracts_to_lot_size():
    """
    KuCoin rejects partial lots. Sizer must floor to a multiple of lot_size.
    """
    sizer = KucoinGridMarginRules(
        futures_leverage=1,
        multiplier=1,
        lot_size=100,
    )

    # 250 budget at price 90, lot=100: per-lot margin = 9000, so 0 lots fit.
    assert sizer.max_contracts_for_margin(250, 90) == 0

    # 18000 budget: 2 lots @ 9000 each fit exactly.
    assert sizer.max_contracts_for_margin(18_000, 90) == 200


def test_sizer_rejects_when_below_min_notional():
    sizer = KucoinGridMarginRules(
        futures_leverage=1,
        multiplier=1,
        lot_size=1,
        min_notional=1_000,
    )

    # 1 contract at price 100 = notional 100 < 1000 min_notional.
    assert sizer.max_contracts_for_margin(500, 100) == 0


def test_post_grid_ladder_close_persists_reason(client, monkeypatch):
    _patch_balance(monkeypatch, 10_000)
    _patch_contract_meta(monkeypatch)

    created = client.post("/grid-ladders", json=_payload())
    assert created.status_code == 200
    ladder_id = created.json()["detail"]["id"]

    closed = client.post(
        f"/grid-ladders/{ladder_id}/close",
        json={"reason": "breakout_high_hit"},
    )

    assert closed.status_code == 200
    detail = closed.json()["detail"]
    assert detail["status"] == "closed"
    assert detail["closed_at"] is not None
    assert detail["context"]["close_reason"] == "breakout_high_hit"


def test_grid_ladder_active_unique_constraint(create_test_tables):
    """
    Two ladders in active statuses for the same symbol must violate the
    partial unique index even if the API-level check is bypassed.
    """
    from sqlalchemy.exc import IntegrityError

    with Session(create_test_tables) as session:
        session.add(_active_ladder("ZZZUSDC"))
        session.commit()

        session.add(_active_ladder("ZZZUSDC"))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_grid_ladder_active_unique_allows_reopen_after_close(create_test_tables):
    """
    A closed ladder must not block a new active ladder on the same symbol.
    """
    with Session(create_test_tables) as session:
        closed = _active_ladder("ZZYUSDC")
        closed.status = GridLadderStatus.closed
        session.add(closed)
        session.commit()

        session.add(_active_ladder("ZZYUSDC"))
        session.commit()


@pytest.mark.parametrize("even_count", [4, 6, 8])
def test_grid_ladder_create_rejects_even_level_count(even_count):
    data = _payload()
    data["level_count"] = even_count

    with pytest.raises(ValidationError, match="level_count must be odd"):
        GridLadderCreate(**data)


def test_post_grid_ladder_rejects_spot_market_type(client, monkeypatch):
    _patch_balance(monkeypatch, 10_000)
    _patch_contract_meta(monkeypatch)

    payload = _payload()
    payload["market_type"] = "SPOT"

    response = client.post("/grid-ladders", json=payload)

    assert response.status_code == 400
    assert "FUTURES" in response.json()["detail"]


def test_post_grid_ladder_rejects_non_kucoin_exchange(client, monkeypatch):
    _patch_balance(monkeypatch, 10_000)
    _patch_contract_meta(monkeypatch)

    payload = _payload()
    payload["exchange"] = "binance"

    response = client.post("/grid-ladders", json=payload)

    assert response.status_code == 400
    assert "KuCoin" in response.json()["detail"]
