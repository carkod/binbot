from sqlmodel import Session, select, desc
from databases.tables.strategy_threshold_override_table import (
    StrategyThresholdOverrideTable,
)


class StrategyThresholdOverrideCrud:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        row: StrategyThresholdOverrideTable,
    ) -> StrategyThresholdOverrideTable:
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def get_active(
        self,
        strategy_name: str,
        symbol: str,
        now_ts: float,
    ) -> StrategyThresholdOverrideTable | None:
        statement = (
            select(StrategyThresholdOverrideTable)
            .where(
                StrategyThresholdOverrideTable.strategy_name == strategy_name,
                StrategyThresholdOverrideTable.symbol == symbol,
                StrategyThresholdOverrideTable.expires_at > now_ts,
            )
            .order_by(desc(StrategyThresholdOverrideTable.created_at))
        )
        return self.session.exec(statement).first()

    def list_for_symbol(
        self,
        strategy_name: str,
        symbol: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[StrategyThresholdOverrideTable]:
        statement = (
            select(StrategyThresholdOverrideTable)
            .where(
                StrategyThresholdOverrideTable.strategy_name == strategy_name,
                StrategyThresholdOverrideTable.symbol == symbol,
            )
            .order_by(desc(StrategyThresholdOverrideTable.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.exec(statement).all())
