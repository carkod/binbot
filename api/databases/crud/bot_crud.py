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

    @staticmethod
    def _ensure_table(bot: Union[BotModel, BotTable]) -> BotTable:
        if isinstance(bot, BotModel):
            bot_payload = bot.model_dump(exclude={"deal", "orders"})
            bot_table = BotTable(**bot_payload)

            bot_table.deal = DealTable(**bot.deal.model_dump())
            bot_table.orders = [
                ExchangeOrderTable(**order.model_dump()) for order in bot.orders
            ]
            return bot_table
        return bot

    def update_logs(
        self, log_message: str | list[str], bot: Union[BotModel, BotTable]
    ) -> BotTable:
        if not bot:
            raise BinbotErrors("Bot not found")

        bot_table = self._ensure_table(bot)
        ts = ts_to_humandate(ts=timestamp())

        if isinstance(log_message, list):
            new_logs = [f"[{ts}] {msg}" for msg in log_message]
            bot_table.logs = new_logs + bot_table.logs
        else:
            bot_table.logs.append(f"[{ts}] {log_message}")

        flag_modified(bot_table, "logs")

        with self._get_session() as s:
            s.add(bot_table)
            s.commit()
            s.refresh(bot_table)

        return bot_table

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
            return s.exec(stmt).unique().all()

    def get_one(
        self,
        bot_id: str | None = None,
        symbol: str | None = None,
        status: Status | None = None,
        strategy: Strategy | None = None,
    ) -> BotTable:

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

        with self._get_session() as s:
            bot = s.exec(stmt).first()

            if not bot:
                raise BinbotErrors("Bot not found")

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

        return new_bot

    def save(self, data: Union[BotModel, BotTable]) -> BotTable:
        bot_table = self._ensure_table(data)

        with self._get_session() as s:
            bot_row = s.get(BotTable, bot_table.id)

            if not bot_row:
                raise SaveBotError("Bot not found")

            # ---- Sync scalar fields
            bot_row.sqlmodel_update(bot_table.model_dump())

            # ---- Sync Deal
            deal = s.get(DealTable, bot_row.deal.id)

            if not deal:
                raise SaveBotError("Bot must have associated deal")

            deal.sqlmodel_update(bot_table.deal.model_dump())
            bot_row.deal = deal

            # ---- Sync Orders
            if hasattr(bot_table, "orders"):
                for order in bot_table.orders:
                    existing = s.exec(
                        select(ExchangeOrderTable).where(
                            ExchangeOrderTable.order_id == order.order_id
                        )
                    ).first()

                    if not existing:
                        new_order = ExchangeOrderTable(
                            order_type=order.order_type,
                            time_in_force=order.time_in_force,
                            timestamp=order.timestamp,
                            order_id=str(order.order_id),
                            order_side=order.order_side,
                            pair=order.pair,
                            qty=order.qty,
                            status=order.status,
                            price=order.price,
                            deal_type=order.deal_type,
                            bot_id=bot_table.id,
                        )
                        s.add(new_order)

            s.add(bot_row)
            s.commit()
            s.refresh(bot_row)

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

            return existing

    # --------------------------------------------------
    # Utility
    # --------------------------------------------------

    def get_active_pairs(self) -> Sequence[str]:
        stmt = select(BotTable.pair).where(BotTable.status == Status.active)

        with self._get_session() as s:
            return s.exec(stmt).all()
