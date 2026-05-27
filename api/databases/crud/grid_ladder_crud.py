from collections.abc import Sequence
from typing import Any, cast
from uuid import UUID

from pybinbot import (
    ExchangeId,
    GridLadderStatus,
    MarketType,
    round_numbers,
    timestamp,
    ts_to_humandate,
)
from sqlalchemy.orm import QueryableAttribute, selectinload
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select, desc

from databases.tables.grid_ladder_table import (
    GridLadderTable,
    GridLevelTable,
    GridOrderTable,
)

ACTIVE_GRID_LADDER_STATUSES = (
    GridLadderStatus.pending,
    GridLadderStatus.active,
    GridLadderStatus.closing,
)
ZERO_USED_MARGIN_STATUSES = (
    GridLadderStatus.closed.value,
    GridLadderStatus.cancelled.value,
)
OPEN_EXPOSURE_LEVEL_STATUSES = {
    "filled",
    "take_profit_open",
    "error",
}
GRID_LADDER_LEVELS_REL = cast(QueryableAttribute[Any], GridLadderTable.levels)
GRID_LADDER_ORDERS_REL = cast(QueryableAttribute[Any], GridLadderTable.orders)
GRID_LADDER_STATUS_COL = cast(Any, GridLadderTable.status)
GRID_LADDER_CREATED_AT_COL = cast(Any, GridLadderTable.created_at)
GRID_LADDER_SYMBOL_COL = cast(Any, GridLadderTable.symbol)
GRID_ORDER_STATUS_COL = cast(Any, GridOrderTable.status)


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
        exchange: ExchangeId | str,
        market_type: MarketType | str,
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
            .options(selectinload(GRID_LADDER_ORDERS_REL))
        )
        return self.session.exec(stmt).first()

    def get_all(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        start_date: float | None = None,
        end_date: float | None = None,
    ) -> Sequence[GridLadderTable]:
        stmt = (
            select(GridLadderTable)
            .options(selectinload(GRID_LADDER_LEVELS_REL))
            .options(selectinload(GRID_LADDER_ORDERS_REL))
            .order_by(desc(GRID_LADDER_CREATED_AT_COL))
            .limit(limit)
            .offset(offset)
        )
        if start_date is not None:
            stmt = stmt.where(GRID_LADDER_CREATED_AT_COL >= start_date)
        if end_date is not None:
            stmt = stmt.where(GRID_LADDER_CREATED_AT_COL <= end_date)
        return self.session.exec(stmt).unique().all()

    def get_active(self) -> Sequence[GridLadderTable]:
        stmt = (
            select(GridLadderTable)
            .where(GRID_LADDER_STATUS_COL.in_(ACTIVE_GRID_LADDER_STATUSES))
            .options(selectinload(GRID_LADDER_LEVELS_REL))
            .options(selectinload(GRID_LADDER_ORDERS_REL))
            .order_by(desc(GRID_LADDER_CREATED_AT_COL))
        )
        return self.session.exec(stmt).unique().all()

    def get_active_symbols(self) -> list[str]:
        stmt = (
            select(GRID_LADDER_SYMBOL_COL)
            .where(GRID_LADDER_STATUS_COL.in_(ACTIVE_GRID_LADDER_STATUSES))
            .distinct()
        )
        return list(self.session.exec(stmt).all())

    def get_active_for_symbol(self, symbol: str) -> GridLadderTable | None:
        stmt = (
            select(GridLadderTable)
            .where(GridLadderTable.symbol == symbol)
            .where(GRID_LADDER_STATUS_COL.in_(ACTIVE_GRID_LADDER_STATUSES))
            .options(selectinload(GRID_LADDER_LEVELS_REL))
            .options(selectinload(GRID_LADDER_ORDERS_REL))
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

    def update_unrealized_pnl(
        self,
        ladder_id: UUID,
        unrealized_pnl: float,
    ) -> GridLadderTable | None:
        ladder = self.session.get(GridLadderTable, ladder_id)
        if ladder is None:
            return None

        ladder.unrealized_pnl = unrealized_pnl
        ladder.updated_at = timestamp()
        self.session.add(ladder)
        self.session.commit()
        self.session.refresh(ladder)
        return ladder

    def update_realized_pnl(
        self,
        ladder_id: UUID,
        realized_pnl: float,
    ) -> GridLadderTable | None:
        ladder = self.session.get(GridLadderTable, ladder_id)
        if ladder is None:
            return None

        ladder.realized_pnl = realized_pnl
        ladder.updated_at = timestamp()
        self.session.add(ladder)
        self.session.commit()
        self.session.refresh(ladder)
        return ladder

    def update_used_margin(
        self,
        ladder_id: UUID,
        used_margin: float,
    ) -> GridLadderTable | None:
        ladder = self.session.get(GridLadderTable, ladder_id)
        if ladder is None:
            return None

        ladder.used_margin = used_margin
        ladder.updated_at = timestamp()
        self.session.add(ladder)
        self.session.commit()
        self.session.refresh(ladder)
        return ladder

    def recalculate_used_margin(self, ladder_id: UUID) -> GridLadderTable | None:
        ladder = self.get(ladder_id)
        if ladder is None:
            return None

        status = (
            ladder.status.value
            if isinstance(ladder.status, GridLadderStatus)
            else str(ladder.status)
        )
        used_margin = 0.0
        if status not in ZERO_USED_MARGIN_STATUSES:
            for level in ladder.levels:
                if level.status not in OPEN_EXPOSURE_LEVEL_STATUSES:
                    continue
                if level.filled_entry_qty <= 0 or level.contracts <= 0:
                    continue

                fill_ratio = min(level.filled_entry_qty / level.contracts, 1)
                used_margin += level.margin_required * fill_ratio

        return self.update_used_margin(ladder_id, round_numbers(used_margin, 8))

    def update_status_with_context(
        self,
        ladder_id: UUID,
        status: GridLadderStatus,
        *,
        context_updates: dict | None = None,
        closed_at: float | None = None,
    ) -> GridLadderTable | None:
        ladder = self.session.get(GridLadderTable, ladder_id)
        if ladder is None:
            return None

        ladder.status = status
        ladder.updated_at = timestamp()
        if closed_at is not None:
            ladder.closed_at = closed_at
        if context_updates:
            merged = dict(ladder.context or {})
            merged.update(context_updates)
            ladder.context = merged
            flag_modified(ladder, "context")
        self.session.add(ladder)
        self.session.commit()
        self.session.refresh(ladder)
        return self.get(ladder_id)

    def update_logs(
        self,
        ladder_id: UUID,
        log_message: Any | list[Any],
    ) -> GridLadderTable | None:
        ladder = self.session.get(GridLadderTable, ladder_id)
        if ladder is None:
            return None

        ts = ts_to_humandate(ts=timestamp())
        messages = log_message if isinstance(log_message, list) else [log_message]
        logs = list(ladder.logs or [])
        for message in messages:
            if isinstance(message, dict):
                logs.append({"timestamp": ts, **message})
            else:
                logs.append(f"[{ts}] {message}")

        ladder.logs = logs
        ladder.updated_at = timestamp()
        flag_modified(ladder, "logs")
        self.session.add(ladder)
        self.session.commit()
        self.session.refresh(ladder)
        return ladder

    def update_error_logs(
        self,
        ladder_id: UUID,
        error: Exception | str,
    ) -> GridLadderTable | None:
        error_message = str(error)
        if isinstance(error, Exception):
            error_type = error.__class__.__name__
        else:
            error_type = "error"

        return self.update_logs(
            ladder_id,
            {
                "event": "error",
                "error_type": error_type,
                "message": error_message,
            },
        )

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

    def create_order(
        self,
        *,
        ladder_id: UUID,
        level_id: UUID | None,
        exchange_order_id: str,
        client_oid: str = "",
        order_role: str,
        side: str,
        price: float,
        contracts: int,
        status: str = "open",
        filled_qty: float = 0,
        filled_price: float | None = None,
    ) -> GridOrderTable:
        order = GridOrderTable(
            ladder_id=ladder_id,
            level_id=level_id,
            exchange_order_id=exchange_order_id,
            client_oid=client_oid,
            order_role=order_role,
            side=side,
            price=price,
            contracts=contracts,
            status=status,
            filled_qty=filled_qty,
            filled_price=filled_price,
        )
        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)
        return order

    def update_order(
        self,
        order_id: UUID,
        *,
        status: str | None = None,
        filled_qty: float | None = None,
        filled_price: float | None = None,
    ) -> GridOrderTable | None:
        order = self.session.get(GridOrderTable, order_id)
        if order is None:
            return None

        if status is not None:
            order.status = status
        if filled_qty is not None:
            order.filled_qty = filled_qty
        if filled_price is not None:
            order.filled_price = filled_price
        order.updated_at = timestamp()
        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)
        return order

    def update_orders_for_ladder(
        self,
        ladder_id: UUID,
        *,
        current_statuses: Sequence[str],
        new_status: str,
    ) -> None:
        stmt = (
            select(GridOrderTable)
            .where(GridOrderTable.ladder_id == ladder_id)
            .where(GRID_ORDER_STATUS_COL.in_(current_statuses))
        )
        for order in self.session.exec(stmt).all():
            order.status = new_status
            order.updated_at = timestamp()
            self.session.add(order)
        self.session.commit()

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
        level.status = "filled"
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

        level.status = "completed"
        level.realized_pnl = realized_pnl
        level.updated_at = timestamp()
        self.session.add(level)
        self.session.commit()
        self.session.refresh(level)
        return level

    def delete(self, ladder_id: UUID) -> bool:
        ladder = self.session.get(GridLadderTable, ladder_id)
        if ladder is None:
            return False
        self.session.delete(ladder)
        self.session.commit()
        return True

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
        ladder.closed_at = timestamp() if status == GridLadderStatus.closed else None
        ladder.updated_at = timestamp()
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
