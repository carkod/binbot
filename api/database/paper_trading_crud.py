from time import time

from sqlmodel import Session, or_, select, case, desc, asc
from database.models.deal_table import DealTable
from database.models.paper_trading_table import PaperTradingTable
from database.utils import independent_session
from tools.enum_definitions import BinbotEnums, Status


class PaperTradingTableCrud:
    def __init__(self, session: Session | None = None):
        if session is None:
            session = independent_session()
        self.session = session
        pass

    def create(self, paper_trading: PaperTradingTable) -> PaperTradingTable:
        """
        Create a new paper trading account
        """
        paper_trading.created_at = time() * 1000
        paper_trading.updated_at = time() * 1000

        # db operations
        self.session.add(paper_trading)
        self.session.commit()
        self.session.close()
        return paper_trading

    def edit(self, paper_trading: PaperTradingTable) -> PaperTradingTable:
        """
        Edit a paper trading account
        """
        self.session.add(paper_trading)
        self.session.commit()
        self.session.close()
        return paper_trading

    def delete(self, id: str) -> bool:
        """
        Delete a paper trading account by id
        """
        paper_trading = self.session.get(PaperTradingTable, id)
        if not paper_trading:
            return False

        self.session.delete(paper_trading)
        self.session.commit()
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
    ) -> PaperTradingTable:
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

    def update_status(
        self, paper_trading: PaperTradingTable, status: Status
    ) -> PaperTradingTable:
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
    ):
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
        return bot

    def get_active_pairs(self):
        """
        Get all active bots
        """
        bots = self.session.exec(
            select(PaperTradingTable).where(PaperTradingTable.status == Status.active)
        ).all()
        self.session.close()
        return bots
