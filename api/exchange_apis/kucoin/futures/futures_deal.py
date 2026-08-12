from time import time
from typing import Any, Type

from kucoin_universal_sdk.generate.futures.order import GetTradeHistoryReq
from kucoin_universal_sdk.generate.futures.order.model_add_order_req import AddOrderReq
from kucoin_universal_sdk.model.common import RestError
from pybinbot import (
    BinanceKlineIntervals,
    BinbotErrors,
    BotModel,
    Candles,
    DealType,
    KucoinFutures,
    OrderBase,
    OrderModel,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    Status,
    convert_to_kucoin_symbol,
    round_numbers,
    round_timestamp,
)

from api.databases.crud.bot_crud import BotTableCrud
from api.databases.crud.paper_trading_crud import PaperTradingTableCrud
from api.databases.crud.symbols_crud import SymbolsCrud
from api.databases.tables.bot_table import BotTable, PaperTradingTable
from api.exchange_apis.kucoin.deals.base import KucoinBaseBalance
from api.exchange_apis.kucoin.futures.balance import KucoinFuturesBalance
from api.tools.constants import (
    GRADUAL_GAINER_RETEST_ALGO,
    GRADUAL_GAINER_RETEST_PENDING_ENTRY_CANDLES,
    RELATIVE_STRENGTH_IMPULSE_RIDER_ALGO,
    RELATIVE_STRENGTH_IMPULSE_RIDER_PENDING_ENTRY_CANDLES,
    TOP_GAINER_EARLY_MOMENTUM_ALGO,
    TOP_GAINER_EARLY_MOMENTUM_PENDING_ENTRY_CANDLES,
)


