from time import time

from sqlmodel import Session
from database.models.paper_trading_table import PaperTradingTable
from database.utils import independent_session
from tools.enum_definitions import Status


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

    def get(self, id: str) -> PaperTradingTable:
        """
        Get a paper trading account by id
        """
        paper_trading = self.session.get(PaperTradingTable, id)
        self.session.close()
        return paper_trading

    def activate(self, paper_trading: PaperTradingTable) -> PaperTradingTable:
        """
        Activate a paper trading account
        """
        paper_trading.status = Status.active
        self.session.add(paper_trading)
        self.session.commit()
        self.session.close()
        return paper_trading

    def deactivate(self, paper_trading: PaperTradingTable) -> PaperTradingTable:
        """
        Deactivate a paper trading account
        """
        paper_trading.status = Status.inactive
        self.session.add(paper_trading)
        self.session.commit()
        self.session.close()
        return paper_trading
