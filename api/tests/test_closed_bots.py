from uuid import uuid4
from unittest.mock import Mock

import pytest
from pybinbot import (
    BotModel,
    DealType,
    EntryMode,
    MarketType,
    OrderModel,
    OrderStatus,
    Status,
)
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import object_session

from api.databases.crud.bot_crud import BotTableCrud
from api.databases.tables.bot_table import BotTable
from api.databases.tables.deal_table import DealTable
from api.databases.utils import get_session
from api.main import app
from api.deals.conditional_entry import ConditionalEntry, ConditionalEntryClosed
from api.exchange_apis.kucoin.futures.futures_deal import KucoinPositionDeal
from streaming.futures_position import FuturesPosition


@pytest.fixture
def closed_bot(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)

    def get_test_session():
        with Session(engine) as session:
            yield session

    monkeypatch.setitem(app.dependency_overrides, get_session, get_test_session)
    with Session(engine) as session:
        row = BotTable(
            pair=f"CLOSED{uuid4().hex[:8]}USDT",
            name=f"closed-{uuid4()}",
            status=Status.closed,
            market_type=MarketType.FUTURES,
            entry_mode=EntryMode.conditional_limit,
            entry_price=10,
            logs=["Conditional entry closed: insufficient futures funds"],
            deal=DealTable(),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        yield row
        session.delete(row)
        session.commit()
    engine.dispose()


@pytest.mark.parametrize("endpoint", ["/bot", "/bot/public"])
def test_lists_hide_closed_bots_unless_requested(client, closed_bot, endpoint):
    for params in ({}, {"status": "all"}):
        data = client.get(endpoint, params=params).json()["data"]
        assert all(bot["status"] != "closed" for bot in data)
    for params in ({"status": "closed"}, {"include_closed": "true"}):
        data = client.get(endpoint, params=params).json()["data"]
        assert any(bot["pair"] == closed_bot.pair for bot in data)
    data = client.get(
        endpoint, params={"status": "active", "include_closed": "true"}
    ).json()["data"]
    assert all(bot["status"] == "active" for bot in data)


@pytest.mark.parametrize("lookup", ["id", "symbol"])
def test_single_bot_requires_explicit_closed_opt_in(client, closed_bot, lookup):
    path = (
        f"/bot/{closed_bot.id}" if lookup == "id" else f"/bot/symbol/{closed_bot.pair}"
    )
    assert client.get(path).json()["error"] == 1
    response = client.get(path, params={"include_closed": "true"}).json()
    assert response["error"] == 0
    assert response["data"]["status"] == "closed"
    assert response["data"]["logs"] == closed_bot.logs


def test_closed_bots_do_not_inflate_rankings_or_occupy_active_pairs(client, closed_bot):
    ranking = client.get("/bot/algo-ranking").json()["detail"]
    assert all(item["name"] != closed_bot.name for item in ranking)
    ranking = client.get("/bot/algo-ranking", params={"include_closed": "true"}).json()[
        "detail"
    ]
    assert (
        next(item for item in ranking if item["name"] == closed_bot.name)["count"] == 1
    )
    assert closed_bot.pair not in client.get("/bot/active-pairs").json()["data"]


def test_closure_persists_identity_deal_and_reason(closed_bot):
    original_session = object_session(closed_bot)
    assert original_session is not None
    with Session(original_session.get_bind()) as session:
        crud = BotTableCrud(session)
        bot = BotModel.dump_from_table(
            crud.get_one(bot_id=str(closed_bot.id), include_closed=True)
        )
        bot.status = Status.pending
        deal_id = closed_bot.deal_id
        with pytest.raises(ConditionalEntryClosed, match="expired before submission"):
            ConditionalEntry(Mock(spec=KucoinPositionDeal, controller=crud)).close(
                bot, "expired before submission"
            )
        saved = crud.get_one(bot_id=str(bot.id), status=Status.closed)
        assert saved.id == bot.id
        assert saved.deal_id == deal_id
        assert saved.status == Status.closed
        assert "expired before submission" in saved.logs[-1]
        assert saved.entry_price == bot.entry_price
        assert saved.entry_expires_at == bot.entry_expires_at
        assert saved.logs[0] == closed_bot.logs[0]


def test_submitted_expiry_retains_deal_client_id_and_order_history(
    closed_bot, monkeypatch
):
    original_session = object_session(closed_bot)
    assert original_session is not None
    with Session(original_session.get_bind()) as session:
        crud = BotTableCrud(session)
        bot = BotModel.dump_from_table(
            crud.get_one(bot_id=str(closed_bot.id), include_closed=True)
        )
        bot.status = Status.pending
        bot.deal.entry_client_oid = "retained-client-id"
        bot.orders = [
            OrderModel(
                order_id="retained-entry",
                order_type="limit",
                pair=bot.pair,
                order_side="buy",
                qty=2,
                requested_qty=2,
                price=10,
                timestamp=1000,
                time_in_force="GTC",
                status=OrderStatus.NEW,
                deal_type=DealType.base_order,
            )
        ]
        crud.save(bot)
        position = FuturesPosition.__new__(FuturesPosition)
        position.execution = Mock(
            spec=KucoinPositionDeal, active_bot=bot, controller=crud
        )
        monkeypatch.setattr(
            position,
            "_cancel_pending_entry_and_confirm_unfilled",
            Mock(return_value=True),
        )
        position._expire_unfilled_base_order(bot.orders[0], bot.pair)

        saved = crud.get_one(bot_id=str(bot.id), include_closed=True)
        assert saved.status == Status.closed
        assert saved.deal_id == closed_bot.deal_id
        assert saved.deal.entry_client_oid == "retained-client-id"
        assert len(saved.orders) == 1
        assert saved.orders[0].order_id == "retained-entry"
        assert saved.orders[0].requested_qty == 2
        assert saved.orders[0].status == OrderStatus.EXPIRED
        assert "no fills or position" in saved.logs[-1]
