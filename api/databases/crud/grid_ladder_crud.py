from collections.abc import Sequence
from typing import Any, cast
from uuid import UUID

from pybinbot import GridLadderStatus, timestamp
from sqlalchemy.orm import QueryableAttribute, selectinload
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select, desc

from databases.tables.grid_ladder_table import GridLadderTable, GridLevelTable

ACTIVE_GRID_LADDER_STATUSES = (
    GridLadderStatus.pending,
    GridLadderStatus.active,
    GridLadderStatus.closing,
)
GRID_LADDER_LEVELS_REL = cast(QueryableAttribute[Any], GridLadderTable.levels)
GRID_LADDER_STATUS_COL = cast(Any, GridLadderTable.status)
GRID_LADDER_CREATED_AT_COL = cast(Any, GridLadderTable.created_at)


class GridLadderCrud:
    """
    CRUD operations for grid ladders.
    """

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        *,
        symbol: str,
        fiat: str,
        exchange: str,
        market_type: str,
        algorithm_name: str,
        range_low: float,
        range_high: float,
        grid_step: float,
        level_count: int,
        total_margin: float,
        reserved_margin: float,
        breakout_low: float,
        breakout_high: float,
        context: dict,
    ) -> GridLadderTable:
        ladder = GridLadderTable(
            symbol=symbol,
            fiat=fiat,
            exchange=exchange,
            market_type=market_type,
            algorithm_name=algorithm_name,
            status=GridLadderStatus.pending,
            range_low=range_low,
            range_high=range_high,
            grid_step=grid_step,
            level_count=level_count,
            total_margin=total_margin,
            reserved_margin=reserved_margin,
            breakout_low=breakout_low,
            breakout_high=breakout_high,
            context=context,
        )
        self.session.add(ladder)
        self.session.commit()
        self.session.refresh(ladder)
        return ladder

    def get(self, ladder_id: UUID) -> GridLadderTable | None:
        stmt = (
            select(GridLadderTable)
            .where(GridLadderTable.id == ladder_id)
            .options(selectinload(GRID_LADDER_LEVELS_REL))
        )
        return self.session.exec(stmt).first()

    def get_all(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[GridLadderTable]:
        stmt = (
            select(GridLadderTable)
            .options(selectinload(GRID_LADDER_LEVELS_REL))
            .order_by(desc(GRID_LADDER_CREATED_AT_COL))
            .limit(limit)
            .offset(offset)
        )
        return self.session.exec(stmt).unique().all()

    def get_active(self) -> Sequence[GridLadderTable]:
        stmt = (
            select(GridLadderTable)
            .where(GRID_LADDER_STATUS_COL.in_(ACTIVE_GRID_LADDER_STATUSES))
            .options(selectinload(GRID_LADDER_LEVELS_REL))
            .order_by(desc(GRID_LADDER_CREATED_AT_COL))
        )
        return self.session.exec(stmt).unique().all()

    def get_active_for_symbol(self, symbol: str) -> GridLadderTable | None:
        stmt = (
            select(GridLadderTable)
            .where(GridLadderTable.symbol == symbol)
            .where(GRID_LADDER_STATUS_COL.in_(ACTIVE_GRID_LADDER_STATUSES))
            .options(selectinload(GRID_LADDER_LEVELS_REL))
        )
        return self.session.exec(stmt).first()

    def update_status(
        self,
        ladder_id: UUID,
        status: GridLadderStatus,
    ) -> GridLadderTable | None:
        ladder = self.session.get(GridLadderTable, ladder_id)
        if ladder is None:
            return None

        ladder.status = status
        ladder.updated_at = timestamp()
        self.session.add(ladder)
        self.session.commit()
        self.session.refresh(ladder)
        return ladder

    def create_levels(
        self,
        ladder_id: UUID,
        levels: list[dict],
    ) -> list[GridLevelTable]:
        rows = [GridLevelTable(ladder_id=ladder_id, **level) for level in levels]
        self.session.add_all(rows)
        self.session.commit()
        for row in rows:
            self.session.refresh(row)
        return rows

    def update_level_order(
        self,
        level_id: UUID,
        *,
        entry_order_id: str | None = None,
        take_profit_order_id: str | None = None,
        status: str | None = None,
    ) -> GridLevelTable | None:
        level = self.session.get(GridLevelTable, level_id)
        if level is None:
            return None

        if entry_order_id is not None:
            level.entry_order_id = entry_order_id
        if take_profit_order_id is not None:
            level.take_profit_order_id = take_profit_order_id
        if status is not None:
            level.status = status
        level.updated_at = timestamp()
        self.session.add(level)
        self.session.commit()
        self.session.refresh(level)
        return level

    def mark_level_entry_filled(
        self,
        level_id: UUID,
        *,
        filled_entry_price: float,
        filled_entry_qty: float,
    ) -> GridLevelTable | None:
        level = self.session.get(GridLevelTable, level_id)
        if level is None:
            return None

        level.filled_entry_price = filled_entry_price
        level.filled_entry_qty = filled_entry_qty
        level.status = "entry_filled"
        level.updated_at = timestamp()
        self.session.add(level)
        self.session.commit()
        self.session.refresh(level)
        return level

    def mark_level_take_profit_filled(
        self,
        level_id: UUID,
        *,
        realized_pnl: float,
    ) -> GridLevelTable | None:
        level = self.session.get(GridLevelTable, level_id)
        if level is None:
            return None

        level.status = "take_profit_filled"
        level.realized_pnl = realized_pnl
        level.updated_at = timestamp()
        self.session.add(level)
        self.session.commit()
        self.session.refresh(level)
        return level

    def close(
        self,
        ladder_id: UUID,
        *,
        status: GridLadderStatus = GridLadderStatus.closed,
        context_updates: dict | None = None,
    ) -> GridLadderTable | None:
        ladder = self.session.get(GridLadderTable, ladder_id)
        if ladder is None:
            return None

        ladder.status = status
        ladder.closed_at = timestamp()
        ladder.updated_at = ladder.closed_at
        if context_updates:
            merged = dict(ladder.context or {})
            merged.update(context_updates)
            ladder.context = merged
            # JSON columns don't auto-detect in-place dict mutation; flag it
            # so SQLAlchemy emits an UPDATE.
            flag_modified(ladder, "context")
        self.session.add(ladder)
        self.session.commit()
        self.session.refresh(ladder)
        return self.get(ladder_id)
