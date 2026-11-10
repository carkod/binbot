from typing import cast

from pybinbot import ExchangeId, MarketBreadthSeries, ema
from sqlalchemy import Table
from sqlmodel import Session

from api.databases.tables.market_breadth_table import MarketBreadthTable
from api.databases.utils import get_db_session
from api.tools.utils import datetime_to_iso


class MarketBreadthCrud:
    """Read stored market breadth samples and their smoothed trend."""

    def __init__(self, session: Session | None = None):
        self._external_session = session

    def query_series(
        self,
        size: int = 7,
        window: int = 8,
        exchange: ExchangeId | None = None,
    ) -> MarketBreadthSeries | None:
        """Return newest-first samples with an EMA over chronological breadth."""
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
        with get_db_session(self._external_session) as session:
            rows = session.execute(stmt).mappings().all()

        if not rows:
            return None

        chronological_rows = list(reversed(rows))
        chronological_market_breadth = [
            float(row["market_breadth"]) for row in chronological_rows
        ]
        chronological_ema = ema(chronological_market_breadth, max(int(window), 1))
        rows_with_ema = list(zip(chronological_rows, chronological_ema, strict=True))
        output_rows = list(reversed(rows_with_ema))[:output_size]

        return MarketBreadthSeries(
            timestamp=[datetime_to_iso(row["timestamp"]) for row, _ in output_rows],
            advancers=[row["advancers"] for row, _ in output_rows],
            decliners=[row["decliners"] for row, _ in output_rows],
            market_breadth=[float(row["market_breadth"]) for row, _ in output_rows],
            market_breadth_ma=[float(ema_value) for _, ema_value in output_rows],
            avg_gain=[float(row["avg_gain"]) for row, _ in output_rows],
            avg_loss=[float(row["avg_loss"]) for row, _ in output_rows],
            total_volume=[float(row["total_volume"]) for row, _ in output_rows],
            strength_index=[float(row["strength_index"]) for row, _ in output_rows],
        )
