from collections.abc import Sequence

from pybinbot import timestamp
from sqlmodel import Session, desc, select

from databases.tables.account_balances import (
    BalancesTable,
    ConsolidatedBalancesTable,
)
from databases.utils import independent_session


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

    def query_balance_series(
        self, start_date: int = 0, end_date: int = 0
    ) -> Sequence[ConsolidatedBalancesTable]:
        """
        Similar to Binance's balance snapshot (that endpoint has too much weight)
        this data is stored daily by store_balance cronjob
        """
        query = select(ConsolidatedBalancesTable)
        if start_date > 0:
            query = query.where(ConsolidatedBalancesTable.id >= int(start_date))
        if end_date > 0:
            query = query.where(ConsolidatedBalancesTable.id <= int(end_date))

        query = query.order_by(desc(ConsolidatedBalancesTable.id))
        results = self.session.exec(query).unique().all()
        return results
