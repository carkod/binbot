from typing import List, Optional
from uuid import UUID
from fastapi import Query
from sqlmodel import Session, asc, desc, or_, select, case
from time import time
from bots.models import BotModel
from database.models.bot_table import BotBase, BotTable
from database.models.deal_table import DealTable
from database.utils import independent_session
from tools.enum_definitions import BinbotEnums, Status


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
    ) -> BotModel:
        """
        Update logs for a bot

        Args:
        - bot_id: str
        - bot: BotModel

        Either id or bot has to be passed
        """
        if bot_id:
            bot_obj = self.session.get(BotTable, bot_id)
            bot = BotModel.model_validate(bot_obj)
        elif not bot:
            raise ValueError("Bot id or BotModel object is required")

        current_logs: list[str] = bot.logs
        if len(current_logs) == 0:
            current_logs = [log_message]
        elif len(current_logs) > 0:
            current_logs.append(log_message)

        bot.logs = current_logs

        # db operations
        self.session.add(bot)
        self.session.commit()
        self.session.refresh(bot)
        self.session.close()
        return bot

    def get(
        self,
        status: Status | None = None,
        start_date: float | None = None,
        end_date: float | None = None,
        no_cooldown=False,
        limit: int = 200,
        offset: int = 0,
    ):
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

        bots = self.session.exec(statement).all()
        self.session.close()

        return bots

    def get_one(
        self,
        bot_id: str | None = None,
        symbol: str | None = None,
        status: Status | None = None,
    ) -> BotModel:
        """
        Get one bot by id or symbol
        """
        if bot_id:
            bot = self.session.get(BotTable, UUID(bot_id))
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
        else:
            raise ValueError("Invalid bot id or symbol")

        self.session.close()
        bot_model = BotModel.model_validate(bot)
        return bot_model

    def create(self, data: BotBase) -> BotModel:
        """
        Create a new bot

        It's crucial to reset fields, so bot can trigger base orders
        and start trailling.

        Args:
        - data: BotBase includes only flat properties (excludes deal and orders which are generated internally)
        """
        bot = BotModel.model_validate(data)

        # Ensure values are reset
        bot.orders = []
        bot.logs = []
        bot.status = Status.inactive

        # db operations
        self.session.add(bot)
        self.session.commit()
        resulted_bot = self.session.get(BotTable, bot.id)
        self.session.close()
        data = BotModel.model_validate(resulted_bot)
        return data

    def save(self, data: BotModel) -> BotModel:
        """
        Save bot

        This can be an edit of an entire object
        or just a few fields
        """
        bot = self.session.get(BotTable, data.id)
        if not bot:
            raise ValueError("Bot not found")

        # double check orders and deal are not overwritten
        dumped_bot = data.model_dump(exclude_unset=True)
        bot.sqlmodel_update(dumped_bot)
        self.session.add(bot)
        self.session.commit()
        resulted_bot = self.session.get(BotTable, bot.id)
        self.session.close()
        data = BotModel.model_validate(resulted_bot)
        return data

    def delete(self, bot_ids: List[str] = Query(...)):
        """
        Delete by multiple ids.
        For a single id, pass one id in a list
        """
        statement = select(BotTable)
        for id in bot_ids:
            statement.where(BotTable.id == id)
        bots = self.session.exec(statement).all()
        self.session.commit()
        self.session.close()
        return bots

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
        return list(pairs)
