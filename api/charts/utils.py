from typing import cast

from sqlalchemy import Table
from sqlmodel import Session

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
