from database.utils import independent_session
from sqlmodel import Session, select
from database.models.symbol_table import SymbolTable
from typing import Optional
from tools.exceptions import BinbotErrors


class SymbolsCrud:
    """
    Database operations for Autotrade settings
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

    def get_all(self, active: bool = True):
        """
        Get all symbols
        this excludes blacklisted items
        """
        statement = select(SymbolTable).where(SymbolTable.active == active)

        results = self.session.exec(statement).all()
        self.session.close()
        return results

    def get_symbol(self, symbol: str) -> SymbolTable:
        """
        Get single blacklisted item
        """
        statement = select(SymbolTable).where(SymbolTable.id == symbol)
        result = self.session.exec(statement).first()
        if result:
            self.session.close()
            return result
        else:
            raise BinbotErrors("Symbol not found")

    def add_symbol(self, symbol: str, active: bool = False, reason: Optional[str] = ""):
        """
        Add a new blacklisted item
        """
        blacklist = SymbolTable(id=symbol, blacklist_reason=reason, active=active)
        self.session.add(blacklist)
        self.session.commit()
        self.session.refresh(blacklist)
        self.session.close()
        return blacklist

    def edit_symbol_item(self, symbol: str, active: bool, reason: Optional[str] = None):
        """
        Edit a blacklisted item
        """
        symbol_model = self.get_symbol(symbol)
        symbol_model.active = active
        if reason:
            symbol_model.blacklist_reason = reason

        self.session.add(symbol_model)
        self.session.commit()
        self.session.refresh(symbol_model)
        self.session.close()
        return symbol_model

    def delete_symbol(self, symbol: str):
        """
        Delete a blacklisted item
        """
        symbol_model = self.get_symbol(symbol)
        self.session.delete(symbol_model)
        self.session.commit()
        self.session.close()
        return symbol_model
