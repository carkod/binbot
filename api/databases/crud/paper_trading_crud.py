from typing import List
from sqlmodel import Session, select, case, desc, asc
from tools.exceptions import BinbotErrors, SaveBotError
from databases.tables.bot_table import PaperTradingTable
from bots.models import BotModel, BotBase
from databases.utils import independent_session
from pybinbot.enum import Status
from collections.abc import Sequence
from uuid import UUID
from databases.tables.deal_table import DealTable
from databases.tables.order_table import FakeOrderTable
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import text


class PaperTradingTableCrud:
    def __init__(self, session: Session | None = None):
        if session is None:
            session = independent_session()
        self.session = session
        pass

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
        if bot:
            bot_id = str(bot.id)
        else:
            raise BinbotErrors("Bot id or BotModel object is required")

        bot_result = self.session.get(PaperTradingTable, bot_id)

        if not bot_result:
            raise BinbotErrors("Bot not found")

        # Update logs as an SQLAlchemy list
        bot_result.logs = [log_message] + bot_result.logs
        flag_modified(bot_result, "logs")

        # db operations
        self.session.add(bot_result)
        self.session.commit()
        self.session.refresh(bot_result)
        self.session.close()
        return bot_result

    def _explain_query(self, statement):
        """
        Test performance of a query
        """
        explain_query = text(f"EXPLAIN {statement}")
        explain_result = self.session.execute(explain_query)
        for row in explain_result:
            print(row)

        pass

    def get(
        self,
        status: Status | None = None,
        start_date: float | None = None,
        end_date: float | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> Sequence[PaperTradingTable]:
        """
        Get all bots in the db except archived
        Args:
        - status: Status enum
        - start_date and end_date are timestamps in milliseconds
        - limit and offset for pagination
        """
        statement = select(PaperTradingTable)

        if status and status in list(Status) and status != Status.all:
            statement = statement.where(PaperTradingTable.status == status)

        if start_date:
            statement = statement.where(PaperTradingTable.created_at >= start_date)

        if end_date:
            statement = statement.where(PaperTradingTable.created_at <= end_date)

        # sorting
        statement = statement.order_by(
            desc(PaperTradingTable.created_at),
            case((PaperTradingTable.status == Status.active, 1), else_=2),
            asc(PaperTradingTable.pair),
        )

        # pagination
        statement = statement.limit(limit).offset(offset)

        bots = self.session.exec(statement).unique().all()
        self.session.close()

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
        if bot_id:
            santize_uuid = UUID(bot_id)
            bot = self.session.get(PaperTradingTable, santize_uuid)
            if not bot:
                raise BinbotErrors("Bot not found")
            return bot
        elif symbol:
            if status:
                bot = self.session.exec(
                    select(PaperTradingTable).where(
                        PaperTradingTable.pair == symbol,
                        PaperTradingTable.status == status,
                    )
                ).first()
            else:
                bot = self.session.exec(
                    select(PaperTradingTable).where(PaperTradingTable.pair == symbol)
                ).first()
            if not bot:
                raise BinbotErrors("Bot not found")
            return bot
        else:
            raise BinbotErrors("Invalid bot id or symbol")

    def create(self, data: BotBase) -> PaperTradingTable:
        """
        Create a new paper trading bot
        """
        bot = PaperTradingTable(**data.model_dump(), deal=DealTable(), orders=[])

        # db operations
        self.session.add(bot)
        self.session.commit()
        self.session.refresh(bot)
        resulted_bot = bot
        return resulted_bot

    def save(self, data: BotModel) -> PaperTradingTable:
        """
        Save operation
        This can be editing a bot, or saving the object,
        or updating a single field.
        """
        # due to incompatibility of SQLModel and Pydantic
        initial_bot = self.get_one(bot_id=str(data.id))
        deal_id = initial_bot.deal_id
        initial_bot.sqlmodel_update(data.model_dump())

        # Use deal id from db to avoid creating a new deal
        # which causes integrity errors
        # there should always be only 1 deal per bot
        deal = self.session.get(DealTable, deal_id)
        if not deal:
            raise SaveBotError("Bot must be created first before updating")
        else:
            deal.sqlmodel_update(data.deal.model_dump())

        if hasattr(data, "orders"):
            for order in data.orders:
                # Unlike real exchange orders,
                # these orders are faked
                statement = select(FakeOrderTable).where(
                    FakeOrderTable.paper_trading_id == data.id,
                    FakeOrderTable.deal_type == order.deal_type,
                )
                get_order = self.session.exec(statement).first()
                if not get_order:
                    new_order_row = FakeOrderTable(
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
                        paper_trading_id=data.id,
                    )
                    self.session.add(new_order_row)

        self.session.add(deal)
        self.session.add(initial_bot)
        self.session.commit()
        self.session.refresh(deal)
        self.session.refresh(initial_bot)
        resulted_bot = initial_bot
        self.session.close()
        return resulted_bot

    def delete(self, bot_ids: List[str]) -> bool:
        """
        Delete a paper trading account by id
        """
        for id in bot_ids:
            statement = select(PaperTradingTable).where(PaperTradingTable.id == id)
            bot = self.session.exec(statement).first()
            self.session.delete(bot)

        self.session.commit()
        self.session.close()
        return True

    def update_status(self, paper_trading: BotModel, status: Status) -> BotModel:
        """
        Activate a paper trading account
        """
        paper_trading.status = status
        self.session.add(paper_trading)
        self.session.commit()
        self.session.close()
        return paper_trading

    def get_active_pairs(self):
        """
        Get all active bots
        """
        bots = self.session.exec(
            select(PaperTradingTable.pair).where(
                PaperTradingTable.status == Status.active
            )
        ).all()
        self.session.close()
        return bots
