from datetime import datetime, timedelta, timezone
from typing import Any

from pybinbot import KucoinFutures
from sqlmodel import Session, col, delete, select

from api.databases.crud.autotrade_crud import AutotradeCrud
from api.databases.tables.top_gainers_losers_series_table import (
    TopGainersLosersSeriesTable,
)
from api.databases.utils import get_db_session
from api.tools.config import Config


class TopGainersLosersSeriesCrud:
    """
    CRUD operations for `top_gainers_losers_series` — hourly snapshots of the
    biggest 24h KuCoin futures movers, kept to identify strategy patterns.
    """

    SOURCE = "kucoin_futures"

    def __init__(self, session: Session | None = None):
        self._external_session = session

    @staticmethod
    def _has_active_market(contract: Any, fiat: str) -> bool:
        """
        Only rank live perpetual contracts settled in the configured fiat
        currency and with recent trading.

        KuCoin keeps closed contracts in the all-symbols response, so status,
        last price, and turnover must agree that the market is active.
        """
        try:
            status = getattr(contract.status, "value", contract.status)
            return (
                status == "Open"
                and contract.settle_currency == fiat
                and not bool(contract.is_inverse)
                and float(contract.last_trade_price) > 0
                and float(contract.turnover_of24h) > 0
                and contract.price_chg_pct is not None
            )
        except (AttributeError, TypeError, ValueError):
            return False

    def ingest(self, top: int = 10) -> list[TopGainersLosersSeriesTable]:
        """
        Pull the current 24h ticker ranking from KuCoin futures and persist the
        top N gainers and top N losers as one row each. Called once an hour
        by the cron. Exchange clients are built here rather than in
        __init__ so the read path (query_series, used by the public,
        unauthenticated GET endpoint) never needs KuCoin credentials.
        """
        config = Config()
        kucoin_futures_api = KucoinFutures(
            key=config.kucoin_key,
            secret=config.kucoin_secret,
            passphrase=config.kucoin_passphrase,
        )
        response = kucoin_futures_api.futures_market_api.get_all_symbols()
        fiat = AutotradeCrud(session=self._external_session).get_fiat()
        ranked = sorted(
            (
                contract
                for contract in response.data or []
                if self._has_active_market(contract, fiat)
            ),
            key=lambda contract: float(contract.price_chg_pct),
            reverse=True,
        )
        recorded_at = datetime.now(timezone.utc)

        rows = [
            TopGainersLosersSeriesTable(
                source=self.SOURCE,
                recorded_at=recorded_at,
                side="gainer",
                rank=rank,
                symbol=contract.symbol,
                price_change_percent=float(contract.price_chg_pct) * 100,
            )
            for rank, contract in enumerate(ranked[:top], start=1)
        ]
        rows += [
            TopGainersLosersSeriesTable(
                source=self.SOURCE,
                recorded_at=recorded_at,
                side="loser",
                rank=rank,
                symbol=contract.symbol,
                price_change_percent=float(contract.price_chg_pct) * 100,
            )
            for rank, contract in enumerate(reversed(ranked[-top:]), start=1)
        ]

        with get_db_session(self._external_session) as session:
            session.add_all(rows)
            session.flush()
            created = [TopGainersLosersSeriesTable(**row.model_dump()) for row in rows]
            if self._external_session is not None:
                session.commit()
        return created

    def query_series(
        self, limit: int = 168, source: str = SOURCE
    ) -> list[dict[str, Any]]:
        """
        Return up to `limit` most recent hourly snapshots, newest first, each
        with its top gainers and top losers ordered by rank.
        """
        with get_db_session(self._external_session) as session:
            distinct_timestamps = session.exec(
                select(TopGainersLosersSeriesTable.recorded_at)
                .where(TopGainersLosersSeriesTable.source == source)
                .distinct()
                .order_by(col(TopGainersLosersSeriesTable.recorded_at).desc())
                .limit(limit)
            ).all()
            if not distinct_timestamps:
                return []

            rows = session.exec(
                select(TopGainersLosersSeriesTable)
                .where(
                    TopGainersLosersSeriesTable.source == source,
                    col(TopGainersLosersSeriesTable.recorded_at).in_(
                        distinct_timestamps
                    ),
                )
                .order_by(
                    col(TopGainersLosersSeriesTable.recorded_at).desc(),
                    col(TopGainersLosersSeriesTable.side),
                    col(TopGainersLosersSeriesTable.rank),
                )
            ).all()

        snapshots: dict[datetime, dict[str, Any]] = {}
        for row in rows:
            snapshot = snapshots.setdefault(
                row.recorded_at,
                {
                    "source": row.source,
                    "recorded_at": row.recorded_at,
                    "top_gainers": [],
                    "top_losers": [],
                },
            )
            entry = {
                "symbol": row.symbol,
                "price_change_percent": row.price_change_percent,
            }
            if row.side == "gainer":
                snapshot["top_gainers"].append(entry)
            else:
                snapshot["top_losers"].append(entry)

        return sorted(snapshots.values(), key=lambda s: s["recorded_at"], reverse=True)

    def delete_entries_older_than_90_days(self) -> int:
        """
        Keep roughly 43,200 rows at the default top-10 hourly ingestion rate.
        """

        cutoff = datetime.now(timezone.utc) - timedelta(days=90)
        stmt = delete(TopGainersLosersSeriesTable).where(
            col(TopGainersLosersSeriesTable.recorded_at) < cutoff
        )
        with get_db_session(self._external_session) as session:
            result = session.exec(stmt)
            if self._external_session is not None:
                session.commit()
            return result.rowcount or 0
