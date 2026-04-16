from copy import deepcopy
from typing import Type, Union

from bots.models import BotModel
from databases.tables.bot_table import BotTable, PaperTradingTable
from exchange_apis.kucoin.futures.futures_deal import KucoinPositionDeal
from pybinbot import (
    BinanceApi,
    ExchangeId,
    HABollinguerSpread,
    HeikinAshi,
    Indicators,
    KucoinApi,
    KucoinFutures,
    convert_to_kucoin_symbol,
    round_numbers,
)
from streaming.apex_flow_closing import ApexFlowClose
from streaming.base import BaseStreaming


class PositionMarket(KucoinPositionDeal):
    """
    Analytics for position deal exist
    """

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

    def set_trailing_params(
        self,
        top_spread: float,
        bottom_spread: float,
        bot_profit: float,
        expansion_multiplier: float,
        is_aggressive_momo: bool,
        expansion_range: float,
        trail_tighten_mult: float,
    ) -> None:
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

        self.active_bot.trailing_profit = round_numbers(max(0.6, raw_trail_profit), 2)
        self.active_bot.trailing_deviation = round_numbers(
            max(0.6, bottom_spread * trail_tighten_mult),
            2,
        )

        if self.active_bot.stop_loss == 0:
            if is_aggressive_momo:
                self.active_bot.stop_loss = round_numbers(
                    self.active_bot.deal.opening_price - (expansion_range * 0.5),
                    self.symbol_data.price_precision,
                )
            else:
                self.active_bot.stop_loss = round_numbers(
                    self.active_bot.deal.opening_price * (1 - 0.03),
                    self.symbol_data.price_precision,
                )

    def dataframe_ops(self) -> tuple[list, list]:
        """
        Converts klines to DataFrame for indicator calculations
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
        candles = self.klines.copy()
        df, _, _, _ = HeikinAshi().pre_process(
            exchange=self.base_streaming.exchange, candles=candles
        )
        self.df = df
        btc_candles = self.btc_klines.copy()
        btc_df, _, _, _ = HeikinAshi().pre_process(
            exchange=self.base_streaming.exchange, candles=btc_candles
        )
        self.btc_df = btc_df

        self.df = Indicators.bollinguer_spreads(self.df)
        self.btc_df = Indicators.bollinguer_spreads(self.btc_df, window=20)

        self.df = HeikinAshi().post_process(self.df)
        self.btc_df = HeikinAshi().post_process(self.btc_df)

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

        # ─────────────────────────────
        # Bollinger spreads
        # ─────────────────────────────
        bb_spreads = self.build_bb_spreads()
        if bb_spreads.bb_high == 0 or bb_spreads.bb_low == 0:
            return

        top_spread = (
            abs((bb_spreads.bb_high - bb_spreads.bb_mid) / bb_spreads.bb_high) * 100
        )
        bottom_spread = (
            abs((bb_spreads.bb_mid - bb_spreads.bb_low) / bb_spreads.bb_mid) * 100
        )

        top_spread = min(max(top_spread, 1.5), 6.0)
        bottom_spread = min(max(bottom_spread, 1.0), 4.0)

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
        self.set_trailing_params(
            top_spread=top_spread,
            bottom_spread=bottom_spread,
            bot_profit=bot_profit,
            expansion_multiplier=expansion_multiplier,
            is_aggressive_momo=is_aggressive_momo,
            expansion_range=expansion_range,
            trail_tighten_mult=trail_tighten_mult,
        )

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
