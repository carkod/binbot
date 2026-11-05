from time import sleep, time

from typing import Any, NoReturn, Type

from pybinbot import (
    ema,
    BinanceKlineIntervals,
    BinbotErrors,
    BotModel,
    Candles,
    KucoinFutures,
    Position,
    Status,
    ceil_price_to_tick,
    floor_price_to_tick,
    round_numbers,
    round_numbers_ceiling,
)

from api.databases.crud.bot_crud import BotTableCrud
from api.databases.crud.symbols_crud import SymbolsCrud
from api.databases.tables.bot_table import BotTable
from api.databases.tables.signals_table import SignalsTable
from api.databases.utils import get_db_session
from api.exchange_apis.kucoin.futures.liquidity import load_futures_order_book
from api.exchange_apis.kucoin.futures.order_execution import OrderExecution
from api.tools.constants import (
    TOP_GAINER_EARLY_MOMENTUM_ALGO,
    TOP_GAINER_FAILURE_REVERSAL_ALGO,
)


ENTRY_ATR_WINDOW = 14


def closed_candle_atr(completed_candles: list) -> float | None:
    """Average true range of the last ENTRY_ATR_WINDOW completed candles."""
    if len(completed_candles) < ENTRY_ATR_WINDOW + 1:
        return None

    candles = completed_candles[-(ENTRY_ATR_WINDOW + 1) :]
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

    if len(true_ranges) < ENTRY_ATR_WINDOW:
        return None
    return sum(true_ranges[-ENTRY_ATR_WINDOW:]) / ENTRY_ATR_WINDOW


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


class EntryLiquidityError(BinbotErrors):
    """A persisted rejection or retry deferral from the pre-entry liquidity gate."""


class EntryPricing(OrderExecution):
    """
    Entry limit pricing and pre-entry gates for one KuCoin futures bot:
    candle-anchored limits, top-gainer retest validation, displacement
    bands and order-book liquidity checks.

    KucoinPositionDeal extends this class with deal and position logic.
    """

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

    def __init__(
        self,
        bot: BotModel,
        db_table: Type[BotTable] = BotTable,
        kucoin_futures_api: KucoinFutures | None = None,
        controller: BotTableCrud | None = None,
        symbols_crud: SymbolsCrud | None = None,
        interval_ms: int | None = None,
    ) -> None:
        super().__init__(
            bot,
            db_table=db_table,
            kucoin_futures_api=kucoin_futures_api,
            controller=controller,
            symbols_crud=symbols_crud,
            interval_ms=interval_ms,
        )
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

        ema20 = ema(closes, 20)[-1]
        ema50 = ema(closes, 50)[-1]
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
                limit=max(ENTRY_ATR_WINDOW + 3, self.ENTRY_TREND_WINDOW + 1),
            )
        except Exception as exc:
            self.active_bot.add_log(
                f"Entry rejected: unable to load reliable candle data ({exc})."
            )
            raise BinbotErrors(
                "Reliable current and completed candles are unavailable for futures entry."
            ) from exc

        klines = normalize_entry_klines(klines)
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
            atr = closed_candle_atr(completed_candles)
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
        atr = closed_candle_atr(completed_candles)
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
