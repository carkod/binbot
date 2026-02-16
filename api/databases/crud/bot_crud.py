from typing import List, Sequence, Union
from uuid import UUID
from sqlmodel import Session, select, asc, desc, case
from sqlalchemy.orm.attributes import flag_modified

from bots.models import BotModel, OrderModel
from databases.tables.bot_table import BotTable
from databases.tables.deal_table import DealTable
from databases.tables.order_table import ExchangeOrderTable
from pybinbot import (
    Status,
    Strategy,
    ts_to_humandate,
    timestamp,
    SaveBotError,
    BinbotErrors,
    BotBase,
)
from databases.utils import get_session


class BotTableCrud:
    """
    CRUD for BotTable.
    Session can be injected or auto-created internally.
    All methods return ORM objects (BotTable), conversion to BotModel happens in service layer.
    """

    def __init__(self, session: Session | None = None):
        self._external_session = session

    @property
    def session(self) -> Session:
        """
        Provide a session. If an external session is passed, use it.
        Otherwise, open a temporary context-managed session for the operation.
        """
        if self._external_session:
            return self._external_session
        return get_session()  # returns a context manager

        # Helper to ensure we always work with BotTable

    @staticmethod
    def _ensure_table(bot: Union[BotModel, BotTable]) -> BotTable:
        if isinstance(bot, BotModel):
            # Convert BotModel → BotTable
            return BotTable.from_model(bot)
        return bot

    # ------------------- Logs -------------------
    def update_logs(
        self, log_message: str | list[str], bot: Union[BotModel, BotTable]
    ) -> BotTable:
        bot = self._ensure_table(bot)
        if not bot:
            raise BinbotErrors("Bot not found")

        ts = ts_to_humandate(ts=timestamp())

        if isinstance(log_message, list):
            new_logs = [f"[{ts}] {msg}" for msg in log_message]
            bot.logs = new_logs + bot.logs
        else:
            bot.logs.append(f"[{ts}] {log_message}")

        flag_modified(bot, "logs")

        with self.session as s:
            s.add(bot)
            s.commit()
            s.refresh(bot)

        return bot

    # ------------------- Getters -------------------
    def get(
        self,
        status: Status | None = None,
        start_date: float | None = None,
        end_date: float | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> Sequence[BotTable]:
        stmt = select(BotTable)
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

        with self.session as s:
            return s.exec(stmt).unique().all()

    def get_one(
        self,
        bot_id: str | None = None,
        symbol: str | None = None,
        status: Status | None = None,
        strategy: Strategy | None = None,
    ) -> BotTable:

        with self.session as s:
            if bot_id:
                bot = s.get(BotTable, UUID(bot_id))
                if not bot:
                    raise BinbotErrors("Bot not found")
                return bot

            if symbol:
                status_filter = None if status == Status.all else status
                stmt = select(BotTable).where(BotTable.pair == symbol)
                if status_filter:
                    stmt = stmt.where(BotTable.status == status_filter)
                elif strategy:
                    stmt = stmt.where(BotTable.strategy == strategy)

                bot = s.exec(stmt).first()
                if not bot:
                    raise BinbotErrors("Bot not found")
                return bot

        raise BinbotErrors("Invalid bot id or symbol")

    # ------------------- Create/Save/Delete -------------------
    def create(self, data: BotBase) -> BotTable:
        new_bot = BotTable(**data.model_dump(), deal=DealTable(), orders=[])
        with self.session as s:
            s.add(new_bot)
            s.commit()
            s.refresh(new_bot)
        return new_bot

    def save(self, data: Union[BotModel, BotTable]) -> BotTable:
        data = self._ensure_table(data)
        with self.session as s:
            bot_row = s.get(BotTable, data.id)
            if not bot_row:
                raise SaveBotError("Bot not found")

            # Sync scalar fields
            bot_row.sqlmodel_update(data.model_dump())

            # Deal sync
            deal = s.get(DealTable, bot_row.deal_id)
            if not deal:
                raise SaveBotError("Bot must have an associated deal")
            deal.sqlmodel_update(data.deal.model_dump())
            bot_row.deal = deal

            # Orders sync
            if hasattr(data, "orders"):
                for order in data.orders:
                    existing_order = s.exec(
                        select(ExchangeOrderTable).where(
                            ExchangeOrderTable.order_id == order.order_id
                        )
                    ).first()
                    if not existing_order:
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
                            bot_id=data.id,
                        )
                        s.add(new_order)

            s.add(bot_row)
            s.commit()
            s.refresh(bot_row)
        return bot_row

    def delete(self, bot_ids: List[str]) -> List[str]:
        with self.session as s:
            for id_str in bot_ids:
                bot = s.get(BotTable, UUID(id_str))
                if bot:
                    s.delete(bot)
            s.commit()
        return bot_ids

    # ------------------- Orders -------------------
    def get_order(self, order_id: str) -> ExchangeOrderTable:
        with self.session as s:
            order = s.exec(
                select(ExchangeOrderTable).where(
                    ExchangeOrderTable.order_id == order_id
                )
            ).first()
            if not order:
                raise BinbotErrors("Order not found")
            return order

    def update_order(self, order: OrderModel) -> ExchangeOrderTable:
        with self.session as s:
            existing = self.get_order(str(order.order_id))
            existing.sqlmodel_update(order.model_dump())
            s.add(existing)
            s.commit()
            s.refresh(existing)
        return existing

    # ------------------- Utility -------------------
    def get_active_pairs(self) -> Sequence[str]:
        stmt = select(BotTable.pair).where(BotTable.status == Status.active)
        with self.session as s:
            return s.exec(stmt).all()
