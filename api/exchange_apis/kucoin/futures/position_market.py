import logging
from copy import deepcopy
from time import time
from typing import Type, Union

from kucoin_universal_sdk.generate.futures.positions.model_get_position_details_resp import (
    GetPositionDetailsResp,
)
from pandas import Series
from pybinbot import (
    BinanceApi,
    BotModel,
    Candles,
    ExchangeId,
    HABollinguerSpread,
    Indicators,
    KucoinApi,
    KucoinFutures,
    MarketType,
    Position,
    Status,
    convert_to_kucoin_symbol,
    round_numbers,
)

from api.databases.tables.bot_table import BotTable, PaperTradingTable
from api.exchange_apis.kucoin.futures.futures_deal import KucoinPositionDeal
from streaming.apex_flow_closing import ApexFlowClose
from streaming.base import BaseStreaming
from api.tools.utils import clamp

# Diagnostic-only: tracks the last time each symbol's exit-analytics poll ran,
# so we can surface (via logging.error, deliberately loud so it isn't lost in
# routine info-level noise) cases where the expected ~15s poll cadence is
# blown through by a wide margin. Investigating a suspected multi-hour gap
# between exchange stop-loss reconciliation checks; remove once root-caused.
_LAST_ANALYTICS_POLL_TS: dict[str, int] = {}
_ANALYTICS_POLL_GAP_ALERT_MS = 60_000  # expected cadence is ~15s; alert past 60s


