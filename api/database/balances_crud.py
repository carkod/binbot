from database.models.account_balances import BalancesTable, ConsolidatedBalancesTable
from database.utils import independent_session, timestamp
from sqlmodel import Session, select


class BalancesCrud:
    """
    Database operations for Autotrade settings
    """

    def __init__(
        self,
        session: Session = None,
    ):
        if session is None:
            session = independent_session()
        self.session = session

    def create_balance_series(self, total_balance, total_estimated_fiat: float):
        """
        Abstraction to reduce complexity
        updates balances DB collection
        """
        ts = timestamp()
        balances = []
        for item in total_balance:
            balance = BalancesTable(
                asset=item["asset"], quantity=item["free"], timestamp=ts
            )
            balances.append(balance)

        consolidated_balance_series = ConsolidatedBalancesTable(
            id=ts,
            balances=balances,
            estimated_total_fiat=total_estimated_fiat,
        )
        self.session.add(consolidated_balance_series)
        self.session.commit()
        self.session.refresh(consolidated_balance_series)
        return consolidated_balance_series

    def query_balance_series(self, start_date: int = 0, end_date: int = 0) -> list[ConsolidatedBalancesTable]:
        """
        Abstraction to reduce complexity
        fetches balances DB collection
        """
        query = select(ConsolidatedBalancesTable)
        if start_date > 0:
            query = query.where(ConsolidatedBalancesTable.id >= int(start_date))
        if end_date > 0:
            query = query.where(ConsolidatedBalancesTable.id <= int(end_date))

        results = self.session.exec(query).unique().all()
        return results
