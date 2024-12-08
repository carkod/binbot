import json
from typing import List
from fastapi import Query
from sqlmodel import Session, asc, desc, or_, select, case
from time import time
from bots.schemas import BotSchema
from database.models.bot_table import BotTable
from database.models.deal_table import DealTable
from database.utils import independent_session
from tools.enum_definitions import BinbotEnums, Status


class BotTableCrud:
    """
    CRUD and database operations for the SQL API DB
    bot_table table.

    Use for lower level APIs that require a session
    e.g.
    client-side -> receive json -> bots.routes -> BotTableCrud
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
        self, log_message: str, bot: BotSchema = None, bot_id: str | None = None
    ):
        """
        Update logs for a bot

        Args:
        - bot_id: str
        - bot: BotSchema

        Either id or bot has to be passed
        """
        if bot_id:
            bot_object: BotTable | BotSchema = self.session.get(BotTable, bot_id)
        elif not bot:
            raise ValueError("Bot id or BotSchema | BotTable object is required")

        bot_object = bot

        current_logs: list[str] = json.loads(bot_object.logs)
        if not current_logs or len(current_logs) == 0:
            current_logs = [log_message]
        elif len(current_logs) > 0:
            current_logs.append(log_message)

        bot_object.logs = json.dumps(current_logs)

        # db operations
        self.session.add(bot_object)
        self.session.commit()
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
    ):
        """
        Get one bot by id or symbol
        """
        if bot_id:
            bot = self.session.get(BotTable, bot_id)
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
        return bot

    def create(self, data: BotTable) -> BotTable:
        """
        Create a new bot

        It's crucial to reset fields, so bot can trigger base orders
        and start trailling.
        """
        bot = BotTable.model_validate(data)
        # Ensure values are reset
        bot.orders = []
        bot.logs = []
        bot.created_at = time() * 1000
        bot.updated_at = time() * 1000
        bot.status = Status.inactive
        bot.deal = DealTable()

        # db operations
        self.session.add(bot)
        self.session.commit()
        self.session.close()
        return bot

    def save(self, data: BotTable):
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
        self.session.close()
        return bot

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

    def update_status(self, bot: BotTable, status: Status) -> BotTable:
        """
        Mostly as a replacement of the previous "activate" and "deactivate"
        although any Status can be passed now
        """
        bot.status = status
        # db operations
        self.session.add(bot)
        self.session.commit()
        self.session.close()
        # do this after db operations in case there is rollback
        # avoids sending unnecessary signals
        return bot

    def get_active_pairs(self):
        """
        Get all active pairs

        a replacement of the previous "distinct pairs" query
        """
        statement = select(BotTable.pair).where(BotTable.status == Status.active)
        pairs = self.session.exec(statement).all()
        self.session.close()
        return pairs
