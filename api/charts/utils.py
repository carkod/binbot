from bisect import bisect_left
from math import sqrt
from datetime import datetime, timedelta, timezone
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


# Sixteen 15-minute samples smooth the cumulative breadth over four hours.
CUMULATIVE_BREADTH_EMA_SPAN = 16


def closest_snapshot_time(
    snapshot_times: list[datetime], target: datetime, tolerance: timedelta
) -> datetime | None:
    """Nearest sorted snapshot time to `target`, if it is within `tolerance`."""
    position = bisect_left(snapshot_times, target)
    return min(
        (
            timestamp
            for timestamp in snapshot_times[max(0, position - 1) : position + 1]
            if abs(timestamp - target) <= tolerance
        ),
        key=lambda timestamp: abs(timestamp - target),
        default=None,
    )


def fetch_cumulative_breadth_series(
    session: Session, timestamps: list[str]
) -> dict[str, list[float | None]]:
    """
    Cumulative net breadth of KuCoin futures for each breadth snapshot, newest
    first, plus its four-hour EMA.

    Each step compares every contract's price with the snapshot 15 minutes
    earlier, not with its rolling 24h change, so a moving 24h comparison point
    cannot turn a rising contract into a loser. The step value is
    (gainers' weight - losers' weight) / total weight * 100, with each
    contract weighted by the square root of its 24h turnover so liquid
    contracts count more but BTC and ETH cannot dominate. The steps do not
    overlap, so the running total counts each move once: noise cancels out and
    persistent breadth adds up. The total starts at the oldest snapshot, so
    only its direction has meaning, not its level.
    """
    result: dict[str, list[float | None]] = {
        "cumulative_breadth": [],
        "cumulative_breadth_ema": [],
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
        select(
            prices.c.recorded_at,
            prices.c.symbol,
            prices.c.last_price,
            prices.c.turnover_24h,
        ).where(
            prices.c.source == "kucoin_futures",
            prices.c.recorded_at >= min(breadth_times) - timedelta(minutes=20),
            prices.c.recorded_at <= max(breadth_times) + timedelta(seconds=1),
        )
    ).all()
    snapshots: dict[datetime, dict[str, tuple[float, float]]] = {}
    for recorded_at, symbol, last_price, turnover_24h in rows:
        timestamp = (
            recorded_at.astimezone(timezone.utc).replace(tzinfo=None)
            if recorded_at.tzinfo is not None
            else recorded_at
        )
        snapshots.setdefault(timestamp, {})[symbol] = (last_price, turnover_24h)
    snapshot_times = sorted(snapshots)

    # Missing steps stay as gaps; the total and its EMA carry over them.
    alpha = 2 / (CUMULATIVE_BREADTH_EMA_SPAN + 1)
    cumulative: float | None = None
    ema_value: float | None = None
    for breadth_time in sorted(breadth_times):
        current_time = closest_snapshot_time(
            snapshot_times, breadth_time.replace(tzinfo=None), timedelta(seconds=1)
        )
        previous_time = (
            closest_snapshot_time(
                snapshot_times,
                current_time - timedelta(minutes=15),
                timedelta(minutes=5),
            )
            if current_time is not None
            else None
        )
        if current_time is None or previous_time is None:
            result["cumulative_breadth"].append(None)
            result["cumulative_breadth_ema"].append(None)
            continue

        previous_prices = snapshots[previous_time]
        net_weight = 0.0
        total_weight = 0.0
        for symbol, (current_price, turnover_24h) in snapshots[current_time].items():
            previous_price = previous_prices.get(symbol, (0.0, 0.0))[0]
            if current_price <= 0 or previous_price <= 0 or turnover_24h <= 0:
                continue
            weight = sqrt(turnover_24h)
            total_weight += weight
            if current_price > previous_price:
                net_weight += weight
            elif current_price < previous_price:
                net_weight -= weight
        if total_weight == 0:
            result["cumulative_breadth"].append(None)
            result["cumulative_breadth_ema"].append(None)
            continue

        step = net_weight / total_weight * 100
        cumulative = step if cumulative is None else cumulative + step
        ema_value = (
            cumulative
            if ema_value is None
            else alpha * cumulative + (1 - alpha) * ema_value
        )
        result["cumulative_breadth"].append(cumulative)
        result["cumulative_breadth_ema"].append(ema_value)

    result["cumulative_breadth"].reverse()
    result["cumulative_breadth_ema"].reverse()
    return result
