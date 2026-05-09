from contextlib import contextmanager
from uuid import UUID

from bots.models import BotModel, BotListResponse, BotPairsList, OrderModel
from databases.crud.bot_crud import BotTableCrud
from databases.tables.bot_table import BotTable, PaperTradingTable
from databases.tables.deal_table import DealTable
from pybinbot import DealType, OrderStatus, Status
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
