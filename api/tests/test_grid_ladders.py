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
from grid_ladders.calculations import calculate_grid_levels, calculate_grid_step
from grid_ladders.capital import evaluate_grid_capital
from grid_ladders.models import GridLadderCreate
from grid_ladders.sizing import KucoinGridMarginRules


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


def test_reserves_only_allowed_portion_of_available_balance():
    active_ladders = [_active_ladder("BTCUSDC", reserved_margin=100)]

    decision = evaluate_grid_capital(
        active_ladders,
        available_fiat_balance=1_000,
        requested_margin=200,
    )

    assert decision.allowed_grid_margin == 500
    assert decision.allowed_margin_for_new_ladder == 250

    with pytest.raises(ValueError, match="exceeds allowed margin 250"):
        evaluate_grid_capital(
            active_ladders,
            available_fiat_balance=1_000,
            requested_margin=251,
        )


def test_calculates_fixed_grid_levels_correctly():
    sizer = KucoinGridMarginRules(futures_leverage=1)

    levels = calculate_grid_levels(90, 110, 5, 1000, sizer)

    assert calculate_grid_step(90, 110, 5) == 5
    assert [level.price for level in levels] == [90, 95, 100, 105, 110]
    assert [level.side for level in levels] == ["buy", "buy", "neutral", "sell", "sell"]
    assert [level.take_profit_price for level in levels] == [95, 100, None, 100, 105]


def test_sizes_level_contracts_using_margin_spend_interpretation():
    sizer = KucoinGridMarginRules(futures_leverage=2, multiplier=1, lot_size=1)

    levels = calculate_grid_levels(90, 110, 5, 1000, sizer)

    buy_level = levels[0]
    assert buy_level.contracts == 5
    assert buy_level.margin_required == 225


def test_rejects_ladder_when_per_level_margin_is_too_small():
    sizer = KucoinGridMarginRules(futures_leverage=1, multiplier=1, lot_size=1)

    with pytest.raises(
        ValueError, match="cannot afford the exchange minimum contract size"
    ):
        calculate_grid_levels(90, 110, 5, 10, sizer)


def test_post_grid_ladder_persists_ladder_and_levels(client, monkeypatch):
    balance = type("Balance", (), {"fiat_available": 10_000})()
    accounts = type("Accounts", (), {"get_balance": lambda self: balance})
    monkeypatch.setattr("grid_ladders.routes.ConsolidatedAccounts", accounts)

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
    balance = type("Balance", (), {"fiat_available": 10_000})()
    accounts = type("Accounts", (), {"get_balance": lambda self: balance})
    monkeypatch.setattr("grid_ladders.routes.ConsolidatedAccounts", accounts)

    first = client.post("/grid-ladders", json=_payload())
    second = client.post("/grid-ladders", json=_payload())

    assert first.status_code == 200
    assert second.status_code == 400
    assert "already exists" in second.json()["detail"]


def test_post_grid_ladder_rejects_default_third_active_ladder(client, monkeypatch):
    balance = type("Balance", (), {"fiat_available": 20_000})()
    accounts = type("Accounts", (), {"get_balance": lambda self: balance})
    monkeypatch.setattr("grid_ladders.routes.ConsolidatedAccounts", accounts)

    first = client.post("/grid-ladders", json=_payload("ADAUSDC", 1000))
    second = client.post("/grid-ladders", json=_payload("ADXUSDC", 1000))
    third = client.post("/grid-ladders", json=_payload("EPICUSDC", 1000))

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 400
    assert "max_active_ladders=2" in third.json()["detail"]
