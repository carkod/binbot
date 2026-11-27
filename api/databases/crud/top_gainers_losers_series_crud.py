from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Iterable, cast

from pybinbot import ExchangeId, KucoinFutures
from pybinbot.shared.telegram_delivery import TelegramDelivery
from sqlalchemy import Table, case, func, select as sa_select
from sqlmodel import Session, col, delete, select

from api.databases.crud.autotrade_crud import AutotradeCrud
from api.databases.tables.futures_price_sample_table import FuturesPriceSampleTable
from api.databases.tables.market_breadth_table import MarketBreadthTable
from api.databases.tables.symbol_exchange_table import SymbolExchangeTable
from api.databases.tables.top_gainers_losers_series_table import (
    TopGainersLosersSeriesTable,
)
from api.databases.utils import get_db_session
from api.charts.models import FastestMoversSnapshot
from api.tools.config import Config


class TopGainersLosersSeriesCrud:
    """
    CRUD operations for `top_gainers_losers_series` — half-hourly snapshots of the
    biggest 24h KuCoin futures movers, kept to identify strategy patterns.
    """

    SOURCE = "kucoin_futures"
    HISTORY_RETENTION_DAYS = 365
    # Keep full-contract snapshots for the dashboard's seven-day price trend.
    PRICE_HISTORY_HOURS = 168

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
        except AttributeError, TypeError, ValueError:
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
        top N gainers and top N losers as one row each. Called at :00 and :30 UTC
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
        settings = AutotradeCrud(session=self._external_session).get_settings()
        fiat = settings.fiat
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
        previous_movers = None
        if settings.telegram_signals:
            with get_db_session(self._external_session) as session:
                previous_ingestion_at = session.exec(
                    select(func.max(TopGainersLosersSeriesTable.recorded_at)).where(
                        TopGainersLosersSeriesTable.source == self.SOURCE
                    )
                ).one()
            if previous_ingestion_at is not None:
                previous_movers = FastestMoversSnapshot.model_validate(
                    self.query_fastest_movers(limit=top, as_of=previous_ingestion_at)
                )

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
        # The committed snapshot is also the membership checkpoint. Failed sends
        # are not replayed when the next ingestion or a restarted worker runs.
        if previous_movers is not None:
            try:
                current_movers = FastestMoversSnapshot.model_validate(
                    self.query_fastest_movers(limit=top, as_of=recorded_at)
                )
                self.notify_fastest_movers(previous_movers, current_movers, config.env)
            except Exception:
                logging.exception(
                    "Fastest-mover notification failed; ingestion is committed"
                )
        return created

    @staticmethod
    def notify_fastest_movers(
        previous: FastestMoversSnapshot,
        current: FastestMoversSnapshot,
        environment: str,
    ) -> None:
        """Attempt fresh ranking entries once, using the same lists as the dashboard."""
        if (
            previous.recorded_at is None
            or previous.comparison_at is None
            or current.recorded_at is None
            or current.comparison_at is None
            or previous.source != current.source
            or not timedelta(0)
            < current.recorded_at - previous.recorded_at
            <= timedelta(minutes=45)
        ):
            return
        expires_at = current.recorded_at + timedelta(minutes=15)
        delivery = None
        for side, movers, old_movers in (
            ("Rising", current.gainers, previous.gainers),
            ("Falling", current.losers, previous.losers),
        ):
            old_members = {mover.symbol for mover in old_movers}
            for rank, mover in enumerate(movers, start=1):
                if mover.symbol in old_members:
                    continue
                now = datetime.now(timezone.utc)
                if not current.recorded_at <= now < expires_at:
                    return
                if delivery is None:
                    delivery = TelegramDelivery()
                change_3h = (
                    f"{mover.price_change_3h_percent:+.2f}%"
                    if mover.price_change_3h_percent is not None
                    else "unavailable"
                )
                message = f"""
                    - [{environment}] <strong>#fastest_movers algorithm</strong> #{mover.symbol}
                    - Event: entered {side}
                    - Event ID: {current.recorded_at.isoformat()}
                    - Rank: {rank}
                    - 1h price change: {mover.price_change_1h_percent:+.2f}%
                    - 3h price change: {change_3h}
                    - Current price: {mover.last_price}
                    - Snapshot time: {current.recorded_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}
                    - Autotrade: disabled, notification only
                """
                delivery.send_once(
                    "\n".join(
                        line.strip() for line in message.splitlines() if line.strip()
                    )
                )

    def query_series(
        self, limit: int = 168, source: str = SOURCE
    ) -> list[dict[str, Any]]:
        """
        Return up to `limit` most recent snapshots, newest first, each
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

    @classmethod
    def query_aggregate_series(
        cls, session: Session, limit: int = 672
    ) -> list[dict[str, Any]]:
        """Gain/loss magnitude at 15-minute KuCoin futures breadth snapshots."""
        prices = cast(Table, getattr(FuturesPriceSampleTable, "__table__"))
        symbol_exchanges = cast(Table, getattr(SymbolExchangeTable, "__table__"))
        breadth = cast(Table, getattr(MarketBreadthTable, "__table__"))
        registered_symbols = sa_select(symbol_exchanges.c.symbol_id).where(
            symbol_exchanges.c.exchange_id == ExchangeId.KUCOIN
        )
        # The breadth cron stores full futures price snapshots every 15 minutes.
        # Its timestamps exclude the separate half-hourly top-gainers fetches.
        recent_timestamps = (
            sa_select(breadth.c.timestamp)
            .where(breadth.c.source == ExchangeId.KUCOIN.value)
            .order_by(breadth.c.timestamp.desc())
            .limit(limit)
            .subquery()
        )
        rows = (
            session.execute(
                sa_select(
                    prices.c.recorded_at,
                    func.sum(
                        case(
                            (
                                prices.c.price_change_percent > 0,
                                prices.c.price_change_percent,
                            ),
                            else_=0.0,
                        )
                    ).label("gainer_magnitude"),
                    func.sum(
                        case(
                            (
                                prices.c.price_change_percent < 0,
                                -prices.c.price_change_percent,
                            ),
                            else_=0.0,
                        )
                    ).label("loser_magnitude"),
                    func.sum(
                        case((prices.c.price_change_percent > 0, 1), else_=0)
                    ).label("advancers"),
                    func.sum(
                        case((prices.c.price_change_percent < 0, 1), else_=0)
                    ).label("decliners"),
                )
                .join(
                    recent_timestamps,
                    prices.c.recorded_at == recent_timestamps.c.timestamp,
                )
                .where(
                    prices.c.source == cls.SOURCE,
                    prices.c.symbol.in_(registered_symbols),
                )
                .group_by(prices.c.recorded_at)
                .order_by(prices.c.recorded_at.desc())
            )
            .mappings()
            .all()
        )
        return [
            {
                "timestamp": row["recorded_at"].replace(tzinfo=timezone.utc)
                if row["recorded_at"].tzinfo is None
                else row["recorded_at"],
                "gainer_magnitude": row["gainer_magnitude"],
                "loser_magnitude": row["loser_magnitude"],
                "advancers": row["advancers"],
                "decliners": row["decliners"],
            }
            for row in rows
        ]

    def query_fastest_movers(
        self, limit: int = 10, *, as_of: datetime | None = None
    ) -> dict[str, Any]:
        """Rank actual one-hour price moves across the stored futures universe."""
        with get_db_session(self._external_session) as session:
            statement = select(FuturesPriceSampleTable.recorded_at).where(
                FuturesPriceSampleTable.source == self.SOURCE
            )
            if as_of is not None:
                statement = statement.where(
                    FuturesPriceSampleTable.recorded_at <= as_of
                )
            timestamps = session.exec(
                statement.distinct()
                .order_by(col(FuturesPriceSampleTable.recorded_at).desc())
                .limit(30)
            ).all()
            result: dict[str, Any] = {
                "source": self.SOURCE,
                "recorded_at": None,
                "comparison_at": None,
                "gainers": [],
                "losers": [],
            }
            if not timestamps:
                return result

            latest_at = timestamps[0]
            result["recorded_at"] = (
                latest_at.replace(tzinfo=timezone.utc)
                if latest_at.tzinfo is None
                else latest_at
            )
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
            result["comparison_at"] = (
                previous_at.replace(tzinfo=timezone.utc)
                if previous_at.tzinfo is None
                else previous_at
            )
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
            selected_timestamps = [
                timestamp
                for timestamp in (latest_at, previous_at, three_hours_at)
                if timestamp is not None
            ]
            rows = session.exec(
                select(FuturesPriceSampleTable).where(
                    FuturesPriceSampleTable.source == self.SOURCE,
                    col(FuturesPriceSampleTable.recorded_at).in_(selected_timestamps),
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
        Keep roughly 350,400 rows at the default top-10 half-hourly ingestion rate.
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
