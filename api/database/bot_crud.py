from typing import List, Optional
from uuid import UUID
from fastapi import Query
from sqlmodel import Session, asc, desc, or_, select, case
from database.utils import timestamp
from bots.models import BotModel
from database.models.bot_table import BotTable
from database.models.deal_table import DealTable
from database.models.order_table import ExchangeOrderTable
from database.utils import independent_session
from tools.enum_definitions import BinbotEnums, Status
from bots.models import BotBase
from collections.abc import Sequence
from sqlalchemy.orm.attributes import flag_modified
from tools.exceptions import SaveBotError


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
        include_cooldown=False,
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
            statement = statement.where(BotTable.status == status)

        if start_date:
            statement = statement.where(BotTable.created_at >= start_date)

        if end_date:
            statement = statement.where(BotTable.created_at <= end_date)

        if include_cooldown:
            current_timestamp = timestamp()
            cooldown_condition = or_(
                current_timestamp - DealTable.sell_timestamp
                < (BotTable.cooldown * 1000),
                current_timestamp - BotTable.created_at < (BotTable.cooldown * 1000),
            )

            statement = statement.where(cooldown_condition)

        # sorting
        statement = statement.order_by(
            desc(BotTable.created_at),
            case((BotTable.status == Status.active, 1), else_=2),
            asc(BotTable.pair),
        )

        # pagination
        statement = statement.limit(limit).offset(offset)

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

        # Insert update to DB only if it doesn't exist
        # Assign correct botId in the one side of the one-many relationship
        for order in data.orders:
            statement = select(ExchangeOrderTable).where(
                ExchangeOrderTable.order_id == order.order_id
            )
            get_order = self.session.exec(statement).first()
            if not get_order:
                new_order_row = ExchangeOrderTable(
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
                    bot_id=data.id,
                )
                self.session.add(new_order_row)

        self.session.add(deal)
        self.session.add(initial_bot)
        self.session.commit()
        self.session.refresh(deal)
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

    def update_order(
        self, order: ExchangeOrderTable, commission: float
    ) -> ExchangeOrderTable:
        """
        Update order data
        """
        statement = select(ExchangeOrderTable).where(
            ExchangeOrderTable.order_id == order.order_id
        )
        initial_order = self.session.exec(statement).first()

        if not initial_order:
            raise ValueError("Order not found")

        initial_order.status = order.status
        initial_order.qty = order.qty
        initial_order.order_side = order.order_side
        initial_order.order_type = order.order_type
        initial_order.timestamp = order.timestamp
        initial_order.pair = order.pair
        initial_order.time_in_force = order.time_in_force
        initial_order.price = order.price

        initial_bot = self.get_one(bot_id=str(initial_order.bot_id))
        initial_bot.total_commission += commission
        initial_bot.logs.append("Order status updated")

        self.session.add(initial_order)
        self.session.add(initial_bot)
        self.session.commit()
        self.session.refresh(initial_order)
        self.session.refresh(initial_bot)
        self.session.close()
        return order
