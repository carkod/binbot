from datetime import datetime, timedelta, timezone
from typing import Any

from pybinbot import BinanceApi
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
    biggest 24h Binance spot movers, kept to spot patterns for new strategies.
    """

    def __init__(self, session: Session | None = None):
        self._external_session = session

    @staticmethod
    def _has_active_market(item: dict[str, Any]) -> bool:
        """
        Delisted/halted symbols keep returning Binance's last real 24h
        ticker window forever (no new trade ever rolls it forward), so their
        priceChangePercent can sit frozen at an extreme value indefinitely.
        A zero bid/ask means there's no live order book, i.e. the window is
        stale rather than a genuine live mover.
        """
        try:
            return float(item["bidPrice"]) > 0 and float(item["askPrice"]) > 0
        except (KeyError, TypeError, ValueError):
            return False

    def ingest(self, top: int = 10) -> list[TopGainersLosersSeriesTable]:
        """
        Pull the current 24h ticker ranking from Binance and persist the
        top N gainers and top N losers as one row each. Called once an hour
        by the cron. Exchange clients are built here rather than in
        __init__ so the read path (query_series, used by the public,
        unauthenticated GET endpoint) never needs Binance credentials.
        """
        config = Config()
        binance_api = BinanceApi(key=config.binance_key, secret=config.binance_secret)
        fiat = AutotradeCrud(session=self._external_session).get_fiat()

        ticker_data = binance_api.ticker_24()
        ranked = sorted(
            (
                item
                for item in ticker_data
                if item["symbol"].endswith(fiat) and self._has_active_market(item)
            ),
            key=lambda item: float(item["priceChangePercent"]),
            reverse=True,
        )
        recorded_at = datetime.now(timezone.utc)

        rows = [
            TopGainersLosersSeriesTable(
                recorded_at=recorded_at,
                side="gainer",
                rank=rank,
                symbol=item["symbol"],
                price_change_percent=float(item["priceChangePercent"]),
            )
            for rank, item in enumerate(ranked[:top], start=1)
        ]
        rows += [
            TopGainersLosersSeriesTable(
                recorded_at=recorded_at,
                side="loser",
                rank=rank,
                symbol=item["symbol"],
                price_change_percent=float(item["priceChangePercent"]),
            )
            for rank, item in enumerate(reversed(ranked[-top:]), start=1)
        ]

        with get_db_session(self._external_session) as session:
            session.add_all(rows)
            session.flush()
            created = [TopGainersLosersSeriesTable(**row.model_dump()) for row in rows]
            if self._external_session is not None:
                session.commit()
        return created

    def query_series(self, limit: int = 168) -> list[dict[str, Any]]:
        """
        Return up to `limit` most recent hourly snapshots, newest first, each
        with its top gainers and top losers ordered by rank.
        """
        with get_db_session(self._external_session) as session:
            distinct_timestamps = session.exec(
                select(TopGainersLosersSeriesTable.recorded_at)
                .distinct()
                .order_by(col(TopGainersLosersSeriesTable.recorded_at).desc())
                .limit(limit)
            ).all()
            if not distinct_timestamps:
                return []

            rows = session.exec(
                select(TopGainersLosersSeriesTable)
                .where(
                    col(TopGainersLosersSeriesTable.recorded_at).in_(
                        distinct_timestamps
                    )
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
