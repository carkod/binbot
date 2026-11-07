from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from pybinbot import KucoinFutures
from sqlmodel import Session, col, delete, select

from api.databases.crud.autotrade_crud import AutotradeCrud
from api.databases.tables.futures_price_sample_table import FuturesPriceSampleTable
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
    HISTORY_RETENTION_DAYS = 365
    PRICE_HISTORY_HOURS = 5

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

    @classmethod
    def record_futures_prices(
        cls,
        session: Session,
        contracts: Iterable[Any],
        recorded_at: datetime,
    ) -> None:
        """Retain recent contract prices from an already fetched KuCoin response."""
        session.add_all(
            FuturesPriceSampleTable(
                source=cls.SOURCE,
                recorded_at=recorded_at,
                symbol=contract.symbol,
                last_price=float(contract.last_trade_price),
                price_change_percent=float(contract.price_chg_pct) * 100,
                turnover_24h=float(contract.turnover_of24h),
            )
            for contract in contracts
        )
        session.exec(
            delete(FuturesPriceSampleTable).where(
                col(FuturesPriceSampleTable.recorded_at)
                < recorded_at - timedelta(hours=cls.PRICE_HISTORY_HOURS)
            )
        )

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
                last_price=float(contract.last_trade_price),
                turnover_24h=float(contract.turnover_of24h),
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
                last_price=float(contract.last_trade_price),
                turnover_24h=float(contract.turnover_of24h),
            )
            for rank, contract in enumerate(reversed(ranked[-top:]), start=1)
        ]
        with get_db_session(self._external_session) as session:
            session.add_all(rows)
            self.record_futures_prices(session, ranked, recorded_at)
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
                "last_price": row.last_price,
                "turnover_24h": row.turnover_24h,
            }
            if row.side == "gainer":
                snapshot["top_gainers"].append(entry)
            else:
                snapshot["top_losers"].append(entry)

        return sorted(snapshots.values(), key=lambda s: s["recorded_at"], reverse=True)

    def query_fastest_movers(self, limit: int = 10) -> dict[str, Any]:
        """Rank actual one-hour price moves across the stored futures universe."""
        with get_db_session(self._external_session) as session:
            timestamps = session.exec(
                select(FuturesPriceSampleTable.recorded_at)
                .where(FuturesPriceSampleTable.source == self.SOURCE)
                .distinct()
                .order_by(col(FuturesPriceSampleTable.recorded_at).desc())
                .limit(30)
            ).all()
            result: dict[str, Any] = {
                "source": self.SOURCE,
                "recorded_at": timestamps[0] if timestamps else None,
                "comparison_at": None,
                "gainers": [],
                "losers": [],
            }
            if not timestamps:
                return result

            latest_at = timestamps[0]
            previous_at = min(
                (
                    timestamp
                    for timestamp in timestamps[1:]
                    if 50 * 60 <= (latest_at - timestamp).total_seconds() <= 70 * 60
                ),
                key=lambda timestamp: abs(
                    (latest_at - timestamp).total_seconds() - 60 * 60
                ),
                default=None,
            )
            if previous_at is None:
                return result
            result["comparison_at"] = previous_at
            three_hours_at = min(
                (
                    timestamp
                    for timestamp in timestamps[1:]
                    if 170 * 60 <= (latest_at - timestamp).total_seconds() <= 190 * 60
                ),
                key=lambda timestamp: abs(
                    (latest_at - timestamp).total_seconds() - 3 * 60 * 60
                ),
                default=None,
            )
            rows = session.exec(
                select(FuturesPriceSampleTable).where(
                    FuturesPriceSampleTable.source == self.SOURCE
                )
            ).all()

        snapshots: dict[datetime, dict[str, FuturesPriceSampleTable]] = {}
        selected = {
            timestamp.replace(tzinfo=None)
            for timestamp in (latest_at, previous_at, three_hours_at)
            if timestamp is not None
        }
        for row in rows:
            timestamp = row.recorded_at.replace(tzinfo=None)
            if timestamp in selected:
                snapshots.setdefault(timestamp, {})[row.symbol] = row

        movers: list[dict[str, Any]] = []
        for symbol, current in snapshots[latest_at.replace(tzinfo=None)].items():
            previous = snapshots[previous_at.replace(tzinfo=None)].get(symbol)
            if previous is None or previous.last_price <= 0:
                continue
            earlier = (
                snapshots.get(three_hours_at.replace(tzinfo=None), {}).get(symbol)
                if three_hours_at
                else None
            )
            movers.append(
                {
                    "symbol": symbol,
                    "price_change_1h_percent": (
                        current.last_price / previous.last_price - 1
                    )
                    * 100,
                    "price_change_3h_percent": (
                        (current.last_price / earlier.last_price - 1) * 100
                        if earlier is not None and earlier.last_price > 0
                        else None
                    ),
                    "price_change_percent": current.price_change_percent,
                    "last_price": current.last_price,
                    "turnover_24h": current.turnover_24h,
                }
            )
        result["gainers"] = sorted(
            (item for item in movers if item["price_change_1h_percent"] > 0),
            key=lambda item: item["price_change_1h_percent"],
            reverse=True,
        )[:limit]
        result["losers"] = sorted(
            (item for item in movers if item["price_change_1h_percent"] < 0),
            key=lambda item: item["price_change_1h_percent"],
        )[:limit]
        return result

    def delete_entries_older_than_one_year(self) -> int:
        """
        Keep roughly 175,200 rows at the default top-10 hourly ingestion rate.
        """

        cutoff = datetime.now(timezone.utc) - timedelta(
            days=self.HISTORY_RETENTION_DAYS
        )
        stmt = delete(TopGainersLosersSeriesTable).where(
            col(TopGainersLosersSeriesTable.recorded_at) < cutoff
        )
        with get_db_session(self._external_session) as session:
            result = session.exec(stmt)
            if self._external_session is not None:
                session.commit()
            return result.rowcount or 0