class PositionMarket(KucoinPositionDeal):
    """
    Analytics for position deal exist
    """

    MIN_STOP_LOSS = 0.8
    MAX_STOP_LOSS = 4.0
    MIN_TRAILING_PROFIT = 0.6
    MAX_TRAILING_PROFIT = 3.5
    MIN_TRAILING_DEVIATION = 0.4
    MAX_TRAILING_DEVIATION = 2.5
    MIN_TRAIL_GAP = 0.35
    PULLBACK_ARM_PROFIT = 1.0
    SHALLOW_PULLBACK = 0.75
    DEEP_PULLBACK = 1.5
    # Algo name match: see binquant/strategies/coinrule/bb_extreme_reversion.py
    BB_EXTREME_REVERSION_ALGO = "bb_extreme_reversion"
    BB_EXTREME_ATR_WINDOW = 14
    BB_EXTREME_ATR_SL_MULTIPLIER = 2.0

    # Algo name match: see binquant/strategies/mean_reversion_fade.py
    MEAN_REVERSION_FADE_ALGO = "mean_reversion_fade"
    # Conservative by design: a tighter ceiling than the shared MAX_STOP_LOSS
    # (4.0) used by other dynamic-trailing algos, and margin_short_reversal
    # is disabled at signal time (binquant) rather than recovered here.
    MRF_MIN_STOP_LOSS = 0.8
    MRF_MAX_STOP_LOSS = 3.0
    MRF_ATR_SL_MULTIPLIER = 2.0
    MRF_RSI_WINDOW = 14
    MRF_INVALIDATION_BARS = 3

    def __init__(
        self,
        api: Union[BinanceApi, KucoinApi, KucoinFutures],
        bot: BotModel,
        symbol: str,
        base_streaming: BaseStreaming,
        db_table: Type[BotTable] | Type[PaperTradingTable],
    ) -> None:
        super().__init__(bot=bot, db_table=db_table, base_streaming=base_streaming)
        self.api = api
        self.active_bot = bot
        self.symbol = symbol
        self.base_streaming = base_streaming
        self.db_table = db_table
        self.symbol_data = base_streaming.symbols_crud.get_symbol(symbol)
        self.qty_precision = self.symbol_data.qty_precision
        self.controller = base_streaming.bot_controller

    def build_bb_spreads(self) -> HABollinguerSpread:
        """
        Builds the bollinguer bands spreads without using pandas_ta
        """
        data = self.klines
        if len(data) < 200:
            return HABollinguerSpread(bb_high=0, bb_mid=0, bb_low=0)

        bb_spreads = HABollinguerSpread(
            bb_high=self.df["bb_upper"].iloc[-1],
            bb_mid=self.df["bb_mid"].iloc[-1],
            bb_low=self.df["bb_lower"].iloc[-1],
        )

        return bb_spreads

    def build_bb_metrics(self) -> tuple[float, float] | None:
        bb_spreads = self.build_bb_spreads()
        if bb_spreads.bb_high == 0 or bb_spreads.bb_low == 0:
            return None

        top_spread = (
            abs((bb_spreads.bb_high - bb_spreads.bb_mid) / bb_spreads.bb_high) * 100
        )
        bottom_spread = (
            abs((bb_spreads.bb_mid - bb_spreads.bb_low) / bb_spreads.bb_mid) * 100
        )

        return (
            clamp(top_spread, 1.5, 6.0),
            clamp(bottom_spread, 1.0, 4.0),
        )

    def build_pullback_metrics(self, current_price: float) -> dict[str, float] | None:
        entry_price = self.active_bot.deal.opening_price
        entry_timestamp = self.active_bot.deal.opening_timestamp
        if entry_price <= 0 or entry_timestamp <= 0:
            return None

        entry_index = None
        for index, candle in enumerate(self.klines):
            if len(candle) < 3:
                continue
            if int(float(candle[0])) >= entry_timestamp:
                entry_index = index
                break

        if entry_index is None:
            return None

        peak_price_since_entry = max(
            [
                float(candle[2])
                for candle in self.klines[entry_index:]
                if len(candle) >= 3
            ]
            + [float(current_price)],
        )
        if peak_price_since_entry <= 0:
            return None

        peak_profit_pct = ((peak_price_since_entry - entry_price) / entry_price) * 100
        pullback_pct = max(
            0.0,
            ((peak_price_since_entry - float(current_price)) / peak_price_since_entry)
            * 100,
        )

        return {
            "peak_price_since_entry": peak_price_since_entry,
            "peak_profit_pct": peak_profit_pct,
            "pullback_pct": pullback_pct,
        }

    def derive_dynamic_trailing_params(
        self,
        top_spread: float,
        bottom_spread: float,
        bot_profit: float,
        expansion_multiplier: float,
        is_aggressive_momo: bool,
        expansion_range: float,
        trail_tighten_mult: float,
        current_price: float,
        direction: int = 1,
    ) -> tuple[float, float, float]:
        """
        LONG + SHORT trailing logic (direction=+1 long, -1 short).

        Rules:
        - stop_loss is the emergency safety net. It is initialised once
          (when the bot has no SL yet), then only ever tightened — never
          widened — toward the live band's protective-side distance.
        - trailing_profit is a ceiling trigger only.
        - trailing_deviation is the real stop once trailing starts; it can
          tighten/widen freely, since it lives in the bot, not the exchange.

        top_spread/bottom_spread are absolute (direction-agnostic) distances
        from the Bollinger mid band to the upper/lower band. The favourable
        side of the band — the one price must travel through to profit — is
        the top for a long and the bottom for a short, mirroring the same
        long/short spread assignment binquant uses at bot creation
        (shared/autotrade.py:_set_bollinguer_spreads). trailing_profit tracks
        the favourable spread; trailing_deviation tracks the opposite
        (protective) spread — the same protective spread also seeds the SL
        ratchet below, since it's the band's read on how far price could
        move against the position.
        """
        profit_spread, deviation_spread = (
            (top_spread, bottom_spread)
            if direction > 0
            else (bottom_spread, top_spread)
        )
        raw_trail_profit = profit_spread * trail_tighten_mult * expansion_multiplier

        # Progressive tightening as profits grow
        if bot_profit >= 5:
            raw_trail_profit = min(raw_trail_profit, 2.0)
        elif bot_profit >= 3:
            raw_trail_profit = min(raw_trail_profit, 3.0)

        trailing_profit = clamp(
            raw_trail_profit,
            self.MIN_TRAILING_PROFIT,
            self.MAX_TRAILING_PROFIT,
        )
        trailing_deviation = clamp(
            deviation_spread * trail_tighten_mult,
            self.MIN_TRAILING_DEVIATION,
            self.MAX_TRAILING_DEVIATION,
        )

        # Emergency SL: once set, only ever ratchet tighter toward the band's
        # protective-side distance (deviation_spread) — never widen, and
        # never loosen based on market state. Before that, derive an initial
        # value the same way as before.
        existing_stop_loss = self.active_bot.stop_loss
        if existing_stop_loss > 0:
            band_sl_candidate = clamp(
                deviation_spread, self.MIN_STOP_LOSS, self.MAX_STOP_LOSS
            )
            stop_loss = clamp(
                min(existing_stop_loss, band_sl_candidate),
                self.MIN_STOP_LOSS,
                self.MAX_STOP_LOSS,
            )
        else:
            opening_price = self.active_bot.deal.opening_price
            if is_aggressive_momo and opening_price > 0:
                stop_loss = ((expansion_range * 0.5) / opening_price) * 100
            else:
                stop_loss = 3.0
            stop_loss = clamp(stop_loss, self.MIN_STOP_LOSS, self.MAX_STOP_LOSS)

        pullback_metrics = self.build_pullback_metrics(current_price=current_price)
        if (
            pullback_metrics
            and pullback_metrics["peak_profit_pct"] >= self.PULLBACK_ARM_PROFIT
        ):
            pullback_pct = pullback_metrics["pullback_pct"]
            if pullback_pct < self.SHALLOW_PULLBACK:
                trailing_profit += 0.25
                trailing_deviation += 0.05
            elif pullback_pct >= self.DEEP_PULLBACK:
                trailing_profit -= 0.30
                trailing_deviation -= 0.10

        stop_loss = clamp(stop_loss, self.MIN_STOP_LOSS, self.MAX_STOP_LOSS)
        trailing_profit = clamp(
            trailing_profit,
            self.MIN_TRAILING_PROFIT,
            self.MAX_TRAILING_PROFIT,
        )
        max_deviation = min(
            self.MAX_TRAILING_DEVIATION,
            trailing_profit - self.MIN_TRAIL_GAP,
        )
        trailing_deviation = clamp(
            trailing_deviation,
            self.MIN_TRAILING_DEVIATION,
            max_deviation,
        )

        return (
            round_numbers(stop_loss, 2),
            round_numbers(trailing_profit, 2),
            round_numbers(trailing_deviation, 2),
        )

    def dataframe_ops(self) -> tuple[list, list]:
        """
        Converts raw klines to DataFrames for indicator calculations.
        """
        # Get klines from the appropriate exchange
        self.klines = self.api.get_ui_klines(
            symbol=self.symbol,
            interval=str(self.base_streaming.interval.value),
        )
        self.btc_klines = self.base_streaming.binance_api.get_ui_klines(
            symbol="BTCUSDT",
            interval=self.base_streaming.binance_interval.value,
        )

        raw_candles = Candles(
            exchange=self.base_streaming.exchange,
            candles=self.klines.copy(),
        )
        self.df = raw_candles.pre_process()

        raw_btc_candles = Candles(
            exchange=ExchangeId.BINANCE,
            candles=self.btc_klines.copy(),
        )
        self.btc_df = raw_btc_candles.pre_process()

        self.df = Indicators.bollinguer_spreads(self.df)
        self.btc_df = Indicators.bollinguer_spreads(self.btc_df, window=20)

        self.df = raw_candles.post_process(self.df)
        self.btc_df = raw_btc_candles.post_process(self.btc_df)

        return self.klines, self.btc_klines

    def position_updates(
        self, position: GetPositionDetailsResp | None = None
    ) -> BotModel:
        """
        Due to ADL, position size (number of contracts can change)
        Therefore we need to keep base_order_size up to date at all times, so that exit execution can succeed with correct qty
        """
        if self.active_bot.deal.base_order_size > 0:
            old_size = self.active_bot.deal.base_order_size
            old_commissions = self.active_bot.deal.total_commissions
            if position is None:
                kucoin_symbol = convert_to_kucoin_symbol(self.active_bot)
                position = self.base_streaming.kucoin_futures_api.get_futures_position(
                    kucoin_symbol
                )
            # position.current_qty can be positive or negative depending on the strategy
            if position and abs(int(position.current_qty)) > 0:
                new_size = round_numbers(
                    abs(int(position.current_qty)), self.qty_precision
                )
                if new_size != old_size:
                    self.active_bot.deal.base_order_size = new_size
                    self.active_bot.add_log(
                        f"Position size updated from system. Old size: {old_size}, new size: {new_size}."
                    )

                if old_commissions != float(position.current_comm):
                    self.active_bot.deal.total_commissions = float(
                        position.current_comm
                    )
                self.controller.save(data=self.active_bot)
            else:
                # Only backfill for active bots — pending/inactive/completed bots
                # have no live position to reconcile and must never be marked error
                # here (e.g. an expired→inactive bot still has base_order_size > 0).
                if self.active_bot.status != Status.active:
                    return self.active_bot
                # Grace window: the position endpoint lags the order fill by up to
                # one candle interval. Skipping backfill during this window prevents
                # a false error on the same tick the entry fills.
                now_ms = int(time() * 1000)
                grace_ms = self.base_streaming.interval.get_ms()
                if (
                    self.active_bot.deal.opening_timestamp > 0
                    and (now_ms - self.active_bot.deal.opening_timestamp) < grace_ms
                ):
                    self.active_bot.add_log(
                        "Position not yet propagated to exchange endpoint; "
                        "within entry grace window. Skipping backfill."
                    )
                    self.controller.save(data=self.active_bot)
                    return self.active_bot
                self.active_bot = self.backfill_position_from_fills()
                self.controller.save(data=self.active_bot)

        return self.active_bot

    def _atr_pct(self, current_price: float) -> float | None:
        """ATR over the last `BB_EXTREME_ATR_WINDOW` candles, expressed as a
        percentage of the current price. Mirrors Indicators.atr inline so we
        don't mutate self.df."""
        if len(self.klines) < self.BB_EXTREME_ATR_WINDOW + 1 or current_price <= 0:
            return None
        true_ranges = []
        for i in range(len(self.klines) - self.BB_EXTREME_ATR_WINDOW, len(self.klines)):
            if i <= 0:
                continue
            prev_close = float(self.klines[i - 1][4])
            high = float(self.klines[i][2])
            low = float(self.klines[i][3])
            true_ranges.append(
                max(high - low, abs(high - prev_close), abs(low - prev_close))
            )
        if not true_ranges:
            return None
        atr = sum(true_ranges) / len(true_ranges)
        return (atr / current_price) * 100

    def bb_extreme_reversion_trailing_analytics(self, current_price: float) -> None:
        """
        ATR-based SL with BB-derived trailing for bb_extreme_reversion bots.
        Works for both long and short — the percentages are direction-agnostic
        and the downstream `exit()` applies the direction multiplier when
        placing orders.

        - stop_loss: derived once from ATR (then pinned, like the long path).
        - trailing_profit / trailing_deviation: BB-derived per tick, same
          formulas as build_bb_metrics.
        """
        original_bot = deepcopy(self.active_bot)
        market_type = getattr(
            self.active_bot.market_type, "value", self.active_bot.market_type
        )
        position = getattr(self.active_bot.position, "value", self.active_bot.position)
        position_value = str(position).lower()
        if (
            str(market_type).lower() != MarketType.FUTURES.value.lower()
            or position_value
            not in {Position.long.value.lower(), Position.short.value.lower()}
            or self.active_bot.deal.opening_price <= 0
        ):
            return

        # ─────────────────────────────
        # ATR-based stop loss (emergency only; pinned once set)
        # ─────────────────────────────
        existing_stop_loss = self.active_bot.stop_loss
        if existing_stop_loss > 0:
            stop_loss = clamp(
                existing_stop_loss, self.MIN_STOP_LOSS, self.MAX_STOP_LOSS
            )
        else:
            atr_pct = self._atr_pct(current_price)
            if atr_pct is None:
                stop_loss = 3.0
            else:
                stop_loss = clamp(
                    self.BB_EXTREME_ATR_SL_MULTIPLIER * atr_pct,
                    self.MIN_STOP_LOSS,
                    self.MAX_STOP_LOSS,
                )

        # ─────────────────────────────
        # BB-derived trailing (re-derived each tick, direction-agnostic)
        # ─────────────────────────────
        bb_metrics = self.build_bb_metrics()
        if bb_metrics:
            top_spread, bottom_spread = bb_metrics
            trailing_profit = clamp(
                top_spread, self.MIN_TRAILING_PROFIT, self.MAX_TRAILING_PROFIT
            )
            trailing_deviation = clamp(
                bottom_spread,
                self.MIN_TRAILING_DEVIATION,
                self.MAX_TRAILING_DEVIATION,
            )
            max_deviation = min(
                self.MAX_TRAILING_DEVIATION, trailing_profit - self.MIN_TRAIL_GAP
            )
            trailing_deviation = clamp(
                trailing_deviation, self.MIN_TRAILING_DEVIATION, max_deviation
            )
        else:
            trailing_profit = (
                self.active_bot.trailing_profit
                if self.active_bot.trailing_profit > 0
                else 2.3
            )
            trailing_deviation = (
                self.active_bot.trailing_deviation
                if self.active_bot.trailing_deviation > 0
                else 1.63
            )

        self.active_bot.stop_loss = round_numbers(stop_loss, 2)
        self.active_bot.trailing_profit = round_numbers(trailing_profit, 2)
        self.active_bot.trailing_deviation = round_numbers(trailing_deviation, 2)

        if (
            self.active_bot.trailing_profit != original_bot.trailing_profit
            or self.active_bot.trailing_deviation != original_bot.trailing_deviation
            or self.active_bot.stop_loss != original_bot.stop_loss
        ):
            self.active_bot = self.update_parameters()
            self.controller.save(data=self.active_bot)

    def _rsi_series_closed(self, window: int) -> Series | None:
        """
        Wilder-smoothed RSI computed inline from closed ca
        ndles in
        `self.klines` only (drops the still-forming candle so repeated
        ~15s polls within one candle are idempotent). Mirrors `_atr_pct`'s
        convention of not mutating `self.df`.
        """
        now_ms = int(time() * 1000)
        poll_key = getattr(self, "symbol", None)
        if poll_key is not None:
            last_poll_ms = _LAST_ANALYTICS_POLL_TS.get(poll_key)
            if last_poll_ms is not None:
                gap_ms = now_ms - last_poll_ms
                if gap_ms > _ANALYTICS_POLL_GAP_ALERT_MS:
                    logging.error(
                        "Exit-analytics poll gap for %s: %.1fs since last poll "
                        "(expected ~15s cadence) — investigating suspected "
                        "reconciliation stalls.",
                        poll_key,
                        gap_ms / 1000,
                    )
            _LAST_ANALYTICS_POLL_TS[poll_key] = now_ms

        interval_ms = self.base_streaming.interval.get_ms()
        closed = [
            candle
            for candle in self.klines
            if len(candle) >= 5 and int(float(candle[0])) + interval_ms <= now_ms
        ]
        if len(closed) < window + 1:
            return None

        closes = Series([float(candle[4]) for candle in closed])
        delta = closes.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
        # 100*avg_gain/(avg_gain+avg_loss) is algebraically the same RSI as
        # 100-100/(1+avg_gain/avg_loss) when avg_loss>0, but — unlike dividing
        # by avg_loss directly — it resolves cleanly to 100 when a window has
        # no losses at all (e.g. a monotonic run against a short), instead of
        # turning the whole window's RSI into NaN. Only the genuine flat case
        # (no gains AND no losses) needs an explicit neutral override; NaN
        # from insufficient warmup history is preserved either way.
        denom = avg_gain + avg_loss
        rsi = (100 * avg_gain / denom).where(denom != 0, 50.0)
        return rsi

    def _mean_reversion_fade_invalidated(
        self, current_price: float, direction: int
    ) -> bool:
        """
        Pessimistic early-exit check: within the first MRF_INVALIDATION_BARS
        closed candles after entry, if price hasn't bounced yet AND RSI
        makes a new local extreme AGAINST the position (a new low for a
        long, a new high for a short) rather than recovering, the
        mean-reversion thesis likely isn't playing out — cut early instead
        of waiting for the full ATR stop. No entry-time snapshot is stored
        (BotModel/DealBase have no free-form field for one); this is fully
        reconstructed each tick from the closed-candle RSI series between
        the entry candle and now.
        """
        entry_price = self.active_bot.deal.opening_price
        entry_timestamp = self.active_bot.deal.opening_timestamp
        if entry_price <= 0 or entry_timestamp <= 0:
            return False

        now_ms = int(time() * 1000)
        interval_ms = self.base_streaming.interval.get_ms()
        closed = [
            candle
            for candle in self.klines
            if len(candle) >= 5 and int(float(candle[0])) + interval_ms <= now_ms
        ]
        if len(closed) < self.MRF_RSI_WINDOW + 1:
            return False

        entry_index = None
        for index, candle in enumerate(closed):
            if int(float(candle[0])) >= entry_timestamp:
                entry_index = index
                break
        if entry_index is None:
            return False

        bars_since_entry = len(closed) - 1 - entry_index
        if not (0 < bars_since_entry <= self.MRF_INVALIDATION_BARS):
            return False

        price_still_losing = (current_price - entry_price) * direction <= 0
        if not price_still_losing:
            return False

        rsi_series = self._rsi_series_closed(self.MRF_RSI_WINDOW)
        if rsi_series is None or entry_index >= len(rsi_series):
            return False
        rsi_since_entry = rsi_series.iloc[entry_index:]
        if rsi_since_entry.isnull().any():
            return False

        rsi_now = float(rsi_since_entry.iloc[-1])
        rsi_at_entry = float(rsi_since_entry.iloc[0])
        if direction > 0:
            return rsi_now <= rsi_since_entry.min() + 1e-9 and rsi_now < rsi_at_entry
        return rsi_now >= rsi_since_entry.max() - 1e-9 and rsi_now > rsi_at_entry

    def mean_reversion_fade_trailing_analytics(self, current_price: float) -> None:
        """
        Conservative exit for mean_reversion_fade bots. Works for both long
        and short futures positions via the direction multiplier.

        - stop_loss: ATR-based emergency stop (pinned once, like
          bb_extreme), but tightened early — never widened — if
          `_mean_reversion_fade_invalidated` fires: cut a "roughly
          cancels out" trade into a cleanly smaller loss instead of riding
          it to the full ATR stop or the max holding period.
        - trailing_profit / trailing_deviation: BB-derived per tick, same
          formulas as `build_bb_metrics` — this is what actually enforces
          the validated take-profit target (reversion to the mid-band);
          without it the strategy would have a stop-loss but no working
          take-profit in production.
        """
        original_bot = deepcopy(self.active_bot)
        market_type = getattr(
            self.active_bot.market_type, "value", self.active_bot.market_type
        )
        position = getattr(self.active_bot.position, "value", self.active_bot.position)
        position_value = str(position).lower()
        if (
            str(market_type).lower() != MarketType.FUTURES.value.lower()
            or position_value
            not in {Position.long.value.lower(), Position.short.value.lower()}
            or self.active_bot.deal.opening_price <= 0
        ):
            return

        direction = self._direction_multiplier()

        # ─────────────────────────────
        # ATR-based stop loss (emergency only; pinned once, then only
        # tightened — matching the conservative posture: a tighter ceiling
        # than the shared MAX_STOP_LOSS used by other dynamic-trailing algos.
        # ─────────────────────────────
        existing_stop_loss = self.active_bot.stop_loss
        if existing_stop_loss > 0:
            stop_loss = clamp(
                existing_stop_loss, self.MRF_MIN_STOP_LOSS, self.MRF_MAX_STOP_LOSS
            )
        else:
            atr_pct = self._atr_pct(current_price)
            stop_loss = (
                self.MRF_MAX_STOP_LOSS
                if atr_pct is None
                else clamp(
                    self.MRF_ATR_SL_MULTIPLIER * atr_pct,
                    self.MRF_MIN_STOP_LOSS,
                    self.MRF_MAX_STOP_LOSS,
                )
            )

        # ─────────────────────────────
        # RSI thesis-invalidation: tighten early, never widen.
        # ─────────────────────────────
        if self._mean_reversion_fade_invalidated(current_price, direction):
            entry_price = self.active_bot.deal.opening_price
            adverse_move_pct = (
                ((entry_price - current_price) / entry_price) * 100 * direction
            )
            early_stop_loss = clamp(
                max(adverse_move_pct, self.MRF_MIN_STOP_LOSS),
                self.MRF_MIN_STOP_LOSS,
                stop_loss,
            )
            if early_stop_loss < stop_loss:
                stop_loss = early_stop_loss
                self.active_bot.add_log(
                    "[mean_reversion_fade] thesis invalidation: RSI resumed "
                    "moving against the position within the first "
                    f"{self.MRF_INVALIDATION_BARS} bars; tightening stop_loss "
                    f"to {stop_loss:.2f}% for an early, smaller exit."
                )

        # ─────────────────────────────
        # BB-derived take-profit / trailing (re-derived each tick,
        # direction-agnostic) — required so the mid-band reversion target
        # is actually enforced, not just described.
        # ─────────────────────────────
        bb_metrics = self.build_bb_metrics()
        if bb_metrics:
            top_spread, bottom_spread = bb_metrics
            trailing_profit = clamp(
                top_spread, self.MIN_TRAILING_PROFIT, self.MAX_TRAILING_PROFIT
            )
            trailing_deviation = clamp(
                bottom_spread,
                self.MIN_TRAILING_DEVIATION,
                self.MAX_TRAILING_DEVIATION,
            )
            max_deviation = min(
                self.MAX_TRAILING_DEVIATION, trailing_profit - self.MIN_TRAIL_GAP
            )
            trailing_deviation = clamp(
                trailing_deviation, self.MIN_TRAILING_DEVIATION, max_deviation
            )
        else:
            trailing_profit = (
                self.active_bot.trailing_profit
                if self.active_bot.trailing_profit > 0
                else 2.3
            )
            trailing_deviation = (
                self.active_bot.trailing_deviation
                if self.active_bot.trailing_deviation > 0
                else 1.63
            )

        self.active_bot.stop_loss = round_numbers(stop_loss, 2)
        self.active_bot.trailing_profit = round_numbers(trailing_profit, 2)
        self.active_bot.trailing_deviation = round_numbers(trailing_deviation, 2)

        if (
            self.active_bot.stop_loss != original_bot.stop_loss
            or self.active_bot.trailing_profit != original_bot.trailing_profit
            or self.active_bot.trailing_deviation != original_bot.trailing_deviation
        ):
            self.active_bot = self.update_parameters()
            self.controller.save(data=self.active_bot)

    def market_trailing_analytics(
        self,
        current_price: float,
    ) -> None:
        """
        ApexFlow-aware trailing manager. Works for both long and short futures
        positions — the direction multiplier flips which side of the band
        feeds trailing_profit vs trailing_deviation and which trend direction
        counts as "favourable" for the tightening schedule; the downstream
        exit() already applies the same direction multiplier when placing
        orders.

        Philosophy:
        1. Initiates PositionMarket (abstraction layer to reduce complexity of KucoinPositionDeal)
        - stop_loss = emergency only
        - trailing_deviation = active stop after trailing
        - trailing_profit = trigger, never exit
        """
        if self._is_recovery_bot():
            return

        self.apex_flow_closing = ApexFlowClose(self.df, self.btc_df)

        # Strategy-specific dispatch: bb_extreme_reversion bots use ATR-based
        # SL instead of the BB-derived path below.
        if self.active_bot.name == self.BB_EXTREME_REVERSION_ALGO:
            return self.bb_extreme_reversion_trailing_analytics(current_price)
        if self.active_bot.name == self.MEAN_REVERSION_FADE_ALGO:
            return self.mean_reversion_fade_trailing_analytics(current_price)

        original_bot = deepcopy(self.active_bot)
        if (
            self.active_bot.market_type != MarketType.FUTURES
            or self.active_bot.position not in {Position.long, Position.short}
            or self.active_bot.deal.opening_price <= 0
        ):
            return

        direction = self._direction_multiplier()

        # ─────────────────────────────
        # Bollinger spreads
        # ─────────────────────────────
        bb_metrics = self.build_bb_metrics()
        if not bb_metrics:
            return
        top_spread, bottom_spread = bb_metrics

        # ─────────────────────────────
        # Profit
        # ─────────────────────────────
        bot_profit = self.base_streaming.compute_single_bot_profit(
            self.active_bot, current_price
        )

        # ─────────────────────────────
        # ApexFlow detectors
        # ─────────────────────────────
        row = self.apex_flow_closing.df.iloc[-1]
        detectors = self.apex_flow_closing.get_detectors()

        vce_signal = detectors.get("vce", False)
        mcd_signal = detectors.get("mcd", False)
        lcrs_signal = detectors.get("lcrs", False)

        expansion_range = row["high"] - row["low"]
        is_aggressive_momo = self.active_bot.name.lower().find("aggressive momo") != -1

        # ─────────────────────────────
        # Trend filter (only for tightening)
        # ─────────────────────────────
        ema_fast, ema_slow = self.apex_flow_closing.get_trend_ema()
        trend_up = ema_fast > ema_slow if ema_fast and ema_slow else True
        # The favourable trend for a short is down, not up.
        trend_favorable = trend_up if direction > 0 else not trend_up

        # ─────────────────────────────
        # Expansion multiplier
        # ─────────────────────────────
        expansion_multiplier = 1.0
        if vce_signal:
            expansion_multiplier += 0.2
        if mcd_signal:
            expansion_multiplier += 0.1
        expansion_multiplier = min(expansion_multiplier, 1.5)

        # ─────────────────────────────
        # Trailing tightening schedule
        # ─────────────────────────────
        if bot_profit < 2:
            trail_tighten_mult = 1.0
        elif bot_profit < 5:
            trail_tighten_mult = 0.7
        else:
            trail_tighten_mult = 0.45

        # Do not tighten against trend while signals are alive
        if (vce_signal or mcd_signal or lcrs_signal) and trend_favorable:
            trail_tighten_mult = max(trail_tighten_mult, 0.7)

        # ─────────────────────────────
        # Apply strategy-specific logic
        # ─────────────────────────────
        stop_loss, trailing_profit, trailing_deviation = (
            self.derive_dynamic_trailing_params(
                top_spread=top_spread,
                bottom_spread=bottom_spread,
                bot_profit=bot_profit,
                expansion_multiplier=expansion_multiplier,
                is_aggressive_momo=is_aggressive_momo,
                expansion_range=expansion_range,
                trail_tighten_mult=trail_tighten_mult,
                current_price=current_price,
                direction=direction,
            )
        )
        self.active_bot.stop_loss = stop_loss
        self.active_bot.trailing_profit = trailing_profit
        self.active_bot.trailing_deviation = trailing_deviation

        # ─────────────────────────────
        # Persist only if changed
        # ─────────────────────────────
        if (
            self.active_bot.trailing_profit != original_bot.trailing_profit
            or self.active_bot.trailing_deviation != original_bot.trailing_deviation
            or self.active_bot.stop_loss != original_bot.stop_loss
        ):
            self.active_bot = self.update_parameters()
            self.controller.save(data=self.active_bot)
