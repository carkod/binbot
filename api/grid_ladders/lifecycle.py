from pybinbot import (
    ExchangeId,
    GridLadderStatus,
    GridLevelStatus,
    GridOrderRole,
    OrderStatus,
    round_numbers,
    timestamp,
)

from api.databases.crud.symbols_crud import SymbolsCrud
from api.databases.tables.grid_ladder_table import (
    GridLadderTable,
    GridLevelTable,
    GridOrderTable,
)
from api.grid_ladders.base_lifecycle import (
    GRID_ORDER_CANCELLED_STATUS,
    GRID_ORDER_FILLED_STATUS,
    GRID_ORDER_OPEN_STATUS,
    NON_TERMINAL_EXCHANGE_ORDER_STATUSES,
    TERMINAL_GRID_ORDER_STATUSES,
    BaseLifecycle,
)
from api.exchange_apis.kucoin.futures.liquidity import (
    calculate_liquidity_snapshot,
    load_futures_order_book,
)


GRID_LIQUIDITY_PRICE_BAND_BPS = 50.0
# Spread/slippage ceilings scale with the ladder's own initial BB-width
# volatility read (mirrors the ATR-scaled thresholds used for standalone
# futures entries in KucoinPositionDeal), clamped to [MIN, MAX] so a quiet
# symbol is held to a tighter bar than a volatile one.
GRID_LIQUIDITY_MIN_SPREAD_BPS = 15.0
GRID_LIQUIDITY_MAX_SPREAD_BPS = 40.0
GRID_LIQUIDITY_SPREAD_BB_WIDTH_MULTIPLIER = 0.05
GRID_LIQUIDITY_MIN_SLIPPAGE_BPS = 18.0
GRID_LIQUIDITY_MAX_SLIPPAGE_BPS = 50.0
GRID_LIQUIDITY_SLIPPAGE_BB_WIDTH_MULTIPLIER = 0.0625
# Used when the ladder has no recorded bb_width feature (e.g. a manually
# created ladder) — a mid-range volatility assumption, not the tightest or
# loosest end of the clamp.
GRID_LIQUIDITY_FALLBACK_BB_WIDTH = 0.03
# See ENTRY_LIQUIDITY_MAX_DATA_AGE_MS in KucoinPositionDeal — thin books can
# go many seconds between quote updates without being genuinely stale.
GRID_LIQUIDITY_MAX_DATA_AGE_MS = 20_000


