from time import sleep, time
from uuid import uuid4

from pybinbot.models.deal import ConditionalCloseOrder
from typing import Any, Callable, NoReturn, Type

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
    OrderStatus,
    OrderType,
    Position,
    Status,
    convert_to_kucoin_symbol,
    round_numbers,
    round_numbers_ceiling,
    round_timestamp,
)

from api.databases.crud.bot_crud import BotTableCrud
from api.databases.crud.symbols_crud import SymbolsCrud
from api.databases.tables.bot_table import BotTable
from api.databases.tables.signals_table import SignalsTable
from api.databases.utils import get_db_session
from api.exchange_apis.kucoin.deals.base import KucoinBaseBalance
from api.exchange_apis.kucoin.futures.balance import KucoinFuturesBalance
from api.exchange_apis.kucoin.futures.liquidity import (
    ceil_price_to_tick,
    floor_price_to_tick,
    load_futures_order_book,
)
from api.tools.constants import (
    TOP_GAINER_EARLY_MOMENTUM_ALGO,
    TOP_GAINER_EARLY_MOMENTUM_PENDING_ENTRY_CANDLES,
    TOP_GAINER_FAILURE_REVERSAL_ALGO,
    TOP_GAINER_FAILURE_REVERSAL_PENDING_ENTRY_TTL_MS,
)


