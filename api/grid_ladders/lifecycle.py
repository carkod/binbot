from enum import Enum
from time import time

from databases.crud.grid_ladder_crud import GridLadderCrud
from databases.tables.grid_ladder_table import (
    GridLadderTable,
    GridLevelTable,
    GridOrderTable,
)
from databases.tables.symbol_table import SymbolTable
from kucoin_universal_sdk.generate.futures.order.model_add_order_req import AddOrderReq
from kucoin_universal_sdk.model.common import RestError
from pybinbot import (
    ExchangeId,
    GridLadderStatus,
    GridLevelStatus,
    GridOrderRole,
    OrderStatus,
    OrderType,
    round_numbers,
    timestamp,
)
from grid_ladders.sizing import round_price_to_precision
from kucoin_universal_sdk.generate.futures.order.model_get_order_by_order_id_resp import (
    GetOrderByOrderIdResp,
)
from sqlmodel import Session
from streaming.base import BaseStreaming


GRID_ORDER_OPEN_STATUS = OrderStatus.NEW.value
GRID_ORDER_FILLED_STATUS = OrderStatus.FILLED.value
GRID_ORDER_CANCELLED_STATUS = OrderStatus.CANCELED.value
GRID_ORDER_ERROR_STATUS = OrderStatus.REJECTED.value
OPEN_ORDER_STATUSES = (GRID_ORDER_OPEN_STATUS,)
TERMINAL_GRID_ORDER_STATUSES = {
    GRID_ORDER_FILLED_STATUS,
    GRID_ORDER_CANCELLED_STATUS,
    GRID_ORDER_ERROR_STATUS,
    OrderStatus.EXPIRED.value,
}


def _coerce_breach_ts(value: object) -> int | None:
    """Return value as int milliseconds, or None if it is absent or non-numeric.

    Treats the result as unset so the breach timer starts fresh rather than
    crashing the market-update loop on unexpected context data.
    """
    if isinstance(value, int):
        return value
    if isinstance(value, (float, str)):
        try:
            return int(value)
        except ValueError:
            return None
    return None