class GridLadderLifecycle(BaseLifecycle):
    """Orchestrate persisted KuCoin futures grid ladders by symbol state."""

    def process_symbol(self, symbol: str) -> None:
        ladder = self.crud.get_active_for_symbol(symbol)
        if ladder is None:
            return

        status = self._status_value(ladder.status)
        if status == GridLadderStatus.error.value:
            self._recover_error_ladder(ladder)
            return

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

            first_cycle_timeout_hours = self._first_cycle_timeout_hours(ladder)
            if first_cycle_timeout_hours is not None and self._is_first_cycle_timeout(
                ladder, first_cycle_timeout_hours
            ):
                self._close_ladder(
                    ladder,
                    context_updates={"close_reason": "first_cycle_timeout"},
                    log_event={
                        "event": "first_cycle_timeout",
                        "timeout_hours": first_cycle_timeout_hours,
                        "has_filled_exposure": self._has_open_exposure(ladder),
                    },
                )
                return

            max_lifetime_hours = self._max_lifetime_hours(ladder)
            if self._is_max_lifetime(ladder, max_lifetime_hours):
                self._close_ladder(
                    ladder,
                    context_updates={"close_reason": "max_lifetime"},
                    log_event={
                        "event": "max_lifetime",
                        "max_lifetime_hours": max_lifetime_hours,
                        "completed_cycles": self._completed_cycle_count(ladder),
                        "has_filled_exposure": self._has_open_exposure(ladder),
                    },
                )
                return

            completed_cycles = self._completed_cycle_count(ladder)
            if completed_cycles >= self._max_completed_cycles(ladder):
                self._close_ladder(
                    ladder,
                    context_updates={
                        "close_reason": "max_completed_cycles",
                        "completed_cycles": completed_cycles,
                    },
                    log_event={
                        "event": "max_completed_cycles",
                        "completed_cycles": completed_cycles,
                    },
                )
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

    def _grid_liquidity_thresholds(
        self, ladder: GridLadderTable
    ) -> tuple[float, float]:
        """Spread/slippage ceilings scaled by the ladder's initial bb_width
        feature (fraction of price), falling back to a mid-range volatility
        assumption when that feature wasn't recorded."""
        bb_width = self._initial_symbol_features(ladder).get("bb_width")
        if not isinstance(bb_width, (int, float)) or bb_width <= 0:
            bb_width = GRID_LIQUIDITY_FALLBACK_BB_WIDTH
        bb_width_bps = bb_width * 10_000
        spread_threshold_bps = max(
            GRID_LIQUIDITY_MIN_SPREAD_BPS,
            min(
                bb_width_bps * GRID_LIQUIDITY_SPREAD_BB_WIDTH_MULTIPLIER,
                GRID_LIQUIDITY_MAX_SPREAD_BPS,
            ),
        )
        slippage_threshold_bps = max(
            GRID_LIQUIDITY_MIN_SLIPPAGE_BPS,
            min(
                bb_width_bps * GRID_LIQUIDITY_SLIPPAGE_BB_WIDTH_MULTIPLIER,
                GRID_LIQUIDITY_MAX_SLIPPAGE_BPS,
            ),
        )
        return spread_threshold_bps, slippage_threshold_bps

    def _place_initial_entries(self, ladder: GridLadderTable) -> None:
        symbol_row = self._symbol_row(ladder.symbol)
        price_precision = SymbolsCrud.get_price_precision(symbol_row, ExchangeId.KUCOIN)
        placed_order_ids: list[str] = []
        spread_threshold_bps, slippage_threshold_bps = self._grid_liquidity_thresholds(
            ladder
        )

        try:
            largest_level_by_side = {
                side: max(
                    (
                        level.contracts
                        for level in ladder.levels
                        if level.side == side and level.contracts > 0
                    ),
                    default=0,
                )
                for side in ("buy", "sell")
            }
            order_book = load_futures_order_book(
                self.base_streaming.kucoin_futures_api,
                symbol_row.get_futures_symbol(),
            )
            liquidity_snapshots = {
                side: calculate_liquidity_snapshot(
                    order_book,
                    self._side_enum(side),
                    contracts,
                    GRID_LIQUIDITY_PRICE_BAND_BPS,
                )
                for side, contracts in largest_level_by_side.items()
                if contracts > 0
            }
            first_snapshot = next(iter(liquidity_snapshots.values()), None)
            if first_snapshot is None:
                raise RuntimeError(
                    "Grid liquidity rejected: ladder has no executable entry levels"
                )

            self.crud.update_logs(
                ladder.id,
                {
                    "event": "liquidity_snapshot",
                    "spread_bps": round(first_snapshot.spread_bps, 4),
                    "depth_contracts": {
                        "10bps": {
                            "bid": first_snapshot.bid_depth_10_bps,
                            "ask": first_snapshot.ask_depth_10_bps,
                        },
                        "25bps": {
                            "bid": first_snapshot.bid_depth_25_bps,
                            "ask": first_snapshot.ask_depth_25_bps,
                        },
                        "50bps": {
                            "bid": first_snapshot.bid_depth_50_bps,
                            "ask": first_snapshot.ask_depth_50_bps,
                        },
                    },
                    "execution": {
                        side: {
                            "requested_contracts": snapshot.requested_contracts,
                            "contracts_fillable": snapshot.contracts_fillable,
                            "expected_average_fill_price": snapshot.expected_average_fill_price,
                            "expected_slippage_bps": snapshot.expected_slippage_bps,
                        }
                        for side, snapshot in liquidity_snapshots.items()
                    },
                    "book_imbalance": first_snapshot.book_imbalance,
                    "data_age_ms": first_snapshot.data_age_ms,
                    "thresholds_bb_width_scaled": {
                        "spread_bps": round(spread_threshold_bps, 4),
                        "slippage_bps": round(slippage_threshold_bps, 4),
                    },
                },
            )

            if first_snapshot.data_age_ms > GRID_LIQUIDITY_MAX_DATA_AGE_MS:
                raise RuntimeError(
                    "Grid liquidity rejected: KuCoin futures order book is stale "
                    f"({first_snapshot.data_age_ms}ms > "
                    f"{GRID_LIQUIDITY_MAX_DATA_AGE_MS}ms)"
                )
            if first_snapshot.spread_bps > spread_threshold_bps:
                raise RuntimeError(
                    "Grid liquidity rejected: KuCoin futures spread is excessive "
                    f"({first_snapshot.spread_bps:.2f}bps > "
                    f"{spread_threshold_bps:.2f}bps, bb_width-scaled)"
                )

            for side, snapshot in liquidity_snapshots.items():
                if snapshot.contracts_fillable < snapshot.requested_contracts:
                    raise RuntimeError(
                        f"Grid liquidity rejected: hollow {side} book has only "
                        f"{snapshot.contracts_fillable:g} contracts fillable "
                        f"within {GRID_LIQUIDITY_PRICE_BAND_BPS:g}bps for a "
                        f"{snapshot.requested_contracts:g}-contract level"
                    )
                if (
                    snapshot.expected_slippage_bps is None
                    or snapshot.expected_slippage_bps > slippage_threshold_bps
                ):
                    slippage = (
                        f"{snapshot.expected_slippage_bps:.2f}bps"
                        if snapshot.expected_slippage_bps is not None
                        else "unavailable"
                    )
                    raise RuntimeError(
                        f"Grid liquidity rejected: expected {side} slippage is "
                        f"{slippage}; maximum is "
                        f"{slippage_threshold_bps:.2f}bps (bb_width-scaled)"
                    )

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

    def _reconcile_active_ladder(self, ladder: GridLadderTable) -> None:
        for order in ladder.orders:
            if order.status in TERMINAL_GRID_ORDER_STATUSES:
                continue
            if order.order_role == GridOrderRole.stop_loss.value:
                continue

            try:
                details = self.base_streaming.kucoin_futures_api.retrieve_order(
                    order.exchange_order_id
                )
            except Exception as error:
                if self._record_reconciliation_failure(ladder, order, error):
                    return
                continue

            self._clear_reconciliation_failure(ladder, order.exchange_order_id)

            status = self._order_status(details.status)
            filled_qty = self._filled_size(details)
            filled_price = self._filled_price(details, order.price)

            if status in NON_TERMINAL_EXCHANGE_ORDER_STATUSES:
                # Still resting on the exchange book — keep polling. Record any
                # partial progress so far, but don't finalize the order or act
                # on it (e.g. sizing a take-profit) until it's actually done.
                if filled_qty > 0:
                    try:
                        self._record_partial_fill(
                            ladder, order, filled_qty, filled_price
                        )
                        level = order.level
                        if (
                            order.order_role == GridOrderRole.entry.value
                            and level is not None
                        ):
                            self._guard_entry_side(
                                ladder, level, filled_qty, filled_price
                            )
                    except Exception as error:
                        self._handle_post_fill_error(ladder, order, error)
                        return
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
                return

        refreshed_ladder = self.crud.get(ladder.id)
        if (
            refreshed_ladder is not None
            and self._status_value(refreshed_ladder.status)
            == GridLadderStatus.active.value
        ):
            self._reconcile_protective_stops(refreshed_ladder)

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
            self._ensure_protective_stop(ladder, level, filled_qty)
            self._place_take_profit_order(ladder, level)
            return

        if order.order_role == GridOrderRole.take_profit.value:
            self._cancel_level_protective_stops(ladder, level)
            self.crud.mark_level_take_profit_filled(
                level.id,
                realized_pnl=level.realized_pnl
                + self._realized_pnl(ladder, level, filled_price),
            )
            self.crud.recalculate_used_margin(ladder.id)
            self.crud.recalculate_realized_pnl(ladder.id)
            refreshed_ladder = self.crud.get(ladder.id)
            if refreshed_ladder is None:
                return
            completed_cycles = self._completed_cycle_count(refreshed_ladder)
            if completed_cycles >= self._max_completed_cycles(refreshed_ladder):
                self._close_ladder(
                    refreshed_ladder,
                    context_updates={
                        "close_reason": "max_completed_cycles",
                        "completed_cycles": completed_cycles,
                    },
                    log_event={
                        "event": "max_completed_cycles",
                        "completed_cycles": completed_cycles,
                    },
                )
                return
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
        price_precision = SymbolsCrud.get_price_precision(symbol_row, ExchangeId.KUCOIN)
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
                price_precision = SymbolsCrud.get_price_precision(
                    symbol_row, ExchangeId.KUCOIN
                )

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
        both sides' levels as error and enter the automatic cancel-and-flatten
        recovery path.

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
        recoverable = self.crud.get(ladder.id)
        if recoverable is not None:
            self._recover_error_ladder(recoverable)

    def _reconcile_protective_stops(self, ladder: GridLadderTable) -> None:
        local_stops = [
            order
            for order in ladder.orders
            if order.order_role == GridOrderRole.stop_loss.value
            and order.status == GRID_ORDER_OPEN_STATUS
        ]
        if not local_stops:
            return

        symbol_row = self._symbol_row(ladder.symbol)
        try:
            exchange_stops = (
                self.base_streaming.kucoin_futures_api.get_all_stop_loss_orders(
                    symbol_row.get_futures_symbol()
                )
            )
        except Exception as error:
            self._record_reconciliation_failure(ladder, local_stops[0], error)
            return
        self._clear_reconciliation_failure(
            ladder,
            local_stops[0].exchange_order_id,
        )
        open_stop_ids = {str(stop.id) for stop in exchange_stops}
        for order in local_stops:
            if order.exchange_order_id in open_stop_ids:
                continue
            if self._has_exchange_position(ladder.symbol):
                error = RuntimeError(
                    f"Protective stop {order.exchange_order_id} is missing while "
                    f"{ladder.symbol} still has exchange exposure"
                )
                self.crud.update_status_with_context(ladder.id, GridLadderStatus.error)
                self.crud.update_error_logs(ladder.id, error)
                recoverable = self.crud.get(ladder.id)
                if recoverable is not None:
                    self._recover_error_ladder(recoverable)
                return

            self.crud.update_order(
                order.id,
                status=GRID_ORDER_FILLED_STATUS,
                filled_qty=order.contracts,
                filled_price=order.price,
            )
            refreshed_ladder = self.crud.get(ladder.id)
            if refreshed_ladder is None:
                return
            self._close_ladder(
                refreshed_ladder,
                forced_close_price=order.price,
                context_updates={
                    "close_reason": "protective_stop_filled",
                    "protective_stop_order_id": order.exchange_order_id,
                },
                log_event={
                    "event": "protective_stop_filled",
                    "order_id": order.exchange_order_id,
                    "trigger_price": order.price,
                },
            )
            return

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
        recoverable = self.crud.get(ladder.id)
        if recoverable is not None:
            self._recover_error_ladder(recoverable)

    def _close_ladder(
        self,
        ladder: GridLadderTable,
        *,
        forced_close_price: float | None = None,
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
        exchange_close_price = self._close_symbol_position(ladder.symbol)
        close_price = (
            forced_close_price
            if forced_close_price is not None
            else exchange_close_price
        )
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

    def _recover_error_ladder(self, ladder: GridLadderTable) -> None:
        try:
            self._close_ladder(
                ladder,
                context_updates={"close_reason": "error_recovery"},
                log_event={
                    "event": "error_recovery",
                    "has_filled_exposure": self._has_open_exposure(ladder),
                    "has_exchange_position": self._has_exchange_position(ladder.symbol),
                },
            )
        except Exception as error:
            self.crud.update_status_with_context(ladder.id, GridLadderStatus.error)
            self.crud.update_error_logs(ladder.id, error)