class EntryLiquidityError(BinbotErrors):
    """A persisted rejection or retry deferral from the pre-entry liquidity gate."""


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
    ENTRY_TREND_WINDOW = 50
    ENTRY_ATR_MULTIPLIER = 0.5
    ENTRY_MIN_ALLOWANCE_PCT = 0.5
    ENTRY_MAX_ALLOWANCE_PCT = 1.5
    ENTRY_FALLBACK_ALLOWANCE_PCT = 0.75
    # Top-gainer retests adapt to both realized volatility and the live book.
    # A quarter ATR centers the old 0.5% heuristic at 2% ATR; two spreads and
    # two ticks keep the distance meaningful for each contract. The 1% cap is
    # half of this strategy's current 2% stop and prevents unfillable deep bids.
    TOP_GAINER_RETEST_ATR_MULTIPLIER = 0.25
    TOP_GAINER_RETEST_FALLBACK_DISCOUNT_PCT = 0.5
    TOP_GAINER_RETEST_MIN_DISCOUNT_PCT = 0.1
    TOP_GAINER_RETEST_MAX_DISCOUNT_PCT = 1.0
    TOP_GAINER_RETEST_SPREAD_MULTIPLIER = 2.0
    TOP_GAINER_RETEST_MIN_TICKS = 2
    TOP_GAINER_PULLBACK_GRACE_PCT = 0.20
    TOP_GAINER_PULLBACK_MAX_DISPLACEMENT_PCT = 1.0
    TOP_GAINER_ENTRY_MIN_MICRO_REGIME_STRENGTH = 0.52
    TOP_GAINER_ENTRY_MAX_UPPER_WICK_FRACTION = 0.30
    ENTRY_BOOK_MAX_ATTEMPTS = 3
    ENTRY_BOOK_RETRY_SECONDS = 1.0
    # Thin books can go many seconds between quote updates without being
    # genuinely stale (KuCoin's ts reflects the last book change, not "now"),
    # confirmed against live low-cap futures books (~15s observed on a quiet
    # book). 20s comfortably clears that while still catching a hung fetch.
    ENTRY_BOOK_MAX_DATA_AGE_MS = 20_000
    ENTRY_DISPLACEMENT_RETRY_MARKER = "Entry displacement retry 1/1:"
    # How long to wait after the first (limit) close leg before checking its
    # fill status — mirrors pybinbot's _EXIT_ESCALATION_SLEEP_S for the same
    # reason: KuCoin's order/position endpoints can lag fill processing.
    CLOSE_ALL_FILL_CHECK_SLEEP_S = 2.0

    def __init__(
        self,
        bot: BotModel,
        db_table: Type[BotTable] = BotTable,
        kucoin_futures_api: KucoinFutures | None = None,
        controller: BotTableCrud | None = None,
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
        else:
            self.controller = BotTableCrud()

        self.symbols_crud = symbols_crud or SymbolsCrud()
        self.interval_ms = (
            interval_ms or BinanceKlineIntervals(bot.candlestick_interval).get_ms()
        )
        self.symbol_info = self.symbols_crud.get_symbol(bot.pair)
        self.kucoin_futures_api.DEFAULT_LEVERAGE = self.active_bot.futures_leverage
        self.kucoin_symbol = convert_to_kucoin_symbol(bot)
        self.kucoin_symbol_data = self.kucoin_futures_api.get_symbol_info(
            self.kucoin_symbol
        )
        self.price_precision = self.symbol_info.price_precision
        # Set by body_capped_entry_limit_price(); reused by
        # prepare_entry_limit_price() keeps the submitted limit inside the
        # same candle-reference band without a second klines fetch.
        self._entry_reference_price: float | None = None
        self._entry_allowance_pct: float | None = None
        self._top_gainer_volatility_discount_pct: float | None = None
        self._entry_completed_candles: list = []
        self._entry_current_candle: list | None = None
        self._entry_signal_loaded = False
        self._entry_signal_context: dict[str, Any] | None = None
        self._entry_signal_indicators: dict[str, Any] | None = None
        self._entry_post_only = False

    def _direction_multiplier(self) -> int:
        return -1 if self.active_bot.position == Position.short else 1

    def matching_exchange_fill_timestamp(
        self,
        order: OrderModel,
        fallback_timestamp: int | None = None,
        *,
        last_fill: bool = False,
    ) -> int:
        """Return the first exchange fill time for an order, in milliseconds."""
        resolved_fallback = fallback_timestamp or order.timestamp
        try:
            fills = self.kucoin_futures_api.get_fills(order_id=str(order.order_id))
        except Exception as exc:
            self.active_bot.add_log(
                f"Unable to load fill timestamp for order {order.order_id}: {exc}. "
                "Using the exchange update timestamp."
            )
            return resolved_fallback

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
            return max(trade_timestamps) if last_fill else min(trade_timestamps)

        created_timestamps = [
            int(fill.created_at)
            for fill in matching_fills
            if fill.created_at is not None
        ]
        if created_timestamps:
            return max(created_timestamps) if last_fill else min(created_timestamps)

        self.active_bot.add_log(
            f"No matching exchange fill timestamp found for order {order.order_id}. "
            "Using the exchange update timestamp."
        )
        return resolved_fallback

    def _is_recovery_bot(self) -> bool:
        recovery_params = self.active_bot.recovery_params
        return (
            recovery_params is not None and recovery_params.reversal_path == "recovery"
        )

    def recovery_source_enabled(self) -> bool:
        params = self.active_bot.recovery_params
        return (
            params is not None
            and params.reversal_path == "source"
            and not self.active_bot.dynamic_position_sizing
        )

    def awaiting_close_confirmation(self) -> bool:
        """A complete native fill can precede the exchange position snapshot."""
        return self.active_bot.deal.closing_qty == 0 and any(
            order.deal_type
            in {DealType.stop_loss, DealType.trailing_profit, DealType.take_profit}
            and order.status == OrderStatus.FILLED
            and order.requested_qty > 0
            and order.qty >= order.requested_qty
            for order in self.active_bot.orders
        )

    def _cleanup_native_protection_after_close(self) -> None:
        """Remove exchange-native protection after a confirmed bot-side close."""

        try:
            self.cancel_current_sl()
        except Exception as exc:
            # The position is already confirmed closed. A stale reduce-only
            # stop cannot reopen it, so cleanup failure is safe to retry later.
            self.active_bot.add_log(
                "Could not clean up exchange-native protection after the "
                f"confirmed bot-side close ({exc})."
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

    @staticmethod
    def _ema(values: list[float], span: int) -> float:
        multiplier = 2 / (span + 1)
        ema = values[0]
        for value in values[1:]:
            ema = value * multiplier + ema * (1 - multiplier)
        return ema

    def _top_gainer_signal_data(
        self,
    ) -> tuple[dict[str, Any], dict[str, Any]] | None:
        if self._entry_signal_loaded:
            context = self._entry_signal_context
            indicators = self._entry_signal_indicators
            if context is None or indicators is None:
                return None
            return context, indicators

        self._entry_signal_loaded = True
        self._entry_signal_context = None
        self._entry_signal_indicators = None
        if self.active_bot.signal_id is None:
            return None

        try:
            with get_db_session() as session:
                signal = session.get(SignalsTable, self.active_bot.signal_id)
                if signal is None:
                    return None
                self._entry_signal_context = signal.context
                self._entry_signal_indicators = signal.indicators
        except Exception as exc:
            self.active_bot.add_log(
                f"Top-gainer signal metadata unavailable for entry validation ({exc})."
            )
            return None

        return self._entry_signal_context, self._entry_signal_indicators

    def _is_sustained_top_gainer_signal(self) -> bool:
        if (
            self.active_bot.name != TOP_GAINER_EARLY_MOMENTUM_ALGO
            or self.active_bot.position != Position.long
        ):
            return False
        signal_data = self._top_gainer_signal_data()
        if signal_data is None:
            return False
        _, indicators = signal_data
        return indicators.get("route_reason") == "sustained_top_gainer_long"

    def _top_gainer_shallow_pullback_validation(
        self,
        execution_price: float,
    ) -> tuple[bool, str, float]:
        reference_price = self._entry_reference_price
        allowance_pct = self._entry_allowance_pct
        if (
            self.active_bot.name != TOP_GAINER_EARLY_MOMENTUM_ALGO
            or self.active_bot.position != Position.long
            or reference_price is None
            or allowance_pct is None
            or execution_price >= reference_price
        ):
            return False, "not a top-gainer downward pullback", 0

        displacement_pct = (reference_price - execution_price) / reference_price * 100
        soft_limit_pct = min(
            allowance_pct + self.TOP_GAINER_PULLBACK_GRACE_PCT,
            self.TOP_GAINER_PULLBACK_MAX_DISPLACEMENT_PCT,
        )
        if (
            displacement_pct <= allowance_pct + 1e-9
            or displacement_pct > soft_limit_pct + 1e-9
        ):
            return False, "outside the shallow-pullback grace band", soft_limit_pct

        signal_data = self._top_gainer_signal_data()
        if signal_data is None:
            return False, "the originating signal is unavailable", soft_limit_pct
        signal_context, _ = signal_data
        symbol_features = (signal_context.get("symbol_features") or {}).get(
            self.active_bot.pair
        )
        if not isinstance(symbol_features, dict):
            return (
                False,
                "the signal has no symbol micro-regime context",
                soft_limit_pct,
            )

        try:
            micro_regime = symbol_features.get("micro_regime")
            micro_regime_strength = float(
                symbol_features.get("micro_regime_strength") or 0
            )
            micro_regime_transition = symbol_features.get("micro_regime_transition")
            completed_candles = self._entry_completed_candles
            current_candle = self._entry_current_candle
            if (
                current_candle is None
                or len(completed_candles) < self.ENTRY_TREND_WINDOW
            ):
                return False, "live candle history is incomplete", soft_limit_pct

            closes = [
                float(candle[4])
                for candle in completed_candles[-self.ENTRY_TREND_WINDOW :]
            ]
            current_open = float(current_candle[1])
            current_high = float(current_candle[2])
            current_low = float(current_candle[3])
            current_close = float(current_candle[4])
            closes.append(current_close)
        except (TypeError, ValueError):
            return False, "live pullback validation inputs are invalid", soft_limit_pct

        if (
            micro_regime != "TREND_UP"
            or micro_regime_strength < self.TOP_GAINER_ENTRY_MIN_MICRO_REGIME_STRENGTH
        ):
            return (
                False,
                "signal micro-regime is not a strong TREND_UP",
                soft_limit_pct,
            )
        if micro_regime_transition in {
            "BREAKDOWN",
            "ENTERED_TREND_DOWN",
            "VOLATILITY_EXPANSION",
        }:
            return (
                False,
                f"signal transition {micro_regime_transition} is not long-safe",
                soft_limit_pct,
            )

        ema20 = self._ema(closes, 20)
        ema50 = self._ema(closes, 50)
        if not current_close > ema20 > ema50:
            return (
                False,
                "live price structure no longer confirms TREND_UP",
                soft_limit_pct,
            )
        if current_close < current_open:
            return False, "the live candle has reversed below its open", soft_limit_pct

        candle_range = current_high - current_low
        if candle_range <= 0:
            return False, "the live candle range is invalid", soft_limit_pct
        upper_wick_fraction = (
            current_high - max(current_open, current_close)
        ) / candle_range
        if upper_wick_fraction > self.TOP_GAINER_ENTRY_MAX_UPPER_WICK_FRACTION:
            return False, "the live upper wick indicates rejection", soft_limit_pct

        return True, "live TREND_UP pullback remains valid", soft_limit_pct

    def _entry_price_is_within_displacement_band(
        self,
        execution_price: float,
        lower_reference_bound: float,
        upper_reference_bound: float,
    ) -> bool:
        if lower_reference_bound <= execution_price <= upper_reference_bound:
            return True

        is_valid, validation_reason, soft_limit_pct = (
            self._top_gainer_shallow_pullback_validation(execution_price)
        )
        if not is_valid:
            return False

        reference_price = self._entry_reference_price
        allowance_pct = self._entry_allowance_pct
        if reference_price is None or allowance_pct is None:
            return False
        displacement_pct = (reference_price - execution_price) / reference_price * 100
        self.active_bot.add_log(
            "Top-gainer shallow pullback accepted: "
            f"price={execution_price:.8g}, displacement={displacement_pct:.2f}%, "
            f"standard_limit={allowance_pct:.2f}%, "
            f"soft_limit={soft_limit_pct:.2f}%; {validation_reason}."
        )
        return True

    def body_capped_entry_limit_price(self) -> float:
        interval = BinanceKlineIntervals(
            self.active_bot.candlestick_interval
        ).to_kucoin_interval()
        try:
            klines = self.kucoin_futures_api.get_ui_klines(
                symbol=self.kucoin_symbol,
                interval=interval,
                limit=max(self.ENTRY_ATR_WINDOW + 3, self.ENTRY_TREND_WINDOW + 1),
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

        self._entry_completed_candles = completed_candles
        self._entry_current_candle = current_candle

        previous_close = float(completed_candles[-1][4])
        current_open = float(current_candle[1])
        current_close = float(current_candle[4])
        if previous_close <= 0 or current_open <= 0 or current_close <= 0:
            self.active_bot.add_log(
                "Entry rejected: candle open, current close, or previous close is invalid."
            )
            raise BinbotErrors(
                "Reliable candle open, current close, and previous close are unavailable "
                "for futures entry."
            )

        if self.active_bot.name == TOP_GAINER_EARLY_MOMENTUM_ALGO:
            self._entry_reference_price = previous_close
            atr = self.closed_candle_atr(completed_candles)
            if atr is None:
                volatility_discount_pct = self.TOP_GAINER_RETEST_FALLBACK_DISCOUNT_PCT
                discount_source = "fallback"
            else:
                volatility_discount_pct = (
                    self.TOP_GAINER_RETEST_ATR_MULTIPLIER * atr / previous_close * 100
                )
                discount_source = "ATR"

            volatility_discount_pct = max(
                self.TOP_GAINER_RETEST_MIN_DISCOUNT_PCT,
                min(
                    volatility_discount_pct,
                    self.TOP_GAINER_RETEST_MAX_DISCOUNT_PCT,
                ),
            )
            self._top_gainer_volatility_discount_pct = volatility_discount_pct
            self._entry_allowance_pct = volatility_discount_pct
            try:
                raw_tick_size = self.kucoin_symbol_data.tick_size
                if raw_tick_size is None:
                    raise ValueError("tick size is missing")
                tick_size = float(raw_tick_size)
                entry_limit_price = floor_price_to_tick(
                    previous_close * (1 - volatility_discount_pct / 100),
                    tick_size,
                )
            except (TypeError, ValueError) as exc:
                self.active_bot.add_log(
                    f"Entry rejected: invalid KuCoin futures tick size ({exc})."
                )
                raise BinbotErrors(
                    "Reliable tick-size data is unavailable for futures entry."
                ) from exc

            actual_discount_pct = (
                (previous_close - entry_limit_price) / previous_close * 100
            )
            self._entry_allowance_pct = actual_discount_pct
            self.active_bot.add_log(
                "Top-gainer momentum retest entry (provisional): "
                f"confirmation_close={previous_close}, "
                f"volatility_discount={volatility_discount_pct:.2f}% "
                f"({discount_source}), tick_size={tick_size}, "
                f"limit={entry_limit_price}."
            )
            return entry_limit_price

        is_failure_reversal = self.active_bot.name == TOP_GAINER_FAILURE_REVERSAL_ALGO
        if is_failure_reversal:
            anchor_price = current_close
        elif self.active_bot.position == Position.short:
            anchor_price = min(current_open, previous_close)
        else:
            anchor_price = max(current_open, previous_close)

        self._entry_reference_price = anchor_price
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

        self._entry_allowance_pct = allowance_pct
        if is_failure_reversal:
            entry_limit_price = round_numbers(anchor_price, self.price_precision)
        else:
            direction = self._direction_multiplier()
            entry_limit_price = round_numbers(
                anchor_price * (1 + direction * allowance_pct / 100),
                self.price_precision,
            )
        entry_label = (
            "Top-gainer failure-reversal prompt entry"
            if is_failure_reversal
            else (
                "Recovery body-capped entry"
                if self.active_bot.recovery_params is not None
                else "Body-capped entry"
            )
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
        risk-at-stop. ``notional = balance * active_bot.futures_leverage`` and
        ``contracts = notional / (price * multiplier)``. Leverage is saved on
        each bot and bounded to 1x–5x.
        """
        if balance <= 0 or price <= 0:
            return 0

        symbol_data = self.kucoin_symbol_data
        multiplier = (
            symbol_data.multiplier or self.kucoin_futures_api.DEFAULT_MULTIPLIER or 1
        )

        contracts = balance * self.active_bot.futures_leverage / (price * multiplier)
        return int(round_numbers(contracts, self.symbol_info.qty_precision))

    def contracts_to_fiat_order_size(self, contracts: float, price: float) -> float:
        """Convert contracts back to their initial-margin equivalent."""
        if contracts <= 0 or price <= 0:
            return 0.0

        multiplier = float(
            self.kucoin_symbol_data.multiplier
            or self.kucoin_futures_api.DEFAULT_MULTIPLIER
        )

        return round_numbers(
            contracts * price * multiplier / self.active_bot.futures_leverage,
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
        initial_margin = notional / self.active_bot.futures_leverage
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

    def prepare_entry_limit_price(self, candidate_limit_price: float) -> float:
        """Prepare a bounded limit price; the entry lifecycle owns fill decisions."""
        self._entry_post_only = False
        for attempt in range(self.ENTRY_BOOK_MAX_ATTEMPTS):
            try:
                order_book = load_futures_order_book(
                    self.kucoin_futures_api, self.kucoin_symbol
                )
                if order_book.data_age_ms > self.ENTRY_BOOK_MAX_DATA_AGE_MS:
                    raise ValueError(
                        f"order book is stale ({order_book.data_age_ms}ms)"
                    )
                break
            except Exception as error:
                if attempt + 1 == self.ENTRY_BOOK_MAX_ATTEMPTS:
                    self.reject_entry_for_liquidity(
                        f"Entry rejected: unable to load a reliable KuCoin futures order book after {self.ENTRY_BOOK_MAX_ATTEMPTS} attempts ({error}).",
                        cause=error,
                    )
                self.active_bot.add_log(
                    f"Entry order-book retry {attempt + 1}/{self.ENTRY_BOOK_MAX_ATTEMPTS - 1}: {error}"
                )
                sleep(self.ENTRY_BOOK_RETRY_SECONDS)

        best_bid = order_book.bids[0].price
        best_ask = order_book.asks[0].price
        midpoint = (best_bid + best_ask) / 2
        spread_bps = (best_ask - best_bid) / midpoint * 10000
        if self.active_bot.name == TOP_GAINER_EARLY_MOMENTUM_ALGO:
            volatility_discount_pct = self._top_gainer_volatility_discount_pct
            if volatility_discount_pct is None or self._entry_reference_price is None:
                self.reject_entry_for_liquidity(
                    "Entry rejected: top-gainer volatility discount is unavailable."
                )

            try:
                raw_tick_size = self.kucoin_symbol_data.tick_size
                if raw_tick_size is None:
                    raise ValueError("tick size is missing")
                tick_size = float(raw_tick_size)
                tick_distance_pct = (
                    tick_size
                    * self.TOP_GAINER_RETEST_MIN_TICKS
                    / self._entry_reference_price
                    * 100
                )
                spread_distance_pct = (
                    spread_bps * self.TOP_GAINER_RETEST_SPREAD_MULTIPLIER / 100
                )
                discount_pct = min(
                    max(
                        volatility_discount_pct,
                        tick_distance_pct,
                        spread_distance_pct,
                        self.TOP_GAINER_RETEST_MIN_DISCOUNT_PCT,
                    ),
                    self.TOP_GAINER_RETEST_MAX_DISCOUNT_PCT,
                )
                maximum_discount_price = self._entry_reference_price * (
                    1 - self.TOP_GAINER_RETEST_MAX_DISCOUNT_PCT / 100
                )
                candidate_limit_price = floor_price_to_tick(
                    self._entry_reference_price * (1 - discount_pct / 100),
                    tick_size,
                )
                if candidate_limit_price < maximum_discount_price:
                    candidate_limit_price = ceil_price_to_tick(
                        maximum_discount_price,
                        tick_size,
                    )
            except (TypeError, ValueError) as exc:
                self.reject_entry_for_liquidity(
                    f"Entry rejected: invalid top-gainer microstructure data ({exc}).",
                    cause=exc,
                )

            actual_discount_pct = (
                (self._entry_reference_price - candidate_limit_price)
                / self._entry_reference_price
                * 100
            )
            minimum_tick_retest_price = (
                self._entry_reference_price
                - tick_size * self.TOP_GAINER_RETEST_MIN_TICKS
            )
            if candidate_limit_price > minimum_tick_retest_price + tick_size * 1e-9:
                self.reject_entry_for_liquidity(
                    "Entry rejected: exact tick-size quantization cannot place the "
                    f"top-gainer retest at least {self.TOP_GAINER_RETEST_MIN_TICKS} "
                    "ticks below its reference without exceeding the "
                    f"{self.TOP_GAINER_RETEST_MAX_DISCOUNT_PCT:.2f}% cap."
                )
            if actual_discount_pct > self.TOP_GAINER_RETEST_MAX_DISCOUNT_PCT + 1e-9:
                self.reject_entry_for_liquidity(
                    "Entry rejected: exact tick-size quantization would move the "
                    f"top-gainer retest {actual_discount_pct:.2f}% below its "
                    f"reference, beyond the {self.TOP_GAINER_RETEST_MAX_DISCOUNT_PCT:.2f}% cap."
                )

            self._entry_allowance_pct = actual_discount_pct
            self.active_bot.add_log(
                "Top-gainer momentum microstructure-aware retest entry: "
                f"confirmation_close={self._entry_reference_price}, "
                f"ATR_component={volatility_discount_pct:.2f}%, "
                f"spread_component={spread_distance_pct:.2f}%, "
                f"tick_component={tick_distance_pct:.2f}%, "
                f"discount={actual_discount_pct:.2f}%, tick_size={tick_size}, "
                f"limit={candidate_limit_price}."
            )

        if self._entry_reference_price is None or self._entry_allowance_pct is None:
            self.reject_entry_for_liquidity(
                "Entry rejected: candle-reference displacement band is unavailable."
            )
        lower_reference_bound = float(
            round_numbers(
                self._entry_reference_price * (1 - self._entry_allowance_pct / 100),
                self.price_precision,
            )
        )
        upper_reference_bound = float(
            round_numbers_ceiling(
                self._entry_reference_price * (1 + self._entry_allowance_pct / 100),
                self.price_precision,
            )
        )

        if self.active_bot.name == TOP_GAINER_FAILURE_REVERSAL_ALGO:
            if self.active_bot.position != Position.short:
                self.reject_entry_for_liquidity(
                    "Entry rejected: top-gainer failure reversal must open short."
                )
            candidate_limit_price = min(
                upper_reference_bound, max(lower_reference_bound, best_bid)
            )
        elif self._is_sustained_top_gainer_signal():
            sustained_best_bid = floor_price_to_tick(best_bid, tick_size)
            if (
                sustained_best_bid > candidate_limit_price
                and lower_reference_bound <= sustained_best_bid <= upper_reference_bound
            ):
                candidate_limit_price = sustained_best_bid
                self._entry_post_only = True
                self.active_bot.add_log(
                    f"Sustained top-gainer maker entry joined the current best bid: best_bid={sustained_best_bid}, permitted_band={lower_reference_bound}-{upper_reference_bound}."
                )

        try:
            tick_size = float(self.kucoin_symbol_data.tick_size)
            candidate_limit_price = (
                ceil_price_to_tick(candidate_limit_price, tick_size)
                if self.active_bot.position == Position.short
                else floor_price_to_tick(candidate_limit_price, tick_size)
            )
        except (TypeError, ValueError) as error:
            self.reject_entry_for_liquidity(
                f"Entry rejected: invalid futures limit price or tick size ({error}).",
                cause=error,
            )

        if not self._entry_price_is_within_displacement_band(
            candidate_limit_price, lower_reference_bound, upper_reference_bound
        ):
            self.reject_entry_for_displacement(
                f"Entry rejected: KuCoin futures limit price {candidate_limit_price:.8g} is outside the candle-reference band {lower_reference_bound:.8g}-{upper_reference_bound:.8g}."
            )
        self.active_bot.add_log(
            f"Futures entry limit prepared at {candidate_limit_price:.8g}; best bid/ask={best_bid:.8g}/{best_ask:.8g}. Fill confirmation is deferred to lifecycle order updates."
        )
        return candidate_limit_price

    def reject_entry_for_liquidity(
        self,
        message: str,
        *,
        cause: Exception | None = None,
    ) -> NoReturn:
        self.active_bot.status = Status.error
        self.active_bot.add_log(message)
        self.controller.save(self.active_bot)
        if cause is not None:
            raise EntryLiquidityError(message) from cause
        raise EntryLiquidityError(message)

    def reject_entry_for_displacement(self, message: str) -> NoReturn:
        already_retried = any(
            self.ENTRY_DISPLACEMENT_RETRY_MARKER in str(log)
            for log in self.active_bot.logs
        )
        if already_retried:
            self.reject_entry_for_liquidity(message)

        detail = message.removeprefix("Entry rejected: ")
        self.active_bot.status = Status.pending
        self.active_bot.add_log(
            f"{self.ENTRY_DISPLACEMENT_RETRY_MARKER} {detail} "
            "Bot remains pending and will retry on the next tick."
        )
        self.controller.save(self.active_bot)
        raise EntryLiquidityError(message)

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
            self.active_bot.deal.current_position_qty = 0
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

    def cancel_current_sl(self, *, deal_type: DealType | None = None) -> None:
        """Cancel only this bot's protection, retaining execution history."""
        # A replacement target can have been tightened in memory. Persist it
        # before cancelling protection so a delayed lookup cannot roll it back.
        self.controller.save(self.active_bot)
        intent = self.active_bot.deal.conditional_close_order
        if intent is not None and intent.order_id is None:
            details = self.kucoin_futures_api.retrieve_order_by_client_oid(
                intent.client_oid
            )
            intent.order_id = str(details.id)
        owned: dict[str, OrderModel | None] = {
            str(order.order_id): order
            for order in self.active_bot.orders
            if order.deal_type in {DealType.stop_loss, DealType.trailing_profit}
            and (deal_type is None or order.deal_type == deal_type)
            and order.status not in self.TERMINAL_STOP_ORDER_STATUSES
        }
        if intent is not None and intent.order_id is not None:
            recorded = next(
                (
                    row
                    for row in self.active_bot.orders
                    if str(row.order_id) == intent.order_id
                ),
                None,
            )
            if (
                recorded is None
                or recorded.status not in self.TERMINAL_STOP_ORDER_STATUSES
            ):
                owned.setdefault(intent.order_id, recorded)
        if not owned:
            self.active_bot.deal.conditional_close_order = None
            return
        untriggered = {
            str(order.id)
            for order in self.kucoin_futures_api.get_all_stop_loss_orders(
                self.kucoin_symbol
            )
        }
        for order_id, local_order in owned.items():
            known_filled_quantity = 0.0
            if local_order is not None and (
                local_order.requested_qty > 0
                or local_order.status == OrderStatus.PARTIALLY_FILLED
            ):
                # Older NEW rows used qty for the requested stop size.
                known_filled_quantity = local_order.qty
            stop_cancellation = None
            standard_cancellation = None
            if order_id in untriggered:
                stop_cancellation = (
                    self.kucoin_futures_api.batch_cancel_stop_loss_orders([order_id])
                )
            else:
                details = self.kucoin_futures_api.retrieve_order(order_id)
                known_filled_quantity = max(
                    known_filled_quantity, float(details.filled_size or 0)
                )
                if details.is_active:
                    standard_cancellation = (
                        self.kucoin_futures_api.cancel_futures_order(order_id)
                    )
            try:
                details = self.kucoin_futures_api.retrieve_order(order_id)
            except RestError as exc:
                missing = str(exc.response.code) == "100001" and any(
                    phrase in str(exc.response.message).lower()
                    for phrase in (
                        "order not found",
                        "order not exist",
                        "order does not exist",
                        "getorder.ordernotexist",
                    )
                )
                acknowledged = (
                    stop_cancellation is not None
                    and any(
                        str(result.order_id) == order_id
                        and str(result.code) == "200000"
                        for result in stop_cancellation.data or []
                    )
                ) or (
                    standard_cancellation is not None
                    and order_id in (standard_cancellation.cancelled_order_ids or [])
                )
                if not missing or not acknowledged:
                    raise
                # The detail endpoint can temporarily lose an untriggered stop
                # after cancellation. An acknowledgement alone is insufficient:
                # verify removal and check history for a fill racing the cancel.
                if any(
                    str(order.id) == order_id
                    for order in self.kucoin_futures_api.get_all_stop_loss_orders(
                        self.kucoin_symbol
                    )
                ):
                    raise BinbotErrors(
                        "Conditional close cancellation is not confirmed; deferring replacement/exit"
                    ) from exc
                filled_quantity, _, _ = self.kucoin_futures_api.get_order_execution(
                    order_id
                )
            else:
                if details.is_active:
                    raise BinbotErrors(
                        "Conditional close cancellation is not confirmed; deferring replacement/exit"
                    )
                filled_quantity = float(details.filled_size or 0)
            if max(known_filled_quantity, filled_quantity) > 0:
                raise BinbotErrors(
                    "Conditional close filled during cancellation; reconcile its fills before another exit"
                )
            if local_order is not None:
                local_order.status = OrderStatus.CANCELED
                local_order.qty = 0
                local_order.price = 0
        self.active_bot.deal.conditional_close_order = None
        self.controller.save(self.active_bot)

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
            order_price = order.stop_price if order.stop_price > 0 else order.price
            ts = order.timestamp
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

    def _exchange_stop_loss_details(
        self, order_id: str | None = None
    ) -> tuple[bool, float | None, float | None]:
        """
        Source of truth from the exchange.

        Returns ``(ok, price, qty)``:
          - ``ok=True, price=float``  → exchange has an SL at this price
          - ``ok=True, price=None``   → exchange confirmed no SL exists
            for the requested order id, or no stop exists when no id is passed
          - ``ok=False, price=None``  → query failed; caller must NOT treat
            this as "no SL", or it will cancel/replace a still-valid one.
        Quantity is ``None`` when KuCoin omits it.
        """
        try:
            stop_orders = self.kucoin_futures_api.get_all_stop_loss_orders(
                self.kucoin_symbol
            )
        except Exception as exc:
            self.active_bot.add_log(f"Could not query exchange stop orders: {exc}")
            return False, None, None

        if not stop_orders:
            return True, None, None

        matching_orders: list[Any] = stop_orders
        if order_id is not None:
            matching_orders = [
                order for order in stop_orders if str(order.id or "") == order_id
            ]

        if not matching_orders:
            return True, None, None

        for order in matching_orders:
            stop_price = float(order.stop_price or 0)
            if stop_price > 0:
                raw_qty = order.size
                qty = abs(float(raw_qty)) if raw_qty is not None else None
                return True, stop_price, qty
        return True, None, None

    def _exchange_stop_loss_price(
        self, order_id: str | None = None
    ) -> tuple[bool, float | None]:
        exchange_ok, exchange_price, _ = self._exchange_stop_loss_details(order_id)
        return exchange_ok, exchange_price

    def should_replace_stop_loss_order(
        self,
        current_stop_price: float | None,
        new_stop_price: float,
        last_replace_ts_ms: int | None = None,
        cooldown_ms: int | None = None,
        allow_widening: bool = False,
    ) -> bool:
        """
        Decide whether the on-exchange SL needs replacing.

        Replace only when:
          - we have a meaningful new price, and
          - either there's no current SL, the new one is *better*, or the
            caller has explicitly allowed favorable-trend widening, and
          - the move exceeds the min-move threshold, and
          - the cooldown since the last replace has elapsed.
        """
        if new_stop_price <= 0:
            return False

        if current_stop_price is None or current_stop_price <= 0:
            return True

        direction = self._direction_multiplier()
        directional_move = (new_stop_price - current_stop_price) * direction
        if directional_move == 0 or (directional_move < 0 and not allow_widening):
            return False

        tick_size = 10 ** (-self.price_precision)
        min_replace_move = max(
            abs(current_stop_price) * self.STOP_LOSS_REPLACE_MIN_MOVE_RATIO,
            tick_size * self.STOP_LOSS_REPLACE_MIN_TICKS,
        )
        if abs(directional_move) < min_replace_move:
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

    def reconcile_exchange_sl(
        self, *, allow_widening: bool = False, position_qty: float | None = None
    ) -> None:
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
          4. A favorable-trend strategy explicitly permits widening — use
             the same material-move and cooldown protection before replacing.

        Skipped when:
          - trailing has armed (trailing_stop_loss_price != 0); in that mode
            the broad emergency stop has been replaced by the exchange-native
            trailing stop and its dedicated reconciler owns further updates.
        """
        intent = self.active_bot.deal.conditional_close_order
        if intent is not None and intent.order_id is None:
            self.place_conditional_close(
                intent.stop_price, intent.requested_qty, intent.deal_type
            )
            return

        if self.active_bot.stop_loss <= 0:
            return
        if self.awaiting_close_confirmation():
            return
        if self.active_bot.deal.trailing_stop_loss_price != 0:
            self.reconcile_trailing_stop_loss(position_qty=position_qty)
            return

        if (
            self.active_bot.deal.closing_qty > 0
            and self.active_bot.deal.current_position_qty == 0
        ):
            return
        if any(
            order.deal_type == DealType.stop_loss
            and order.qty > 0
            and order.client_oid is not None
            and order.status not in self.TERMINAL_STOP_ORDER_STATUSES
            for order in self.active_bot.orders
        ):
            return
        # Intended price
        if self.active_bot.deal.stop_loss_price <= 0:
            return

        exchange_ok, exchange_price, exchange_qty = self._exchange_stop_loss_details()
        if not exchange_ok:
            # API blip — we don't know what's on the exchange. Bail out and
            # try again next tick rather than risk cancelling/duplicating
            # a still-valid emergency SL.
            return

        bot_known_price, last_replace_ts_ms = self._bot_known_stop_loss()
        expected_qty = (
            position_qty
            if position_qty is not None
            else self.current_position_quantity()
        )

        # Case 1: exchange confirmed no SL exists — re-place.
        if exchange_price is None:
            if bot_known_price is not None:
                self.active_bot.add_log(
                    "Exchange SL missing — re-placing emergency stop."
                )
            self.cancel_current_sl()  # cleans local stale records, no-op on empty
            self.place_stop_loss(position_qty=position_qty)
            return

        quantity_changed = (
            exchange_qty is not None and exchange_qty != expected_qty
        ) or (
            position_qty is not None
            and any(
                order.deal_type == DealType.stop_loss
                and order.status not in self.TERMINAL_STOP_ORDER_STATUSES
                and (order.requested_qty if order.requested_qty > 0 else order.qty)
                != expected_qty
                for order in self.active_bot.orders
            )
        )
        if expected_qty > 0 and quantity_changed:
            self.active_bot.add_log(
                f"Exchange SL quantity drift detected: stop={exchange_qty} "
                f"contracts, current position={expected_qty}; replacing."
            )
            self.cancel_current_sl()
            self.place_stop_loss(position_qty=expected_qty)
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
            allow_widening=allow_widening,
        ):
            if (ratcheted_target - exchange_price) * self._direction_multiplier() < 0:
                self.active_bot.add_log(
                    "Favorable-trend volatility expansion widened the exchange "
                    f"stop from {exchange_price} to {ratcheted_target}."
                )
            self.cancel_current_sl()
            self.place_stop_loss()
        else:
            # Not replacing — the exchange price is what's actually
            # protecting the position, so adopt it as truth.
            self.active_bot.deal.stop_loss_price = round_numbers(
                exchange_price, self.price_precision
            )

    def base_order(self) -> BotModel:
        """Place or adopt the bot's entry, preserving identity across restarts."""
        client_oid = self.active_bot.deal.entry_client_oid
        if client_oid is not None:
            try:
                details = self.kucoin_futures_api.retrieve_order_by_client_oid(
                    client_oid
                )
            except RestError as exc:
                if str(
                    exc.response.code
                ) == "100001" or "getOrder.orderNotExist" in str(exc.response.message):
                    self.active_bot.add_log(
                        "Entry acknowledgement unresolved; retaining clientOid without resubmitting."
                    )
                    self.active_bot.status = Status.pending
                    self.controller.save(self.active_bot)
                    return self.active_bot
                raise
            contracts = float(details.size or 0)
            entry_limit_price = float(details.price or 0)
            order = OrderBase(
                order_id=str(details.id),
                client_oid=client_oid,
                requested_qty=contracts,
                pair=self.kucoin_symbol,
                order_type="limit",
                time_in_force="GTC",
                order_side="sell"
                if self.active_bot.position == Position.short
                else "buy",
                price=float(details.avg_deal_price or 0),
                qty=float(details.filled_size or 0),
                timestamp=int(details.created_at or 0),
                status=OrderStatus.map_from_kucoin_status(details.status.value),
                deal_type=DealType.base_order,
            )
        else:
            if self.active_bot.fiat_order_size <= 0:
                raise BinbotErrors("Fiat order size must be set.")

            available_balance = self.compute_available_balance()
            candidate_limit_price = self.body_capped_entry_limit_price()
            price = candidate_limit_price

            margin_sized_contracts = self.calculate_contracts(
                self.active_bot.fiat_order_size, price
            )

            if margin_sized_contracts <= 0:
                raise BinbotErrors(
                    "Calculated contracts is 0. Check if the order size, stop loss, and risk settings are correct."
                )

            affordable_contracts = self.max_contracts_for_margin(
                available_balance, price
            )
            affordability_capped_contracts = min(
                margin_sized_contracts,
                affordable_contracts,
            )

            if affordability_capped_contracts <= 0:
                min_contract_margin = self.required_margin_for_contracts(
                    self.kucoin_symbol_data.lot_size or 1, price
                )
                raise BinbotErrors(
                    f"Required futures margin {min_contract_margin} {self.fiat} for the minimum contract size "
                    f"exceeds available balance {available_balance} {self.fiat}."
                )

            if affordability_capped_contracts < margin_sized_contracts:
                self.active_bot.add_log(
                    f"Futures order downsized from {margin_sized_contracts} to "
                    f"{affordability_capped_contracts} contracts because required "
                    "margin exceeded available balance."
                )

            contracts = affordability_capped_contracts
            entry_limit_price = self.prepare_entry_limit_price(candidate_limit_price)
            required_margin = self.required_margin_for_contracts(
                contracts, entry_limit_price
            )
            if required_margin > available_balance:
                raise BinbotErrors(
                    f"Required futures margin {required_margin} {self.fiat} for {contracts} contracts "
                    f"exceeds available balance {available_balance} {self.fiat}."
                )

            notional = round_numbers(
                self.notional_for_contracts(contracts, entry_limit_price), 8
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
                f"leverage={self.active_bot.futures_leverage}x, required_margin={required_margin} {self.fiat}, "
                f"available_balance={available_balance} {self.fiat}, planned_margin={self.active_bot.fiat_order_size} {self.fiat}."
            )

            client_oid = str(uuid4())
            self.active_bot.deal.entry_client_oid = client_oid
            self.controller.save(self.active_bot)
            order = self.kucoin_futures_api.place_futures_order(
                symbol=self.kucoin_symbol,
                side=AddOrderReq.SideEnum.SELL
                if self.active_bot.position == Position.short
                else AddOrderReq.SideEnum.BUY,
                size=contracts,
                leverage=self.active_bot.futures_leverage,
                order_type=OrderType.limit,
                price=entry_limit_price,
                time_in_force=AddOrderReq.TimeInForceEnum.GOOD_TILL_CANCELED,
                post_only=self._entry_post_only
                if self.active_bot.position == Position.long
                else False,
                reduce_only=False,
                allow_market_fallback=False,
                client_oid=client_oid,
            )

        order.deal_type = DealType.base_order
        order = OrderModel(**order.model_dump())
        self.active_bot.orders.append(order)

        # Keep acknowledgements nonterminal until streaming verifies the fills.
        order.status = OrderStatus.NEW
        order.qty = contracts
        self.active_bot.deal.base_order_size = contracts
        self.active_bot.deal.opening_timestamp = order.timestamp
        self.active_bot.status = Status.pending
        pending_entry_minutes = 5
        if self.active_bot.name == TOP_GAINER_EARLY_MOMENTUM_ALGO:
            pending_entry_minutes = (
                self.interval_ms
                * TOP_GAINER_EARLY_MOMENTUM_PENDING_ENTRY_CANDLES
                // 60_000
            )
        elif self.active_bot.name == TOP_GAINER_FAILURE_REVERSAL_ALGO:
            pending_entry_minutes = (
                TOP_GAINER_FAILURE_REVERSAL_PENDING_ENTRY_TTL_MS // 60_000
            )
        self.controller.update_logs(
            bot=self.active_bot,
            log_message=(
                f"Futures entry limit order {order.order_id} submitted at {entry_limit_price} "
                f"with {contracts} contracts. Bot is pending for up to "
                f"{pending_entry_minutes} minutes awaiting fill confirmation by lifecycle order updates."
            ),
        )

        self.controller.save(self.active_bot)
        return self.active_bot

    def current_position_quantity(self) -> float:
        """Return live contracts, falling back to the latest known quantity.

        KuCoin occasionally omits or temporarily reports no position quantity
        immediately after a market fill. In that case current_position_qty is
        safer than the historical opening quantity after partial exits or ADL.
        """
        try:
            position = self.kucoin_futures_api.get_futures_position(self.kucoin_symbol)
        except Exception as exc:
            self.active_bot.add_log(
                f"Could not refresh current position quantity from KuCoin: {exc}. "
                "Using the last confirmed quantity."
            )
        else:
            raw_position_qty = position.current_qty
            if raw_position_qty is not None:
                live_qty = round_numbers(
                    abs(float(raw_position_qty)), self.symbol_info.qty_precision
                )
                self.active_bot.deal.current_position_qty = live_qty
                if live_qty > 0:
                    self.active_bot.deal.base_order_size = live_qty
                return live_qty

        if self.active_bot.deal.current_position_qty > 0:
            return self.active_bot.deal.current_position_qty
        return self.active_bot.deal.opening_qty

    def place_conditional_close(
        self, stop_price: float, quantity: float, deal_type: DealType
    ) -> OrderModel | None:
        """Persist identity; resolve lost acknowledgements before conditional retry."""
        intent = self.active_bot.deal.conditional_close_order
        details = None
        if intent is not None:
            try:
                details = (
                    self.kucoin_futures_api.retrieve_order(intent.order_id)
                    if intent.order_id is not None
                    else self.kucoin_futures_api.retrieve_order_by_client_oid(
                        intent.client_oid
                    )
                )
            except RestError as exc:
                missing = str(exc.response.code) == "100001" and any(
                    phrase in str(exc.response.message).lower()
                    for phrase in (
                        "order not found",
                        "order not exist",
                        "order does not exist",
                        "getorder.ordernotexist",
                    )
                )
                if not missing:
                    raise
                now_ms = int(time() * 1000)
                if intent.not_found_count == 0:
                    intent.not_found_since_ms = now_ms
                intent.not_found_count += 1
                self.controller.save(self.active_bot)
                if (
                    intent.order_id is not None
                    or intent.not_found_count < 3
                    or now_ms - intent.not_found_since_ms < 60_000
                ):
                    self.active_bot.add_log(
                        "Conditional acknowledgement unresolved; retaining the same clientOid and trigger."
                    )
                    return None
        else:
            intent = ConditionalCloseOrder(
                client_oid=str(uuid4()),
                requested_qty=quantity,
                stop_price=stop_price,
                deal_type=deal_type,
            )
            self.active_bot.deal.conditional_close_order = intent
            self.controller.save(self.active_bot)
        if details is not None:
            response = OrderBase(
                order_id=str(details.id),
                client_oid=intent.client_oid,
                requested_qty=intent.requested_qty,
                stop_price=intent.stop_price,
                pair=self.kucoin_symbol,
                order_type="market",
                time_in_force="GTC",
                order_side="buy"
                if self.active_bot.position == Position.short
                else "sell",
                price=float(details.avg_deal_price or 0),
                qty=float(details.filled_size or 0),
                timestamp=int(details.created_at or 0),
                status=OrderStatus.map_from_kucoin_status(details.status.value),
                deal_type=intent.deal_type,
            )
        else:
            intent.not_found_count = 0
            intent.not_found_since_ms = 0
            self.controller.save(self.active_bot)
            short = self.active_bot.position == Position.short
            response = self.kucoin_futures_api.place_futures_order(
                symbol=self.kucoin_symbol,
                side=AddOrderReq.SideEnum.BUY if short else AddOrderReq.SideEnum.SELL,
                order_type=OrderType.market,
                size=intent.requested_qty,
                leverage=self.active_bot.futures_leverage,
                stop=AddOrderReq.StopEnum.UP if short else AddOrderReq.StopEnum.DOWN,
                stop_price=intent.stop_price,
                stop_price_type=AddOrderReq.StopPriceTypeEnum.MARK_PRICE,
                reduce_only=True,
                allow_market_fallback=False,
                client_oid=intent.client_oid,
            )
        intent.order_id = str(response.order_id)
        response.deal_type = intent.deal_type
        response.client_oid = intent.client_oid
        response.requested_qty = intent.requested_qty
        response.stop_price = intent.stop_price
        if response.status == OrderStatus.FILLED and response.qty <= 0:
            response.status = OrderStatus.CANCELED
        order = OrderModel(**response.model_dump())
        existing = next(
            (
                row
                for row in self.active_bot.orders
                if str(row.order_id) == str(order.order_id)
            ),
            None,
        )
        if existing is None:
            self.active_bot.orders.append(order)
        else:
            existing.__dict__.update(order.__dict__)
            order = existing
        self.controller.save(self.active_bot)
        return order

    def place_stop_loss(self, position_qty: float | None = None) -> None:
        if self.active_bot.stop_loss <= 0 or self.awaiting_close_confirmation():
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
        else:
            side = AddOrderReq.SideEnum.SELL

        qty = (
            position_qty
            if position_qty is not None and position_qty > 0
            else self.current_position_quantity()
        )
        if qty <= 0:
            self.active_bot.add_log(
                "Stop loss was not placed because no current or historical "
                "position quantity is available."
            )
            return

        intent = self.active_bot.deal.conditional_close_order
        if (
            intent is not None
            and intent.order_id is not None
            and any(
                str(order.order_id) == intent.order_id
                and order.status in self.TERMINAL_STOP_ORDER_STATUSES
                for order in self.active_bot.orders
            )
        ):
            self.active_bot.deal.conditional_close_order = None
            self.controller.save(self.active_bot)

        # Adopt matching protection already on the exchange. New submissions
        # persist their clientOid before placing an order, so a lost response
        # can be recovered without creating another identity.
        try:
            exchange_stop_orders = self.kucoin_futures_api.get_all_stop_loss_orders(
                self.kucoin_symbol
            )
        except Exception:
            exchange_stop_orders = []
        for exchange_order in exchange_stop_orders:
            exchange_price = float(exchange_order.stop_price or 0)
            raw_exchange_qty = exchange_order.size
            exchange_qty = (
                abs(float(raw_exchange_qty)) if raw_exchange_qty is not None else None
            )
            if abs(exchange_price - stop_price) > 10**-self.price_precision:
                continue
            # An explicit fill quantity must not adopt a stop whose size the
            # exchange has omitted; that does not confirm full protection.
            if exchange_qty is None and position_qty is not None:
                continue
            if exchange_qty is not None and exchange_qty != qty:
                continue
            if (
                exchange_order.side is not None
                and exchange_order.side.lower() != side.value
            ):
                continue
            if exchange_order.reduce_only is False:
                continue

            exchange_order_id = str(exchange_order.id or "")
            if not exchange_order_id:
                continue
            if not any(
                str(local_order.order_id) == exchange_order_id
                and local_order.status not in self.TERMINAL_STOP_ORDER_STATUSES
                for local_order in self.active_bot.orders
            ):
                self.active_bot.orders.append(
                    OrderModel(
                        timestamp=int(exchange_order.created_at or time() * 1000),
                        order_id=exchange_order_id,
                        deal_type=DealType.stop_loss,
                        pair=self.kucoin_symbol,
                        order_side=side.value,
                        order_type=OrderType.market,
                        price=0,
                        stop_price=stop_price,
                        requested_qty=exchange_qty if exchange_qty is not None else qty,
                        qty=0,
                        client_oid=exchange_order.client_oid,
                        time_in_force="GTC",
                        status=OrderStatus.NEW,
                    )
                )
            client_oid = exchange_order.client_oid
            identifier = (
                f"{exchange_order_id} (clientOid {client_oid})"
                if client_oid
                else exchange_order_id
            )
            self.active_bot.add_log(
                f"Reused matching KuCoin stop order {identifier} instead of "
                "placing a duplicate."
            )
            self.active_bot.deal.stop_loss_price = stop_price
            return

        order_model = self.place_conditional_close(stop_price, qty, DealType.stop_loss)
        if order_model is None:
            return
        self.active_bot.deal.stop_loss_price = stop_price

        if order_model.status == OrderStatus.FILLED:
            self.active_bot.add_log(
                "Native stop has execution activity; awaiting position/fill reconciliation."
            )
            self.controller.save(self.active_bot)
            return

        self.controller.update_logs(
            bot=self.active_bot,
            log_message=f"Stop-market set @ {stop_price}",
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
                    if self.active_bot.deal.current_position_qty == 0:
                        self.active_bot.deal.current_position_qty = order.qty
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
            if (
                not self.active_bot.dynamic_position_sizing
                or self.active_bot.deal.trailing_profit_price == 0
            ):
                self.active_bot.deal.trailing_profit_price = round_numbers(
                    trailing_profit_price, self.price_precision
                )
            # NOTE: trailing_stop_loss_price is intentionally preserved here.
            # Resetting an armed trail every tick would (a) defeat dynamic
            # trailing and (b) bypass the trailing-armed guard in
            # reconcile_exchange_sl(). The "Update Deal" flow that needs to
            # disarm the trail does so explicitly in open_deal().

        return self.active_bot

    def update_parameters(self, *, allow_stop_loss_widening: bool = False) -> BotModel:
        """
        Update derived prices in-memory and reconcile the on-exchange
        emergency SL with what the bot now expects. The two halves are
        deliberately separated:

          - recompute_derived_prices() is pure and tick-safe.
          - reconcile_exchange_sl() touches the exchange and is gated by
            drift detection + min-move + cooldown to avoid order churn.
        """
        self.recompute_derived_prices()
        self.reconcile_exchange_sl(allow_widening=allow_stop_loss_widening)
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
        take_profit_pct = self.active_bot.take_profit / 100
        take_profit_multiplier = (
            1 - take_profit_pct
            if self.active_bot.position == Position.short
            else 1 + take_profit_pct
        )
        self.active_bot.deal.take_profit_price = take_profit_multiplier * deal_buy_price

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
                leverage=self.active_bot.futures_leverage,
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
                leverage=self.active_bot.futures_leverage,
            )

        order_base.deal_type = DealType.take_profit
        # Convert OrderBase to OrderModel using model_dump/model_construct
        order_data = OrderModel.model_construct(**order_base.model_dump())

        self.active_bot.orders.append(order_data)
        self.active_bot.deal.closing_price = float(order_data.price)
        self.active_bot.deal.closing_qty = float(order_data.qty)
        self.active_bot.deal.closing_timestamp = round_timestamp(order_data.timestamp)
        self.active_bot.deal.current_position_qty = 0
        self.active_bot.status = Status.completed

        if order_data.status == OrderStatus.FILLED:
            self._cleanup_native_protection_after_close()

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

        qty = self.current_position_quantity()
        if qty <= 0:
            self.active_bot = self.backfill_position_from_fills()
            self.controller.save(self.active_bot)
            return self.active_bot
        try:
            if self.active_bot.position == Position.short:
                order_base = self.kucoin_futures_api.buy(
                    symbol=self.kucoin_symbol,
                    qty=qty,
                    leverage=self.active_bot.futures_leverage,
                    reduce_only=True,
                    reference_price=reference_price,
                )
            else:
                order_base = self.kucoin_futures_api.sell(
                    symbol=self.kucoin_symbol,
                    qty=qty,
                    reduce_only=True,
                    leverage=self.active_bot.futures_leverage,
                    reference_price=reference_price,
                )

        except RestError as e:
            if float(e.response.code) == 300009:
                self.controller.update_logs(
                    bot=self.active_bot,
                    log_message=f"{str(e.response.message)}",
                )
                self.active_bot.status = Status.completed
                self.active_bot.deal.current_position_qty = 0
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

        if stop_loss_order.status != OrderStatus.FILLED:
            self.controller.update_logs(
                bot=self.active_bot,
                log_message=f"Stop loss order not filled immediately, got status {stop_loss_order.status}. Manual intervention may be required.",
            )
        else:
            self.active_bot.deal.closing_price = stop_loss_order.price
            self.active_bot.deal.closing_qty = stop_loss_order.qty
            self.active_bot.deal.closing_timestamp = stop_loss_order.timestamp
            self.active_bot.deal.current_position_qty = 0
            self.active_bot.add_log("Completed futures Stop loss.")
            self.active_bot.status = Status.completed
            self._cleanup_native_protection_after_close()

        self.controller.save(self.active_bot)

        return self.active_bot

    def place_trailing_stop_loss(
        self, repurchase_multiplier: float = 1, *, position_qty: float | None = None
    ) -> BotModel | None:
        """
        Place the closing position (stop loss in Kucoin) when the bot (long or short) is
        in a profitable position

        This only places the stop loss order at the exchange, the actual bot status and deal parameters will be updated when the order is filled and the streaming worker reconciles the actual fills (futures_position.order_updates)
        """

        intent = self.active_bot.deal.conditional_close_order
        if intent is not None and intent.order_id is None:
            self.place_conditional_close(
                intent.stop_price, intent.requested_qty, intent.deal_type
            )
            return self.active_bot

        if position_qty is None:
            position = self.kucoin_futures_api.get_futures_position(self.kucoin_symbol)
            if not position or float(position.current_qty) == 0:
                self.active_bot = self.backfill_position_from_fills()
                return self.active_bot
            position_qty = abs(float(position.current_qty))

        qty = round_numbers(position_qty * repurchase_multiplier, 8)
        intended_price = self.active_bot.deal.trailing_stop_loss_price
        _, last_replace_ts_ms, trailing_order_id = self._bot_known_trailing_stop_loss()
        exchange_ok, exchange_price, exchange_qty = self._exchange_stop_loss_details(
            order_id=trailing_order_id
        )
        if not exchange_ok:
            return self.active_bot
        quantity_changed = (exchange_qty is not None and exchange_qty != qty) or any(
            str(order.order_id) == trailing_order_id
            and (order.requested_qty if order.requested_qty > 0 else order.qty) != qty
            for order in self.active_bot.orders
        )
        if quantity_changed and exchange_price is not None:
            # Resizing protection must never loosen a tighter exchange stop.
            direction = self._direction_multiplier()
            if (exchange_price - intended_price) * direction > 0:
                intended_price = exchange_price
                self.active_bot.deal.trailing_stop_loss_price = exchange_price
        if exchange_ok and not quantity_changed:
            if exchange_price is None and self.trailing_stop_replace_on_cooldown(
                last_replace_ts_ms
            ):
                return self.active_bot
            if exchange_price is not None and not self.should_replace_stop_loss_order(
                current_stop_price=exchange_price,
                new_stop_price=intended_price,
                last_replace_ts_ms=last_replace_ts_ms,
                cooldown_ms=self.TRAILING_STOP_REPLACE_COOLDOWN_MS,
            ):
                return self.active_bot

        action = "buy" if self.active_bot.position == Position.short else "sell"
        self.controller.update_logs(
            f"Dispatching futures {action} order for trailing profit...",
            self.active_bot,
        )

        self.cancel_current_sl(
            deal_type=DealType.trailing_profit
            if trailing_order_id is not None
            else None
        )

        order_data = self.place_conditional_close(
            self.active_bot.deal.trailing_stop_loss_price, qty, DealType.trailing_profit
        )
        if order_data is None:
            return self.active_bot

        if order_data.status == OrderStatus.FILLED:
            self.active_bot.add_log(
                "Trailing stop filled; waiting for position and execution reconciliation"
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

    def reconcile_trailing_stop_loss(
        self, *, position_qty: float | None = None
    ) -> None:
        """
        Re-place an armed futures trailing stop if the exchange no longer has
        a stop order. The bot-side trailing price is the intended exit once
        trailing has armed.
        """
        intended_price = self.active_bot.deal.trailing_stop_loss_price
        if intended_price <= 0:
            return

        _, last_replace_ts_ms, trailing_order_id = self._bot_known_trailing_stop_loss()
        exchange_ok, exchange_price, exchange_qty = self._exchange_stop_loss_details(
            order_id=trailing_order_id
        )
        if not exchange_ok:
            return

        quantity_changed = (
            exchange_qty is not None
            and exchange_qty
            != (
                position_qty
                if position_qty is not None
                else self.current_position_quantity()
            )
        ) or (
            position_qty is not None
            and any(
                str(order.order_id) == trailing_order_id
                and (order.requested_qty if order.requested_qty > 0 else order.qty)
                != position_qty
                for order in self.active_bot.orders
            )
        )
        if quantity_changed:
            self.active_bot.add_log(
                "Exchange trailing SL quantity changed; resizing full-position protection."
            )
            self.place_trailing_stop_loss(position_qty=position_qty)
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
        self.place_trailing_stop_loss(position_qty=position_qty)

    # Strategies whose reversal chain has historically compounded losses on chop;
    # for these, a second SL on the same pair within the cooldown closes instead of flipping.
    _NO_REVERSAL_AFTER_LOSS_NAMES = {
        "coinrule_buy_the_dip",
        "coinrule_price_tracker",
        "bb_extreme_reversion",
    }

    def _actual_fill(self, order: OrderBase | None) -> tuple[float, float]:
        """Best-effort real (filled_qty, avg_price) for a just-placed order.

        place_futures_order()'s own response doesn't reliably carry fill
        details, so query the order and then its fills to get the real numbers.
        Returns zero filled quantity when confirmation is unavailable; callers
        decide how to handle an unconfirmed fill.
        """
        if not order or not order.order_id:
            return 0.0, 0.0
        try:
            details = self.kucoin_futures_api.retrieve_order(str(order.order_id))
            filled_qty = float(details.filled_size or 0)
            avg_price = float(details.avg_deal_price or 0)
            if filled_qty > 0 and avg_price > 0:
                return filled_qty, avg_price
        except Exception:
            pass

        try:
            fills = self.kucoin_futures_api.get_fills(order_id=str(order.order_id))
            matching_fills = [
                fill
                for fill in (fills.items or [])
                if str(fill.order_id) == str(order.order_id)
                and float(fill.size or 0) > 0
                and float(fill.price or 0) > 0
            ]
            filled_qty = sum(float(fill.size) for fill in matching_fills)
            if filled_qty > 0:
                fill_notional = sum(
                    float(fill.size) * float(fill.price) for fill in matching_fills
                )
                return filled_qty, fill_notional / filled_qty
        except Exception:
            pass

        if order.status == OrderStatus.FILLED and order.qty > 0 and order.price > 0:
            return order.qty, order.price
        return 0.0, float(order.price or 0)

    def _close_with_market_fallback(
        self, side: AddOrderReq.SideEnum, qty: int, *, market_only: bool = False
    ) -> list[tuple[OrderBase, float, float]]:
        """Cross the spread with an IOC limit at the 1-tick matching-engine
        price first (better fill than a market order when the book has the
        depth); whatever doesn't fill immediately is guaranteed closed with
        a market order for the residual qty, so this always fully closes.

        Market-only exits skip the IOC leg and use the same fill confirmation.
        Returns every leg that actually filled as (order, filled_qty,
        avg_price) — both legs when the IOC only partially fills — so the
        caller can record every fill and compute a true weighted-average
        close price instead of only the last order placed.
        """
        fills: list[tuple[OrderBase, float, float]] = []
        limit_filled_qty = 0.0
        if not market_only:
            try:
                limit_price = self.kucoin_futures_api.matching_engine(
                    self.kucoin_symbol, size=qty, side=side
                )
                if limit_price is None:
                    raise ValueError("matching engine returned no executable price")
                limit_order = self.kucoin_futures_api.place_futures_order(
                    symbol=self.kucoin_symbol,
                    side=side,
                    size=qty,
                    price=limit_price,
                    leverage=self.active_bot.futures_leverage,
                    order_type=OrderType.limit,
                    reduce_only=True,
                    time_in_force=AddOrderReq.TimeInForceEnum.IMMEDIATE_OR_CANCEL,
                )
                sleep(self.CLOSE_ALL_FILL_CHECK_SLEEP_S)
                limit_filled_qty, limit_avg_price = self._actual_fill(limit_order)
                limit_filled_qty = min(limit_filled_qty, float(qty))
                if limit_filled_qty > 0:
                    fills.append((limit_order, limit_filled_qty, limit_avg_price))
            except Exception as error:
                self.active_bot.add_log(
                    "IOC close leg unavailable; sending the full residual as a "
                    f"reduce-only market order ({error})."
                )

        remaining_qty = qty - limit_filled_qty
        if remaining_qty <= 0:
            return fills

        market_order = self.kucoin_futures_api.place_futures_order(
            symbol=self.kucoin_symbol,
            side=side,
            size=int(round(remaining_qty)),
            leverage=self.active_bot.futures_leverage,
            order_type=OrderType.market,
            reduce_only=True,
        )
        sleep(self.CLOSE_ALL_FILL_CHECK_SLEEP_S)
        market_filled_qty, market_avg_price = self._actual_fill(market_order)
        if market_filled_qty <= 0:
            raise RuntimeError(
                "Reduce-only market close was submitted but its fill could not be "
                "confirmed; leaving the bot open for exchange-fill reconciliation."
            )
        market_filled_qty = min(market_filled_qty, remaining_qty)
        fills.append((market_order, market_filled_qty, market_avg_price))
        return fills

    def close_all(
        self,
        algorithmic_close: bool = False,
        *,
        deal_type: DealType = DealType.panic_close,
        market_only: bool = False,
        progress: Callable[[int, str], None] | None = None,
    ) -> BotModel:
        """
        Closes all open positions and cancels all orders.
        To be used also for panic selling from terminal.

        Tries a spread-crossing limit order first for a better fill; any
        amount that doesn't fill immediately is closed with a market order
        for whatever qty is left. ``market_only`` skips the limit leg.
        """
        if algorithmic_close:
            deal_type = DealType.algorithmic_close
        if progress:
            progress(35, "Cancelling protective and pending orders")
        if (
            deal_type != DealType.stop_loss
            and self.active_bot.recovery_params is not None
        ):
            self.active_bot.deal.recovery_cancelled = True
            self.controller.save(self.active_bot)
        if self.active_bot.deal.conditional_close_order is not None or any(
            order.deal_type in {DealType.stop_loss, DealType.trailing_profit}
            and order.status not in self.TERMINAL_STOP_ORDER_STATUSES
            for order in self.active_bot.orders
        ):
            self.cancel_current_sl()
        if self.active_bot.deal.position_size_order is not None:
            # Stop recovery before cancelling: a restart must never replay an
            # uncertain increase after the position's protective exit.
            self.active_bot.dynamic_position_sizing = False
            self.controller.save(self.active_bot)
            self.kucoin_futures_api.cancel_all_futures_orders(self.kucoin_symbol)
        position = self.kucoin_futures_api.get_futures_position(self.kucoin_symbol)
        if progress:
            progress(55, "Checking the exchange position")

        if position and float(position.current_qty) != 0:
            if progress:
                progress(65, "Closing the exchange position")
            position_qty = float(position.current_qty)
            qty = abs(int(position_qty))
            close_side = (
                AddOrderReq.SideEnum.BUY
                if position_qty < 0
                else AddOrderReq.SideEnum.SELL
            )
            fills = self._close_with_market_fallback(
                close_side, qty, market_only=market_only
            )

            total_filled_qty = 0.0
            weighted_notional = 0.0
            for order, filled_qty, avg_price in fills:
                order_dict = order.model_dump()
                order_dict["qty"] = filled_qty
                order_dict["price"] = avg_price
                order_model = OrderModel(**order_dict)
                order_model.deal_type = deal_type
                self.active_bot.orders.append(order_model)
                total_filled_qty += filled_qty
                weighted_notional += filled_qty * avg_price

            if total_filled_qty < qty:
                raise RuntimeError(
                    "Futures close did not confirm the full exchange position: "
                    f"confirmed={total_filled_qty}, expected={qty}."
                )
            if progress:
                progress(85, "Close fills confirmed")

            # Both legs recorded and blended into a single weighted-average
            # close — a partial IOC fill plus market-fallback residual must
            # not be reported (and downstream-PnL'd) as if the entire
            # position closed at only the last order's price.
            self.active_bot.deal.closing_qty = (
                total_filled_qty if total_filled_qty > 0 else qty
            )
            self.active_bot.deal.closing_price = (
                weighted_notional / total_filled_qty if total_filled_qty > 0 else 0.0
            )
            self.active_bot.deal.closing_timestamp = max(
                order.timestamp for order, _, _ in fills
            )
            self.active_bot.deal.current_position_qty = 0
            self.active_bot.status = Status.completed
            self._cleanup_native_protection_after_close()
            self.controller.update_logs(
                bot=self.active_bot,
                log_message=f"Futures position closed successfully ({deal_type.value})",
            )

        elif (
            self.active_bot.status == Status.completed
            and self.active_bot.deal.closing_price > 0
        ):
            # A native stop already recorded the close; do not aggregate old
            # partial reductions into it when retiring a pending increase.
            self._cleanup_native_protection_after_close()
        elif (
            not self.active_bot.orders
            and self.active_bot.deal.opening_timestamp == 0
            and self.active_bot.deal.opening_qty == 0
        ):
            self.active_bot.add_log(
                "No futures position, entry order, or opening fill exists; "
                "skipping fill-history reconciliation."
            )
        else:
            self.active_bot = self.backfill_position_from_fills()

        self.controller.save(self.active_bot)
        if progress:
            progress(95, "Bot state saved")
        return self.active_bot

    def open_deal(self, progress: Callable[[int, str], None] | None = None) -> BotModel:
        if progress:
            progress(35, "Preparing the futures entry")
        if (
            self.active_bot.dynamic_position_sizing
            and self.active_bot.recovery_params is not None
        ):
            raise BinbotErrors(
                "Dynamic position sizing and recovery are mutually exclusive"
            )
        base_order = next(
            (
                bo_deal
                for bo_deal in self.active_bot.orders
                if bo_deal.deal_type == DealType.base_order
            ),
            None,
        )

        if not base_order:
            if progress:
                progress(45, "Submitting the entry order")
            self.active_bot.add_log(
                f"Opening new future deal for {self.kucoin_symbol}..."
            )
            self.controller.save(self.active_bot)
            self.base_order()
            if progress:
                progress(75, "Entry order submitted")

        # Entry not filled yet (opening_price == 0): leave the bot pending and
        # return. order_updates() will promote it to active once KuCoin confirms
        # the fill by calling open_deal() again, which will reach the branch below.
        if self.active_bot.deal.opening_price == 0:
            self.active_bot.status = Status.pending
            self.active_bot.add_log(
                "Entry order is live but not yet filled; bot set to pending."
            )
            self.controller.save(self.active_bot)
            if progress:
                progress(95, "Waiting for the exchange fill")
            return self.active_bot

        # Entry is filled (opening_price > 0): activate / reactivate.
        # Disarm any stale trail — parameters may have changed (e.g. Update Deal).
        self.active_bot.deal.trailing_stop_loss_price = 0
        self.active_bot = self.update_parameters()
        if self.active_bot.status != Status.completed:
            self.active_bot.status = Status.active
        self.controller.save(self.active_bot)
        if progress:
            progress(95, "Bot state saved")
        return self.active_bot