class KucoinPositionDeal(KucoinBaseBalance):
    """
    Futures-only deal entry implementation (USDT-M).

    - Position-based (not balance-based)
    - Uses contracts, not qty
    - Orders create / modify positions
    - SL / TP are reduce-only orders
    """

    # SL replacement gating — stop loss is "emergency only", we only
    # touch the on-exchange order when it materially changes, and even
    # then no more often than the cooldown.
    STOP_LOSS_REPLACE_MIN_MOVE_RATIO = 0.0015  # 0.15% of price
    STOP_LOSS_REPLACE_MIN_TICKS = 2
    STOP_LOSS_REPLACE_COOLDOWN_MS = 30_000
    TRAILING_STOP_REFRESH_MIN_IMPROVEMENT_RATIO = 0.002
    TRAILING_STOP_REPLACE_COOLDOWN_MS = 5 * 60 * 1000
    TERMINAL_STOP_ORDER_STATUSES = (
        OrderStatus.FILLED,
        OrderStatus.CANCELED,
        OrderStatus.EXPIRED,
        OrderStatus.REJECTED,
    )
    ENTRY_ATR_WINDOW = 14
    ENTRY_ATR_MULTIPLIER = 0.5
    ENTRY_MIN_ALLOWANCE_PCT = 0.5
    ENTRY_MAX_ALLOWANCE_PCT = 1.5
    ENTRY_FALLBACK_ALLOWANCE_PCT = 0.75
    TOP_GAINER_EARLY_MOMENTUM_RETEST_DISCOUNT_PCT = 0.5
    TOP_GAINER_EARLY_MOMENTUM_STOP_TRIGGER_BUFFER_PCT = 0.5
    GRADUAL_GAINER_RETEST_DISCOUNT_PCT = 0.5

    def __init__(
        self,
        bot: BotModel,
        db_table: Type[BotTable] | Type[PaperTradingTable] = BotTable,
        kucoin_futures_api: KucoinFutures | None = None,
        controller: BotTableCrud | PaperTradingTableCrud | None = None,
        symbols_crud: SymbolsCrud | None = None,
        interval_ms: int | None = None,
    ) -> None:
        super().__init__()
        self.active_bot = bot
        self.db_table = db_table
        self.kucoin_futures_api = kucoin_futures_api or KucoinFutures(
            key=self.config.kucoin_key,
            secret=self.config.kucoin_secret,
            passphrase=self.config.kucoin_passphrase,
        )
        if controller is not None:
            self.controller = controller
        elif db_table == PaperTradingTable:
            self.controller = PaperTradingTableCrud()
        else:
            self.controller = BotTableCrud()

        self.symbols_crud = symbols_crud or SymbolsCrud()
        self.interval_ms = (
            interval_ms or BinanceKlineIntervals(bot.candlestick_interval).get_ms()
        )
        self.symbol_info = self.symbols_crud.get_symbol(bot.pair)
        self.kucoin_futures_api.DEFAULT_LEVERAGE = self.symbol_info.futures_leverage
        self.kucoin_symbol = convert_to_kucoin_symbol(bot)
        self.kucoin_symbol_data = self.kucoin_futures_api.get_symbol_info(
            self.kucoin_symbol
        )
        self.price_precision = self.symbol_info.price_precision

    def _direction_multiplier(self) -> int:
        return -1 if self.active_bot.position == Position.short else 1

    def matching_exchange_fill_timestamp(self, order: OrderModel) -> int:
        """Return the first exchange fill time for an entry order, in milliseconds."""
        try:
            fills = self.kucoin_futures_api.get_fills(order_id=str(order.order_id))
        except Exception as exc:
            self.active_bot.add_log(
                f"Unable to load fill timestamp for order {order.order_id}: {exc}. "
                "Using the exchange order timestamp."
            )
            return order.timestamp

        matching_fills = [
            fill
            for fill in (fills.items or [])
            if str(fill.order_id) == str(order.order_id)
        ]
        trade_timestamps = [
            int(fill.trade_time) // 1_000_000
            for fill in matching_fills
            if fill.trade_time is not None
        ]
        if trade_timestamps:
            return min(trade_timestamps)

        created_timestamps = [
            int(fill.created_at)
            for fill in matching_fills
            if fill.created_at is not None
        ]
        if created_timestamps:
            return min(created_timestamps)

        self.active_bot.add_log(
            f"No matching exchange fill timestamp found for order {order.order_id}. "
            "Using the exchange order timestamp."
        )
        return order.timestamp

    def _is_recovery_bot(self) -> bool:
        recovery_params = self.active_bot.recovery_params
        return (
            recovery_params is not None and recovery_params.reversal_path == "recovery"
        )

    def _reversal_eligible(self) -> bool:
        """True for any bot that should exit bot-side and run the gated reversal
        logic rather than relying on a native exchange stop order.

        Covers:
        - source bots (margin_short_reversal=True, reversal_path="source")
        - recovery bots (margin_short_reversal=False, reversal_path="recovery")
        - plain margin-short bots (margin_short_reversal=True, no recovery_params)
        """
        return (
            self.active_bot.margin_short_reversal
            or self.active_bot.recovery_params is not None
        )

    @classmethod
    def closed_candle_atr(cls, completed_candles: list) -> float | None:
        if len(completed_candles) < cls.ENTRY_ATR_WINDOW + 1:
            return None

        candles = completed_candles[-(cls.ENTRY_ATR_WINDOW + 1) :]
        true_ranges: list[float] = []
        for index in range(1, len(candles)):
            previous_close = float(candles[index - 1][4])
            high = float(candles[index][2])
            low = float(candles[index][3])
            true_ranges.append(
                max(
                    high - low,
                    abs(high - previous_close),
                    abs(low - previous_close),
                )
            )

        if len(true_ranges) < cls.ENTRY_ATR_WINDOW:
            return None
        return sum(true_ranges[-cls.ENTRY_ATR_WINDOW :]) / cls.ENTRY_ATR_WINDOW

    @staticmethod
    def normalize_entry_klines(klines: list) -> list:
        """Normalize KuCoin UI candles to timestamp/open/high/low/close order."""
        normalized_klines = []
        for candle in klines:
            if len(candle) < 5:
                normalized_klines.append(candle)
                continue

            try:
                open_price = float(candle[1])
                standard_high = float(candle[2])
                standard_low = float(candle[3])
                standard_close = float(candle[4])
                dashboard_close = float(candle[2])
                dashboard_high = float(candle[3])
                dashboard_low = float(candle[4])
            except (TypeError, ValueError):
                normalized_klines.append(candle)
                continue

            standard_ohlc_is_valid = standard_high >= max(
                open_price, standard_close
            ) and standard_low <= min(open_price, standard_close)
            dashboard_ohlc_is_valid = dashboard_high >= max(
                open_price, dashboard_close
            ) and dashboard_low <= min(open_price, dashboard_close)
            if not standard_ohlc_is_valid and dashboard_ohlc_is_valid:
                normalized_klines.append(
                    [
                        candle[0],
                        candle[1],
                        candle[3],
                        candle[4],
                        candle[2],
                        *candle[5:],
                    ]
                )
            else:
                normalized_klines.append(candle)

        return normalized_klines

    def body_capped_entry_limit_price(self) -> float:
        interval = BinanceKlineIntervals(
            self.active_bot.candlestick_interval
        ).to_kucoin_interval()
        try:
            klines = self.kucoin_futures_api.get_ui_klines(
                symbol=self.kucoin_symbol,
                interval=interval,
                limit=self.ENTRY_ATR_WINDOW + 3,
            )
        except Exception as exc:
            self.active_bot.add_log(
                f"Entry rejected: unable to load reliable candle data ({exc})."
            )
            raise BinbotErrors(
                "Reliable current and completed candles are unavailable for futures entry."
            ) from exc

        klines = self.normalize_entry_klines(klines)
        completed_candles, current_candle = Candles.partition_closed_candles(
            klines,
            now_ms=int(time() * 1000),
        )
        if not completed_candles or current_candle is None:
            raise BinbotErrors(
                "Reliable current and completed candles are unavailable for futures entry."
            )

        previous_close = float(completed_candles[-1][4])
        current_open = float(current_candle[1])
        if previous_close <= 0 or current_open <= 0:
            self.active_bot.add_log(
                "Entry rejected: candle open or previous close is invalid."
            )
            raise BinbotErrors(
                "Reliable candle open and previous close are unavailable for futures entry."
            )

        if self.active_bot.name == GRADUAL_GAINER_RETEST_ALGO:
            entry_limit_price = round_numbers(
                previous_close * (1 - self.GRADUAL_GAINER_RETEST_DISCOUNT_PCT / 100),
                self.price_precision,
            )
            self.active_bot.add_log(
                "Gradual-gainer retest entry: "
                f"confirmation_close={previous_close}, "
                f"discount={self.GRADUAL_GAINER_RETEST_DISCOUNT_PCT:.2f}%, "
                f"limit={entry_limit_price}."
            )
            return entry_limit_price

        if self.active_bot.name == TOP_GAINER_EARLY_MOMENTUM_ALGO:
            entry_limit_price = round_numbers(
                previous_close
                * (1 - self.TOP_GAINER_EARLY_MOMENTUM_RETEST_DISCOUNT_PCT / 100),
                self.price_precision,
            )
            self.active_bot.add_log(
                "Top-gainer momentum retest entry: "
                f"confirmation_close={previous_close}, "
                f"discount={self.TOP_GAINER_EARLY_MOMENTUM_RETEST_DISCOUNT_PCT:.2f}%, "
                f"limit={entry_limit_price}."
            )
            return entry_limit_price

        if self.active_bot.position == Position.short:
            anchor_price = min(current_open, previous_close)
        else:
            anchor_price = max(current_open, previous_close)

        atr = self.closed_candle_atr(completed_candles)
        if atr is None:
            allowance_pct = self.ENTRY_FALLBACK_ALLOWANCE_PCT
            allowance_source = "fallback"
        else:
            atr_allowance_pct = self.ENTRY_ATR_MULTIPLIER * atr / anchor_price * 100
            allowance_pct = max(
                self.ENTRY_MIN_ALLOWANCE_PCT,
                min(atr_allowance_pct, self.ENTRY_MAX_ALLOWANCE_PCT),
            )
            allowance_source = "ATR"

        direction = self._direction_multiplier()
        entry_limit_price = round_numbers(
            anchor_price * (1 + direction * allowance_pct / 100),
            self.price_precision,
        )
        entry_label = (
            "Recovery body-capped entry"
            if self.active_bot.recovery_params is not None
            else "Body-capped entry"
        )
        self.active_bot.add_log(
            f"{entry_label}: "
            f"anchor={anchor_price}, allowance={allowance_pct:.2f}% "
            f"({allowance_source}), limit={entry_limit_price}."
        )
        return entry_limit_price

    def recovery_entry_limit_price(self) -> float | None:
        if self.active_bot.recovery_params is None:
            return None

        return self.body_capped_entry_limit_price()

    def calculate_contracts(self, balance: float, price: float) -> int:
        """
        Size futures positions from initial margin (margin-spend interpretation).

        ``fiat_order_size`` is the initial margin the bot commits, not the
        risk-at-stop. ``notional = balance * symbol_info.futures_leverage`` and
        ``contracts = notional / (price * multiplier)``. Per-symbol leverage is
        sourced from the symbol table, capped at ``le=3``.
        """
        if balance <= 0 or price <= 0:
            return 0

        symbol_data = self.kucoin_symbol_data
        multiplier = (
            symbol_data.multiplier or self.kucoin_futures_api.DEFAULT_MULTIPLIER or 1
        )

        contracts = balance * self.symbol_info.futures_leverage / (price * multiplier)
        return int(round_numbers(contracts, self.symbol_info.qty_precision))

    def _is_reversal_possible(
        self, mark_price: float, current_contracts: float
    ) -> float:
        reversal_buffer = 1.40
        min_contract_step = float(self.kucoin_symbol_data.lot_size or 1)
        available_balance = float(self.compute_available_balance())
        min_step_margin = self.required_margin_for_contracts(
            min_contract_step, mark_price
        )
        estimated_available_buffer = available_balance - reversal_buffer

        if estimated_available_buffer <= 0 or min_step_margin <= 0:
            return float(current_contracts)

        minimum_flip_contracts = round_numbers(
            float(current_contracts) + min_contract_step,
            self.symbol_info.qty_precision,
        )

        if estimated_available_buffer < min_step_margin:
            return float(current_contracts)

        return float(minimum_flip_contracts)

    def estimate_reversal_possible_for_new_bot(self) -> bool:
        """
        Estimate whether a newly activated futures bot is likely to support a
        same-size one-order reversal later.

        This is weaker than the live reversal pre-check because there is no
        current exchange position yet; it estimates contracts from the current
        market and then reuses the internal affordability logic.
        """
        if not self._reversal_eligible() or self.active_bot.stop_loss <= 0:
            return True

        side = (
            AddOrderReq.SideEnum.SELL
            if self.active_bot.position == Position.short
            else AddOrderReq.SideEnum.BUY
        )
        estimated_price = self.kucoin_futures_api.matching_engine(
            symbol=self.kucoin_symbol,
            side=side,
            size=1,
        )
        if estimated_price is None:
            return False

        estimated_contracts = self.calculate_contracts(
            self.active_bot.fiat_order_size, estimated_price
        )

        if estimated_contracts <= 0:
            return False

        available_contracts = self._is_reversal_possible(
            estimated_price, estimated_contracts
        )
        return available_contracts > estimated_contracts

    def contracts_to_fiat_order_size(self, contracts: float, price: float) -> float:
        """
        Invert calculate_contracts() so fiat_order_size reflects the initial
        margin actually committed by an open futures position.
        """
        if contracts <= 0 or price <= 0:
            return 0.0

        symbol_data = getattr(self, "kucoin_symbol_data", None)
        multiplier = float(
            getattr(symbol_data, "multiplier", 0)
            or getattr(self.kucoin_futures_api, "DEFAULT_MULTIPLIER", 1)
        )

        return round_numbers(
            contracts * price * multiplier / self.symbol_info.futures_leverage,
            8,
        )

    def compute_available_balance(self) -> float:
        """
        Compute the available balance for placing a futures BUY order.

        Balance lookup order:
        1. Futures account (available balance)
        2. Main account (spot main wallet)
        3. Trade account (spot trading wallet)

        Raises BinbotErrors if there is no fiat balance or if the
        configured base order size exceeds the available balance.
        """
        _, _, futures_available = KucoinFuturesBalance().compute_futures_balance()

        if futures_available > 0:
            available_balance = futures_available
        else:
            # 2) Fall back to MAIN, then TRADE accounts from spot API snapshot
            result_balances, _, _ = self.compute_balance()

            if (
                "main" in result_balances
                and self.fiat in result_balances["main"]
                and float(result_balances["main"][self.fiat]) > 0
            ):
                available_balance = float(result_balances["main"][self.fiat])
            elif (
                "trade" in result_balances
                and self.fiat in result_balances["trade"]
                and float(result_balances["trade"][self.fiat]) > 0
            ):
                available_balance = float(result_balances["trade"][self.fiat])

        return available_balance

    def notional_for_contracts(self, contracts: float, price: float) -> float:
        multiplier = (
            self.kucoin_symbol_data.multiplier
            or self.kucoin_futures_api.DEFAULT_MULTIPLIER
        )
        return contracts * price * multiplier

    def required_margin_for_contracts(self, contracts: float, price: float) -> float:
        """
        Estimate the margin needed for a futures order before submitting it.

        Under margin-spend sizing the required margin for a freshly calculated
        position should equal ``fiat_order_size`` (modulo rounding from
        integer contracts), but we recompute it from the contracts actually
        placed so the affordability check uses the exchange-truth notional.
        """
        if contracts <= 0 or price <= 0:
            return 0.0

        notional = self.notional_for_contracts(contracts, price)
        initial_margin = notional / self.symbol_info.futures_leverage
        fees = 2 * notional * (self.kucoin_symbol_data.taker_fee_rate or 0)
        return round_numbers(initial_margin + fees, 8)

    def max_contracts_for_margin(self, available_balance: float, price: float) -> int:
        if available_balance <= 0 or price <= 0:
            return 0

        min_contract_step = self.kucoin_symbol_data.lot_size or 1
        per_contract_margin = self.required_margin_for_contracts(
            min_contract_step, price
        )
        if per_contract_margin <= 0:
            return 0

        contracts = round_numbers(
            (available_balance / per_contract_margin) * min_contract_step,
            self.symbol_info.qty_precision,
        )

        while (
            contracts > 0
            and self.required_margin_for_contracts(contracts, price) > available_balance
        ):
            contracts = round_numbers(
                contracts - min_contract_step,
                self.symbol_info.qty_precision,
            )

        return int(contracts)

    def backfill_position_from_fills(self) -> BotModel:
        self.active_bot.add_log(
            "Position not found in exchange, cannot update size. ADL might have happened, or position might have been closed without bot's knowledge."
        )
        side = (
            GetTradeHistoryReq.SideEnum.BUY
            if self.active_bot.position == Position.short
            else GetTradeHistoryReq.SideEnum.SELL
        )

        start_at = self.active_bot.deal.opening_timestamp
        now_ms = int(time() * 1000)

        fills = self.kucoin_futures_api.get_fills(
            side=side,
            symbol=self.kucoin_symbol,
            start_at=start_at,
            end_at=now_ms,
        )
        self.active_bot.add_log(
            f"Fetched fills history to check for position updates. Number of fills found: {len(fills.items)}."
        )
        if len(fills.items) > 0:
            total_qty = sum(abs(float(fill.size)) for fill in fills.items)
            order_resp = fills.items[0]
            total_notional = sum(
                abs(float(fill.size)) * float(fill.price) for fill in fills.items
            )
            closing_price = (
                round_numbers(total_notional / total_qty, self.price_precision)
                if total_qty > 0
                else float(order_resp.price)
            )
            if self.active_bot.position == Position.short:
                deal_type = (
                    DealType.take_profit
                    if (closing_price < self.active_bot.deal.opening_price)
                    else DealType.stop_loss
                )
            else:
                deal_type = (
                    DealType.take_profit
                    if (closing_price > self.active_bot.deal.opening_price)
                    else DealType.stop_loss
                )

            exit_order = OrderModel(
                order_id=order_resp.order_id,
                order_type=order_resp.order_type.value,
                pair=order_resp.symbol,
                timestamp=order_resp.created_at,
                order_side=order_resp.side.value,
                qty=total_qty,
                price=closing_price,
                status=OrderStatus.FILLED,
                # no data, assumed
                time_in_force="GTC",
                deal_type=deal_type,
            )
            self.active_bot.orders.append(exit_order)
            self.active_bot.deal.closing_price = closing_price
            self.active_bot.deal.closing_qty = total_qty
            self.active_bot.deal.closing_timestamp = order_resp.created_at
            self.active_bot.deal.total_commissions += float(order_resp.fee)
            self.active_bot.status = Status.completed
            self.active_bot.add_log(
                f"Position size updated from fills history. New size: {total_qty}."
            )
            return self.active_bot

        else:
            self.active_bot.add_log(
                "No fills found in history, cannot update position size. ADL might have happened, or position might have been closed without bot's knowledge."
            )
            self.active_bot.status = Status.error

        return self.active_bot

    def remove_stale_orders(self) -> None:
        stale_orders = [
            order
            for order in self.active_bot.orders
            if order.deal_type == DealType.trailing_profit
            and order.status == OrderStatus.FILLED
            and order.price == 0
            and order.qty == 0
        ]
        for stale_order in stale_orders:
            try:
                self.controller.delete_order(
                    str(stale_order.order_id), str(self.active_bot.id)
                )
            except BinbotErrors:
                pass

        self.active_bot.orders = [
            order
            for order in self.active_bot.orders
            if not (
                order.deal_type == DealType.trailing_profit
                and order.status == OrderStatus.FILLED
                and order.price == 0
                and order.qty == 0
            )
        ]

    def cancel_current_sl(self) -> None:
        """
        Find current stop loss orders in exchange in place and batch cancel them.
        this works for both trailing and stop loss, long and short
        """
        stop_orders = self.kucoin_futures_api.get_all_stop_loss_orders(
            self.kucoin_symbol
        )
        if len(stop_orders) > 0:
            stop_order_ids = [order.id for order in stop_orders]
            self.kucoin_futures_api.batch_cancel_stop_loss_orders(stop_order_ids)
            self.active_bot.orders = [
                o for o in self.active_bot.orders if o.order_id not in stop_order_ids
            ]
        else:
            self.remove_stale_orders()

    def cancel_current_trailing_sl(self) -> None:
        """
        Cancel only the active trailing stop when the bot knows its order id.

        First trailing activation still falls back to the broad stop cleanup so
        the emergency SL can be replaced by the trailing SL.
        """
        _, _, trailing_order_id = self._bot_known_trailing_stop_loss()
        if trailing_order_id is None:
            self.cancel_current_sl()
            return

        stop_orders = self.kucoin_futures_api.get_all_stop_loss_orders(
            self.kucoin_symbol
        )
        stop_order_ids = [
            order.id
            for order in stop_orders
            if str(getattr(order, "id", "")) == trailing_order_id
        ]
        if stop_order_ids:
            self.kucoin_futures_api.batch_cancel_stop_loss_orders(stop_order_ids)

        self.active_bot.orders = [
            order
            for order in self.active_bot.orders
            if str(order.order_id) != trailing_order_id
        ]
        if not stop_order_ids:
            self.remove_stale_orders()

    def _bot_known_stop_order(
        self,
        deal_type: DealType,
        fallback_price: float,
    ) -> tuple[float | None, int | None, str | None]:
        """
        Source of truth from the bot's local order list:
        return (price, timestamp_ms, order_id) of the most recent open stop
        order matching the requested deal type, or (None, None, None) if
        there is no matching local order.
        """
        for order in reversed(self.active_bot.orders):
            if order.deal_type != deal_type:
                continue
            if order.status in self.TERMINAL_STOP_ORDER_STATUSES:
                continue
            order_price = float(order.price or 0)
            ts = int(order.timestamp or 0)
            order_id = str(order.order_id) if order.order_id else None
            if order_price > 0:
                return order_price, ts, order_id
            if fallback_price > 0:
                return fallback_price, ts, order_id
            return None, ts, order_id
        return None, None, None

    def _bot_known_stop_loss(self) -> tuple[float | None, int | None]:
        stop_price, ts, _ = self._bot_known_stop_order(
            DealType.stop_loss,
            self.active_bot.deal.stop_loss_price,
        )
        return stop_price, ts

    def _bot_known_trailing_stop_loss(
        self,
    ) -> tuple[float | None, int | None, str | None]:
        return self._bot_known_stop_order(
            DealType.trailing_profit,
            self.active_bot.deal.trailing_stop_loss_price,
        )

    def _exchange_stop_loss_price(
        self, order_id: str | None = None
    ) -> tuple[bool, float | None]:
        """
        Source of truth from the exchange.

        Returns ``(ok, price)``:
          - ``ok=True, price=float``  → exchange has an SL at this price
          - ``ok=True, price=None``   → exchange confirmed no SL exists
            for the requested order id, or no stop exists when no id is passed
          - ``ok=False, price=None``  → query failed; caller must NOT treat
            this as "no SL", or it will cancel/replace a still-valid one.
        """
        try:
            stop_orders = self.kucoin_futures_api.get_all_stop_loss_orders(
                self.kucoin_symbol
            )
        except Exception as exc:
            self.active_bot.add_log(f"Could not query exchange stop orders: {exc}")
            return False, None

        if not stop_orders:
            return True, None

        matching_orders: list[Any] = stop_orders
        if order_id is not None:
            matching_orders = [
                order
                for order in stop_orders
                if str(getattr(order, "id", "")) == order_id
            ]

        if not matching_orders:
            return True, None

        for order in matching_orders:
            stop_price = float(getattr(order, "stop_price", 0) or 0)
            if stop_price > 0:
                return True, stop_price
        return True, None

    def should_replace_stop_loss_order(
        self,
        current_stop_price: float | None,
        new_stop_price: float,
        last_replace_ts_ms: int | None = None,
        cooldown_ms: int | None = None,
    ) -> bool:
        """
        Decide whether the on-exchange SL needs replacing.

        Replace only when:
          - we have a meaningful new price, and
          - either there's no current SL, or the new one is *better* by more
            than the min-move threshold, and
          - the cooldown since the last replace has elapsed.
        """
        if new_stop_price <= 0:
            return False

        if current_stop_price is None or current_stop_price <= 0:
            return True

        direction = self._direction_multiplier()
        improvement = (new_stop_price - current_stop_price) * direction
        if improvement <= 0:
            return False

        tick_size = 10 ** (-self.price_precision)
        min_replace_move = max(
            abs(current_stop_price) * self.STOP_LOSS_REPLACE_MIN_MOVE_RATIO,
            tick_size * self.STOP_LOSS_REPLACE_MIN_TICKS,
        )
        if improvement < min_replace_move:
            return False

        if last_replace_ts_ms and last_replace_ts_ms > 0:
            cooldown = (
                self.STOP_LOSS_REPLACE_COOLDOWN_MS
                if cooldown_ms is None
                else cooldown_ms
            )
            now_ms = int(time() * 1000)
            if now_ms - last_replace_ts_ms < cooldown:
                return False

        return True

    def reconcile_exchange_sl(self) -> None:
        """
        Reconcile the on-exchange emergency stop loss with what the bot
        thinks should be there.

        Cases handled:
          1. Bot expects SL but exchange has none — re-place (it was cancelled
             externally, expired, or never made it through).
          2. Exchange has an SL at a price that disagrees with the bot's
             local record — adopt the exchange price as truth (someone moved
             it manually) and only replace if it's now unsafe.
          3. Bot wants to ratchet SL closer to entry — only replace if the
             move is material and the cooldown has elapsed.

        Skipped when:
          - bot is reversal-eligible (margin_short_reversal=True or recovery_params set);
            those bots exit bot-side via exit() so a native exchange stop must not be
            placed or it would complete the bot before the gated reversal can run.
          - trailing has armed (trailing_stop_loss_price != 0); in that
            mode the exit is bot-side, the emergency SL is left alone.
        """
        if self.active_bot.stop_loss <= 0:
            return
        if self._reversal_eligible():
            return
        if self.active_bot.deal.trailing_stop_loss_price != 0:
            trailing_reconciler = getattr(self, "reconcile_trailing_stop_loss", None)
            if callable(trailing_reconciler):
                trailing_reconciler()
            return

        # Intended price
        if self.active_bot.deal.stop_loss_price <= 0:
            return

        exchange_ok, exchange_price = self._exchange_stop_loss_price()
        if not exchange_ok:
            # API blip — we don't know what's on the exchange. Bail out and
            # try again next tick rather than risk cancelling/duplicating
            # a still-valid emergency SL.
            return

        bot_known_price, last_replace_ts_ms = self._bot_known_stop_loss()

        # Case 1: exchange confirmed no SL exists — re-place.
        if exchange_price is None:
            if bot_known_price is not None:
                self.active_bot.add_log(
                    "Exchange SL missing — re-placing emergency stop."
                )
            self.cancel_current_sl()  # cleans local stale records, no-op on empty
            self.place_stop_loss()
            return

        if self.active_bot.name == TOP_GAINER_EARLY_MOMENTUM_ALGO:
            expected_trigger_price = self.top_gainer_stop_trigger_price(
                self.active_bot.deal.stop_loss_price
            )
            if abs(exchange_price - expected_trigger_price) > (
                10**-self.price_precision
            ):
                self.active_bot.add_log(
                    "Bounded top-gainer stop drift detected: "
                    f"expected trigger={expected_trigger_price} exchange={exchange_price}; replacing."
                )
                self.cancel_current_sl()
                self.place_stop_loss()
            return

        # Case 2: exchange disagrees with our local record. Log the drift,
        # but keep the bot's freshly-ratcheted target (already computed into
        # deal.stop_loss_price by recompute_derived_prices) intact so Case 3
        # can judge it against the exchange price below. Overwriting it here
        # would make current_stop_price == new_stop_price in Case 3 and
        # permanently disable the ratchet the first time drift is seen.
        ratcheted_target = self.active_bot.deal.stop_loss_price
        if bot_known_price is not None and abs(exchange_price - bot_known_price) > (
            10**-self.price_precision
        ):
            self.active_bot.add_log(
                f"Exchange SL drift detected: bot={bot_known_price} exchange={exchange_price}; trusting exchange."
            )

        # Case 3: ratchet — replace only if materially better and not on cooldown.
        if self.should_replace_stop_loss_order(
            current_stop_price=exchange_price,
            new_stop_price=ratcheted_target,
            last_replace_ts_ms=last_replace_ts_ms,
        ):
            self.cancel_current_sl()
            self.place_stop_loss()
        else:
            # Not replacing — the exchange price is what's actually
            # protecting the position, so adopt it as truth.
            self.active_bot.deal.stop_loss_price = round_numbers(
                exchange_price, self.price_precision
            )

    def base_order(self) -> BotModel:
        """
        Futures have positions intrinsically built, the base order can be either LONG or SHORT, we don't need to deal with loans, we simply set the position as an order
        """
        if self.active_bot.fiat_order_size <= 0:
            raise BinbotErrors("Fiat order size must be set.")

        available_balance = self.compute_available_balance()
        entry_limit_price = self.body_capped_entry_limit_price()
        price = entry_limit_price

        margin_sized_contracts = self.calculate_contracts(
            self.active_bot.fiat_order_size, price
        )

        if margin_sized_contracts <= 0:
            raise BinbotErrors(
                "Calculated contracts is 0. Check if the order size, stop loss, and risk settings are correct."
            )

        affordable_contracts = self.max_contracts_for_margin(available_balance, price)
        contracts = min(margin_sized_contracts, affordable_contracts)

        if contracts <= 0:
            min_contract_margin = self.required_margin_for_contracts(
                self.kucoin_symbol_data.lot_size or 1, price
            )
            raise BinbotErrors(
                f"Required futures margin {min_contract_margin} {self.fiat} for the minimum contract size "
                f"exceeds available balance {available_balance} {self.fiat}."
            )

        required_margin = self.required_margin_for_contracts(contracts, price)
        if required_margin > available_balance:
            raise BinbotErrors(
                f"Required futures margin {required_margin} {self.fiat} for {contracts} contracts "
                f"exceeds available balance {available_balance} {self.fiat}."
            )

        actual_margin = self.contracts_to_fiat_order_size(contracts, price)
        notional = round_numbers(self.notional_for_contracts(contracts, price), 8)

        if contracts < margin_sized_contracts:
            self.active_bot.add_log(
                f"Futures order downsized from {margin_sized_contracts} to {contracts} contracts "
                f"because required margin exceeded available balance."
            )

        recovery_params = self.active_bot.recovery_params
        if (
            self._is_recovery_bot()
            and recovery_params is not None
            and recovery_params.source_contracts > 0
            and contracts < recovery_params.source_contracts * 0.60
        ):
            self.active_bot.add_log(
                "underpowered_recovery: "
                f"opening {contracts} contracts, below 60% of source "
                f"{recovery_params.source_contracts} contracts."
            )

        self.active_bot.add_log(
            f"Futures activation sizing: contracts={contracts}, notional={notional} {self.fiat}, "
            f"leverage={self.symbol_info.futures_leverage}x, required_margin={required_margin} {self.fiat}, "
            f"available_balance={available_balance} {self.fiat}, planned_margin={self.active_bot.fiat_order_size} {self.fiat}, "
            f"actual_margin={actual_margin} {self.fiat}."
        )

        if self.active_bot.position == Position.short:
            order: OrderBase = self.kucoin_futures_api.sell(
                symbol=self.kucoin_symbol,
                qty=contracts,
                leverage=self.symbol_info.futures_leverage,
                entry_limit_price=entry_limit_price,
            )
        else:
            order = self.kucoin_futures_api.buy(
                symbol=self.kucoin_symbol,
                qty=contracts,
                entry_limit_price=entry_limit_price,
            )

        order.deal_type = DealType.base_order
        order = OrderModel(**order.model_dump())
        self.active_bot.orders.append(order)

        mark_price = self.kucoin_futures_api.get_mark_price(self.kucoin_symbol)

        # For Futures, base_order_size is contracts
        # Kucoin only operates with contracts, not underlying asset (qty)
        # so in Binbot we only care about that
        self.active_bot.deal.base_order_size = contracts
        self.active_bot.deal.opening_timestamp = order.timestamp
        self.active_bot.deal.current_price = mark_price

        # Check if the order has already been filled on the exchange. Futures
        # market orders settle quickly but not always before this code runs —
        # the position endpoint can lag by several minutes. If unfilled, leave
        # opening_price == 0 and do not activate; open_deal() will set the bot
        # to pending and order_updates() will promote it once KuCoin confirms
        # the fill. Only set status = active here on an instant fill.
        system_order = self.kucoin_futures_api.retrieve_order(str(order.order_id))
        filled_size = float(system_order.filled_size)
        avg_price = float(system_order.avg_deal_price)
        if filled_size > 0 and avg_price > 0:
            order.status = OrderStatus.FILLED
            order.qty = filled_size
            order.price = avg_price
            self.active_bot.deal.opening_price = avg_price
            self.active_bot.deal.opening_qty = filled_size
            if self.active_bot.name == RELATIVE_STRENGTH_IMPULSE_RIDER_ALGO:
                self.active_bot.deal.opening_timestamp = (
                    self.matching_exchange_fill_timestamp(order)
                )
            self.active_bot.status = Status.active
        else:
            self.active_bot.status = Status.pending

        position_label = getattr(
            self.active_bot.position,
            "name",
            self.active_bot.position,
        )
        if self.active_bot.deal.opening_price > 0:
            log_message = f"Futures {position_label} opened @ {self.active_bot.deal.opening_price} with {int(self.active_bot.deal.opening_qty)} contracts"
        else:
            pending_entry_minutes = 5
            if self.active_bot.name == GRADUAL_GAINER_RETEST_ALGO:
                pending_entry_minutes = (
                    self.interval_ms
                    * GRADUAL_GAINER_RETEST_PENDING_ENTRY_CANDLES
                    // 60_000
                )
            elif self.active_bot.name == RELATIVE_STRENGTH_IMPULSE_RIDER_ALGO:
                pending_entry_minutes = (
                    self.interval_ms
                    * RELATIVE_STRENGTH_IMPULSE_RIDER_PENDING_ENTRY_CANDLES
                    // 60_000
                )
            elif self.active_bot.name == TOP_GAINER_EARLY_MOMENTUM_ALGO:
                pending_entry_minutes = (
                    self.interval_ms
                    * TOP_GAINER_EARLY_MOMENTUM_PENDING_ENTRY_CANDLES
                    // 60_000
                )
            log_message = (
                f"Futures {position_label} entry limit order {order.order_id} submitted "
                f"at {entry_limit_price} with {contracts} contracts. Bot is pending "
                f"for up to {pending_entry_minutes} minutes awaiting fill."
            )
        self.controller.update_logs(
            bot=self.active_bot,
            log_message=log_message,
        )

        self.controller.save(self.active_bot)
        return self.active_bot

    def top_gainer_stop_trigger_price(self, stop_price: float) -> float:
        direction = self._direction_multiplier()
        return round_numbers(
            stop_price
            * (
                1
                + direction
                * self.TOP_GAINER_EARLY_MOMENTUM_STOP_TRIGGER_BUFFER_PCT
                / 100
            ),
            self.price_precision,
        )

    def place_stop_loss(self) -> None:
        if self.active_bot.stop_loss <= 0:
            return

        direction = self._direction_multiplier()
        stop_price = self.active_bot.deal.stop_loss_price
        if stop_price <= 0:
            stop_price = round_numbers(
                self.active_bot.deal.opening_price
                - (
                    self.active_bot.deal.opening_price
                    * (self.active_bot.stop_loss / 100)
                    * direction
                ),
                self.price_precision,
            )

        if self.active_bot.position == Position.short:
            side = AddOrderReq.SideEnum.BUY
            stop = AddOrderReq.StopEnum.UP
        else:
            side = AddOrderReq.SideEnum.SELL
            stop = AddOrderReq.StopEnum.DOWN

        bounded_top_gainer_stop = self.active_bot.name == TOP_GAINER_EARLY_MOMENTUM_ALGO
        trigger_price = (
            self.top_gainer_stop_trigger_price(stop_price)
            if bounded_top_gainer_stop
            else stop_price
        )

        order_response = self.kucoin_futures_api.place_futures_order(
            symbol=self.kucoin_symbol,
            side=side,
            order_type=(
                OrderType.limit if bounded_top_gainer_stop else OrderType.market
            ),
            price=stop_price if bounded_top_gainer_stop else None,
            stop=stop,
            stop_price=trigger_price,
            stop_price_type=AddOrderReq.StopPriceTypeEnum.MARK_PRICE,
            reduce_only=True,
            size=self.active_bot.deal.opening_qty,
            leverage=self.symbol_info.futures_leverage,
            allow_market_fallback=not bounded_top_gainer_stop,
        )

        if order_response.price and order_response.qty:
            self.active_bot.add_log(
                f"Stop loss placed @ {order_response.price} for {order_response.qty} contracts."
            )
            self.remove_stale_orders()

        order_response.deal_type = DealType.stop_loss
        order_model = OrderModel(**order_response.model_dump())
        self.active_bot.orders.append(order_model)
        self.active_bot.deal.stop_loss_price = stop_price

        self.controller.update_logs(
            bot=self.active_bot,
            log_message=(
                f"Bounded stop loss trigger set @ {trigger_price}, limit @ {stop_price}"
                if bounded_top_gainer_stop
                else f"Stop loss set @ {stop_price}"
            ),
        )

    def recompute_derived_prices(self) -> BotModel:
        """
        Pure in-memory recomputation of derived deal prices from the bot's
        percent parameters and opening price. Safe to call every tick — does
        no exchange I/O, places no orders.
        """
        direction = self._direction_multiplier()

        # edge case, should be set from base_order
        if self.active_bot.deal.opening_price == 0:
            for order in self.active_bot.orders:
                if order.deal_type == DealType.base_order:
                    self.active_bot.deal.opening_price = order.price
                    self.active_bot.deal.opening_qty = order.qty
                    self.active_bot.deal.opening_timestamp = order.timestamp
                    break

        if self.active_bot.stop_loss > 0:
            entry_price = self.active_bot.deal.opening_price
            delta = entry_price * (self.active_bot.stop_loss / 100)
            stop_loss_price = entry_price - (delta * direction)
            self.active_bot.deal.stop_loss_price = round_numbers(
                stop_loss_price, self.price_precision
            )

        if (
            self.active_bot.trailing
            and self.active_bot.trailing_deviation > 0
            and self.active_bot.trailing_profit > 0
        ):
            entry_price = self.active_bot.deal.opening_price
            trailing_profit_price = entry_price * (
                1 + direction * (self.active_bot.trailing_profit / 100)
            )
            self.active_bot.deal.trailing_profit_price = round_numbers(
                trailing_profit_price, self.price_precision
            )
            # NOTE: trailing_stop_loss_price is intentionally preserved here.
            # Resetting an armed trail every tick would (a) defeat dynamic
            # trailing and (b) bypass the trailing-armed guard in
            # reconcile_exchange_sl(). The "Update Deal" flow that needs to
            # disarm the trail does so explicitly in open_deal().

        return self.active_bot

    def update_parameters(self) -> BotModel:
        """
        Update derived prices in-memory and reconcile the on-exchange
        emergency SL with what the bot now expects. The two halves are
        deliberately separated:

          - recompute_derived_prices() is pure and tick-safe.
          - reconcile_exchange_sl() touches the exchange and is gated by
            drift detection + min-move + cooldown to avoid order churn.
        """
        self.recompute_derived_prices()
        self.reconcile_exchange_sl()
        return self.active_bot

    def update_parameters_with_activation(self) -> BotModel:
        """
        update_parameters with some additional logic for activation:
        - If the bot is already active, it means we are updating parameters without changing the position, so we just call update_parameters.
        - If the bot is not active, it means we are activating the bot, so we need to set the parameters and then activate it. This is used for example when we open a new deal and we want to set the SL and TP at the same time, so we update parameters with activation right after opening the deal.
        """
        direction = self._direction_multiplier()

        if self.active_bot.stop_loss > 0:
            price = self.active_bot.deal.opening_price
            delta = price * (self.active_bot.stop_loss / 100)
            self.active_bot.deal.stop_loss_price = price - (delta * direction)

        if self.active_bot.trailing:
            trailing_profit = self.active_bot.deal.opening_price * (
                1 + direction * (self.active_bot.trailing_profit / 100)
            )
            self.active_bot.deal.trailing_profit_price = trailing_profit
            self.active_bot.deal.trailing_stop_loss_price = 0
            self.active_bot.deal.take_profit_price = 0
        else:
            take_profit_price = self.active_bot.deal.opening_price * (
                1 + direction * (self.active_bot.take_profit / 100)
            )
            self.active_bot.deal.take_profit_price = take_profit_price

        self.active_bot.status = Status.active
        if direction == -1:
            self.active_bot.add_log("Bot re-activated (short)")
        else:
            self.active_bot.add_log("Bot re-activated")
        self.controller.save(self.active_bot)
        return self.active_bot

    def should_refresh_trailing_stop_loss(
        self,
        current_stop_price: float,
        new_stop_price: float,
        direction: int,
        last_replace_ts_ms: int | None = None,
    ) -> bool:
        if new_stop_price <= 0:
            return False

        if self.trailing_stop_replace_on_cooldown(last_replace_ts_ms):
            return False

        if current_stop_price <= 0:
            return True

        improvement = (new_stop_price - current_stop_price) * direction
        if improvement <= 0:
            return False

        min_improvement = (
            abs(current_stop_price) * self.TRAILING_STOP_REFRESH_MIN_IMPROVEMENT_RATIO
        )
        return improvement >= min_improvement

    def trailing_stop_replace_on_cooldown(self, last_replace_ts_ms: int | None) -> bool:
        if not last_replace_ts_ms or last_replace_ts_ms <= 0:
            return False

        now_ms = int(time() * 1000)
        return now_ms - last_replace_ts_ms < self.TRAILING_STOP_REPLACE_COOLDOWN_MS

    def last_trailing_stop_replace_ts_ms(self) -> int | None:
        _, ts, _ = self._bot_known_trailing_stop_loss()
        return ts

    def take_profit_order(self) -> BotModel:
        """
        Futures take profit:
        - Closes the current futures position with a reduce-only order
          (SELL for longs, BUY for shorts).
        """
        deal_buy_price = self.active_bot.deal.opening_price
        buy_total_qty = self.active_bot.deal.opening_qty
        take_profit_pct = self.active_bot.take_profit / 100
        take_profit_multiplier = (
            1 - take_profit_pct
            if self.active_bot.position == Position.short
            else 1 + take_profit_pct
        )
        self.active_bot.deal.take_profit_price = take_profit_multiplier * deal_buy_price
        close_side = (
            OrderSide.buy
            if self.active_bot.position == Position.short
            else OrderSide.sell
        )

        # Paper trading: do not hit the exchange, just simulate an order
        if isinstance(self.controller, PaperTradingTableCrud):
            price = (
                self.active_bot.deal.current_price
                if self.active_bot.deal.current_price > 0
                else deal_buy_price
            )
            qty = round_numbers(buy_total_qty, 8)
            order_data = OrderModel(
                timestamp=int(time() * 1000),
                order_id="paper-futures-tp",
                deal_type=DealType.take_profit,
                pair=self.kucoin_symbol,
                order_side=close_side,
                order_type="MARKET",
                price=price,
                qty=float(qty),
                time_in_force="GTC",
                status=OrderStatus.FILLED,
            )
        else:
            # Real futures: close current LONG position via reduce-only SELL
            position = self.kucoin_futures_api.get_futures_position(self.kucoin_symbol)
            if not position or float(position.current_qty) == 0:
                self.active_bot = self.backfill_position_from_fills()
                return self.active_bot

            qty = round_numbers(abs(float(position.current_qty)), 8)
            if self.active_bot.position == Position.short:
                self.controller.update_logs(
                    "Dispatching futures buy order for take profit...",
                    self.active_bot,
                )
                order_base = self.kucoin_futures_api.buy(
                    symbol=self.kucoin_symbol,
                    qty=qty,
                    reduce_only=True,
                )
            else:
                self.controller.update_logs(
                    "Dispatching futures sell order for take profit...",
                    self.active_bot,
                )
                order_base = self.kucoin_futures_api.place_futures_order(
                    symbol=self.kucoin_symbol,
                    side=AddOrderReq.SideEnum.SELL,
                    size=qty,
                    order_type=OrderType.market,
                    reduce_only=True,
                    leverage=self.symbol_info.futures_leverage,
                )

            order_base.deal_type = DealType.take_profit
            # Convert OrderBase to OrderModel using model_dump/model_construct
            order_data = OrderModel.model_construct(**order_base.model_dump())

        self.active_bot.orders.append(order_data)
        self.active_bot.deal.closing_price = float(order_data.price)
        self.active_bot.deal.closing_qty = float(order_data.qty)
        self.active_bot.deal.closing_timestamp = round_timestamp(order_data.timestamp)
        self.active_bot.status = Status.completed

        self.active_bot.add_log("Completed futures take profit.")
        self.controller.save(self.active_bot)

        return self.active_bot

    def execute_stop_loss(self, reference_price: float | None = None) -> BotModel:
        """
        Place a stop loss limit order, since we've hit the threshold

        - Hard sell (order status="FILLED" immediately) initial amount crypto in deal
        - Close current opened take profit order
        - Deactivate bot

        When ``reference_price`` is provided the close order is routed through the
        anti-wick escalation path (band-capped IOC → market fallback) so the fill
        stays within a sane slippage band off the last-closed-candle price.
        """
        self.controller.update_logs("Placing Futures stop loss...", self.active_bot)

        # Paper trading: simulate without hitting the exchange
        if isinstance(self.controller, PaperTradingTableCrud):
            qty = self.active_bot.deal.opening_qty
            if qty <= 0:
                return self.active_bot

            # Use reference_price as the simulated fill price when available so
            # paper-trade results reflect the anti-wick capped behaviour.
            price = (
                reference_price
                if reference_price is not None
                else self.active_bot.deal.current_price
            )
            close_side = (
                OrderSide.buy
                if self.active_bot.position == Position.short
                else OrderSide.sell
            )
            stop_loss_order = OrderModel(
                timestamp=int(time() * 1000),
                order_id="paper-futures-sl",
                deal_type=DealType.stop_loss,
                pair=self.kucoin_symbol,
                order_side=close_side,
                order_type=OrderType.limit,
                price=price,
                qty=float(qty),
                time_in_force="GTC",
                status=OrderStatus.FILLED,
            )
        else:
            qty = self.active_bot.deal.opening_qty
            try:
                if self.active_bot.position == Position.short:
                    order_base = self.kucoin_futures_api.buy(
                        symbol=self.kucoin_symbol,
                        qty=qty,
                        reduce_only=True,
                        reference_price=reference_price,
                    )
                else:
                    order_base = self.kucoin_futures_api.sell(
                        symbol=self.kucoin_symbol,
                        qty=qty,
                        reduce_only=True,
                        leverage=self.symbol_info.futures_leverage,
                        reference_price=reference_price,
                    )

            except RestError as e:
                if float(e.response.code) == 300009:
                    self.controller.update_logs(
                        bot=self.active_bot,
                        log_message=f"{str(e.response.message)}",
                    )
                    self.active_bot.status = Status.completed
                    self.controller.save(self.active_bot)
                    return self.active_bot
                else:
                    self.controller.update_logs(
                        bot=self.active_bot,
                        log_message=f"Failed to execute stop loss order: {str(e.response.message)}",
                    )
                    self.active_bot.status = Status.error
                    return self.active_bot

            order_base.deal_type = DealType.stop_loss
            stop_loss_order = OrderModel.model_construct(**order_base.model_dump())

        self.active_bot.orders.append(stop_loss_order)
        self.active_bot.deal.closing_price = float(stop_loss_order.price)
        self.active_bot.deal.closing_qty = float(stop_loss_order.qty)
        self.active_bot.deal.closing_timestamp = stop_loss_order.timestamp
        self.active_bot.add_log("Completed futures Stop loss.")

        if stop_loss_order.status != OrderStatus.FILLED:
            self.controller.update_logs(
                bot=self.active_bot,
                log_message=f"Stop loss order not filled immediately, got status {stop_loss_order.status}. Manual intervention may be required.",
            )
        else:
            self.active_bot.status = Status.completed

        self.controller.save(self.active_bot)

        return self.active_bot

    def place_trailing_stop_loss(
        self, repurchase_multiplier: float = 1
    ) -> BotModel | None:
        """
        Place the closing position (stop loss in Kucoin) when the bot (long or short) is
        in a profitable position

        This only places the stop loss order at the exchange, the actual bot status and deal parameters will be updated when the order is filled and the system receives the update via websocket (handled in futures_position.order_updates)
        """

        if isinstance(self.controller, PaperTradingTableCrud):
            # all qty simulated
            qty = self.active_bot.deal.opening_qty or 1.0
            price = self.active_bot.deal.current_price
            close_side = (
                OrderSide.buy
                if self.active_bot.position == Position.short
                else OrderSide.sell
            )
            order_data = OrderModel(
                timestamp=int(time() * 1000),
                order_id="paper-futures-trail",
                deal_type=DealType.trailing_profit,
                pair=self.kucoin_symbol,
                order_side=close_side,
                order_type="MARKET",
                price=price,
                qty=float(qty),
                time_in_force="GTC",
                status=OrderStatus.FILLED,
            )
        else:
            position = self.kucoin_futures_api.get_futures_position(self.kucoin_symbol)
            if not position or float(position.current_qty) == 0:
                # If position doesn't exist, there's no point in trailing anymore
                # so we backfill orders and finish
                self.active_bot = self.backfill_position_from_fills()
                return self.active_bot

            qty = round_numbers(
                abs(float(position.current_qty)) * repurchase_multiplier, 8
            )
            intended_price = self.active_bot.deal.trailing_stop_loss_price
            _, last_replace_ts_ms, trailing_order_id = (
                self._bot_known_trailing_stop_loss()
            )
            exchange_ok, exchange_price = self._exchange_stop_loss_price(
                order_id=trailing_order_id
            )
            if exchange_ok:
                if exchange_price is None and self.trailing_stop_replace_on_cooldown(
                    last_replace_ts_ms
                ):
                    return self.active_bot
                if (
                    exchange_price is not None
                    and not self.should_replace_stop_loss_order(
                        current_stop_price=exchange_price,
                        new_stop_price=intended_price,
                        last_replace_ts_ms=last_replace_ts_ms,
                        cooldown_ms=self.TRAILING_STOP_REPLACE_COOLDOWN_MS,
                    )
                ):
                    return self.active_bot
            elif self.trailing_stop_replace_on_cooldown(last_replace_ts_ms):
                return self.active_bot

            action = "buy" if self.active_bot.position == Position.short else "sell"
            self.controller.update_logs(
                f"Dispatching futures {action} order for trailing profit...",
                self.active_bot,
            )

            self.cancel_current_trailing_sl()

            if self.active_bot.position == Position.short:
                order_base: OrderBase = self.kucoin_futures_api.place_futures_order(
                    side=AddOrderReq.SideEnum.BUY,
                    symbol=self.kucoin_symbol,
                    size=qty,
                    reduce_only=True,
                    order_type=OrderType.market,
                    stop_price_type=AddOrderReq.StopPriceTypeEnum.MARK_PRICE,
                    stop=AddOrderReq.StopEnum.UP,
                    stop_price=self.active_bot.deal.trailing_stop_loss_price,
                    leverage=self.symbol_info.futures_leverage,
                )
            else:
                order_base = self.kucoin_futures_api.place_futures_order(
                    side=AddOrderReq.SideEnum.SELL,
                    symbol=self.kucoin_symbol,
                    size=qty,
                    reduce_only=True,
                    order_type=OrderType.market,
                    stop_price_type=AddOrderReq.StopPriceTypeEnum.MARK_PRICE,
                    stop=AddOrderReq.StopEnum.DOWN,
                    stop_price=self.active_bot.deal.trailing_stop_loss_price,
                    leverage=self.symbol_info.futures_leverage,
                )

            order_base.deal_type = DealType.trailing_profit
            order_data = OrderModel(**order_base.model_dump())

        self.remove_stale_orders()
        self.active_bot.orders.append(order_data)

        if order_data.status == OrderStatus.FILLED:
            self.active_bot.add_log(
                "Completed futures take profit after failing to break trailing"
            )
        elif order_data.status == OrderStatus.NEW:
            self.active_bot.add_log(
                f"Trailing stop armed on exchange with status {order_data.status}"
            )
        else:
            self.active_bot.add_log(
                f"Trailing stop placement returned status {order_data.status}; verify exchange order state"
            )

        self.controller.save(self.active_bot)
        return self.active_bot

    def reconcile_trailing_stop_loss(self) -> None:
        """
        Re-place an armed futures trailing stop if the exchange no longer has
        a stop order. The bot-side trailing price is the intended exit once
        trailing has armed.
        """
        intended_price = self.active_bot.deal.trailing_stop_loss_price
        if intended_price <= 0:
            return

        _, last_replace_ts_ms, trailing_order_id = self._bot_known_trailing_stop_loss()
        exchange_ok, exchange_price = self._exchange_stop_loss_price(
            order_id=trailing_order_id
        )
        if not exchange_ok:
            return

        if exchange_price is None and self.trailing_stop_replace_on_cooldown(
            last_replace_ts_ms
        ):
            return

        if exchange_price is not None and not self.should_replace_stop_loss_order(
            current_stop_price=exchange_price,
            new_stop_price=intended_price,
            last_replace_ts_ms=last_replace_ts_ms,
            cooldown_ms=self.TRAILING_STOP_REPLACE_COOLDOWN_MS,
        ):
            return

        reason = (
            "missing"
            if exchange_price is None
            else f"at {exchange_price}, expected {intended_price}"
        )
        self.active_bot.add_log(
            f"Exchange trailing SL {reason} — re-placing trailing stop."
        )
        self.place_trailing_stop_loss()

    # Strategies whose reversal chain has historically compounded losses on chop;
    # for these, a second SL on the same pair within the cooldown closes instead of flipping.
    _NO_REVERSAL_AFTER_LOSS_NAMES = {
        "coinrule_buy_the_dip",
        "coinrule_price_tracker",
        "bb_extreme_reversion",
    }

    def close_position_for_reversal(
        self,
        reference_price: float | None = None,
    ) -> tuple[OrderModel, float] | None:
        current_position = self.kucoin_futures_api.get_futures_position(
            self.kucoin_symbol
        )
        if not current_position or abs(current_position.current_qty) == 0:
            self.active_bot.add_log("No open futures position to reverse; aborting.")
            self.active_bot.status = Status.error
            self.controller.save(self.active_bot)
            return None

        current_contracts = abs(float(current_position.current_qty))
        try:
            if self.active_bot.position == Position.long:
                close_order = self.kucoin_futures_api.sell(
                    symbol=self.kucoin_symbol,
                    qty=current_contracts,
                    reduce_only=True,
                    leverage=self.symbol_info.futures_leverage,
                    reference_price=reference_price,
                )
            else:
                close_order = self.kucoin_futures_api.buy(
                    symbol=self.kucoin_symbol,
                    qty=current_contracts,
                    reduce_only=True,
                    reference_price=reference_price,
                )
        except RestError as kucoin_error:
            message = kucoin_error.response.message
            self.active_bot.add_log(
                f"Reduce-only close failed during reversal: {message}"
            )
            self.active_bot.status = Status.error
            self.controller.save(self.active_bot)
            return None

        return (
            OrderModel(
                timestamp=int(time() * 1000),
                order_id=str(close_order.order_id),
                deal_type=DealType.margin_short,
                pair=self.kucoin_symbol,
                order_side=close_order.order_side,
                order_type=close_order.order_type,
                price=close_order.price,
                qty=close_order.qty,
                time_in_force=close_order.time_in_force,
                status=close_order.status,
            ),
            current_contracts,
        )

    def close_all(self, algorithmic_close: bool = False) -> BotModel:
        """
        Closes all open positions and cancels all orders.
        To be used also for panic selling from terminal.
        """
        deal_type = (
            DealType.algorithmic_close if algorithmic_close else DealType.panic_close
        )
        position = self.kucoin_futures_api.get_futures_position(self.kucoin_symbol)

        if position and float(position.current_qty) != 0:
            if self.active_bot.position == Position.short:
                order_response = self.kucoin_futures_api.buy(
                    symbol=self.kucoin_symbol,
                    qty=abs(int(position.current_qty)),
                    reduce_only=True,
                )
            else:
                order_response = self.kucoin_futures_api.sell(
                    symbol=self.kucoin_symbol,
                    qty=abs(int(position.current_qty)),
                    reduce_only=True,
                    leverage=self.symbol_info.futures_leverage,
                )

            order_model = OrderModel(**order_response.model_dump())
            order_model.deal_type = deal_type
            self.active_bot.orders.append(order_model)
            self.active_bot.deal.closing_price = order_response.price
            self.active_bot.deal.closing_qty = abs(int(position.current_qty))
            self.active_bot.status = Status.completed
            self.controller.update_logs(
                bot=self.active_bot,
                log_message="Futures position panic-closed successfully",
            )

        else:
            self.active_bot = self.backfill_position_from_fills()

        self.controller.save(self.active_bot)
        return self.active_bot

    def open_deal(self) -> BotModel:
        base_order = next(
            (
                bo_deal
                for bo_deal in self.active_bot.orders
                if bo_deal.deal_type == DealType.base_order
            ),
            None,
        )

        if not base_order:
            self.active_bot.add_log(
                f"Opening new future deal for {self.kucoin_symbol}..."
            )
            self.controller.save(self.active_bot)
            self.base_order()

        # Entry not filled yet (opening_price == 0): leave the bot pending and
        # return. order_updates() will promote it to active once KuCoin confirms
        # the fill by calling open_deal() again, which will reach the branch below.
        if self.active_bot.deal.opening_price == 0:
            self.active_bot.status = Status.pending
            self.active_bot.add_log(
                "Entry order is live but not yet filled; bot set to pending."
            )
            self.controller.save(self.active_bot)
            return self.active_bot

        # Entry is filled (opening_price > 0): activate / reactivate.
        # Disarm any stale trail — parameters may have changed (e.g. Update Deal).
        self.active_bot.deal.trailing_stop_loss_price = 0
        self.active_bot = self.update_parameters()
        self.active_bot.status = Status.active
        self.controller.save(self.active_bot)
        return self.active_bot
