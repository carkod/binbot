import re
from typing import Any, List, cast
from uuid import UUID
from sqlmodel import Session, select, case, desc, asc
from sqlalchemy.orm import QueryableAttribute, selectinload
from databases.tables.bot_table import PaperTradingTable
from bots.models import BotModel
from databases.utils import detach_bot_graph, get_db_session
from pybinbot import Status, BotBase, BinbotErrors, SaveBotError
from collections.abc import Sequence
from databases.tables.deal_table import DealTable
from databases.tables.order_table import FakeOrderTable
from sqlalchemy.orm.attributes import flag_modified


PAPER_DEAL_REL = cast(QueryableAttribute[Any], PaperTradingTable.deal)
PAPER_ORDERS_REL = cast(QueryableAttribute[Any], PaperTradingTable.orders)


class PaperTradingTableCrud:
    def __init__(self, session: Session | None = None):
        self._external_session = session
        self.session = session

    def update_logs(
        self, log_message: str | list[str], bot: BotModel = None
    ) -> PaperTradingTable:
        """
        Update logs for a bot

        Args:
        - bot: BotModel

        bot has to be passed
        for bot_id use endpoint function to get BotModel
        """
        if not bot:
            raise BinbotErrors("Bot id or BotModel object is required")

        with get_db_session(self._external_session) as s:
            bot_result = s.get(PaperTradingTable, UUID(str(bot.id)))
            if not bot_result:
                raise BinbotErrors("Bot not found")

            # Update logs as an SQLAlchemy list
            bot_result.logs = [log_message] + bot_result.logs
            flag_modified(bot_result, "logs")

            s.add(bot_result)
            s.commit()
            s.refresh(bot_result)
            detach_bot_graph(s, bot_result)
            return bot_result

    def get(
        self,
        status: Status | None = None,
        start_date: float | None = None,
        end_date: float | None = None,
        limit: int = 200,
        offset: int = 0,
        bot_name: str | None = None,
    ) -> Sequence[PaperTradingTable]:
        """
        Get all bots in the db except archived
        Args:
        - status: Status enum
        - start_date and end_date are timestamps in milliseconds
        - limit and offset for pagination
        """
        statement = select(PaperTradingTable).options(
            selectinload(PAPER_DEAL_REL),
            selectinload(PAPER_ORDERS_REL),
        )

        if status and status in list(Status) and status != Status.all:
            statement = statement.where(PaperTradingTable.status == status)

        if start_date:
            statement = statement.where(PaperTradingTable.created_at >= start_date)

        if end_date:
            statement = statement.where(PaperTradingTable.created_at <= end_date)

        if bot_name:
            bot_name = re.sub(r"[^\w\s\-']", "", bot_name.strip())
            statement = statement.where(PaperTradingTable.name == bot_name)

        # sorting
        statement = statement.order_by(
            desc(PaperTradingTable.created_at),
            case((PaperTradingTable.status == Status.active, 1), else_=2),
            asc(PaperTradingTable.pair),
        )

        # pagination
        statement = statement.limit(limit).offset(offset)

        with get_db_session(self._external_session) as s:
            bots = s.exec(statement).unique().all()
            for bot in bots:
                detach_bot_graph(s, bot)
            return bots

    def get_one(
        self,
        bot_id: str | None = None,
        symbol: str | None = None,
        status: Status | None = None,
    ) -> PaperTradingTable:
        """
        Get one bot by id or symbol
        """
        statement = select(PaperTradingTable).options(
            selectinload(PAPER_DEAL_REL),
            selectinload(PAPER_ORDERS_REL),
        )

        if bot_id:
            statement = statement.where(PaperTradingTable.id == UUID(bot_id))
        elif symbol:
            statement = statement.where(PaperTradingTable.pair == symbol)
            if status:
                statement = statement.where(PaperTradingTable.status == status)
        else:
            raise BinbotErrors("Invalid bot id or symbol")

        with get_db_session(self._external_session) as s:
            bot = s.exec(statement).first()
            if not bot:
                raise BinbotErrors("Bot not found")
            detach_bot_graph(s, bot)
            return bot

    def create(self, data: BotBase) -> PaperTradingTable:
        """
        Create a new paper trading bot
        """
        bot = PaperTradingTable(**data.model_dump(), deal=DealTable(), orders=[])

        with get_db_session(self._external_session) as s:
            s.add(bot)
            s.commit()
            s.refresh(bot)
            detach_bot_graph(s, bot)
            return bot

    def save(self, data: BotModel) -> PaperTradingTable:
        """
        Save operation
        This can be editing a bot, or saving the object,
        or updating a single field.
        """
        with get_db_session(self._external_session) as s:
            initial_bot = s.exec(
                select(PaperTradingTable)
                .options(
                    selectinload(PAPER_DEAL_REL),
                    selectinload(PAPER_ORDERS_REL),
                )
                .where(PaperTradingTable.id == UUID(str(data.id)))
            ).first()
            if not initial_bot:
                raise SaveBotError("Bot not found")

            deal_id = initial_bot.deal_id
            initial_bot.sqlmodel_update(
                data.model_dump(exclude={"id", "deal", "orders", "deal_id"})
            )

            deal = s.get(DealTable, deal_id)
            if not deal:
                raise SaveBotError("Bot must be created first before updating")
            deal.sqlmodel_update(data.deal.model_dump())

            for order in data.orders:
                statement = select(FakeOrderTable).where(
                    FakeOrderTable.paper_trading_id == UUID(str(data.id)),
                    FakeOrderTable.deal_type == order.deal_type,
                )
                get_order = s.exec(statement).first()
                if not get_order:
                    s.add(
                        FakeOrderTable(
                            order_type=order.order_type,
                            time_in_force=order.time_in_force,
                            timestamp=order.timestamp,
                            order_id=order.order_id,
                            order_side=order.order_side,
                            pair=order.pair,
                            qty=order.qty,
                            status=order.status,
                            price=order.price,
                            deal_type=order.deal_type,
                            paper_trading_id=UUID(str(data.id)),
                        )
                    )

            s.add(deal)
            s.add(initial_bot)
            s.commit()
            s.refresh(deal)
            s.refresh(initial_bot)
            detach_bot_graph(s, initial_bot)
            return initial_bot

    def delete(self, bot_ids: List[str]) -> bool:
        """
        Delete a paper trading account by id
        """
        with get_db_session(self._external_session) as s:
            for id_value in bot_ids:
                sanitized_id = UUID(id_value)

                statement = select(PaperTradingTable).where(
                    PaperTradingTable.id == sanitized_id
                )
                bot = s.exec(statement).first()
                if bot:
                    s.delete(bot)

            s.commit()
        return True

    def delete_order(self, order_id: str, bot_id: str | None = None) -> str:
        statement = select(FakeOrderTable).where(FakeOrderTable.order_id == order_id)
        if bot_id:
            statement = statement.where(FakeOrderTable.paper_trading_id == UUID(bot_id))

        with get_db_session(self._external_session) as s:
            order = s.exec(statement).first()
            if not order:
                raise BinbotErrors("Order not found")

            s.delete(order)
            s.commit()
            return str(order_id)

    def update_status(self, paper_trading: BotModel, status: Status) -> BotModel:
        """
        Activate a paper trading account
        """
        with get_db_session(self._external_session) as s:
            bot = s.get(PaperTradingTable, UUID(str(paper_trading.id)))
            if not bot:
                raise BinbotErrors("Bot not found")
            bot.status = status
            s.add(bot)
            s.commit()
            paper_trading.status = status
            return paper_trading

    def get_active_pairs(self):
        """
        Get all active bots
        """
        with get_db_session(self._external_session) as s:
            return s.exec(
                select(PaperTradingTable.pair).where(
                    PaperTradingTable.status == Status.active
                )
            ).all()
