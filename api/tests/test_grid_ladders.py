from time import time
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from kucoin_universal_sdk.generate.futures.order.model_get_order_by_order_id_resp import (
    GetOrderByOrderIdResp,
)
from pydantic import ValidationError
from pybinbot import (
    DealType,
    ExchangeId,
    GridLadderStatus,
    MarketType,
    OrderBase,
    OrderStatus,
)
from sqlmodel import Session, delete

from databases.crud.grid_ladder_crud import GridLadderCrud
from databases.tables.bot_table import BotTable
from databases.tables.deal_table import DealTable
from databases.tables.grid_ladder_table import (
    GridLadderTable,
    GridLevelTable,
    GridOrderTable,
)
from grid_ladders.calculations import calculate_grid_levels
from grid_ladders.capital import GridCapitalSettings
from grid_ladders.lifecycle import GridLadderLifecycle
from grid_ladders.models import GridLadderCreate
from grid_ladders.routes import GridContractMeta
from grid_ladders.sizing import KucoinGridMarginRules


def _order_details(
    *,
    status: GetOrderByOrderIdResp.StatusEnum = GetOrderByOrderIdResp.StatusEnum.OPEN,
    filled_size: int = 0,
    avg_deal_price: float = 0,
    price: float = 0,
) -> GetOrderByOrderIdResp:
    return GetOrderByOrderIdResp(
        status=status,
        filled_size=filled_size,
        avg_deal_price=str(avg_deal_price),
        price=str(price),
    )


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


class FakeFuturesApi:
    def __init__(self):
        self.orders: list[dict] = []
        self.cancelled_symbols: list[str] = []
        self.position_qty = 0
        self.position_unrealized_pnl: float = 0
        self.position_mark_price: float | None = None
        self.raise_on_order = False
        self.fail_on_call: int | None = None
        self._counter = 0
        self.order_details: dict[str, GetOrderByOrderIdResp] = {}
        self.retrieved_order_ids: list[str] = []

    def place_futures_order(self, **kwargs):
        if self.raise_on_order or self.fail_on_call == self._counter + 1:
            raise RuntimeError("exchange rejected order")
        self._counter += 1
        order_id = f"grid-order-{self._counter}"
        self.orders.append({"order_id": order_id, **kwargs})
        return OrderBase(
            order_type=kwargs["order_type"].value,
            time_in_force="GTC",
            timestamp=123,
            order_id=order_id,
            order_side=kwargs["side"].value,
            pair=kwargs["symbol"],
            qty=kwargs["size"],
            status="NEW",
            price=kwargs.get("price") or 0,
            deal_type=DealType.base_order,
        )

    def retrieve_order(self, order_id: str):
        self.retrieved_order_ids.append(order_id)
        return self.order_details.get(
            order_id,
            _order_details(),
        )

    def cancel_all_futures_orders(self, symbol: str):
        self.cancelled_symbols.append(symbol)
        return ["cancelled"]

    def get_futures_position(self, symbol: str):
        return SimpleNamespace(
            current_qty=self.position_qty,
            unrealized_pnl=self.position_unrealized_pnl,
            mark_price=self.position_mark_price,
        )

    def get_symbol_info(self, symbol: str):
        return SimpleNamespace(multiplier=1)


def _grid_base(fake_api: FakeFuturesApi):
    return SimpleNamespace(kucoin_futures_api=fake_api)


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


def test_rejects_fourth_active_ladder_when_hard_max_is_used(monkeypatch):
    active_ladders = [
        _active_ladder("BTCUSDC"),
        _active_ladder("ETHUSDC"),
        _active_ladder("SOLUSDC"),
    ]
    monkeypatch.setattr(
        "grid_ladders.capital.AutotradeCrud.get_settings",
        lambda self: SimpleNamespace(
            grid_max_active_ladders=3,
            grid_allocation_pct=1.0,
            grid_cash_reserve_pct=0.0,
        ),
    )
    with pytest.raises(ValueError, match="max_active_ladders=3"):
        GridCapitalSettings().evaluate_grid_capital(
            active_ladders,
            available_fiat_balance=10_000,
            requested_margin=100,
        )


