from database.utils import independent_session
from sqlmodel import Session, select
from models.blacklist_table import BlacklistTable

class BlackListCrud:
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

    def get_blacklist(self):
        """
        Get all blacklisted items
        """
        statement = select(BlacklistTable)

        results = self.session.exec(statement).all()
        self.session.close()
        return results

    def get_blacklisted_item(self, symbol: str):
        """
        Get single blacklisted item
        """
        statement = select(BlacklistTable).where(
            BlacklistTable.id == symbol
        )

        results = self.session.exec(statement).first()
        self.session.close()
        return results

    def add_blacklist(self, symbol: str, reason: str):
        """
        Add a new blacklisted item
        """
        blacklist = BlacklistTable(id=symbol, reason=reason)
        self.session.add(blacklist)
        self.session.commit()
        self.session.refresh(blacklist)
        self.session.close()
        return blacklist

    def edit_blacklist_item(self, symbol: str, reason: str):
        """
        Edit a blacklisted item
        """
        blacklist = self.get_blacklisted_item(symbol)
        blacklist.reason = reason
        self.session.commit()
        self.session.refresh(blacklist)
        self.session.close()
        return blacklist

    def delete_blacklist_item(self, symbol: str):
        """
        Delete a blacklisted item
        """
        blacklist = self.get_blacklisted_item(symbol)
        self.session.delete(blacklist)
        self.session.commit()
        self.session.close()
        return blacklist
