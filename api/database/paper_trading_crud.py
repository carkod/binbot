from time import time
from typing import Union
from sqlmodel import Session, or_, select, case, desc, asc
from database.models.bot_table import PaperTradingTable
from bots.models import BotModel, BotBase
from database.models.deal_table import DealTable
from database.utils import independent_session
from tools.enum_definitions import BinbotEnums, Status
from collections.abc import Sequence


class PaperTradingTableCrud:
    def __init__(self, session: Session | None = None):
        if session is None:
            session = independent_session()
        self.session = session
        pass

    def update_logs(
        self, log_message: str, bot: BotModel = None, bot_id: str | None = None
    ) -> BotModel:
        """
        Update logs for a bot

        Args:
        - bot_id: str
        - bot: BotModel

        Either id or bot has to be passed
        """
        if bot_id:
            bot_obj = self.session.get(PaperTradingTable, bot_id)
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

    def create(self, data: BotBase) -> BotModel:
        """
        Create a new paper trading account
        """
        bot = BotModel.model_validate(data)

        # Ensure values are reset
        bot.orders = []
        bot.logs = []
        bot.status = Status.inactive

        # db operations
        self.session.add(bot)
        self.session.commit()
        resulted_bot = self.session.get(PaperTradingTable, bot.id)
        self.session.close()
        data = BotModel.model_validate(resulted_bot)
        return data

    def save(self, data: BotModel) -> BotModel:
        """
        Save operation
        This can be editing a bot, or saving the object,
        or updating a single field.
        """
        bot = self.session.get(PaperTradingTable, data.id)
        if not bot:
            raise ValueError("Bot not found")

        # double check orders and deal are not overwritten
        dumped_bot = data.model_dump(exclude_unset=True)
        bot.sqlmodel_update(dumped_bot)
        self.session.add(bot)
        self.session.commit()
        resulted_bot = self.session.get(PaperTradingTable, bot.id)
        self.session.close()
        data = BotModel.model_validate(resulted_bot)
        return data

    def delete(self, id: Union[list[str], str]) -> bool:
        """
        Delete a paper trading account by id
        """
        data = self.session.get(PaperTradingTable, id)
        if not data:
            return False

        self.session.delete(data)
        self.session.commit()
        self.session.refresh(data)
        self.session.close()
        return True

    def get(
        self,
        status: Status | None = None,
        start_date: float | None = None,
        end_date: float | None = None,
        no_cooldown=False,
        limit: int = 200,
        offset: int = 0,
    ) -> Sequence[PaperTradingTable]:
        """
        Get all bots in the db except archived
        Args:
        - status: Status enum
        - start_date and end_date are timestamps in milliseconds
        - no_cooldown: bool - filter out bots that are in cooldown
        - limit and offset for pagination
        """
        statement = select(PaperTradingTable)

        if status and status in BinbotEnums.statuses:
            statement.where(PaperTradingTable.status == status)

        if start_date:
            statement.where(PaperTradingTable.created_at >= start_date)

        if end_date:
            statement.where(PaperTradingTable.created_at <= end_date)

        if status and no_cooldown:
            current_timestamp = time()
            cooldown_condition = cooldown_condition = or_(
                PaperTradingTable.status == status,
                case(
                    (
                        (DealTable.sell_timestamp > 0),
                        current_timestamp - DealTable.sell_timestamp
                        < (PaperTradingTable.cooldown * 1000),
                    ),
                    else_=(
                        current_timestamp - PaperTradingTable.created_at
                        < (PaperTradingTable.cooldown * 1000)
                    ),
                ),
            )

            statement.where(cooldown_condition)

        # sorting
        statement.order_by(
            desc(PaperTradingTable.created_at),
            case((PaperTradingTable.status == Status.active, 1), else_=2),
            asc(PaperTradingTable.pair),
        )

        # pagination
        statement.limit(limit).offset(offset)

        bots = self.session.exec(statement).all()
        self.session.close()
        return bots

    def update_status(self, paper_trading: BotModel, status: Status) -> BotModel:
        """
        Activate a paper trading account
        """
        paper_trading.status = status
        self.session.add(paper_trading)
        self.session.commit()
        self.session.close()
        return paper_trading

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
            bot = self.session.get(PaperTradingTable, bot_id)
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
        else:
            raise ValueError("Invalid bot id or symbol")

        self.session.close()
        data = BotModel.model_validate(bot)
        return data

    def get_active_pairs(self):
        """
        Get all active bots
        """
        bots = self.session.exec(
            select(PaperTradingTable).where(PaperTradingTable.status == Status.active)
        ).all()
        self.session.close()
        return bots
