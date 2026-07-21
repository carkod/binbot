from enum import Enum
from time import time

from api.account.controller import ConsolidatedAccounts
from api.databases.crud.grid_ladder_crud import GridLadderCrud
from api.databases.tables.grid_ladder_table import (
    GridLadderTable,
    GridLevelTable,
    GridOrderTable,
)
from api.databases.tables.symbol_table import SymbolTable
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
from api.grid_ladders.sizing import round_price_to_precision
from kucoin_universal_sdk.generate.futures.order.model_get_order_by_order_id_resp import (
    GetOrderByOrderIdResp,
)
from sqlmodel import Session
from streaming.base import BaseStreaming


GRID_ORDER_OPEN_STATUS = OrderStatus.NEW.value
GRID_ORDER_FILLED_STATUS = OrderStatus.FILLED.value
GRID_ORDER_CANCELLED_STATUS = OrderStatus.CANCELED.value
GRID_ORDER_ERROR_STATUS = OrderStatus.REJECTED.value
TERMINAL_GRID_ORDER_STATUSES = {
    GRID_ORDER_FILLED_STATUS,
    GRID_ORDER_CANCELLED_STATUS,
    GRID_ORDER_ERROR_STATUS,
    OrderStatus.EXPIRED.value,
}
# Statuses meaning the order is still resting on the exchange book (possibly
# partially filled) — must keep being polled rather than finalized.
NON_TERMINAL_EXCHANGE_ORDER_STATUSES = {
    OrderStatus.NEW.value,
    OrderStatus.PARTIALLY_FILLED.value,
}
_STALE_LADDER_AGE_MS = int(1.5 * 24 * 60 * 60 * 1000)
_STALE_LADDER_PNL_PCT_LOW = -1.0
_STALE_LADDER_PNL_PCT_HIGH = 1.0


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
    # before a filled ladder closes (prevents wicks from exiting prematurely).
    # Each tick corresponds to one process_symbol() call, typically every ~15 m.
    BREACH_CANDLES_REQUIRED = 1
    UNFILLED_BREACH_CANDLES_REQUIRED = 1

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
            self._reconcile_active_ladder(ladder)
            refreshed_ladder = self.crud.get(ladder.id)
            if refreshed_ladder is None:
                return
            ladder = refreshed_ladder
            if self._status_value(ladder.status) != GridLadderStatus.active.value:
                return

            self._retry_pending_rearms(ladder)

            # All entry orders cancelled/expired on the exchange and no open position —
            # the ladder is an orphan with no way to fill. Close it immediately.
            if self._is_orphaned(ladder):
                self._close_ladder(
                    ladder,
                    context_updates={"close_reason": "orphaned_close"},
                    log_event={
                        "event": "orphaned_close",
                        "reason": "all_orders_terminal_no_exposure",
                    },
                )
                return

            # Panic close stale ladders with flat PnL after 1.5 days (mirrors
            # Lifecycle.exit stale-position logic).
            if self._is_stale(ladder):
                total_pnl = float(ladder.realized_pnl or 0) + float(
                    ladder.unrealized_pnl or 0
                )
                pnl_pct = (
                    (total_pnl / float(ladder.total_margin) * 100)
                    if ladder.total_margin > 0
                    else 0
                )
                self._close_ladder(
                    ladder,
                    context_updates={"close_reason": "stale_close"},
                    log_event={
                        "event": "stale_close",
                        "pnl_pct": round(pnl_pct, 4),
                        "realized_pnl": ladder.realized_pnl,
                        "unrealized_pnl": ladder.unrealized_pnl,
                    },
                )
                return

            range_break = self._range_break(ladder)
            if range_break is not None:
                direction, price = range_break
                close_reason = f"range_break_{direction}"
                breakout_close_type = self._breakout_close_type(ladder)
                self._close_ladder(
                    ladder,
                    context_updates={
                        "close_reason": close_reason,
                        "breakout_close_type": breakout_close_type,
                        "range_break_price": price,
                        "breakout_low": ladder.breakout_low,
                        "breakout_high": ladder.breakout_high,
                    },
                    log_event={
                        "event": "range_break_close",
                        "direction": direction,
                        "breakout_close_type": breakout_close_type,
                        "has_filled_exposure": self._has_open_exposure(ladder),
                        "has_exchange_position": self._has_exchange_position(
                            ladder.symbol
                        ),
                        "price": price,
                        "breakout_low": ladder.breakout_low,
                        "breakout_high": ladder.breakout_high,
                    },
                )
                return

            self._refresh_unrealized_pnl(ladder)
            return

        if status == GridLadderStatus.closing.value:
            self._close_ladder(ladder)

    def _status_value(self, status: GridLadderStatus | str) -> str:
        if isinstance(status, GridLadderStatus):
            return status.value
        return str(status)

    def _has_filled_exposure(
        self,
        ladder: GridLadderTable,
        levels: list[GridLevelTable] | None = None,
    ) -> bool:
        exposure_levels = ladder.levels if levels is None else levels
        return any(
            level.side != "neutral"
            and level.filled_entry_qty > 0
            and level.status != GridLevelStatus.completed.value
            for level in exposure_levels
        )

    def _has_exchange_position(self, symbol: str) -> bool:
        symbol_row = self._symbol_row(symbol)
        position = self.base_streaming.kucoin_futures_api.get_futures_position(
            symbol_row.get_futures_symbol()
        )
        if position is None:
            return False
        return abs(float(position.current_qty or 0)) > 0

    def _has_open_exposure(
        self,
        ladder: GridLadderTable,
        levels: list[GridLevelTable] | None = None,
    ) -> bool:
        return self._has_filled_exposure(
            ladder,
            levels,
        ) or self._has_exchange_position(ladder.symbol)

    def _has_side_exposure(self, ladder: GridLadderTable, side: str) -> bool:
        """True when a level on the given side has a filled entry not yet
        closed by its take-profit — real, live exchange exposure on that
        side. Used to keep only one directional side live at a time on a
        netted futures symbol. Includes partially filled `open` levels and
        `error` levels because both still represent unresolved exposure."""
        return any(
            level.side == side
            and level.filled_entry_qty > 0
            and level.status
            in (
                GridLevelStatus.open.value,
                GridLevelStatus.filled.value,
                GridLevelStatus.take_profit_open.value,
                GridLevelStatus.error.value,
            )
            for level in ladder.levels
        )

    def _breach_candles_required(self, ladder: GridLadderTable) -> int:
        if self._has_open_exposure(ladder):
            return self.BREACH_CANDLES_REQUIRED
        return self.UNFILLED_BREACH_CANDLES_REQUIRED

    def _breakout_close_type(self, ladder: GridLadderTable) -> str:
        if self._has_open_exposure(ladder):
            return "filled_breakout_close"
        return "unfilled_breakout_close"

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
        for raw_price in (details.avg_deal_price, details.price, fallback):
            try:
                price = float(raw_price)
            except (TypeError, ValueError):
                continue
            if price > 0:
                return price
        return 0.0

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

    def _opposite_side(self, side: str) -> str:
        return "sell" if side == "buy" else "buy"

    def _range_break(self, ladder: GridLadderTable) -> tuple[str, float] | None:
        price = self._current_market_price(ladder.symbol)
        if price is None:
            return None

        now_ms = int(time() * 1000)
        breach_duration_ms = self._breach_candles_required(ladder) * 15 * 60 * 1000

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

    def _current_market_price(self, symbol: str) -> float | None:
        symbol_row = self._symbol_row(symbol)
        futures_symbol = symbol_row.get_futures_symbol()
        prices: list[float] = []
        for side in (AddOrderReq.SideEnum.BUY, AddOrderReq.SideEnum.SELL):
            try:
                raw_price = self.base_streaming.kucoin_futures_api.matching_engine(
                    futures_symbol,
                    size=1,
                    side=side,
                )
            except Exception:
                continue
            price = float(raw_price or 0)
            if price > 0:
                prices.append(price)

        if not prices:
            return None

        precision = self._price_precision(symbol_row)
        return round_numbers(sum(prices) / len(prices), precision or 8)

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

                placed_order_ids.append(
                    self._arm_level_entry(ladder, symbol_row, price_precision, level)
                )

            self.crud.update_status(ladder.id, GridLadderStatus.active)
        except Exception as error:
            self._cancel_ladder_orders(ladder.symbol)
            self.crud.update_orders_for_ladder(
                ladder.id,
                current_statuses=(GRID_ORDER_OPEN_STATUS,),
                new_status=GRID_ORDER_CANCELLED_STATUS,
            )
            self.crud.update_status_with_context(
                ladder.id,
                GridLadderStatus.error,
                context_updates={"cancelled_order_ids": placed_order_ids},
            )
            self.crud.update_error_logs(ladder.id, error)

    def _arm_level_entry(
        self,
        ladder: GridLadderTable,
        symbol_row: SymbolTable,
        price_precision: int | None,
        level: GridLevelTable,
    ) -> str:
        """Place a fresh entry limit order for a level and mark it open.

        Shared by the ladder's initial placement and by re-arming a level
        whose entry/take-profit cycle has just completed or been paused —
        resets the level's prior round-trip state first so it can't block
        the next one (see `reset_level_for_rearm`).
        """
        self.crud.reset_level_for_rearm(level.id)

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
        return str(order.order_id)

    def _cancel_side_entries(self, ladder: GridLadderTable, side: str) -> bool:
        """Cancel every still-resting entry order on the given side. Called
        the instant the opposite side fills, so only one directional side
        ever has live exposure at a time on a netted futures symbol.

        Before cancelling, checks each order's live exchange state — a local
        "still resting" status can be stale if that order filled on the
        exchange in the same tick. Returns False (and cancels nothing) the
        moment that's found, so the caller can escalate instead of treating
        this side as the only one with exposure.
        """
        for order in ladder.orders:
            if order.order_role != GridOrderRole.entry.value:
                continue
            if order.side != side:
                continue
            if order.status in TERMINAL_GRID_ORDER_STATUSES:
                continue

            details = self.base_streaming.kucoin_futures_api.retrieve_order(
                order.exchange_order_id
            )
            if self._filled_size(details) > 0:
                return False

            self.base_streaming.kucoin_futures_api.cancel_futures_order(
                order.exchange_order_id
            )
            self.crud.update_order(order.id, status=GRID_ORDER_CANCELLED_STATUS)
            if order.level_id:
                self.crud.update_level_order(
                    order.level_id, status=GridLevelStatus.pending.value
                )
            self.crud.update_logs(
                ladder.id,
                (
                    f"Cancelled resting {side} entry order "
                    f"{order.exchange_order_id} — opposite side now live"
                ),
            )
        return True

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

            if status in NON_TERMINAL_EXCHANGE_ORDER_STATUSES:
                # Still resting on the exchange book — keep polling. Record any
                # partial progress so far, but don't finalize the order or act
                # on it (e.g. sizing a take-profit) until it's actually done.
                if filled_qty > 0:
                    self._record_partial_fill(ladder, order, filled_qty, filled_price)
                    level = order.level
                    if (
                        order.order_role == GridOrderRole.entry.value
                        and level is not None
                    ):
                        try:
                            self._guard_entry_side(
                                ladder, level, filled_qty, filled_price
                            )
                        except Exception as error:
                            self._handle_post_fill_error(ladder, order, error)
                continue

            if filled_qty <= 0:
                if status == OrderStatus.FILLED.value:
                    # KuCoin's get-order-by-id endpoint sometimes reports "done"
                    # with a blank fill payload even for genuinely fully-filled
                    # orders — fall back to the requested size rather than
                    # losing the fill.
                    filled_qty = float(order.contracts)
                else:
                    # Exchange reports a terminal non-fill status (cancelled/
                    # expired/unrecognized) with nothing filled — the order
                    # died without executing.
                    self.crud.update_order(order.id, status=GRID_ORDER_CANCELLED_STATUS)
                    if order.level_id:
                        self.crud.update_level_order(
                            order.level_id, status=GridLevelStatus.cancelled.value
                        )
                    self.crud.update_logs(
                        ladder.id,
                        f"Order {order.exchange_order_id} {status} on exchange; marked terminal",
                    )
                    continue

            # filled_qty > 0 here — a real fill occurred (however the terminal
            # status is labeled), so it must be tracked and never silently
            # discarded (an untracked fill is exactly the unhedged-position
            # incident this reconciliation logic exists to prevent).
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
                self._handle_post_fill_error(ladder, order, error)

    def _record_partial_fill(
        self,
        ladder: GridLadderTable,
        order: GridOrderTable,
        filled_qty: float,
        filled_price: float,
    ) -> None:
        if filled_qty <= order.filled_qty:
            return

        self.crud.update_order(
            order.id,
            filled_qty=filled_qty,
            filled_price=filled_price,
        )
        self.crud.update_logs(
            ladder.id,
            (
                f"Order {order.exchange_order_id} partially filled: "
                f"{order.order_role} {filled_qty}/{order.contracts} contracts "
                f"@ {filled_price}"
            ),
        )
        if order.order_role == GridOrderRole.entry.value and order.level_id:
            self.crud.record_level_entry_fill(
                order.level_id,
                filled_entry_price=filled_price,
                filled_entry_qty=filled_qty,
                status=GridLevelStatus.open.value,
            )
            self.crud.recalculate_used_margin(ladder.id)

    def _guard_entry_side(
        self,
        ladder: GridLadderTable,
        level: GridLevelTable,
        filled_qty: float,
        filled_price: float,
    ) -> bool:
        """Keep opposite-side entries off the book after any entry fill.

        Escalate to manual reconciliation if recorded exposure already exists
        or an opposite order wins the race while its cancellation is pending.
        """
        opposite_side = self._opposite_side(level.side)
        if self._has_side_exposure(ladder, opposite_side):
            self._handle_conflicting_exposure(ladder, level, filled_qty, filled_price)
            return False
        if not self._cancel_side_entries(ladder, opposite_side):
            self._handle_conflicting_exposure(ladder, level, filled_qty, filled_price)
            return False
        return True

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
            if not self._guard_entry_side(ladder, level, filled_qty, filled_price):
                return

            self.crud.record_level_entry_fill(
                level.id,
                filled_entry_price=filled_price,
                filled_entry_qty=filled_qty,
                status=GridLevelStatus.filled.value,
            )
            self.crud.recalculate_used_margin(ladder.id)
            self._place_take_profit_order(ladder, level)
            return

        if order.order_role == GridOrderRole.take_profit.value:
            self.crud.mark_level_take_profit_filled(
                level.id,
                realized_pnl=level.realized_pnl
                + self._realized_pnl(ladder, level, filled_price),
            )
            self.crud.recalculate_used_margin(ladder.id)
            self.crud.recalculate_realized_pnl(ladder.id)
            self._rearm_after_flat(ladder, level)

    def _rearm_after_flat(
        self,
        ladder: GridLadderTable,
        level: GridLevelTable,
    ) -> None:
        """A leg's take-profit just closed it back to flat. Re-arm this
        level immediately (same-side levels never conflict with each other),
        and only re-arm the paused opposite side once this side has no
        remaining live exposure at all — otherwise resting opposite-side
        orders would recreate the exact netting hazard this fix prevents.

        Available balance can shrink between ladder creation and a later
        round trip (other ladders/positions consuming margin), so each arm
        attempt is gated on a fresh balance check rather than assuming the
        margin reserved at creation is still free. A level that fails the
        check is left for `_retry_pending_rearms` to pick up on a later tick
        instead of raising and freezing the whole ladder into `error`."""
        symbol_row = self._symbol_row(ladder.symbol)
        price_precision = self._price_precision(symbol_row)
        if not self._try_arm_level_entry(ladder, symbol_row, price_precision, level):
            return

        if self._has_side_exposure(ladder, level.side):
            return

        opposite_side = self._opposite_side(level.side)
        for other_level in ladder.levels:
            if (
                other_level.side == opposite_side
                and other_level.status == GridLevelStatus.pending.value
            ):
                self._try_arm_level_entry(
                    ladder, symbol_row, price_precision, other_level
                )

    def _has_sufficient_balance(self, level: GridLevelTable) -> bool:
        balance = ConsolidatedAccounts(session=self.session).get_balance()
        return balance.fiat_available >= level.margin_required

    def _try_arm_level_entry(
        self,
        ladder: GridLadderTable,
        symbol_row: SymbolTable,
        price_precision: int | None,
        level: GridLevelTable,
    ) -> bool:
        """Arm a level's entry order if there's enough available balance to
        cover its margin, otherwise log and leave it for a later retry."""
        if not self._has_sufficient_balance(level):
            self.crud.update_logs(
                ladder.id,
                (
                    f"Insufficient balance to rearm level {level.level_index} "
                    f"({level.side} {level.contracts} contracts, needs "
                    f"{level.margin_required} margin) — will retry once funds "
                    "are available"
                ),
            )
            return False

        self._arm_level_entry(ladder, symbol_row, price_precision, level)
        return True

    def _retry_pending_rearms(self, ladder: GridLadderTable) -> None:
        """Pick up levels that finished a round trip but couldn't be
        re-armed last tick for lack of available balance (see
        `_rearm_after_flat`). A round-tripped level sits in `completed`
        status with no live order until this successfully arms it, so it's
        safe to treat every `completed` level found here as awaiting retry."""
        symbol_row = None
        price_precision = None
        for level in ladder.levels:
            if level.side == "neutral" or level.contracts <= 0:
                continue
            if level.status != GridLevelStatus.completed.value:
                continue

            if symbol_row is None:
                symbol_row = self._symbol_row(ladder.symbol)
                price_precision = self._price_precision(symbol_row)

            try:
                self._try_arm_level_entry(ladder, symbol_row, price_precision, level)
            except Exception as error:
                self.crud.update_level_order(
                    level.id, status=GridLevelStatus.error.value
                )
                self.crud.update_status_with_context(ladder.id, GridLadderStatus.error)
                self.crud.recalculate_used_margin(ladder.id)
                self.crud.update_error_logs(ladder.id, error)
                return

    def _handle_conflicting_exposure(
        self,
        ladder: GridLadderTable,
        level: GridLevelTable,
        filled_qty: float,
        filled_price: float,
    ) -> None:
        """Both directional sides ended up filled and exposed at the same
        time (the guard's cancel lost a race to an in-flight fill). Mark
        both sides' levels as error and halt automation for this ladder —
        an error-status ladder is untouched by process_symbol — so a human
        reconciles the real exchange position rather than the code guessing.

        Records this level's real fill (rather than leaving filled_entry_qty
        at 0) so _has_side_exposure still recognizes it as live exposure if
        another fill on the same side arrives in this same tick.
        """
        opposite_side = self._opposite_side(level.side)
        self.crud.record_level_entry_fill(
            level.id,
            filled_entry_price=filled_price,
            filled_entry_qty=filled_qty,
            status=GridLevelStatus.error.value,
        )
        for other_level in ladder.levels:
            if other_level.side == opposite_side and other_level.status in (
                GridLevelStatus.filled.value,
                GridLevelStatus.take_profit_open.value,
                GridLevelStatus.error.value,
            ):
                self.crud.update_level_order(
                    other_level.id, status=GridLevelStatus.error.value
                )
        self.crud.update_status_with_context(ladder.id, GridLadderStatus.error)
        self.crud.recalculate_used_margin(ladder.id)
        self.crud.update_error_logs(
            ladder.id,
            (
                f"Conflicting exposure: level {level.level_index} ({level.side}) "
                "filled while the opposite side already had live exposure — "
                "manual reconciliation required"
            ),
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
        opposite_side = self._opposite_side(level.side)
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
            side=opposite_side,
            price=price,
            contracts=int(level.filled_entry_qty or level.contracts),
            status=GRID_ORDER_OPEN_STATUS,
        )
        self.crud.update_logs(
            ladder.id,
            (
                f"Placed take-profit order {order.order_id} for level "
                f"{level.level_index}: {opposite_side} "
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
        self.crud.update_order(order.id, status=GRID_ORDER_ERROR_STATUS)
        self._handle_post_fill_error(ladder, order, error)

    def _handle_post_fill_error(
        self,
        ladder: GridLadderTable,
        order: GridOrderTable,
        error: Exception | str,
    ) -> None:
        """Flag the level/ladder as needing attention without touching the
        order's own status — used when a fill was recorded successfully but a
        downstream step (e.g. placing the take-profit order) failed, so the
        order's real FILLED status and quantity must not be overwritten."""
        if order.level_id:
            self.crud.update_level_order(
                order.level_id,
                status=GridLevelStatus.error.value,
            )
        self.crud.update_status_with_context(
            ladder.id,
            GridLadderStatus.error,
        )
        self.crud.recalculate_used_margin(ladder.id)
        self.crud.update_error_logs(ladder.id, error)

    def _is_orphaned(self, ladder: GridLadderTable) -> bool:
        """True when every non-neutral order is in a terminal non-fill state and
        there is no open exchange position — the ladder has nothing left to do."""
        has_any_active = any(
            order.status == GRID_ORDER_OPEN_STATUS for order in ladder.orders
        )
        if has_any_active:
            return False
        return not self._has_open_exposure(ladder)

    def _is_stale(self, ladder: GridLadderTable) -> bool:
        """True when the ladder has been running for 1.5 days with flat PnL
        (between -1% and +1% of total_margin), mirroring Lifecycle's
        panic-close logic for low-activity positions."""
        if not ladder.created_at:
            return False
        age_ms = int(time() * 1000) - int(ladder.created_at)
        if age_ms < _STALE_LADDER_AGE_MS:
            return False
        if ladder.total_margin <= 0:
            return False
        total_pnl = float(ladder.realized_pnl or 0) + float(ladder.unrealized_pnl or 0)
        pnl_pct = total_pnl / float(ladder.total_margin) * 100
        return _STALE_LADDER_PNL_PCT_LOW <= pnl_pct < _STALE_LADDER_PNL_PCT_HIGH

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
            current_statuses=(GRID_ORDER_OPEN_STATUS,),
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

        # Always attempt to close the exchange position regardless of DB state.
        # _close_symbol_position returns early (mark price) when current_qty == 0,
        # so this is safe even when no position exists. Skipping the DB exposure
        # check avoids a race where a TP fill arrives after cancel_all_futures_orders
        # but before get_futures_position, leaving a residual position.
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
        self.crud.recalculate_used_margin(ladder.id)
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
