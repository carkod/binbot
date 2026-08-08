from abc import ABC, abstractmethod
from enum import Enum
from time import time

from api.account.controller import ConsolidatedAccounts
from api.databases.crud.grid_ladder_crud import GridLadderCrud
from api.databases.crud.symbols_crud import SymbolsCrud
from api.databases.tables.grid_ladder_table import (
    GridLadderTable,
    GridLevelTable,
    GridOrderTable,
)
from api.databases.tables.signals_table import SignalsTable
from api.databases.tables.symbol_table import SymbolTable
from kucoin_universal_sdk.generate.futures.order.model_add_order_req import AddOrderReq
from pybinbot import (
    ExchangeId,
    GridLadderStatus,
    GridLevelStatus,
    GridOrderRole,
    OrderStatus,
    OrderType,
    round_numbers,
)
from api.grid_ladders.sizing import round_price_to_precision
from kucoin_universal_sdk.generate.futures.order.model_get_order_by_order_id_resp import (
    GetOrderByOrderIdResp,
)
from sqlmodel import Session, col, select
from streaming.base import BaseStreaming
from api.tools.utils import coerce_millisecond_timestamp

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
GRID_REARM_MARKET_REGIMES = frozenset({"RANGE", "TRANSITIONAL"})
GRID_REARM_BLOCKING_MICRO_REGIMES = frozenset({"BREAKOUT_UP", "BREAKDOWN"})
DEFAULT_MAX_COMPLETED_CYCLES = 2
DEFAULT_MAX_LIFETIME_HOURS = 12.0
DEFAULT_MAX_BB_WIDTH_CHANGE_PCT = 20.0
MAX_RECONCILIATION_FAILURES = 3


