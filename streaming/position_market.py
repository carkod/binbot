from time import time
from typing import Union

from kucoin_universal_sdk.generate.futures.positions.model_get_position_details_resp import (
    GetPositionDetailsResp,
)
from pybinbot import (
    BinanceApi,
    BotModel,
    Candles,
    ExchangeId,
    HABollinguerSpread,
    Indicators,
    KucoinApi,
    KucoinFutures,
    Status,
    convert_to_kucoin_symbol,
    round_numbers,
)

from api.exchange_apis.kucoin.futures.futures_deal import KucoinPositionDeal
from api.tools.utils import clamp
from streaming.base import BaseStreaming


class PositionMarket:
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

    def __init__(
        self,
        execution: KucoinPositionDeal,
        api: Union[BinanceApi, KucoinApi, KucoinFutures],
        symbol: str,
        base_streaming: BaseStreaming,
    ) -> None:
        self.execution = execution
        self.api = api
        self.symbol = symbol
        self.base_streaming = base_streaming
        self.symbol_data = base_streaming.symbols_crud.get_symbol(symbol)
        self.qty_precision = self.symbol_data.qty_precision
        self.klines: list = []
        self.btc_klines: list = []

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
        entry_price = self.execution.active_bot.deal.opening_price
        entry_timestamp = self.execution.active_bot.deal.opening_timestamp
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
        trail_tighten_mult: float,
        current_price: float,
        direction: int = 1,
        initial_stop_loss: float = 3.0,
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
        existing_stop_loss = self.execution.active_bot.stop_loss
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
            stop_loss = initial_stop_loss
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
        if self.execution.active_bot.deal.base_order_size > 0:
            old_size = self.execution.active_bot.deal.base_order_size
            old_commissions = self.execution.active_bot.deal.total_commissions
            if position is None:
                kucoin_symbol = convert_to_kucoin_symbol(self.execution.active_bot)
                position = self.base_streaming.kucoin_futures_api.get_futures_position(
                    kucoin_symbol
                )
            # position.current_qty can be positive or negative depending on the strategy
            if position and abs(int(position.current_qty)) > 0:
                new_size = round_numbers(
                    abs(int(position.current_qty)), self.qty_precision
                )
                if new_size != old_size:
                    self.execution.active_bot.deal.base_order_size = new_size
                    self.execution.active_bot.add_log(
                        f"Position size updated from system. Old size: {old_size}, new size: {new_size}."
                    )

                if old_commissions != float(position.current_comm):
                    self.execution.active_bot.deal.total_commissions = float(
                        position.current_comm
                    )
                self.execution.controller.save(data=self.execution.active_bot)
            else:
                # Only backfill for active bots — pending/inactive/completed bots
                # have no live position to reconcile and must never be marked error
                # here (e.g. an expired→inactive bot still has base_order_size > 0).
                if self.execution.active_bot.status != Status.active:
                    return self.execution.active_bot
                # Grace window: the position endpoint lags the order fill by up to
                # one candle interval. Skipping backfill during this window prevents
                # a false error on the same tick the entry fills.
                now_ms = int(time() * 1000)
                grace_ms = self.base_streaming.interval.get_ms()
                if (
                    self.execution.active_bot.deal.opening_timestamp > 0
                    and (now_ms - self.execution.active_bot.deal.opening_timestamp)
                    < grace_ms
                ):
                    self.execution.active_bot.add_log(
                        "Position not yet propagated to exchange endpoint; "
                        "within entry grace window. Skipping backfill."
                    )
                    self.execution.controller.save(data=self.execution.active_bot)
                    return self.execution.active_bot
                self.execution.active_bot = (
                    self.execution.backfill_position_from_fills()
                )
                self.execution.controller.save(data=self.execution.active_bot)

        return self.execution.active_bot
