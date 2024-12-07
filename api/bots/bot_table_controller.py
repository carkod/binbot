import json
from typing import List
from fastapi import Query
from sqlmodel import Session, asc, desc, or_, select, case
from time import time
from base_producer import BaseProducer
from bots.schemas import BotSchema
from database.models.bot_table import BotTable
from database.models.deal_table import DealTable
from database.utils import independent_session
from deals.controllers import CreateDealController
from deals.models import DealModel
from tools.enum_definitions import BinbotEnums, Status
from psycopg.types.json import Json, set_json_loads


class BotTableController:
    """
    CRUD and database operations for the SQL API DB
    bot_table table.
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
        self.base_producer = BaseProducer()
        self.producer = self.base_producer.start_producer()
        self.deal: CreateDealController | None = None

    def update_logs(self, log_message: str, bot: BotSchema = None, bot_id: str | None = None):
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
            raise ValueError("Bot id or bot BotSchema object is required")

        bot_object = bot

        current_logs: list[str] = json.loads(bot_object.logs)
        if not current_logs or len(current_logs) == 0:
            current_logs = [log_message]
        elif len(current_logs) > 0:
            current_logs.append(log_message)

        bot_object.logs = json.dumps(current_logs)
        self.session.add(bot_object)
        self.session.commit()
        self.session.close()
        return bot

    def get(
        self,
        status,
        start_date: float | None = None,
        end_date: float | None = None,
        no_cooldown=False,
        limit: int = 200,
        offset: int = 0,
    ):
        """
        Get all bots in the db except archived
        Args:
        - archive=false
        - filter_by: string - last-week, last-month, all
        """
        statement = select(BotTable)

        if status in BinbotEnums.statuses:
            statement.where(BotTable.status == status)
        else:
            raise ValueError("Invalid status")

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

    def get_one(self, bot_id: str | None = None, symbol: str | None = None):
        """
        Get one bot by id or symbol
        """
        if bot_id:
            bot = self.session.get(BotTable, bot_id)
        elif symbol:
            bot = self.session.exec(
                select(BotTable).where(BotTable.pair == symbol)
            ).first()
        else:
            raise ValueError("Invalid bot id or symbol")

        self.session.close()
        return bot

    def create(self, data: BotSchema):
        """
        Create a new bot
        """
        bot = BotTable.model_validate(data)
        # Ensure values are reset
        bot.orders = []
        bot.logs = Json([])
        bot.created_at = time() * 1000
        bot.updated_at = time() * 1000
        bot.status = Status.inactive
        bot.deal = DealModel()
        self.session.add(bot)
        self.session.commit()
        self.session.close()
        self.base_producer.update_required(self.producer, "CREATE_BOT")
        return bot

    def edit(self, bot_id: str, data: BotSchema):
        """
        Edit a bot
        """
        bot = self.session.get(BotTable, bot_id)
        if not bot:
            return bot

        dumped_bot = bot.model_dump(exclude_unset=True)
        bot.sqlmodel_update(dumped_bot)
        self.session.add(bot)
        self.session.commit()
        self.session.close()
        self.base_producer.update_required(self.producer, "UPDATE_BOT")
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
        self.base_producer.update_required(self.producer, "DELETE_BOT")
        return bots

    def activate(self, bot_id: str):
        """
        Activate a bot
        """
        bot = self.session.get(BotTable, bot_id)
        if not bot:
            return bot

        bot.status = Status.active
        self.session.add(bot)
        self.session.commit()
        self.session.close()
        self.base_producer.update_required(self.producer, "ACTIVATE_BOT")
        return bot

    def deactivate(self, bot_id: str):
        """
        Deactivate a bot (panic sell)
        """
        bot = self.session.get(BotTable, bot_id)
        if not bot:
            return bot

        bot.status = Status.completed

        self.session.add(bot)
        self.session.commit()
        self.session.close()
        self.base_producer.update_required(self.producer, "DEACTIVATE_BOT")
        return bot

    def get_active_pairs(self):
        """
        Get all active pairs
        """
        statement = select(BotTable.pair).where(BotTable.status == Status.active)
        pairs = self.session.exec(statement).all()
        self.session.close()
        return pairs
