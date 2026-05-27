from contextlib import contextmanager
from typing import Any, cast
from uuid import UUID

from bots.models import BotModel, BotListResponse, BotPairsList, OrderModel
from databases.crud.bot_crud import BotTableCrud
from databases.tables.bot_table import BotTable, PaperTradingTable
from databases.tables.deal_table import DealTable
from exchange_apis.kucoin.futures.position_deal import PositionDeal
from pybinbot import DealType, MarketType, OrderStatus, Status
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine


def test_bot_model_orders_are_isolated():
    first = BotModel(
        pair="BTCUSDC",
        logs=[],
    )
    second = BotModel(
        pair="ETHUSDC",
        logs=[],
    )

    first.orders.append(
        OrderModel(
            deal_type=DealType.base_order,
            order_id="test-order-id",
            order_side="buy",
            order_type="MARKET",
            pair="BTCUSDC",
            price=1.0,
            qty=1.0,
            status=OrderStatus.FILLED,
            time_in_force="GTC",
            timestamp=0,
        )
    )

    assert second.orders == []


def test_bot_table_logs_are_isolated():
    first = BotTable(pair="BTCUSDC")
    second = BotTable(pair="ETHUSDC")

    first.logs.append("first")

    assert second.logs == []


def test_paper_trading_logs_are_isolated():
    first = PaperTradingTable(pair="BTCUSDC")
    second = PaperTradingTable(pair="ETHUSDC")

    first.logs.append("first")

    assert second.logs == []


def test_response_lists_are_isolated():
    first_pairs = BotPairsList(message="")
    second_pairs = BotPairsList(message="")
    first_pairs.data.append("BTCUSDC")
    assert second_pairs.data == []

    first_list = BotListResponse(message="")
    second_list = BotListResponse(message="")
    first_list.data.append("bot")
    assert second_list.data == []


def test_bot_crud_get_one_returns_loaded_deal_after_read_session_commit(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    bot_id = UUID("c2d5cbdf-a01d-4831-ab8b-0c39099b1762")

    with Session(engine) as session:
        bot = BotTable(
            id=bot_id,
            pair="BTCUSDC",
            status=Status.active,
            deal=DealTable(base_order_size=15),
        )
        session.add(bot)
        session.commit()

    @contextmanager
    def committing_session(session: Session | None = None):
        session = session or Session(engine)
        try:
            yield session
            session.commit()
        finally:
            session.close()

    monkeypatch.setattr("databases.crud.bot_crud.get_db_session", committing_session)

    bot = BotTableCrud().get_one(bot_id=str(bot_id))
    model = BotModel.dump_from_table(bot)

    assert model.deal.base_order_size == 15


def make_in_memory_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@contextmanager
def session_for(engine):
    session = Session(engine, expire_on_commit=False)
    try:
        yield session
        session.commit()
    finally:
        session.close()


def test_get_active_pairs_includes_pending_and_active(monkeypatch):
    engine = make_in_memory_db()

    with session_for(engine) as session:
        for pair, status in [
            ("ACTIVEUSDT", "active"),
            ("PENDINGUSDT", "pending"),
            ("INACTIVEUSDT", "inactive"),
            ("COMPLETEDUSDT", "completed"),
            ("ERRORUSDT", "error"),
        ]:
            session.add(BotTable(pair=pair, status=status))

    @contextmanager
    def patched_session(s=None):
        with session_for(engine) as sess:
            yield sess

    monkeypatch.setattr("databases.crud.bot_crud.get_db_session", patched_session)

    pairs = BotTableCrud().get_active_pairs()

    assert set(pairs) == {"ACTIVEUSDT", "PENDINGUSDT"}


def test_exit_pending_calls_open_deal_and_returns_early():
    bot = BotModel(
        pair="BTCUSDT",
        market_type=MarketType.FUTURES,
        status=Status.pending,
    )
    open_deal_calls = []

    class StubController:
        def save(self, b):
            return b

    def stub_open_deal(self):
        open_deal_calls.append(True)
        self.active_bot.status = Status.active
        return self.active_bot

    position_deal = cast(Any, PositionDeal.__new__(PositionDeal))
    position_deal.active_bot = bot
    position_deal.controller = StubController()
    position_deal.price_precision = 2
    position_deal.open_deal = lambda: stub_open_deal(position_deal)

    result = PositionDeal.exit(position_deal, close_price=100.0)

    assert open_deal_calls == [True]
    assert result.status == Status.active
