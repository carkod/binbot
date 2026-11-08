from bisect import bisect_left
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import cast

from sqlalchemy import Table, select
from sqlmodel import Session

from api.databases.tables.futures_price_sample_table import FuturesPriceSampleTable
from api.databases.tables.market_breadth_table import MarketBreadthTable
from pybinbot import ExchangeId, MarketBreadthSeries, ema
from api.tools.utils import datetime_to_iso


def fetch_market_breadth_series(
    session: Session,
    size: int = 7,
    window: int = 8,
    exchange: ExchangeId | None = None,
) -> MarketBreadthSeries | None:
    """
    Return parallel arrays (newest-first). Every field is read straight from
    storage except market_breadth_ma, which is an EMA-smoothed market
    breadth level computed over chronological samples.

    Standalone (session-only) so callers that only need a read — e.g.
    binbot/streaming's live lifecycle strategies — can fetch breadth without
    constructing MarketDominationController's exchange API clients.
    """
    output_size = size + max(int(window) - 1, 0)
    fetch_size = output_size + max(int(window) * 3, 0)
    market_breadth = cast(Table, getattr(MarketBreadthTable, "__table__"))

    recent_columns = (
        market_breadth.c.timestamp,
        market_breadth.c.advancers,
        market_breadth.c.decliners,
        market_breadth.c.total_volume,
        market_breadth.c.strength_index,
        market_breadth.c.adp.label("market_breadth"),
        market_breadth.c.avg_gain,
        market_breadth.c.avg_loss,
    )

    recent_stmt = market_breadth.select().with_only_columns(*recent_columns)
    if exchange:
        recent_stmt = recent_stmt.where(market_breadth.c.source == exchange.value)

    stmt = recent_stmt.order_by(market_breadth.c.timestamp.desc()).limit(fetch_size)
    result = session.execute(stmt)
    rows = result.mappings().all()

    if not rows:
        return None

    chronological_rows = list(reversed(rows))
    chronological_market_breadth = [
        float(r["market_breadth"]) for r in chronological_rows
    ]
    chronological_ema = ema(chronological_market_breadth, max(int(window), 1))
    rows_with_ema = list(zip(chronological_rows, chronological_ema, strict=True))
    output_rows = list(reversed(rows_with_ema))[:output_size]

    return MarketBreadthSeries(
        timestamp=[datetime_to_iso(r["timestamp"]) for r, _ in output_rows],
        advancers=[r["advancers"] for r, _ in output_rows],
        decliners=[r["decliners"] for r, _ in output_rows],
        market_breadth=[float(r["market_breadth"]) for r, _ in output_rows],
        market_breadth_ma=[float(ema_value) for _, ema_value in output_rows],
        avg_gain=[float(r["avg_gain"]) for r, _ in output_rows],
        avg_loss=[float(r["avg_loss"]) for r, _ in output_rows],
        total_volume=[float(r["total_volume"]) for r, _ in output_rows],
        strength_index=[float(r["strength_index"]) for r, _ in output_rows],
    )


def fetch_recent_futures_movement_series(
    session: Session, timestamps: list[str]
) -> dict[str, list[float | None]]:
    """Median price returns and falling shares for each breadth snapshot."""
    result: dict[str, list[float | None]] = {
        "median_return_15m": [],
        "median_return_1h": [],
        "median_return_3h": [],
        "falling_share_1h": [],
        "falling_share_3h": [],
    }
    if not timestamps:
        return result

    breadth_times: list[datetime] = []
    for value in timestamps:
        parsed = datetime.fromisoformat(value)
        breadth_times.append(
            parsed.replace(tzinfo=timezone.utc)
            if parsed.tzinfo is None
            else parsed.astimezone(timezone.utc)
        )
    prices = cast(Table, getattr(FuturesPriceSampleTable, "__table__"))
    rows = session.execute(
        select(prices.c.recorded_at, prices.c.symbol, prices.c.last_price).where(
            prices.c.source == "kucoin_futures",
            prices.c.recorded_at >= min(breadth_times) - timedelta(hours=3, minutes=10),
            prices.c.recorded_at <= max(breadth_times) + timedelta(seconds=1),
        )
    ).all()
    snapshots: dict[datetime, dict[str, float]] = {}
    for recorded_at, symbol, last_price in rows:
        timestamp = (
            recorded_at.astimezone(timezone.utc).replace(tzinfo=None)
            if recorded_at.tzinfo is not None
            else recorded_at
        )
        snapshots.setdefault(timestamp, {})[symbol] = last_price
    snapshot_times = sorted(snapshots)

    for breadth_time in breadth_times:
        point_time = breadth_time.replace(tzinfo=None)
        position = bisect_left(snapshot_times, point_time)
        current_time = min(
            (
                timestamp
                for timestamp in snapshot_times[max(0, position - 1) : position + 1]
                if abs(timestamp - point_time) <= timedelta(seconds=1)
            ),
            key=lambda timestamp: abs(timestamp - point_time),
            default=None,
        )
        current_prices = snapshots.get(current_time, {}) if current_time else {}
        for label, duration, tolerance in (
            ("15m", timedelta(minutes=15), timedelta(minutes=5)),
            ("1h", timedelta(hours=1), timedelta(minutes=10)),
            ("3h", timedelta(hours=3), timedelta(minutes=10)),
        ):
            return_key = f"median_return_{label}"
            share_key = f"falling_share_{label}" if label != "15m" else None
            if current_time is None:
                result[return_key].append(None)
                if share_key is not None:
                    result[share_key].append(None)
                continue
            target = current_time - duration
            position = bisect_left(snapshot_times, target)
            candidates = snapshot_times[max(0, position - 1) : position + 1]
            comparison = min(
                (
                    timestamp
                    for timestamp in candidates
                    if timestamp < current_time and abs(timestamp - target) <= tolerance
                ),
                key=lambda timestamp: abs(timestamp - target),
                default=None,
            )
            previous_prices = snapshots.get(comparison, {}) if comparison else {}
            returns = [
                (current_price / previous_prices[symbol] - 1) * 100
                for symbol, current_price in current_prices.items()
                if current_price > 0
                and symbol in previous_prices
                and previous_prices[symbol] > 0
            ]
            result[return_key].append(median(returns) if returns else None)
            if share_key is not None:
                result[share_key].append(
                    sum(value < 0 for value in returns) / len(returns)
                    if returns
                    else None
                )

    return result
