from typing import List, Optional
from uuid import UUID
from fastapi import Query
from sqlmodel import Session, asc, desc, or_, select, case, col
from time import time
from bots.models import BotModel
from database.models.bot_table import BotTable
from database.models.deal_table import DealTable
from database.utils import independent_session
from tools.enum_definitions import BinbotEnums, Status
from bots.models import BotBase
from collections.abc import Sequence
from sqlalchemy import delete, update


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
        if bot_id:
            bot_obj = self.session.get(BotTable, bot_id)
            if not bot_obj:
                raise ValueError("Bot not found")
            # No validation needed, this is a trusted source
            bot = BotModel.model_construct(**bot_obj.model_dump())
        elif not bot:
            raise ValueError("Bot id or BotModel object is required")

        current_logs: list[str] = bot.logs
        if len(current_logs) == 0:
            current_logs = [log_message]
        elif len(current_logs) > 0:
            current_logs.append(log_message)

        bot_table_model = BotTable.model_validate(bot.model_dump())
        bot_table_model.logs = current_logs

        # db operations
        self.session.add(bot_table_model)
        self.session.commit()
        self.session.refresh(bot_table_model)
        self.session.close()
        return bot_table_model

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

        bots = self.session.exec(statement).all()
        self.session.close()
        return bots

    def get_one(
        self,
        bot_id: str | None = None,
        symbol: str | None = None,
        status: Status | None = None,
    ) -> BotTable:
        """
        Get one bot by id or symbol
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

    def create(self, data: BotBase) -> BotModel:
        """
        Create a new bot

        It's crucial to reset fields, so bot can trigger base orders
        and start trailling.

        Args:
        - data: BotBase includes only flat properties (excludes deal and orders which are generated internally)
        """
        bot = BotModel.model_construct(**data.model_dump())
        deal = bot.deal

        # db operations
        serialised_bot = BotTable.model_validate(data)
        serialised_deal = DealTable.model_validate(deal)

        self.session.add(serialised_bot)
        self.session.add(serialised_deal)

        self.session.commit()
        self.session.refresh(serialised_bot)
        self.session.refresh(serialised_deal)
        self.session.close()
        resulted_bot = self.session.get(BotTable, serialised_bot.id)
        if resulted_bot:
            bot_model = BotModel.model_validate(resulted_bot.model_dump())
        else:
            bot_model = bot
        return bot_model

    def save(self, data: BotModel) -> BotTable:
        """
        Save bot

        This can be an edit of an entire object
        or just a few fields
        """
        # due to incompatibility of SQLModel and Pydantic
        statement = update(BotTable).where(BotTable.id == data.id)
        self.session.connection().execute(statement, data.model_dump())
        self.session.commit()
        self.session.close()
        resulted_bot = self.get_one(bot_id=str(data.id))
        return resulted_bot

    def delete(self, bot_ids: List[str] = Query(...)):
        """
        Delete by multiple ids.
        For a single id, pass one id in a list
        """
        statement = delete(BotTable).where(col(BotTable.id).in_(bot_ids))
        # exec doesn't pass mypy
        bots = self.session.connection().execute(statement)
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