def test_allows_full_grid_budget_while_keeping_per_ladder_cap(monkeypatch):
    active_ladders = [_active_ladder("BTCUSDC", reserved_margin=100)]
    monkeypatch.setattr(
        "grid_ladders.capital.AutotradeCrud.get_settings",
        lambda self: SimpleNamespace(
            grid_max_active_ladders=3,
            grid_allocation_pct=1.0,
            grid_cash_reserve_pct=0.0,
        ),
    )
    settings = GridCapitalSettings()

    decision = settings.evaluate_grid_capital(
        active_ladders,
        available_fiat_balance=1_000,
        requested_margin=200,
    )

    assert decision.available_after_cash_reserve == 1000
    assert decision.allowed_grid_margin == 1000
    assert decision.allowed_margin_for_new_ladder == 250

    with pytest.raises(ValueError, match="exceeds allowed margin 250"):
        settings.evaluate_grid_capital(
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


def test_grid_levels_round_prices_to_symbol_data_precision():
    sizer = KucoinGridMarginRules(
        futures_leverage=1,
        multiplier=1,
        lot_size=1,
        price_precision=5,
    )

    calculated = calculate_grid_levels(0.010003, 0.010061, 5, 10, sizer)

    assert [level.price for level in calculated.levels] == [
        0.01000,
        0.01001,
        0.01003,
        0.01004,
        0.01006,
    ]
    assert [level.take_profit_price for level in calculated.levels] == [
        0.01001,
        0.01003,
        None,
        0.01003,
        0.01004,
    ]


def test_grid_rejects_levels_that_collapse_after_symbol_data_rounding():
    sizer = KucoinGridMarginRules(
        futures_leverage=1,
        multiplier=1,
        lot_size=1,
        price_precision=2,
    )

    with pytest.raises(ValueError, match="collapse after symbol price precision"):
        calculate_grid_levels(1.001, 1.009, 5, 1000, sizer)


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
    assert ladder["used_margin"] == 0
    assert len(ladder["levels"]) == 5
    assert [level["side"] for level in ladder["levels"]] == [
        "buy",
        "buy",
        "neutral",
        "sell",
        "sell",
    ]


def test_post_grid_ladder_rejects_second_active_ladder_for_same_symbol(
    client, monkeypatch, create_test_tables
):
    _patch_balance(monkeypatch, 10_000)
    _patch_contract_meta(monkeypatch)

    first = client.post("/grid-ladders", json=_payload())
    second = client.post("/grid-ladders", json=_payload())

    assert first.status_code == 200
    assert second.status_code == 400
    assert "already exists" in second.json()["detail"]
    with Session(create_test_tables) as session:
        ladder = GridLadderCrud(session).get_active_for_symbol("ADAUSDC")
        assert ladder is not None
        assert any("Rejected grid ladder create" in log for log in ladder.logs)


def test_post_grid_ladder_rejects_active_bot_for_same_symbol_and_logs(
    client, monkeypatch, create_test_tables
):
    _patch_balance(monkeypatch, 10_000)
    _patch_contract_meta(monkeypatch)
    bot_id = UUID("22222222-2222-2222-2222-222222222222")

    with Session(create_test_tables) as session:
        bot = BotTable(
            id=bot_id,
            pair="QNTUSDTM",
            fiat="USDC",
            market_type=MarketType.FUTURES,
            name="active_futures_bot",
            status="active",
            deal=DealTable(),
        )
        session.add(bot)
        session.commit()

    response = client.post("/grid-ladders", json=_payload("QNTUSDTM"))

    assert response.status_code == 400
    assert "active or pending bot" in response.json()["detail"]
    with Session(create_test_tables) as session:
        bot = session.get(BotTable, bot_id)
        assert bot is not None
        assert any("Rejected grid ladder create" in log for log in bot.logs)


def test_post_grid_ladder_rejects_pending_bot_for_same_symbol_and_logs(
    client, monkeypatch, create_test_tables
):
    _patch_balance(monkeypatch, 10_000)
    _patch_contract_meta(monkeypatch)
    bot_id = UUID("33333333-3333-3333-3333-333333333333")

    with Session(create_test_tables) as session:
        bot = BotTable(
            id=bot_id,
            pair="PNDUSDTM",
            fiat="USDC",
            market_type=MarketType.FUTURES,
            name="pending_reversal_bot",
            status="pending",
            deal=DealTable(),
        )
        session.add(bot)
        session.commit()

    response = client.post("/grid-ladders", json=_payload("PNDUSDTM"))

    assert response.status_code == 400
    assert "active or pending bot" in response.json()["detail"]
    with Session(create_test_tables) as session:
        bot = session.get(BotTable, bot_id)
        assert bot is not None
        assert any("Rejected grid ladder create" in log for log in bot.logs)


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


def test_grid_lifecycle_places_initial_entry_orders(
    client, monkeypatch, create_test_tables
):
    _patch_balance(monkeypatch, 10_000)
    _patch_contract_meta(monkeypatch)
    response = client.post("/grid-ladders", json=_payload())
    assert response.status_code == 200

    fake_api = FakeFuturesApi()
    with Session(create_test_tables) as session:
        GridLadderLifecycle(_grid_base(fake_api), session).process_symbol("ADAUSDC")

    assert len(fake_api.orders) == 4

    refreshed = client.get(f"/grid-ladders/{response.json()['detail']['id']}")
    detail = refreshed.json()["detail"]
    assert detail["status"] == "active"
    entry_levels = [level for level in detail["levels"] if level["side"] != "neutral"]
    assert len(detail["orders"]) == 4
    assert "raw" + "_response" not in detail["orders"][0]
    assert all(level["status"] == "open" for level in entry_levels)
    assert all(level["entry_order_id"] for level in entry_levels)
    assert len(detail["logs"]) == 4
    assert "Placed entry order grid-order-1" in detail["logs"][0]


def test_grid_lifecycle_rounds_pending_ladder_prices_before_placing_orders(
    client, monkeypatch, create_test_tables
):
    _patch_balance(monkeypatch, 10_000)
    _patch_contract_meta(monkeypatch)
    payload = _payload(total_margin=10)
    payload["range_low"] = 0.01003
    payload["range_high"] = 0.01061
    payload["breakout_low"] = 0.009
    payload["breakout_high"] = 0.011
    response = client.post("/grid-ladders", json=payload)
    assert response.status_code == 200

    fake_api = FakeFuturesApi()
    with Session(create_test_tables) as session:
        GridLadderLifecycle(_grid_base(fake_api), session).process_symbol("ADAUSDC")

    assert [order["price"] for order in fake_api.orders] == [
        0.01,
        0.0101,
        0.0104,
        0.0106,
    ]


def test_grid_lifecycle_places_take_profit_after_entry_fill(
    client, monkeypatch, create_test_tables
):
    _patch_balance(monkeypatch, 10_000)
    _patch_contract_meta(monkeypatch)
    created = client.post("/grid-ladders", json=_payload())
    fake_api = FakeFuturesApi()

    with Session(create_test_tables) as session:
        lifecycle = GridLadderLifecycle(_grid_base(fake_api), session)
        lifecycle.process_symbol("ADAUSDC")
        ladder = GridLadderCrud(session).get_active_for_symbol("ADAUSDC")
        assert ladder is not None
        entry_order = next(order for order in ladder.orders if order.side == "buy")
        entry_order_id = entry_order.exchange_order_id
        fake_api.order_details[entry_order.exchange_order_id] = _order_details(
            status=GetOrderByOrderIdResp.StatusEnum.DONE,
            filled_size=entry_order.contracts,
            avg_deal_price=entry_order.price,
            price=entry_order.price,
        )
        lifecycle.process_symbol("ADAUSDC")

    detail = client.get(f"/grid-ladders/{created.json()['detail']['id']}").json()[
        "detail"
    ]
    filled_level = next(
        level for level in detail["levels"] if level["entry_order_id"] == entry_order_id
    )
    tp_order = next(order for order in fake_api.orders if order["reduce_only"])
    assert filled_level["status"] == "take_profit_open"
    assert detail["used_margin"] == filled_level["margin_required"]
    assert filled_level["take_profit_order_id"] == tp_order["order_id"]
    assert tp_order["side"].value == "sell"
    assert any("filled" in log for log in detail["logs"])
    assert any("Placed take-profit order" in log for log in detail["logs"])


def test_grid_lifecycle_marks_level_completed_after_take_profit_fill(
    client, monkeypatch, create_test_tables
):
    _patch_balance(monkeypatch, 10_000)
    _patch_contract_meta(monkeypatch)
    created = client.post("/grid-ladders", json=_payload())
    fake_api = FakeFuturesApi()

    with Session(create_test_tables) as session:
        lifecycle = GridLadderLifecycle(_grid_base(fake_api), session)
        lifecycle.process_symbol("ADAUSDC")
        ladder = GridLadderCrud(session).get_active_for_symbol("ADAUSDC")
        assert ladder is not None
        entry_order = next(order for order in ladder.orders if order.side == "buy")
        entry_order_id = entry_order.exchange_order_id
        fake_api.order_details[entry_order.exchange_order_id] = _order_details(
            status=GetOrderByOrderIdResp.StatusEnum.DONE,
            filled_size=entry_order.contracts,
            avg_deal_price=entry_order.price,
            price=entry_order.price,
        )
        lifecycle.process_symbol("ADAUSDC")
        ladder = GridLadderCrud(session).get_active_for_symbol("ADAUSDC")
        assert ladder is not None
        tp_order = next(
            order for order in ladder.orders if order.order_role == "take_profit"
        )
        fake_api.order_details[tp_order.exchange_order_id] = _order_details(
            status=GetOrderByOrderIdResp.StatusEnum.DONE,
            filled_size=tp_order.contracts,
            avg_deal_price=tp_order.price,
            price=tp_order.price,
        )
        lifecycle.process_symbol("ADAUSDC")

    detail = client.get(f"/grid-ladders/{created.json()['detail']['id']}").json()[
        "detail"
    ]
    completed_level = next(
        level for level in detail["levels"] if level["entry_order_id"] == entry_order_id
    )
    assert completed_level["status"] == "completed"
    assert completed_level["realized_pnl"] > 0
    assert detail["used_margin"] == 0


def test_grid_lifecycle_scales_used_margin_for_partial_entry_fill(
    client, monkeypatch, create_test_tables
):
    _patch_balance(monkeypatch, 10_000)
    _patch_contract_meta(monkeypatch)
    created = client.post("/grid-ladders", json=_payload())
    fake_api = FakeFuturesApi()

    with Session(create_test_tables) as session:
        lifecycle = GridLadderLifecycle(_grid_base(fake_api), session)
        lifecycle.process_symbol("ADAUSDC")
        ladder = GridLadderCrud(session).get_active_for_symbol("ADAUSDC")
        assert ladder is not None
        entry_order = next(order for order in ladder.orders if order.side == "buy")
        partial_fill = max(entry_order.contracts // 2, 1)
        fake_api.order_details[entry_order.exchange_order_id] = _order_details(
            status=GetOrderByOrderIdResp.StatusEnum.OPEN,
            filled_size=partial_fill,
            avg_deal_price=entry_order.price,
            price=entry_order.price,
        )
        lifecycle.process_symbol("ADAUSDC")

    detail = client.get(f"/grid-ladders/{created.json()['detail']['id']}").json()[
        "detail"
    ]
    filled_level = next(
        level
        for level in detail["levels"]
        if level["entry_order_id"] == entry_order.exchange_order_id
    )
    expected_used_margin = round(
        filled_level["margin_required"]
        * (filled_level["filled_entry_qty"] / filled_level["contracts"]),
        8,
    )
    assert detail["used_margin"] == expected_used_margin


def test_grid_lifecycle_keeps_used_margin_for_filled_entry_that_errors(
    client, monkeypatch, create_test_tables
):
    _patch_balance(monkeypatch, 10_000)
    _patch_contract_meta(monkeypatch)
    created = client.post("/grid-ladders", json=_payload())
    fake_api = FakeFuturesApi()

    with Session(create_test_tables) as session:
        lifecycle = GridLadderLifecycle(_grid_base(fake_api), session)
        lifecycle.process_symbol("ADAUSDC")
        fake_api.fail_on_call = len(fake_api.orders) + 1
        ladder = GridLadderCrud(session).get_active_for_symbol("ADAUSDC")
        assert ladder is not None
        entry_order = next(order for order in ladder.orders if order.side == "buy")
        fake_api.order_details[entry_order.exchange_order_id] = _order_details(
            status=GetOrderByOrderIdResp.StatusEnum.DONE,
            filled_size=entry_order.contracts,
            avg_deal_price=entry_order.price,
            price=entry_order.price,
        )
        lifecycle.process_symbol("ADAUSDC")

    detail = client.get(f"/grid-ladders/{created.json()['detail']['id']}").json()[
        "detail"
    ]
    errored_level = next(
        level
        for level in detail["levels"]
        if level["entry_order_id"] == entry_order.exchange_order_id
    )
    assert detail["status"] == "error"
    assert errored_level["status"] == "error"
    assert detail["used_margin"] == errored_level["margin_required"]


def test_grid_lifecycle_ignores_zero_avg_deal_price_for_filled_order(
    create_test_tables,
):
    with Session(create_test_tables) as session:
        lifecycle = GridLadderLifecycle(_grid_base(FakeFuturesApi()), session)
    details = _order_details(
        status=GetOrderByOrderIdResp.StatusEnum.DONE,
        filled_size=13,
        avg_deal_price=0,
        price=77.37,
    )

    assert lifecycle._filled_price(details, 76.06) == 77.37


def test_grid_lifecycle_uses_order_defaults_for_zero_filled_take_profit_payload(
    client, monkeypatch, create_test_tables
):
    _patch_balance(monkeypatch, 10_000)
    _patch_contract_meta(monkeypatch)
    created = client.post("/grid-ladders", json=_payload())
    fake_api = FakeFuturesApi()

    with Session(create_test_tables) as session:
        lifecycle = GridLadderLifecycle(_grid_base(fake_api), session)
        lifecycle.process_symbol("ADAUSDC")
        ladder = GridLadderCrud(session).get_active_for_symbol("ADAUSDC")
        assert ladder is not None
        entry_order = next(order for order in ladder.orders if order.side == "buy")
        entry_order_id = entry_order.exchange_order_id
        fake_api.order_details[entry_order.exchange_order_id] = _order_details(
            status=GetOrderByOrderIdResp.StatusEnum.DONE,
            filled_size=entry_order.contracts,
            avg_deal_price=entry_order.price,
            price=entry_order.price,
        )
        lifecycle.process_symbol("ADAUSDC")
        ladder = GridLadderCrud(session).get_active_for_symbol("ADAUSDC")
        assert ladder is not None
        tp_order = next(
            order for order in ladder.orders if order.order_role == "take_profit"
        )
        fake_api.order_details[tp_order.exchange_order_id] = _order_details(
            status=GetOrderByOrderIdResp.StatusEnum.DONE,
            filled_size=0,
            avg_deal_price=0,
            price=0,
        )
        lifecycle.process_symbol("ADAUSDC")

    detail = client.get(f"/grid-ladders/{created.json()['detail']['id']}").json()[
        "detail"
    ]
    completed_level = next(
        level for level in detail["levels"] if level["entry_order_id"] == entry_order_id
    )
    completed_order = next(
        order for order in detail["orders"] if order["order_role"] == "take_profit"
    )
    assert completed_order["filled_qty"] == tp_order.contracts
    assert completed_order["filled_price"] == tp_order.price
    assert completed_level["realized_pnl"] > 0


def test_grid_lifecycle_updates_unrealized_pnl_on_active_ladder(
    client, monkeypatch, create_test_tables
):
    _patch_balance(monkeypatch, 10_000)
    _patch_contract_meta(monkeypatch)
    created = client.post("/grid-ladders", json=_payload())
    fake_api = FakeFuturesApi()
    fake_api.position_unrealized_pnl = 12.3456789

    with Session(create_test_tables) as session:
        lifecycle = GridLadderLifecycle(_grid_base(fake_api), session)
        lifecycle.process_symbol("ADAUSDC")
        lifecycle.process_symbol("ADAUSDC")

    detail = client.get(f"/grid-ladders/{created.json()['detail']['id']}").json()[
        "detail"
    ]
    assert detail["status"] == "active"
    assert detail["unrealized_pnl"] == 12.3456789


def test_grid_lifecycle_closes_ladder_when_price_breaks_below_range(
    client, monkeypatch, create_test_tables
):
    _patch_balance(monkeypatch, 10_000)
    _patch_contract_meta(monkeypatch)
    created = client.post("/grid-ladders", json=_payload())
    ladder_id = created.json()["detail"]["id"]
    fake_api = FakeFuturesApi()
    fake_api.position_qty = 2

    with Session(create_test_tables) as session:
        lifecycle = GridLadderLifecycle(_grid_base(fake_api), session)
        lifecycle.process_symbol("ADAUSDC")
        fake_api.position_mark_price = 84
        # First out-of-range tick: starts the breach timer, does not close yet.
        lifecycle.process_symbol("ADAUSDC")
        # Expire the breach timer by backdating first_breach_at.
        crud = GridLadderCrud(session)
        ladder = crud.get_active_for_symbol("ADAUSDC")
        assert ladder is not None
        past_ms = (
            int(time() * 1000)
            - GridLadderLifecycle.BREACH_CANDLES_REQUIRED * 15 * 60 * 1000
            - 1000
        )
        crud.update_status_with_context(
            ladder.id,
            GridLadderStatus.active,
            context_updates={"first_breach_at": past_ms},
        )
        # Second out-of-range tick: timer expired → ladder closes.
        lifecycle.process_symbol("ADAUSDC")

    detail = client.get(f"/grid-ladders/{ladder_id}").json()["detail"]
    assert detail["status"] == "closed"
    assert detail["closed_at"] is not None
    assert detail["unrealized_pnl"] == 0
    assert detail["used_margin"] == 0
    assert detail["context"]["close_reason"] == "range_break_down"
    assert detail["context"]["range_break_price"] == 84
    assert fake_api.cancelled_symbols == ["ADAUSDCM"]
    assert any(order["reduce_only"] for order in fake_api.orders)
    assert all(
        order["status"] == OrderStatus.CANCELED.value for order in detail["orders"]
    )
    open_level_statuses = [
        level["status"] for level in detail["levels"] if level["side"] != "neutral"
    ]
    assert set(open_level_statuses) == {"cancelled"}
    assert detail["logs"][-2]["event"] == "range_break_close"
    assert detail["logs"][-2]["direction"] == "down"


def test_grid_lifecycle_closes_unfilled_ladder_after_one_breach_candle(
    client, monkeypatch, create_test_tables
):
    _patch_balance(monkeypatch, 10_000)
    _patch_contract_meta(monkeypatch)
    created = client.post("/grid-ladders", json=_payload())
    ladder_id = created.json()["detail"]["id"]
    fake_api = FakeFuturesApi()

    with Session(create_test_tables) as session:
        lifecycle = GridLadderLifecycle(_grid_base(fake_api), session)
        lifecycle.process_symbol("ADAUSDC")
        fake_api.position_mark_price = 84
        lifecycle.process_symbol("ADAUSDC")
        crud = GridLadderCrud(session)
        ladder = crud.get_active_for_symbol("ADAUSDC")
        assert ladder is not None
        past_ms = (
            int(time() * 1000)
            - GridLadderLifecycle.UNFILLED_BREACH_CANDLES_REQUIRED * 15 * 60 * 1000
            - 1000
        )
        crud.update_status_with_context(
            ladder.id,
            GridLadderStatus.active,
            context_updates={"first_breach_at": past_ms},
        )
        lifecycle.process_symbol("ADAUSDC")

    detail = client.get(f"/grid-ladders/{ladder_id}").json()["detail"]
    assert detail["status"] == "closed"
    assert detail["context"]["close_reason"] == "range_break_down"


def test_grid_lifecycle_keeps_filled_ladder_open_after_one_breach_candle(
    client, monkeypatch, create_test_tables
):
    _patch_balance(monkeypatch, 10_000)
    _patch_contract_meta(monkeypatch)
    created = client.post("/grid-ladders", json=_payload())
    ladder_id = created.json()["detail"]["id"]
    fake_api = FakeFuturesApi()
    fake_api.position_mark_price = 100

    with Session(create_test_tables) as session:
        lifecycle = GridLadderLifecycle(_grid_base(fake_api), session)
        lifecycle.process_symbol("ADAUSDC")
        ladder = GridLadderCrud(session).get_active_for_symbol("ADAUSDC")
        assert ladder is not None
        entry_order = next(order for order in ladder.orders if order.side == "buy")
        fake_api.order_details[entry_order.exchange_order_id] = _order_details(
            status=GetOrderByOrderIdResp.StatusEnum.DONE,
            filled_size=entry_order.contracts,
            avg_deal_price=entry_order.price,
            price=entry_order.price,
        )
        lifecycle.process_symbol("ADAUSDC")
        fake_api.position_mark_price = 84
        lifecycle.process_symbol("ADAUSDC")
        crud = GridLadderCrud(session)
        ladder = crud.get_active_for_symbol("ADAUSDC")
        assert ladder is not None
        past_ms = (
            int(time() * 1000)
            - GridLadderLifecycle.UNFILLED_BREACH_CANDLES_REQUIRED * 15 * 60 * 1000
            - 1000
        )
        crud.update_status_with_context(
            ladder.id,
            GridLadderStatus.active,
            context_updates={"first_breach_at": past_ms},
        )
        lifecycle.process_symbol("ADAUSDC")

    detail = client.get(f"/grid-ladders/{ladder_id}").json()["detail"]
    assert detail["status"] == "active"
    assert detail["context"]["first_breach_at"] == past_ms


def test_grid_lifecycle_closes_ladder_when_price_breaks_above_range(
    client, monkeypatch, create_test_tables
):
    _patch_balance(monkeypatch, 10_000)
    _patch_contract_meta(monkeypatch)
    created = client.post("/grid-ladders", json=_payload())
    ladder_id = created.json()["detail"]["id"]
    fake_api = FakeFuturesApi()
    fake_api.position_qty = -2

    with Session(create_test_tables) as session:
        lifecycle = GridLadderLifecycle(_grid_base(fake_api), session)
        lifecycle.process_symbol("ADAUSDC")
        fake_api.position_mark_price = 116
        # First out-of-range tick: starts the breach timer, does not close yet.
        lifecycle.process_symbol("ADAUSDC")
        # Expire the breach timer by backdating first_breach_up_at.
        crud = GridLadderCrud(session)
        ladder = crud.get_active_for_symbol("ADAUSDC")
        assert ladder is not None
        past_ms = (
            int(time() * 1000)
            - GridLadderLifecycle.BREACH_CANDLES_REQUIRED * 15 * 60 * 1000
            - 1000
        )
        crud.update_status_with_context(
            ladder.id,
            GridLadderStatus.active,
            context_updates={"first_breach_up_at": past_ms},
        )
        # Second out-of-range tick: timer expired → ladder closes.
        lifecycle.process_symbol("ADAUSDC")

    detail = client.get(f"/grid-ladders/{ladder_id}").json()["detail"]
    assert detail["status"] == "closed"
    assert detail["context"]["close_reason"] == "range_break_up"
    assert detail["context"]["range_break_price"] == 116
    assert fake_api.cancelled_symbols == ["ADAUSDCM"]
    assert any(order["reduce_only"] for order in fake_api.orders)
    assert detail["logs"][-2]["event"] == "range_break_close"
    assert detail["logs"][-2]["direction"] == "up"


def test_grid_lifecycle_continues_reconciliation_inside_breakout_bounds(
    client, monkeypatch, create_test_tables
):
    _patch_balance(monkeypatch, 10_000)
    _patch_contract_meta(monkeypatch)
    created = client.post("/grid-ladders", json=_payload())
    fake_api = FakeFuturesApi()
    fake_api.position_mark_price = 100

    with Session(create_test_tables) as session:
        lifecycle = GridLadderLifecycle(_grid_base(fake_api), session)
        lifecycle.process_symbol("ADAUSDC")
        ladder = GridLadderCrud(session).get_active_for_symbol("ADAUSDC")
        assert ladder is not None
        entry_order = next(order for order in ladder.orders if order.side == "buy")
        entry_order_id = entry_order.exchange_order_id
        fake_api.order_details[entry_order_id] = _order_details(
            status=GetOrderByOrderIdResp.StatusEnum.DONE,
            filled_size=entry_order.contracts,
            avg_deal_price=entry_order.price,
            price=entry_order.price,
        )
        lifecycle.process_symbol("ADAUSDC")

    detail = client.get(f"/grid-ladders/{created.json()['detail']['id']}").json()[
        "detail"
    ]
    filled_level = next(
        level for level in detail["levels"] if level["entry_order_id"] == entry_order_id
    )
    assert detail["status"] == "active"
    assert fake_api.cancelled_symbols == []
    assert entry_order_id in fake_api.retrieved_order_ids
    assert filled_level["status"] == "take_profit_open"


def test_grid_lifecycle_does_not_range_break_pending_ladder_before_initial_entries(
    client, monkeypatch, create_test_tables
):
    _patch_balance(monkeypatch, 10_000)
    _patch_contract_meta(monkeypatch)
    created = client.post("/grid-ladders", json=_payload())
    fake_api = FakeFuturesApi()
    fake_api.position_mark_price = 84

    with Session(create_test_tables) as session:
        GridLadderLifecycle(_grid_base(fake_api), session).process_symbol("ADAUSDC")

    detail = client.get(f"/grid-ladders/{created.json()['detail']['id']}").json()[
        "detail"
    ]
    assert detail["status"] == "active"
    assert len(detail["orders"]) == 4
    assert fake_api.cancelled_symbols == []


def test_grid_lifecycle_range_break_closes_ladder_with_zero_position_qty(
    client, monkeypatch, create_test_tables
):
    _patch_balance(monkeypatch, 10_000)
    _patch_contract_meta(monkeypatch)
    created = client.post("/grid-ladders", json=_payload())
    ladder_id = created.json()["detail"]["id"]
    fake_api = FakeFuturesApi()
    fake_api.position_qty = 0

    with Session(create_test_tables) as session:
        lifecycle = GridLadderLifecycle(_grid_base(fake_api), session)
        lifecycle.process_symbol("ADAUSDC")
        fake_api.position_mark_price = 84
        # First out-of-range tick: starts the breach timer, does not close yet.
        lifecycle.process_symbol("ADAUSDC")
        # Expire the breach timer by backdating first_breach_at.
        crud = GridLadderCrud(session)
        ladder = crud.get_active_for_symbol("ADAUSDC")
        assert ladder is not None
        past_ms = (
            int(time() * 1000)
            - GridLadderLifecycle.BREACH_CANDLES_REQUIRED * 15 * 60 * 1000
            - 1000
        )
        crud.update_status_with_context(
            ladder.id,
            GridLadderStatus.active,
            context_updates={"first_breach_at": past_ms},
        )
        # Second out-of-range tick: timer expired → ladder closes.
        lifecycle.process_symbol("ADAUSDC")

    detail = client.get(f"/grid-ladders/{ladder_id}").json()["detail"]
    reduce_only_orders = [order for order in fake_api.orders if order["reduce_only"]]
    assert detail["status"] == "closed"
    assert detail["context"]["close_reason"] == "range_break_down"
    assert detail["used_margin"] == 0
    assert fake_api.cancelled_symbols == ["ADAUSDCM"]
    assert reduce_only_orders == []


def test_grid_lifecycle_cancels_partial_initial_orders_on_failure(
    client, monkeypatch, create_test_tables
):
    _patch_balance(monkeypatch, 10_000)
    _patch_contract_meta(monkeypatch)
    created = client.post("/grid-ladders", json=_payload())
    fake_api = FakeFuturesApi()
    fake_api.fail_on_call = 2

    with Session(create_test_tables) as session:
        GridLadderLifecycle(_grid_base(fake_api), session).process_symbol("ADAUSDC")

    detail = client.get(f"/grid-ladders/{created.json()['detail']['id']}").json()[
        "detail"
    ]
    assert detail["status"] == "error"
    assert detail["context"]["execution_error"] == "exchange rejected order"
    assert fake_api.cancelled_symbols == ["ADAUSDCM"]
    assert detail["orders"][0]["status"] == OrderStatus.CANCELED.value
    assert detail["logs"][-1]["event"] == "error"
    assert detail["logs"][-1]["error_type"] == "RuntimeError"
    assert detail["logs"][-1]["message"] == "exchange rejected order"


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
    assert detail["status"] == "closing"
    assert detail["closed_at"] is None
    assert detail["context"]["close_reason"] == "breakout_high_hit"


def test_grid_lifecycle_closes_ladder_and_position(
    client, monkeypatch, create_test_tables
):
    _patch_balance(monkeypatch, 10_000)
    _patch_contract_meta(monkeypatch)
    created = client.post("/grid-ladders", json=_payload())
    ladder_id = created.json()["detail"]["id"]
    fake_api = FakeFuturesApi()
    fake_api.position_qty = 2

    with Session(create_test_tables) as session:
        lifecycle = GridLadderLifecycle(_grid_base(fake_api), session)
        lifecycle.process_symbol("ADAUSDC")

    close = client.post(
        f"/grid-ladders/{ladder_id}/close",
        json={"reason": "manual_close"},
    )
    assert close.status_code == 200

    with Session(create_test_tables) as session:
        GridLadderLifecycle(_grid_base(fake_api), session).process_symbol("ADAUSDC")

    detail = client.get(f"/grid-ladders/{ladder_id}").json()["detail"]
    assert detail["status"] == "closed"
    assert detail["closed_at"] is not None
    assert detail["used_margin"] == 0
    assert fake_api.cancelled_symbols == ["ADAUSDCM"]
    assert any(order["reduce_only"] for order in fake_api.orders)


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
