from datetime import datetime
from typing import Any, Generator, Sequence
from contextlib import AbstractContextManager, contextmanager

from sqlmodel import Session, col, select

from databases.tables.signals_table import SignalsTable
from databases.utils import get_db_session as _get_db_session


def get_session() -> AbstractContextManager[Session]:
    """Module-level session factory kept overridable for tests."""
    return _get_db_session()


class SignalsCrud:
    """
    CRUD operations for `signals`. Stable join keys (algorithm_name, symbol,
    generated_at) live as columns; per-strategy payload lives in JSONB.
    """

    def __init__(self, session: Session | None = None):
        self._external_session = session

    def _get_session(self) -> AbstractContextManager[Session]:
        if self._external_session is not None:
            session = self._external_session

            @contextmanager
            def external_ctx() -> Generator[Session, None, None]:
                yield session

            return external_ctx()

        return get_session()

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
        with self._get_session() as session:
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
        stmt = select(SignalsTable)
        if algorithm_name is not None:
            stmt = stmt.where(SignalsTable.algorithm_name == algorithm_name)
        if symbol is not None:
            stmt = stmt.where(SignalsTable.symbol == symbol)
        if current_regime is not None:
            stmt = stmt.where(SignalsTable.current_regime == current_regime)
        if autotrade is not None:
            stmt = stmt.where(SignalsTable.autotrade == autotrade)
        if since is not None:
            stmt = stmt.where(SignalsTable.generated_at >= since)
        if until is not None:
            stmt = stmt.where(SignalsTable.generated_at <= until)
        stmt = (
            stmt.order_by(col(SignalsTable.generated_at).desc())
            .offset(offset)
            .limit(limit)
        )
        with self._get_session() as session:
            rows = session.exec(stmt).all()
            if self._external_session is None:
                for row in rows:
                    session.expunge(row)
            return rows
