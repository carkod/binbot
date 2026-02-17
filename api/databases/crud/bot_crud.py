from typing import Any, List, Sequence, Union, Generator, cast
from uuid import UUID
from contextlib import contextmanager, AbstractContextManager

from sqlmodel import Session, select, asc, desc, case
from sqlalchemy.orm import QueryableAttribute, selectinload
from sqlalchemy.orm.attributes import flag_modified

from bots.models import BotModel, OrderModel
from databases.tables.bot_table import BotTable
from databases.tables.deal_table import DealTable
from databases.tables.order_table import ExchangeOrderTable
from databases.utils import get_db_session as _get_db_session

from pybinbot import (
    Status,
    Strategy,
    ts_to_humandate,
    timestamp,
    SaveBotError,
    BinbotErrors,
    BotBase,
)


def get_session() -> AbstractContextManager[Session]:
    """Module-level session factory kept overridable for tests."""
    return _get_db_session()


# Deal with SQLModel vs mypy issues
BOT_DEAL_REL = cast(QueryableAttribute[Any], BotTable.deal)
BOT_ORDERS_REL = cast(QueryableAttribute[Any], BotTable.orders)


class BotTableCrud:
    """
    CRUD for BotTable.

    - If session is injected → it will be reused.
    - If not → a fresh session is created per operation.
    - Always returns ORM objects.
    """

    def __init__(self, session: Session | None = None):
        self._external_session = session

    def _get_session(self) -> AbstractContextManager[Session]:
        """
        Session handling
        """
        if self._external_session is not None:
            session = self._external_session  # <-- bind locally

            @contextmanager
            def external_ctx() -> Generator[Session, None, None]:
                yield session

            return external_ctx()

        return get_session()

    def update_table(self, bot: Union[BotModel, BotTable]) -> BotTable:
        """
        Convert a BotModel to BotTable (or return BotTable as-is),
        fully populating deal and orders in a detached manner.
        Safe to attach to a session later for save/commit.
        """
        if isinstance(bot, BotTable):
            return bot

        # Step 1: Copy BotModel fields (except relationships)
        bot_table = BotTable()
        for field_name in BotTable.model_fields.keys():
            if field_name in {"deal", "orders"}:
                continue
            if hasattr(bot, field_name):
                setattr(bot_table, field_name, getattr(bot, field_name))

        # Step 2: Copy DealTable fields
        bot_table.deal = DealTable()
        if bot.deal:
            for field_name in DealTable.model_fields.keys():
                if hasattr(bot.deal, field_name):
                    setattr(bot_table.deal, field_name, getattr(bot.deal, field_name))

        # Step 3: Copy Orders
        bot_table.orders = []
        for order in getattr(bot, "orders", []):
            order_row = ExchangeOrderTable.model_construct(**order.model_dump())
            bot_table.orders.append(order_row)

        return bot_table

    def update_logs(
        self, log_message: str | list[str], bot: Union[BotModel, BotTable]
    ) -> BotTable:
        if not bot:
            raise BinbotErrors("Bot not found")

        ts = ts_to_humandate(ts=timestamp())

        with self._get_session() as s:
            # Get the managed bot instance from the session
            bot_row = s.get(BotTable, UUID(str(bot.id)))
            if not bot_row:
                raise BinbotErrors("Bot not found")

            if isinstance(log_message, list):
                new_logs = [f"[{ts}] {msg}" for msg in log_message]
                bot_row.logs = new_logs + (bot_row.logs or [])
            else:
                if bot_row.logs is None:
                    bot_row.logs = []
                bot_row.logs.append(f"[{ts}] {log_message}")

            flag_modified(bot_row, "logs")

            s.add(bot_row)
            s.commit()
            s.refresh(bot_row)
            s.expunge(bot_row)

            return bot_row

    def get(
        self,
        status: Status | None = None,
        start_date: float | None = None,
        end_date: float | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> Sequence[BotTable]:

        stmt = select(BotTable).options(
            selectinload(BOT_DEAL_REL),
            selectinload(BOT_ORDERS_REL),
        )

        if status and status != Status.all:
            stmt = stmt.where(BotTable.status == status)

        if start_date:
            stmt = stmt.where(BotTable.created_at >= int(start_date))

        if end_date:
            stmt = stmt.where(BotTable.created_at <= int(end_date))

        stmt = (
            stmt.order_by(
                desc(BotTable.created_at),
                case((BotTable.status == Status.active, 1), else_=2),
                asc(BotTable.pair),
            )
            .limit(limit)
            .offset(offset)
        )

        with self._get_session() as s:
            bots = s.exec(stmt).unique().all()
            for bot in bots:
                s.expunge(bot)
            return bots

    def get_one(
        self,
        bot_id: str | None = None,
        symbol: str | None = None,
        status: Status | None = None,
        strategy: Strategy | None = None,
    ) -> BotTable:

        with self._get_session() as s:
            stmt = select(BotTable).options(
                selectinload(BOT_DEAL_REL),
                selectinload(BOT_ORDERS_REL),
            )

            if bot_id:
                stmt = stmt.where(BotTable.id == UUID(bot_id))

            elif symbol:
                stmt = stmt.where(BotTable.pair == symbol)

                if status and status != Status.all:
                    stmt = stmt.where(BotTable.status == status)
                elif strategy:
                    stmt = stmt.where(BotTable.strategy == strategy)

            else:
                raise BinbotErrors("Invalid bot id or symbol")

            bot = s.exec(stmt).first()

            if not bot:
                raise BinbotErrors("Bot not found")

            s.expunge(bot)
            return bot

    # --------------------------------------------------
    # Create / Save / Delete
    # --------------------------------------------------

    def create(self, data: BotBase) -> BotTable:
        new_bot = BotTable(
            **data.model_dump(),
            deal=DealTable(),
            orders=[],
        )

        with self._get_session() as s:
            s.add(new_bot)
            s.commit()
            s.refresh(new_bot)
            s.expunge(new_bot)

        return new_bot

    def save(self, data: Union[BotModel, BotTable]) -> BotTable:
        with self._get_session() as s:
            # Fetch the existing bot from DB (already attached to session)
            bot_row = s.get(BotTable, UUID(str(data.id)))
            if not bot_row:
                raise SaveBotError("Bot not found")

            if not bot_row.deal:
                raise SaveBotError("Bot must have associated deal")

            # Convert BotModel to BotTable if needed (detached)
            data_table = self.update_table(data)

            # Update scalar fields on the managed bot_row
            for field_name in BotTable.model_fields.keys():
                if field_name in {"id", "deal", "orders", "deal_id"}:
                    continue
                if hasattr(data_table, field_name):
                    setattr(bot_row, field_name, getattr(data_table, field_name))

            # Update deal fields (preserve existing deal.id)
            for field_name in DealTable.model_fields.keys():
                if field_name in {"id", "bot", "paper_trading"}:
                    continue
                if hasattr(data_table.deal, field_name):
                    setattr(
                        bot_row.deal, field_name, getattr(data_table.deal, field_name)
                    )

            # Sync orders
            for order_data in getattr(data_table, "orders", []):
                existing = s.exec(
                    select(ExchangeOrderTable).where(
                        ExchangeOrderTable.order_id == str(order_data.order_id)
                    )
                ).first()

                if existing:
                    for field_name in ExchangeOrderTable.model_fields.keys():
                        if field_name in {"id", "bot", "bot_id"}:
                            continue
                        if hasattr(order_data, field_name):
                            setattr(
                                existing, field_name, getattr(order_data, field_name)
                            )
                else:
                    new_order = ExchangeOrderTable.model_construct(
                        **order_data.model_dump(exclude={"id", "bot"})
                    )
                    new_order.bot_id = bot_row.id
                    s.add(new_order)

            s.add(bot_row)
            s.commit()
            s.refresh(bot_row)
            s.expunge(bot_row)

            return bot_row

    def delete(self, bot_ids: List[str]) -> List[str]:
        with self._get_session() as s:
            for id_str in bot_ids:
                bot = s.get(BotTable, UUID(id_str))
                if bot:
                    s.delete(bot)
            s.commit()

        return bot_ids

    # --------------------------------------------------
    # Orders
    # --------------------------------------------------

    def get_order(self, order_id: str) -> ExchangeOrderTable:
        with self._get_session() as s:
            order = s.exec(
                select(ExchangeOrderTable).where(
                    ExchangeOrderTable.order_id == order_id
                )
            ).first()

            if not order:
                raise BinbotErrors("Order not found")

            s.expunge(order)
            return order

    def update_order(self, order: OrderModel) -> ExchangeOrderTable:
        with self._get_session() as s:
            existing = s.exec(
                select(ExchangeOrderTable).where(
                    ExchangeOrderTable.order_id == str(order.order_id)
                )
            ).first()

            if not existing:
                raise BinbotErrors("Order not found")

            existing.sqlmodel_update(order.model_dump())

            s.add(existing)
            s.commit()
            s.refresh(existing)
            s.expunge(existing)

            return existing

    # --------------------------------------------------
    # Utility
    # --------------------------------------------------

    def get_active_pairs(self) -> Sequence[str]:
        stmt = select(BotTable.pair).where(BotTable.status == Status.active)

        with self._get_session() as s:
            return s.exec(stmt).all()
