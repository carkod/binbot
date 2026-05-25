from datetime import datetime, timedelta, timezone
from typing import Any, Sequence, cast

from sqlalchemy.orm import load_only
from sqlmodel import Session, col, delete, select
from sqlmodel.sql.expression import SelectOfScalar

from databases.tables.signals_table import SignalsTable
from databases.utils import get_db_session


class SignalsCrud:
    """
    CRUD operations for `signals`. Stable join keys (algorithm_name, symbol,
    generated_at) live as columns; per-strategy payload lives in JSONB.
    """

    def __init__(self, session: Session | None = None):
        self._external_session = session

    def create(
        self,
        algorithm_name: str,
        symbol: str,
        generated_at: datetime,
        direction: str,
        autotrade: bool = False,
        current_regime: str | None = None,
        context: dict[str, Any] | None = None,
        bot_params: dict[str, Any] | None = None,
        indicators: dict[str, Any] | None = None,
    ) -> SignalsTable:
        row = SignalsTable(
            algorithm_name=algorithm_name,
            symbol=symbol,
            generated_at=generated_at,
            direction=direction,
            autotrade=autotrade,
            current_regime=current_regime,
            context=context or {},
            bot_params=bot_params or {},
            indicators=indicators or {},
        )
        with get_db_session(self._external_session) as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            if self._external_session is None:
                session.expunge(row)
        return row

    def query(
        self,
        algorithm_name: str | None = None,
        symbol: str | None = None,
        current_regime: str | None = None,
        autotrade: bool | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[SignalsTable]:
        stmt = self._filtered_query(
            algorithm_name=algorithm_name,
            symbol=symbol,
            current_regime=current_regime,
            autotrade=autotrade,
            since=since,
            until=until,
        )
        stmt = (
            stmt.order_by(col(SignalsTable.generated_at).desc())
            .offset(offset)
            .limit(limit)
        )
        with get_db_session(self._external_session) as session:
            rows = session.exec(stmt).all()
            if self._external_session is None:
                for row in rows:
                    session.expunge(row)
            return rows

    def query_summary(
        self,
        algorithm_name: str | None = None,
        symbol: str | None = None,
        current_regime: str | None = None,
        autotrade: bool | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        stmt = self._filtered_query(
            algorithm_name=algorithm_name,
            symbol=symbol,
            current_regime=current_regime,
            autotrade=autotrade,
            since=since,
            until=until,
        )
        stmt = (
            stmt.options(
                load_only(
                    cast(Any, SignalsTable.id),
                    cast(Any, SignalsTable.algorithm_name),
                    cast(Any, SignalsTable.symbol),
                    cast(Any, SignalsTable.generated_at),
                    cast(Any, SignalsTable.direction),
                    cast(Any, SignalsTable.autotrade),
                    cast(Any, SignalsTable.current_regime),
                )
            )
            .order_by(col(SignalsTable.generated_at).desc())
            .offset(offset)
            .limit(limit)
        )
        with get_db_session(self._external_session) as session:
            rows = session.exec(stmt).all()
            return [
                {
                    "id": row.id,
                    "algorithm_name": row.algorithm_name,
                    "symbol": row.symbol,
                    "generated_at": row.generated_at,
                    "direction": row.direction,
                    "autotrade": row.autotrade,
                    "current_regime": row.current_regime,
                }
                for row in rows
            ]

    def delete_entries_older_than_14_days(self) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=14)
        stmt = delete(SignalsTable).where(col(SignalsTable.generated_at) < cutoff)
        if self._external_session is not None:
            result = self._external_session.exec(stmt)
            return result.rowcount or 0

        with get_db_session() as session:
            result = session.exec(stmt)
            return result.rowcount or 0

    def _filtered_query(
        self,
        algorithm_name: str | None = None,
        symbol: str | None = None,
        current_regime: str | None = None,
        autotrade: bool | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> SelectOfScalar[SignalsTable]:
        stmt = select(SignalsTable)
        if algorithm_name is not None:
            stmt = stmt.where(col(SignalsTable.algorithm_name) == algorithm_name)
        if symbol is not None:
            stmt = stmt.where(col(SignalsTable.symbol) == symbol)
        if current_regime is not None:
            stmt = stmt.where(col(SignalsTable.current_regime) == current_regime)
        if autotrade is not None:
            stmt = stmt.where(col(SignalsTable.autotrade) == autotrade)
        if since is not None:
            stmt = stmt.where(col(SignalsTable.generated_at) >= since)
        if until is not None:
            stmt = stmt.where(col(SignalsTable.generated_at) <= until)
        return stmt