class BaseLifecycle(ABC):
    """Low-level exchange, persistence, and risk mechanics for grid ladders."""

    # Unfilled ladders retain a one-candle confirmation. Filled exposure has
    # an exchange-native protective stop and an immediate lifecycle fallback.
    UNFILLED_BREACH_CANDLES_REQUIRED = 1

    def __init__(self, base_streaming: BaseStreaming, session: Session):
        self.base_streaming = base_streaming
        self.session = session
        self.crud = GridLadderCrud(session)

    @abstractmethod
    def _handle_conflicting_exposure(
        self,
        ladder: GridLadderTable,
        level: GridLevelTable,
        filled_qty: float,
        filled_price: float,
    ) -> None:
        """Close a ladder when opposing fills create conflicting exposure."""

    @abstractmethod
    def _recover_error_ladder(self, ladder: GridLadderTable) -> None:
        """Safely close a ladder after a lifecycle error."""

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

    def _breakout_close_type(self, ladder: GridLadderTable) -> str:
        if self._has_open_exposure(ladder):
            return "filled_breakout_close"
        return "unfilled_breakout_close"

    def _symbol_row(self, symbol: str) -> SymbolTable:
        symbol_row = self.session.get(SymbolTable, symbol)
        if symbol_row is None:
            raise ValueError(f"Symbol not found: {symbol}")
        return symbol_row

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
        has_open_exposure = self._has_open_exposure(ladder)
        breach_duration_ms = self.UNFILLED_BREACH_CANDLES_REQUIRED * 15 * 60 * 1000

        if price < ladder.breakout_low:
            if has_open_exposure:
                return "down", price
            first_breach = coerce_millisecond_timestamp(
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
            if has_open_exposure:
                return "up", price
            first_breach_up = coerce_millisecond_timestamp(
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

        precision = SymbolsCrud.get_price_precision(symbol_row, ExchangeId.KUCOIN)
        return round_numbers(sum(prices) / len(prices), precision or 8)

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

    def _record_reconciliation_failure(
        self,
        ladder: GridLadderTable,
        order: GridOrderTable,
        error: Exception,
    ) -> bool:
        refreshed_ladder = self.crud.get(ladder.id)
        context = dict(
            refreshed_ladder.context
            if refreshed_ladder is not None and refreshed_ladder.context
            else {}
        )
        failures = context.get("reconciliation_failures")
        if not isinstance(failures, dict):
            failures = {}
        failure_count = int(failures.get(order.exchange_order_id, 0)) + 1
        failures[order.exchange_order_id] = failure_count
        self.crud.update_status_with_context(
            ladder.id,
            GridLadderStatus.active,
            context_updates={"reconciliation_failures": failures},
        )
        self.crud.update_logs(
            ladder.id,
            {
                "event": "order_reconciliation_retry",
                "order_id": order.exchange_order_id,
                "attempt": failure_count,
                "error_type": error.__class__.__name__,
                "message": str(error),
            },
        )
        if failure_count < MAX_RECONCILIATION_FAILURES:
            return False

        self.crud.update_status_with_context(ladder.id, GridLadderStatus.error)
        self.crud.update_error_logs(ladder.id, error)
        recoverable = self.crud.get(ladder.id)
        if recoverable is not None:
            self._recover_error_ladder(recoverable)
        return True

    def _clear_reconciliation_failure(
        self,
        ladder: GridLadderTable,
        exchange_order_id: str,
    ) -> None:
        refreshed_ladder = self.crud.get(ladder.id)
        failures = (
            (refreshed_ladder.context or {}).get("reconciliation_failures")
            if refreshed_ladder is not None
            else None
        )
        if not isinstance(failures, dict) or exchange_order_id not in failures:
            return
        remaining = dict(failures)
        remaining.pop(exchange_order_id, None)
        self.crud.update_status_with_context(
            ladder.id,
            GridLadderStatus.active,
            context_updates={"reconciliation_failures": remaining},
        )

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
            self._ensure_protective_stop(ladder, order.level, filled_qty)

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
        market_regime = self._current_market_regime(ladder)
        if market_regime not in GRID_REARM_MARKET_REGIMES:
            regime_label = market_regime or "UNAVAILABLE"
            allowed = ", ".join(sorted(GRID_REARM_MARKET_REGIMES))
            self.crud.update_logs(
                ladder.id,
                (
                    f"Skipped rearm level {level.level_index}: market_regime "
                    f"{regime_label} is not one of {allowed}"
                ),
            )
            return False

        symbol_block_reason = self._symbol_rearm_block_reason(ladder)
        if symbol_block_reason is not None:
            self.crud.update_logs(
                ladder.id,
                (f"Skipped rearm level {level.level_index}: {symbol_block_reason}"),
            )
            return False

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

    def _current_market_regime(self, ladder: GridLadderTable) -> str | None:
        latest_signal = self.session.exec(
            select(SignalsTable)
            .where(col(SignalsTable.current_regime).is_not(None))
            .order_by(col(SignalsTable.generated_at).desc())
            .limit(1)
        ).first()
        if latest_signal is not None and latest_signal.current_regime:
            return str(latest_signal.current_regime).upper()

        context = ladder.context if isinstance(ladder.context, dict) else {}
        context_regime = context.get("market_regime")
        if context_regime is None:
            return None
        return str(context_regime).upper()

    def _latest_symbol_features(self, ladder: GridLadderTable) -> dict:
        latest_signal = self.session.exec(
            select(SignalsTable)
            .where(SignalsTable.symbol == ladder.symbol)
            .order_by(col(SignalsTable.generated_at).desc())
            .limit(1)
        ).first()
        if latest_signal is None:
            return {}

        context = (
            latest_signal.context if isinstance(latest_signal.context, dict) else {}
        )
        symbol_features = context.get("symbol_features")
        if isinstance(symbol_features, dict):
            features = symbol_features.get(ladder.symbol)
            if isinstance(features, dict):
                return features
        return context

    def _initial_symbol_features(self, ladder: GridLadderTable) -> dict:
        context = ladder.context if isinstance(ladder.context, dict) else {}
        symbol_features = context.get("symbol_features")
        if not isinstance(symbol_features, dict):
            return {}
        features = symbol_features.get(ladder.symbol)
        return features if isinstance(features, dict) else {}

    def _symbol_rearm_block_reason(self, ladder: GridLadderTable) -> str | None:
        features = self._latest_symbol_features(ladder)
        for field_name in ("micro_regime", "micro_regime_transition"):
            raw_value = features.get(field_name)
            if raw_value is None:
                continue
            value = str(raw_value).upper()
            if value in GRID_REARM_BLOCKING_MICRO_REGIMES:
                return f"symbol_{field_name}_{value.lower()}"

        initial_width = self._initial_symbol_features(ladder).get("bb_width")
        current_width = features.get("bb_width")
        if not isinstance(initial_width, (int, float)) or initial_width <= 0:
            return None
        if not isinstance(current_width, (int, float)) or current_width <= 0:
            return None
        max_change_pct = self._grid_option_number(
            ladder,
            "max_bb_width_change_pct",
            DEFAULT_MAX_BB_WIDTH_CHANGE_PCT,
        )
        expansion_pct = ((current_width - initial_width) / initial_width) * 100
        if expansion_pct > max_change_pct:
            return f"bb_width_expanded_{round(expansion_pct, 2)}pct"
        return None

    def _protective_stop_price(
        self,
        ladder: GridLadderTable,
        level: GridLevelTable,
    ) -> float:
        return ladder.breakout_low if level.side == "buy" else ladder.breakout_high

    def _active_level_protective_stops(
        self,
        ladder: GridLadderTable,
        level: GridLevelTable,
    ) -> list[GridOrderTable]:
        return [
            order
            for order in ladder.orders
            if order.level_id == level.id
            and order.order_role == GridOrderRole.stop_loss.value
            and order.status not in TERMINAL_GRID_ORDER_STATUSES
        ]

    def _ensure_protective_stop(
        self,
        ladder: GridLadderTable,
        level: GridLevelTable | None,
        filled_qty: float,
    ) -> None:
        if level is None or filled_qty <= 0:
            return

        active_stops = self._active_level_protective_stops(ladder, level)
        stop_contracts = int(filled_qty)
        if len(active_stops) == 1 and active_stops[0].contracts == stop_contracts:
            return
        if active_stops:
            self._cancel_protective_stop_orders(ladder, active_stops)

        symbol_row = self._symbol_row(ladder.symbol)
        stop_price = round_price_to_precision(
            self._protective_stop_price(ladder, level),
            SymbolsCrud.get_price_precision(symbol_row, ExchangeId.KUCOIN),
        )
        stop_direction = (
            AddOrderReq.StopEnum.DOWN
            if level.side == "buy"
            else AddOrderReq.StopEnum.UP
        )
        order = self.base_streaming.kucoin_futures_api.place_futures_order(
            symbol=symbol_row.get_futures_symbol(),
            side=self._opposite_side_enum(level.side),
            size=stop_contracts,
            leverage=symbol_row.futures_leverage,
            order_type=OrderType.market,
            stop=stop_direction,
            stop_price=stop_price,
            stop_price_type=AddOrderReq.StopPriceTypeEnum.MARK_PRICE,
            reduce_only=True,
        )
        self.crud.create_order(
            ladder_id=ladder.id,
            level_id=level.id,
            exchange_order_id=str(order.order_id),
            order_role=GridOrderRole.stop_loss.value,
            side=self._opposite_side(level.side),
            price=stop_price,
            contracts=stop_contracts,
            status=GRID_ORDER_OPEN_STATUS,
        )
        self.crud.update_logs(
            ladder.id,
            (
                f"Placed protective stop {order.order_id} for level "
                f"{level.level_index}: {self._opposite_side(level.side)} "
                f"{stop_contracts} contracts @ trigger {stop_price}"
            ),
        )

    def _cancel_protective_stop_orders(
        self,
        ladder: GridLadderTable,
        orders: list[GridOrderTable],
    ) -> None:
        order_ids = [order.exchange_order_id for order in orders]
        if not order_ids:
            return
        symbol_row = self._symbol_row(ladder.symbol)
        exchange_stops = (
            self.base_streaming.kucoin_futures_api.get_all_stop_loss_orders(
                symbol_row.get_futures_symbol()
            )
        )
        exchange_stop_ids = {str(stop.id) for stop in exchange_stops}
        cancellable_order_ids = [
            order_id for order_id in order_ids if order_id in exchange_stop_ids
        ]
        if cancellable_order_ids:
            self.base_streaming.kucoin_futures_api.batch_cancel_stop_loss_orders(
                cancellable_order_ids
            )
        for order in orders:
            self.crud.update_order(order.id, status=GRID_ORDER_CANCELLED_STATUS)
        self.crud.update_logs(
            ladder.id,
            f"Cancelled protective stop orders: {', '.join(order_ids)}",
        )

    def _cancel_level_protective_stops(
        self,
        ladder: GridLadderTable,
        level: GridLevelTable,
    ) -> None:
        self._cancel_protective_stop_orders(
            ladder,
            self._active_level_protective_stops(ladder, level),
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
            SymbolsCrud.get_price_precision(symbol_row, ExchangeId.KUCOIN),
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
        *,
        market_exit: bool = False,
    ) -> float:
        symbol_row = self._symbol_row(ladder.symbol)
        contract = self.base_streaming.kucoin_futures_api.get_symbol_info(
            symbol_row.get_futures_symbol()
        )
        multiplier = float(contract.multiplier or 1)
        entry_price = float(level.filled_entry_price or level.price)
        qty = float(level.filled_entry_qty or level.contracts)
        direction = 1 if level.side == "buy" else -1
        gross_pnl = (exit_price - entry_price) * qty * multiplier * direction
        taker_fee_rate = float(getattr(contract, "taker_fee_rate", 0) or 0)
        raw_maker_fee_rate = getattr(contract, "maker_fee_rate", None)
        maker_fee_rate = (
            taker_fee_rate if raw_maker_fee_rate is None else float(raw_maker_fee_rate)
        )
        entry_fee = entry_price * qty * multiplier * maker_fee_rate
        exit_fee_rate = taker_fee_rate if market_exit else maker_fee_rate
        exit_fee = exit_price * qty * multiplier * exit_fee_rate
        return round_numbers(gross_pnl - entry_fee - exit_fee)

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

    def _grid_option_number(
        self,
        ladder: GridLadderTable,
        option_name: str,
        default: float,
    ) -> float:
        grid_context = (ladder.context or {}).get("grid_ladder")
        if not isinstance(grid_context, dict):
            return default
        raw_value = grid_context.get(option_name)
        if not isinstance(raw_value, (int, float)) or raw_value <= 0:
            return default
        return float(raw_value)

    def _max_completed_cycles(self, ladder: GridLadderTable) -> int:
        return int(
            self._grid_option_number(
                ladder,
                "max_completed_cycles",
                DEFAULT_MAX_COMPLETED_CYCLES,
            )
        )

    def _completed_cycle_count(self, ladder: GridLadderTable) -> int:
        return sum(
            order.order_role == GridOrderRole.take_profit.value
            and order.status == GRID_ORDER_FILLED_STATUS
            for order in ladder.orders
        )

    def _max_lifetime_hours(self, ladder: GridLadderTable) -> float:
        return self._grid_option_number(
            ladder,
            "max_lifetime_hours",
            DEFAULT_MAX_LIFETIME_HOURS,
        )

    def _is_max_lifetime(
        self,
        ladder: GridLadderTable,
        max_lifetime_hours: float,
    ) -> bool:
        if not ladder.created_at:
            return False
        max_lifetime_ms = max_lifetime_hours * 60 * 60 * 1000
        return int(time() * 1000) - ladder.created_at >= max_lifetime_ms

    def _first_cycle_timeout_hours(self, ladder: GridLadderTable) -> float | None:
        grid_context = (ladder.context or {}).get("grid_ladder")
        if not isinstance(grid_context, dict):
            return None
        raw_timeout = grid_context.get("first_cycle_timeout_hours")
        if not isinstance(raw_timeout, (int, float)) or raw_timeout <= 0:
            return None
        return float(raw_timeout)

    def _is_first_cycle_timeout(
        self, ladder: GridLadderTable, timeout_hours: float
    ) -> bool:
        if not ladder.created_at:
            return False
        has_completed_cycle = any(
            order.order_role == GridOrderRole.take_profit.value
            and order.status == GRID_ORDER_FILLED_STATUS
            for order in ladder.orders
        )
        if has_completed_cycle:
            return False
        timeout_ms = timeout_hours * 60 * 60 * 1000
        return int(time() * 1000) - ladder.created_at >= timeout_ms

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
            total += self._realized_pnl(
                ladder,
                level,
                close_price,
                market_exit=True,
            )
        return total

    def _cancel_ladder_orders(self, symbol: str) -> None:
        symbol_row = self._symbol_row(symbol)
        self.base_streaming.kucoin_futures_api.cancel_all_futures_orders(
            symbol_row.get_futures_symbol()
        )
        ladder = self.crud.get_active_for_symbol(symbol)
        if ladder is None:
            return
        protective_stops = [
            order
            for order in ladder.orders
            if order.order_role == GridOrderRole.stop_loss.value
            and order.status == GRID_ORDER_OPEN_STATUS
        ]
        if protective_stops:
            self._cancel_protective_stop_orders(ladder, protective_stops)

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
