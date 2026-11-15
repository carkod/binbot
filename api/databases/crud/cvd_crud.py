from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Integer, Table, func, select
from sqlmodel import Session

from api.databases.tables.cvd_table import SOURCE, CvdBucketTable, CvdMinuteTable


def query_cvd_aggregate(session: Session, limit: int, now: float) -> dict[str, Any]:
    """Fixed UTC 15m windows, including outages. Never consult the exchange."""
    table: Table = getattr(CvdMinuteTable, "__table__")
    end = int(now) // 900 * 900
    start = end - (limit - 1) * 900
    grouped = (
        session.execute(
            select(
                (table.c.minute // 900).label("window"),
                func.sum(table.c.buy).label("buy"),
                func.sum(table.c.sell).label("sell"),
                func.min(table.c.expected_symbols).label("expected_min"),
                func.max(table.c.expected_symbols).label("expected"),
                func.min(table.c.covered_symbols).label("covered"),
                func.count().label("minutes"),
                func.sum(table.c.finalized.cast(Integer)).label("finalized"),
                func.count(func.distinct(table.c.universe)).label("universes"),
                func.min(table.c.universe).label("universe"),
                func.max(table.c.updated_at).label("updated_at"),
            )
            .where(
                table.c.source == SOURCE,
                table.c.minute >= start,
                table.c.minute <= int(now) // 60 * 60,
            )
            .group_by("window")
        )
        .mappings()
        .all()
    )
    rows = {row["window"] * 900: row for row in grouped}
    latest = session.execute(
        select(func.max(table.c.updated_at)).where(table.c.source == SOURCE)
    ).scalar_one()
    if latest is not None and latest.tzinfo is None:
        latest = latest.replace(tzinfo=timezone.utc)
    points = []
    cumulative = 0.0
    previous_universe = None
    interrupted = False
    for timestamp in range(start, end + 1, 900):
        row = rows.get(timestamp)
        current = timestamp == end
        complete = bool(
            row
            and row["minutes"] == 15
            and row["finalized"] == 15
            and row["expected"] > 0
            and row["covered"] == row["expected"]
            and row["expected_min"] == row["expected"]
            and row["universes"] == 1
        )
        gap = not complete
        changed = bool(
            row and previous_universe and previous_universe != row["universe"]
        )
        if row:
            previous_universe = row["universe"]
        buy, sell = (float(row["buy"]), float(row["sell"])) if row else (0.0, 0.0)
        cumulative += buy - sell
        interrupted = interrupted or gap or changed
        points.append(
            {
                "timestamp": datetime.fromtimestamp(timestamp, timezone.utc),
                "buy": buy if row else None,
                "sell": sell if row else None,
                "cvd": cumulative if row else None,
                "expected_symbols": row["expected"] if row else None,
                "covered_symbols": row["covered"] if row else 0,
                "observed_minutes": row["minutes"] if row else 0,
                "complete": complete,
                "gap": gap,
                "current": current,
                "universe_changed": changed or bool(row and row["universes"] > 1),
            }
        )
    return {
        "source": SOURCE,
        "data": points if rows else [],
        "reset_at": datetime.fromtimestamp(start, timezone.utc),
        "updated_at": latest,
        "stale": latest is None or now - latest.timestamp() > 90,
        "partial": interrupted,
    }


def query_cvd_symbol(
    session: Session, symbol: str, limit: int, now: float
) -> dict[str, Any]:
    """One symbol's stored UTC minutes, independent of other markets' coverage."""
    buckets: Table = getattr(CvdBucketTable, "__table__")
    minutes: Table = getattr(CvdMinuteTable, "__table__")
    end = int(now) // 60 * 60
    start = end - (limit - 1) * 60
    statement = (
        select(buckets, minutes.c.finalized, minutes.c.updated_at)
        .join(
            minutes,
            (buckets.c.source == minutes.c.source)
            & (buckets.c.minute == minutes.c.minute),
        )
        .where(buckets.c.source == SOURCE, buckets.c.symbol == symbol)
    )
    rows = {
        row["minute"]: row
        for row in session.execute(
            statement.where(buckets.c.minute >= start, buckets.c.minute <= end)
        )
        .mappings()
        .all()
    }
    latest = (
        session.execute(statement.order_by(buckets.c.minute.desc()).limit(1))
        .mappings()
        .first()
    )
    updated_at = latest["updated_at"] if latest else None
    if updated_at is not None and updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    points = []
    cumulative = 0.0
    previous_multiplier = None
    interrupted = False
    for timestamp in range(start, end + 1, 60):
        row = rows.get(timestamp)
        complete = bool(row and row["covered"] and row["finalized"])
        changed = bool(
            row
            and previous_multiplier is not None
            and previous_multiplier != row["multiplier"]
        )
        if row:
            previous_multiplier = row["multiplier"]
        buy, sell = (float(row["buy"]), float(row["sell"])) if row else (0.0, 0.0)
        cumulative += buy - sell
        interrupted = interrupted or not complete or changed
        points.append(
            {
                "timestamp": datetime.fromtimestamp(timestamp, timezone.utc),
                "buy": buy if row else None,
                "sell": sell if row else None,
                "cvd": cumulative if row else None,
                "expected_symbols": 1 if row else None,
                "covered_symbols": int(row["covered"]) if row else 0,
                "observed_minutes": 1 if row else 0,
                "complete": complete,
                "gap": not complete,
                "current": timestamp == end,
                "universe_changed": changed,
            }
        )
    return {
        "source": SOURCE,
        "symbol": symbol,
        "data": points if rows else [],
        "reset_at": datetime.fromtimestamp(start, timezone.utc),
        "updated_at": updated_at,
        "stale": updated_at is None or now - updated_at.timestamp() > 90,
        "partial": interrupted,
    }
