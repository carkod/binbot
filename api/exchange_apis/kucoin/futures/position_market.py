from copy import deepcopy
from typing import Type, Union
from bots.models import BotModel
from databases.tables.bot_table import BotTable, PaperTradingTable
from exchange_apis.kucoin.futures.futures_deal import KucoinPositionDeal
from pybinbot import (
    BinanceApi,
    Candles,
    ExchangeId,
    HABollinguerSpread,
    Indicators,
    KucoinApi,
    KucoinFutures,
    MarketType,
    Position,
    convert_to_kucoin_symbol,
    round_numbers,
)
from tools.utils import clamp
from streaming.apex_flow_closing import ApexFlowClose
from streaming.base import BaseStreaming


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

    def __init__(
        self,
        api: Union[BinanceApi, KucoinApi, KucoinFutures],
        bot: BotModel,
        symbol: str,
        base_streaming: BaseStreaming,
        db_table: Type[BotTable] | Type[PaperTradingTable],
    ) -> None:
        super().__init__(bot=bot, db_table=db_table)
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
        entry_price = float(self.active_bot.deal.opening_price or 0)
        entry_timestamp = int(self.active_bot.deal.opening_timestamp or 0)
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
    ) -> tuple[float, float, float]:
        """
        LONG trailing logic.

        Rules:
        - stop_loss is a fixed safety net (handled elsewhere, never trailed)
        - trailing_profit is a ceiling trigger only
        - trailing_deviation is the real stop once trailing starts
        """
        raw_trail_profit = top_spread * trail_tighten_mult * expansion_multiplier

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
            bottom_spread * trail_tighten_mult,
            self.MIN_TRAILING_DEVIATION,
            self.MAX_TRAILING_DEVIATION,
        )

        opening_price = float(self.active_bot.deal.opening_price or 0)
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
                stop_loss += 0.25
                trailing_profit += 0.25
                trailing_deviation += 0.05
            elif pullback_pct >= self.DEEP_PULLBACK:
                stop_loss -= 0.50
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
        self.btc_klines = self.api.get_ui_klines(
            symbol=self.base_streaming.kucoin_benchmark_symbol
            if self.base_streaming.exchange == ExchangeId.KUCOIN
            else self.base_streaming.benchmark_symbol,
            interval=str(self.base_streaming.interval.value),
        )

        raw_candles = Candles(
            exchange=self.base_streaming.exchange,
            candles=self.klines.copy(),
        )
        self.df = raw_candles.pre_process()

        raw_btc_candles = Candles(
            exchange=self.base_streaming.exchange,
            candles=self.btc_klines.copy(),
        )
        self.btc_df = raw_btc_candles.pre_process()

        self.df = Indicators.bollinguer_spreads(self.df)
        self.btc_df = Indicators.bollinguer_spreads(self.btc_df, window=20)

        self.df = raw_candles.post_process(self.df)
        self.btc_df = raw_btc_candles.post_process(self.btc_df)

        return self.klines, self.btc_klines

    def position_updates(self) -> BotModel:
        """
        Due to ADL, position size (number of contracts can change)
        Therefore we need to keep base_order_size up to date at all times, so that exit execution can succeed with correct qty
        """
        if self.active_bot.deal.base_order_size > 0:
            old_size = self.active_bot.deal.base_order_size
            old_commissions = self.active_bot.deal.total_commissions
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
                self.active_bot = self.backfill_position_from_fills()
                self.controller.save(data=self.active_bot)

        return self.active_bot

    def market_trailing_analytics(
        self,
        current_price: float,
    ) -> None:
        """
        ApexFlow-aware trailing manager.

        Philosophy:
        1. Initiates PositionMarket (abstraction layer to reduce complexity of KucoinPositionDeal)
        - stop_loss = emergency only
        - trailing_deviation = active stop after trailing
        - trailing_profit = trigger, never exit
        """
        self.apex_flow_closing = ApexFlowClose(self.df, self.btc_df)

        original_bot = deepcopy(self.active_bot)
        market_type = getattr(
            self.active_bot.market_type, "value", self.active_bot.market_type
        )
        position = getattr(self.active_bot.position, "value", self.active_bot.position)
        if (
            str(market_type).lower() != MarketType.FUTURES.value.lower()
            or str(position).lower() != Position.long.value.lower()
            or float(self.active_bot.deal.opening_price or 0) <= 0
        ):
            return

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
        if (vce_signal or mcd_signal or lcrs_signal) and trend_up:
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