class GridLadderLifecycle:
    """
    Market-update lifecycle for persisted KuCoin futures grid ladders.

    The API creates a pending ladder plan. This class turns that plan into
    exchange orders and reconciles fills on the same loop as normal bots.
    """

    # Price must stay outside the breakout zone for this many monitoring ticks
    # before a close is triggered (prevents wicks from exiting prematurely).
    # Each tick corresponds to one process_symbol() call, typically every ~15 m.
    BREACH_CANDLES_REQUIRED = 3

    def __init__(self, base_streaming: BaseStreaming, session: Session):
        self.base_streaming = base_streaming
        self.session = session
        self.crud = GridLadderCrud(session)

    def process_symbol(self, symbol: str) -> None:
        ladder = self.crud.get_active_for_symbol(symbol)
        if ladder is None:
            return

        status = self._status_value(ladder.status)
        if status == GridLadderStatus.pending.value:
            self._place_initial_entries(ladder)
            return

        if status == GridLadderStatus.active.value:
            range_break = self._range_break(ladder)
            if range_break is not None:
                direction, price = range_break
                close_reason = f"range_break_{direction}"
                self._close_ladder(
                    ladder,
                    context_updates={
                        "close_reason": close_reason,
                        "range_break_price": price,
                        "breakout_low": ladder.breakout_low,
                        "breakout_high": ladder.breakout_high,
                    },
                    log_event={
                        "event": "range_break_close",
                        "direction": direction,
                        "price": price,
                        "breakout_low": ladder.breakout_low,
                        "breakout_high": ladder.breakout_high,
                    },
                )
                return

            self._reconcile_active_ladder(ladder)
            self._refresh_unrealized_pnl(ladder)
            return

        if status == GridLadderStatus.closing.value:
            self._close_ladder(ladder)

    def _status_value(self, status: GridLadderStatus | str) -> str:
        if isinstance(status, GridLadderStatus):
            return status.value
        return str(status)

    def _symbol_row(self, symbol: str) -> SymbolTable:
        symbol_row = self.session.get(SymbolTable, symbol)
        if symbol_row is None:
            raise ValueError(f"Symbol not found: {symbol}")
        return symbol_row

    def _price_precision(self, symbol_row: SymbolTable) -> int | None:
        exchange_values = symbol_row.exchange_values or []
        for row in exchange_values:
            if row.exchange_id == ExchangeId.KUCOIN:
                return row.price_precision
        if exchange_values:
            return exchange_values[0].price_precision
        return None

    def _order_status(self, value: Enum | str | None) -> str:
        if value is None:
            return OrderStatus.REJECTED.value

        raw_status = str(value.value if isinstance(value, Enum) else value)
        try:
            return OrderStatus(raw_status).value
        except ValueError:
            return OrderStatus.map_from_kucoin_status(raw_status.lower()).value

    def _filled_size(self, details: GetOrderByOrderIdResp) -> float:
        return float(details.filled_size or 0)

    def _filled_price(self, details: GetOrderByOrderIdResp, fallback: float) -> float:
        price = details.avg_deal_price or details.price or fallback
        return float(price)

    def _side_enum(self, side: str) -> AddOrderReq.SideEnum:
        if side == "buy":
            return AddOrderReq.SideEnum.BUY
        if side == "sell":
            return AddOrderReq.SideEnum.SELL
        raise ValueError(f"Unsupported grid side: {side}")

    def _opposite_side_enum(self, side: str) -> AddOrderReq.SideEnum:
        if side == "buy":
            return AddOrderReq.SideEnum.SELL
        if side == "sell":
            return AddOrderReq.SideEnum.BUY
        raise ValueError(f"Unsupported grid side: {side}")

    def _range_break(self, ladder: GridLadderTable) -> tuple[str, float] | None:
        price = self._current_position_price(ladder.symbol)
        if price is None:
            return None

        now_ms = int(time() * 1000)
        breach_duration_ms = self.BREACH_CANDLES_REQUIRED * 15 * 60 * 1000

        if price < ladder.breakout_low:
            first_breach = _coerce_breach_ts(
                (ladder.context or {}).get("first_breach_at")
            )
            if first_breach is None:
                self.crud.update_status_with_context(
                    ladder.id,
                    GridLadderStatus.active,
                    context_updates={
                        "first_breach_at": now_ms,
                        "first_breach_up_at": None,
                    },
                )
                return None
            if now_ms - first_breach >= breach_duration_ms:
                self.crud.update_status_with_context(
                    ladder.id,
                    GridLadderStatus.active,
                    context_updates={"first_breach_at": None},
                )
                return "down", price
            return None

        if price > ladder.breakout_high:
            first_breach_up = _coerce_breach_ts(
                (ladder.context or {}).get("first_breach_up_at")
            )
            if first_breach_up is None:
                self.crud.update_status_with_context(
                    ladder.id,
                    GridLadderStatus.active,
                    context_updates={
                        "first_breach_up_at": now_ms,
                        "first_breach_at": None,
                    },
                )
                return None
            if now_ms - first_breach_up >= breach_duration_ms:
                self.crud.update_status_with_context(
                    ladder.id,
                    GridLadderStatus.active,
                    context_updates={"first_breach_up_at": None},
                )
                return "up", price
            return None

        # Price recovered inside the breakout zone — reset both counters
        ctx = ladder.context or {}
        if ctx.get("first_breach_at") or ctx.get("first_breach_up_at"):
            self.crud.update_status_with_context(
                ladder.id,
                GridLadderStatus.active,
                context_updates={"first_breach_at": None, "first_breach_up_at": None},
            )
        return None

    def _current_position_price(self, symbol: str) -> float | None:
        symbol_row = self._symbol_row(symbol)
        position = self.base_streaming.kucoin_futures_api.get_futures_position(
            symbol_row.get_futures_symbol()
        )
        if position is None:
            return None

        for field_name in ("mark_price", "current_price", "price"):
            raw_price = getattr(position, field_name, None)
            if raw_price is not None:
                return float(raw_price)
        return None

    def _place_initial_entries(self, ladder: GridLadderTable) -> None:
        symbol_row = self._symbol_row(ladder.symbol)
        price_precision = self._price_precision(symbol_row)
        placed_order_ids: list[str] = []

        try:
            for level in ladder.levels:
                if level.side == "neutral" or level.contracts <= 0:
                    continue
                if level.entry_order_id:
                    continue

                price = round_price_to_precision(level.price, price_precision)
                order = self.base_streaming.kucoin_futures_api.place_futures_order(
                    symbol=symbol_row.get_futures_symbol(),
                    side=self._side_enum(level.side),
                    size=level.contracts,
                    price=price,
                    leverage=symbol_row.futures_leverage,
                    order_type=OrderType.limit,
                    reduce_only=False,
                )
                placed_order_ids.append(str(order.order_id))
                self.crud.create_order(
                    ladder_id=ladder.id,
                    level_id=level.id,
                    exchange_order_id=str(order.order_id),
                    order_role=GridOrderRole.entry.value,
                    side=level.side,
                    price=price,
                    contracts=level.contracts,
                    status=GRID_ORDER_OPEN_STATUS,
                )
                self.crud.update_logs(
                    ladder.id,
                    (
                        f"Placed entry order {order.order_id} for level "
                        f"{level.level_index}: {level.side} {level.contracts} "
                        f"contracts @ {price}"
                    ),
                )
                self.crud.update_level_order(
                    level.id,
                    entry_order_id=str(order.order_id),
                    status=GridLevelStatus.open.value,
                )

            self.crud.update_status(ladder.id, GridLadderStatus.active)
        except Exception as error:
            self._cancel_ladder_orders(ladder.symbol)
            self.crud.update_orders_for_ladder(
                ladder.id,
                current_statuses=OPEN_ORDER_STATUSES,
                new_status=GRID_ORDER_CANCELLED_STATUS,
            )
            self.crud.update_status_with_context(
                ladder.id,
                GridLadderStatus.error,
                context_updates={
                    "execution_error": str(error),
                    "cancelled_order_ids": placed_order_ids,
                },
            )
            self.crud.update_error_logs(ladder.id, error)

    def _reconcile_active_ladder(self, ladder: GridLadderTable) -> None:
        for order in ladder.orders:
            if order.status in TERMINAL_GRID_ORDER_STATUSES:
                continue

            try:
                details = self.base_streaming.kucoin_futures_api.retrieve_order(
                    order.exchange_order_id
                )
            except RestError as error:
                self._mark_order_error(ladder, order, error)
                continue
            except Exception as error:
                self._mark_order_error(ladder, order, error)
                continue

            status = self._order_status(details.status)
            filled_qty = self._filled_size(details)
            filled_price = self._filled_price(details, order.price)

            if status == OrderStatus.FILLED.value or filled_qty > 0:
                self.crud.update_order(
                    order.id,
                    status=GRID_ORDER_FILLED_STATUS,
                    filled_qty=filled_qty,
                    filled_price=filled_price,
                )
                self.crud.update_logs(
                    ladder.id,
                    (
                        f"Order {order.exchange_order_id} filled: "
                        f"{order.order_role} {filled_qty} contracts @ {filled_price}"
                    ),
                )
                try:
                    self._handle_filled_order(ladder, order, filled_qty, filled_price)
                except Exception as error:
                    self._mark_order_error(ladder, order, error)
                continue

            self.crud.update_order(
                order.id,
                status=GRID_ORDER_OPEN_STATUS,
            )

    def _handle_filled_order(
        self,
        ladder: GridLadderTable,
        order: GridOrderTable,
        filled_qty: float,
        filled_price: float,
    ) -> None:
        level = order.level
        if level is None:
            return

        if order.order_role == GridOrderRole.entry.value:
            self.crud.mark_level_entry_filled(
                level.id,
                filled_entry_price=filled_price,
                filled_entry_qty=filled_qty,
            )
            self._place_take_profit_order(ladder, level)
            return

        if order.order_role == GridOrderRole.take_profit.value:
            self.crud.mark_level_take_profit_filled(
                level.id,
                realized_pnl=self._realized_pnl(ladder, level, filled_price),
            )

    def _place_take_profit_order(
        self,
        ladder: GridLadderTable,
        level: GridLevelTable,
    ) -> None:
        if level.take_profit_order_id or level.take_profit_price is None:
            return

        symbol_row = self._symbol_row(ladder.symbol)
        price = round_price_to_precision(
            level.take_profit_price,
            self._price_precision(symbol_row),
        )
        order = self.base_streaming.kucoin_futures_api.place_futures_order(
            symbol=symbol_row.get_futures_symbol(),
            side=self._opposite_side_enum(level.side),
            size=level.filled_entry_qty or level.contracts,
            price=price,
            leverage=symbol_row.futures_leverage,
            order_type=OrderType.limit,
            reduce_only=True,
        )
        self.crud.create_order(
            ladder_id=ladder.id,
            level_id=level.id,
            exchange_order_id=str(order.order_id),
            order_role=GridOrderRole.take_profit.value,
            side="sell" if level.side == "buy" else "buy",
            price=price,
            contracts=int(level.filled_entry_qty or level.contracts),
            status=GRID_ORDER_OPEN_STATUS,
        )
        self.crud.update_logs(
            ladder.id,
            (
                f"Placed take-profit order {order.order_id} for level "
                f"{level.level_index}: {'sell' if level.side == 'buy' else 'buy'} "
                f"{int(level.filled_entry_qty or level.contracts)} contracts "
                f"@ {price}"
            ),
        )
        self.crud.update_level_order(
            level.id,
            take_profit_order_id=str(order.order_id),
            status=GridLevelStatus.take_profit_open.value,
        )

    def _realized_pnl(
        self,
        ladder: GridLadderTable,
        level: GridLevelTable,
        exit_price: float,
    ) -> float:
        symbol_row = self._symbol_row(ladder.symbol)
        contract = self.base_streaming.kucoin_futures_api.get_symbol_info(
            symbol_row.get_futures_symbol()
        )
        multiplier = float(contract.multiplier or 1)
        entry_price = float(level.filled_entry_price or level.price)
        qty = float(level.filled_entry_qty or level.contracts)
        direction = 1 if level.side == "buy" else -1
        return round_numbers((exit_price - entry_price) * qty * multiplier * direction)

    def _mark_order_error(
        self,
        ladder: GridLadderTable,
        order: GridOrderTable,
        error: Exception | str,
    ) -> None:
        message = str(error)
        self.crud.update_order(order.id, status=GRID_ORDER_ERROR_STATUS)
        if order.level_id:
            self.crud.update_level_order(
                order.level_id,
                status=GridLevelStatus.error.value,
            )
        self.crud.update_status_with_context(
            ladder.id,
            GridLadderStatus.error,
            context_updates={"execution_error": message},
        )
        self.crud.update_error_logs(ladder.id, error)

    def _refresh_unrealized_pnl(self, ladder: GridLadderTable) -> None:
        symbol_row = self._symbol_row(ladder.symbol)
        position = self.base_streaming.kucoin_futures_api.get_futures_position(
            symbol_row.get_futures_symbol()
        )
        raw_pnl = None
        for field_name in (
            "unrealized_pnl",
            "unrealised_pnl",
            "unrealizedPnl",
            "unrealisedPnl",
        ):
            raw_pnl = getattr(position, field_name, None)
            if raw_pnl is not None:
                break

        unrealized_pnl = round_numbers(float(raw_pnl or 0), 8)
        self.crud.update_unrealized_pnl(ladder.id, unrealized_pnl)

    def _forced_close_pnl(
        self,
        ladder: GridLadderTable,
        close_price: float | None,
        open_levels: list,
    ) -> float:
        if close_price is None:
            return 0.0
        total = 0.0
        for level in open_levels:
            if level.filled_entry_price is None:
                continue
            if level.status == GridLevelStatus.completed.value:
                continue
            total += self._realized_pnl(ladder, level, close_price)
        return total

    def _close_ladder(
        self,
        ladder: GridLadderTable,
        *,
        context_updates: dict | None = None,
        log_event: dict | None = None,
    ) -> None:
        # Snapshot level state before any mutations so PnL computation sees
        # the original statuses (some will be flipped to "cancelled" below).
        open_levels = list(ladder.levels)

        self._cancel_ladder_orders(ladder.symbol)
        self.crud.update_orders_for_ladder(
            ladder.id,
            current_statuses=OPEN_ORDER_STATUSES,
            new_status=GRID_ORDER_CANCELLED_STATUS,
        )
        for level in open_levels:
            if level.status in {
                GridLevelStatus.pending.value,
                GridLevelStatus.open.value,
                GridLevelStatus.take_profit_open.value,
            }:
                self.crud.update_level_order(
                    level.id,
                    status=GridLevelStatus.cancelled.value,
                )

        close_price = self._close_symbol_position(ladder.symbol)
        forced_pnl = self._forced_close_pnl(ladder, close_price, open_levels)
        total_pnl = sum(float(lv.realized_pnl or 0) for lv in open_levels) + forced_pnl
        self.crud.update_realized_pnl(ladder.id, round_numbers(total_pnl))

        self.crud.update_status_with_context(
            ladder.id,
            GridLadderStatus.closed,
            context_updates=context_updates,
            closed_at=timestamp(),
        )
        self.crud.update_unrealized_pnl(ladder.id, 0)
        if log_event is not None:
            self.crud.update_logs(ladder.id, log_event)
        self.crud.update_logs(ladder.id, {"event": "ladder_closed"})

    def _cancel_ladder_orders(self, symbol: str) -> None:
        symbol_row = self._symbol_row(symbol)
        self.base_streaming.kucoin_futures_api.cancel_all_futures_orders(
            symbol_row.get_futures_symbol()
        )

    def _close_symbol_position(self, symbol: str) -> float | None:
        symbol_row = self._symbol_row(symbol)
        futures_symbol = symbol_row.get_futures_symbol()
        position = self.base_streaming.kucoin_futures_api.get_futures_position(
            futures_symbol
        )
        current_qty = abs(float(position.current_qty or 0))

        # Capture mark price now as a fallback before any orders are placed
        mark_price: float | None = None
        for field_name in ("mark_price", "current_price", "price"):
            raw = getattr(position, field_name, None)
            if raw is not None:
                mark_price = float(raw)
                break

        if current_qty <= 0:
            return mark_price

        side = (
            AddOrderReq.SideEnum.SELL
            if float(position.current_qty) > 0
            else AddOrderReq.SideEnum.BUY
        )
        closed_order = self.base_streaming.kucoin_futures_api.place_futures_order(
            symbol=futures_symbol,
            side=side,
            size=current_qty,
            leverage=symbol_row.futures_leverage,
            order_type=OrderType.market,
            reduce_only=True,
        )
        # place_futures_order internally calls retrieve_order (5 s delay) and
        # sets .price = avg_deal_price. Fall back to mark price if unavailable.
        fill_price = float(closed_order.price) if closed_order.price else mark_price
        return fill_price
