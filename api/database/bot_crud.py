from typing import List, Optional
from uuid import UUID
from fastapi import Query
from sqlmodel import Session, asc, desc, or_, select, case
from time import time
from bots.models import BotModel
from database.models.bot_table import BotTable
from database.models.deal_table import DealTable
from database.models.order_table import ExchangeOrderTable
from database.utils import independent_session
from tools.enum_definitions import BinbotEnums, Status
from bots.models import BotBase
from collections.abc import Sequence
from sqlalchemy.orm.attributes import flag_modified


class BotTableCrud:
    """
    CRUD and database operations for the SQL API DB
    bot_table table.

    Use for lower level APIs that require a session
    e.g.
    client-side -> receive json -> bots.routes -> BotModelCrud
    """

    def __init__(
        self,
        # Some instances of AutotradeSettingsController are used outside of the FastAPI context
        # this is designed this way for reusability
        session: Session | None = None,
    ):
        if session is None:
            session = independent_session()
        self.session = session

    def update_logs(
        self,
        log_message: str,
        bot: Optional[BotModel] = None,
        bot_id: str | None = None,
    ) -> BotTable:
        """
        Update logs for a bot

        Args:
        - bot_id: str
        - bot: BotModel

        Either id or bot has to be passed
        """
        if bot:
            bot_id = str(bot.id)
        elif not bot and not bot_id:
            raise ValueError("Bot id or BotModel object is required")

        bot_result = self.session.get(BotTable, bot_id)

        if not bot_result:
            raise ValueError("Bot not found")

        # Update logs as an SQLAlchemy list
        bot_result.logs = [log_message] + bot_result.logs
        flag_modified(bot_result, "logs")

        # db operations
        self.session.add(bot_result)
        self.session.commit()
        self.session.refresh(bot_result)
        self.session.close()
        return bot_result

    def get(
        self,
        status: Status | None = None,
        start_date: float | None = None,
        end_date: float | None = None,
        no_cooldown=False,
        limit: int = 200,
        offset: int = 0,
    ) -> Sequence[BotTable]:
        """
        Get all bots in the db except archived
        Args:
        - status: Status enum
        - start_date and end_date are timestamps in milliseconds
        - no_cooldown: bool - filter out bots that are in cooldown
        - limit and offset for pagination
        """
        statement = select(BotTable)

        if status and status in BinbotEnums.statuses:
            statement.where(BotTable.status == status)

        if start_date:
            statement.where(BotTable.created_at >= start_date)

        if end_date:
            statement.where(BotTable.created_at <= end_date)

        if status and no_cooldown:
            current_timestamp = time()
            cooldown_condition = cooldown_condition = or_(
                BotTable.status == status,
                case(
                    (
                        (DealTable.sell_timestamp > 0),
                        current_timestamp - DealTable.sell_timestamp
                        < (BotTable.cooldown * 1000),
                    ),
                    else_=(
                        current_timestamp - BotTable.created_at
                        < (BotTable.cooldown * 1000)
                    ),
                ),
            )

            statement.where(cooldown_condition)

        # sorting
        statement.order_by(
            desc(BotTable.created_at),
            case((BotTable.status == Status.active, 1), else_=2),
            asc(BotTable.pair),
        )

        # pagination
        statement.limit(limit).offset(offset)

        # unique is necessary for a joinload
        bots = self.session.exec(statement).unique().all()
        self.session.close()
        return bots

    def get_one(
        self,
        bot_id: Optional[str] = None,
        symbol: Optional[str] = None,
        status: Status | None = None,
    ) -> BotTable:
        """
        Get one bot by id or symbol

        If only bot_id is passed, it will always match 1, so status doesn't matter too much.
        If only symbol is passed, it is possible to match more than one so more specificity is needed. Therefore, status is used too.
        """
        if bot_id:
            santize_uuid = UUID(bot_id)
            bot = self.session.get(BotTable, santize_uuid)
            if not bot:
                raise ValueError("Bot not found")
            return bot
        elif symbol:
            if status:
                bot = self.session.exec(
                    select(BotTable).where(
                        BotTable.pair == symbol, BotTable.status == status
                    )
                ).first()
            else:
                bot = self.session.exec(
                    select(BotTable).where(BotTable.pair == symbol)
                ).first()
            if not bot:
                raise ValueError("Bot not found")
            return bot
        else:
            raise ValueError("Invalid bot id or symbol")

    def create(self, data: BotBase) -> BotTable:
        """
        Create a new bot

        It's crucial to reset fields, so bot can trigger base orders
        and start trailling.

        Args:
        - data: BotBase includes only flat properties (excludes deal and orders which are generated internally)
        """

        new_bot = BotTable(**data.model_dump(), deal=DealTable(), orders=[])

        # db operations
        self.session.add(new_bot)
        self.session.commit()
        self.session.refresh(new_bot)
        resulted_bot = new_bot
        return resulted_bot

    def save(self, data: BotModel) -> BotTable:
        """
        Save bot

        This can be an edit of an entire object
        or just a few fields
        """
        # due to incompatibility of SQLModel and Pydantic
        initial_bot = self.get_one(bot_id=str(data.id))
        initial_bot.sqlmodel_update(data.model_dump())

        # Handle deal update
        deal = self.session.get(DealTable, str(initial_bot.deal.id))
        if not deal:
            initial_bot.deal = DealTable()
        else:
            deal.sqlmodel_update(data.deal)
            initial_bot.deal = deal

        # Handle orders update
        initial_bot.orders.clear()
        for order in data.orders:
            new_order_row = ExchangeOrderTable(**order.model_dump())
            initial_bot.orders.append(new_order_row)

        self.session.add(initial_bot)
        self.session.commit()
        self.session.refresh(initial_bot)
        resulted_bot = initial_bot
        return resulted_bot

    def delete(self, bot_ids: List[str] = Query(...)):
        """
        Delete by multiple ids.
        For a single id, pass one id in a list
        """
        for id in bot_ids:
            statement = select(BotTable).where(BotTable.id == id)
            bot = self.session.exec(statement).first()
            self.session.delete(bot)

        self.session.commit()
        self.session.close()
        return bot_ids

    def update_status(self, bot: BotModel, status: Status) -> BotModel:
        """
        Mostly as a replacement of the previous "activate" and "deactivate"
        although any Status can be passed now
        """
        bot.status = status
        self.save(bot)
        return bot

    def get_active_pairs(self) -> list:
        """
        Get all active pairs

        a replacement of the previous "distinct pairs" query
        """
        statement = (
            select(BotTable.pair).where(BotTable.status == Status.active).distinct()
        )
        pairs = self.session.exec(statement).all()
        self.session.close()
        if not pairs:
            return []
        return list(pairs)
