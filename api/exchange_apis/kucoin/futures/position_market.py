from pybinbot import (
    ExchangeId,
    round_numbers,
    BinanceApi,
    KucoinApi,
    HABollinguerSpread,
    Indicators,
    HeikinAshi,
    KucoinFutures,
)
from databases.tables.bot_table import BotTable, PaperTradingTable
from streaming.base import BaseStreaming
from bots.models import BotModel
from typing import Union, Type


class PositionMarket:
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
        self.api = api
        self.active_bot = bot
        self.symbol = symbol
        self.base_streaming = base_streaming
        self.db_table = db_table
        self.symbol_data = base_streaming.symbols_crud.get_symbol(symbol)

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

        self.active_bot.trailling_profit = round_numbers(max(0.6, raw_trail_profit), 2)
        self.active_bot.trailling_deviation = round_numbers(
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
        df, _, _ = HeikinAshi().pre_process(
            exchange=self.base_streaming.exchange, candles=candles
        )
        self.df = df
        btc_candles = self.btc_klines.copy()
        btc_df, _, _ = HeikinAshi().pre_process(
            exchange=self.base_streaming.exchange, candles=btc_candles
        )
        self.btc_df = btc_df

        self.df = Indicators.bollinguer_spreads(self.df)
        self.btc_df = Indicators.bollinguer_spreads(self.btc_df, window=20)

        self.df = HeikinAshi().post_process(self.df)
        self.btc_df = HeikinAshi().post_process(self.btc_df)

        return self.klines, self.btc_klines
