import logging
from datetime import datetime
from typing import Type, Union

from streaming.apex_flow_closing import ApexFlowClose
from deals.gateway import DealGateway
from bots.models import BotModel
from databases.crud.autotrade_crud import AutotradeCrud
from databases.crud.bot_crud import BotTableCrud
from databases.crud.candles_crud import CandlesCrud
from databases.tables.bot_table import BotTable, PaperTradingTable
from databases.crud.paper_trading_crud import PaperTradingTableCrud
from databases.crud.symbols_crud import SymbolsCrud
from pybinbot import (
    Status,
    Strategy,
    ExchangeId,
    round_numbers,
    BinanceKlineIntervals,
    Indicators,
    HeikinAshi,
    BinanceErrors,
    BinbotErrors,
    BinanceApi,
    KucoinApi,
    HABollinguerSpread,
)
from copy import deepcopy
from tools.config import Config


class BaseStreaming:
    """
    Static data that doesn't change often, loaded once on startup
    and used across the application
    """

    def __init__(self) -> None:
        self.config = Config()
        self.binance_api = BinanceApi(
            key=self.config.binance_key, secret=self.config.binance_secret
        )
        self.kucoin_api = KucoinApi(
            key=self.config.kucoin_key,
            secret=self.config.kucoin_secret,
            passphrase=self.config.kucoin_passphrase,
        )
        self.bot_controller = BotTableCrud()
        self.paper_trading_controller = PaperTradingTableCrud()
        self.symbols_crud = SymbolsCrud()
        self.cs = CandlesCrud()
        self.autotrade_crud = AutotradeCrud()
        self.autotrade_settings = self.autotrade_crud.get_settings()
        self.exchange = self.autotrade_settings.exchange_id
        # Always have it active
        self.active_bot_pairs: list = self.get_all_active_pairs()

    def get_all_active_pairs(self) -> list:
        """
        Reused by children classes
        so it needs to be reassigned to self.active_bot_pairs
        """
        bot_active_pairs = list(self.bot_controller.get_active_pairs())
        paper_trading_active_pairs = list(
            self.paper_trading_controller.get_active_pairs()
        )
        active_pairs = list(set(bot_active_pairs + paper_trading_active_pairs))
        active_pairs.extend(["BTCUSDC", "ETHUSDC"])
        self.active_bot_pairs = active_pairs
        return active_pairs

    def get_current_bot(self, symbol: str) -> BotModel | None:
        try:
            current_bot = self.bot_controller.get_one(
                symbol=symbol, status=Status.active
            )
            bot = BotModel.dump_from_table(current_bot)
            return bot
        except BinbotErrors:
            bot = None
            return bot

    def get_current_test_bot(self, symbol: str) -> BotModel | None:
        try:
            current_test_bot = self.paper_trading_controller.get_one(
                symbol=symbol, status=Status.active
            )
            bot = BotModel.dump_from_table(current_test_bot)
            return bot
        except BinbotErrors:
            bot = None
            return bot


class PositionManager:
    def __init__(self, base: BaseStreaming, symbol: str) -> None:
        super().__init__()
        # Gets any signal to restart streaming
        self.autotrade_controller = AutotradeCrud()
        self.symbol_data = base.symbols_crud.get_symbol(symbol)
        self.price_precision = self.symbol_data.price_precision
        self.base_streaming = base
        self.symbol = symbol
        self.benchmark_symbol = "BTCUSDT"
        self.kucoin_benchmark_symbol = "BTC-USDT"
        self.api: Union[BinanceApi, KucoinApi]

        binance_interval = BinanceKlineIntervals.fifteen_minutes
        # Prepare interval based on exchange
        if self.base_streaming.exchange == ExchangeId.KUCOIN:
            self.interval = binance_interval.to_kucoin_interval()
            self.symbol = (
                self.symbol_data.base_asset + "-" + self.symbol_data.quote_asset
            )
            self.api = self.base_streaming.kucoin_api
        else:
            self.interval = binance_interval.value
            self.api = self.base_streaming.binance_api

        self.current_bot: BotModel | None = None
        self.current_test_bot: BotModel | None = None
        self.dataframe_ops(self.interval)
        self.apex_flow_closing = ApexFlowClose(self.df, self.btc_df)

    def dataframe_ops(self, interval: str) -> None:
        """
        Converts klines to DataFrame for indicator calculations
        """

        # Get klines from the appropriate exchange
        self.klines = self.api.get_ui_klines(
            symbol=self.symbol,
            interval=interval,
        )
        self.btc_klines = self.api.get_ui_klines(
            symbol=self.kucoin_benchmark_symbol
            if self.base_streaming.exchange == ExchangeId.KUCOIN
            else self.benchmark_symbol,
            interval=interval,
        )
        candles = self.klines.copy()
        df, _, _ = HeikinAshi().pre_process(
            exchange=self.base_streaming.exchange, candles=candles
        )
        self.df = df
        btc_df, _, _ = HeikinAshi().pre_process(
            exchange=self.base_streaming.exchange, candles=self.btc_klines.copy()
        )
        self.btc_df = btc_df

        self.df = Indicators.bollinguer_spreads(self.df)
        self.btc_df = Indicators.bollinguer_spreads(self.btc_df, window=20)

        self.df = HeikinAshi().post_process(self.df)
        self.btc_df = HeikinAshi().post_process(self.btc_df)

    def load_current_bots(self, symbol: str) -> None:
        try:
            current_bot_payload = self.base_streaming.get_current_bot(symbol)
            if current_bot_payload:
                self.current_bot = BotModel.model_validate(current_bot_payload)

            current_test_bot_payload = self.base_streaming.get_current_test_bot(symbol)
            if current_test_bot_payload:
                self.current_test_bot = BotModel.model_validate(
                    current_test_bot_payload
                )

        except ValueError:
            pass
        except Exception as e:
            logging.error(e)
            pass

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

    def get_interests_short_margin(self, bot: BotModel) -> tuple[float, float, float]:
        close_timestamp = bot.deal.closing_timestamp
        if close_timestamp == 0:
            close_timestamp = int(datetime.now().timestamp() * 1000)

        asset = bot.pair.split(bot.fiat)[0]
        interest_details = self.base_streaming.binance_api.get_interest_history(
            asset=asset, symbol=bot.pair
        )

        if len(interest_details["rows"]) > 0:
            interests = float(interest_details["rows"][0]["interests"])
        else:
            interests = 0

        close_total = bot.deal.closing_price
        open_total = bot.deal.closing_price

        return interests, open_total, close_total

    def compute_single_bot_profit(self, bot: BotModel, current_price: float) -> float:
        if bot.deal and bot.deal.base_order_size > 0:
            price = (
                bot.deal.closing_price if bot.deal.closing_price > 0 else current_price
            )
            if bot.deal.opening_price > 0:
                buy_price = bot.deal.opening_price
                profit_change = ((price - buy_price) / buy_price) * 100
                if price == 0:
                    profit_change = 0
                return round_numbers(profit_change)
            elif bot.deal.opening_price > 0:
                # Completed margin short
                if bot.deal.closing_price > 0:
                    interests, open_total, close_total = (
                        self.get_interests_short_margin(bot)
                    )
                    profit_change = (
                        (open_total - close_total) / open_total - interests
                    ) * 100
                    return round(profit_change, 2)
                else:
                    # Not completed margin short
                    close_price = (
                        bot.deal.closing_price
                        if bot.deal.closing_price > 0
                        else current_price or bot.deal.current_price
                    )
                    if close_price == 0:
                        return 0
                    interests, open_total, close_total = (
                        self.get_interests_short_margin(bot)
                    )
                    profit_change = (
                        (open_total - close_price) / open_total - interests
                    ) * 100
                    return round(profit_change, 2)
            else:
                return 0
        else:
            return 0

    def set_long_trail_params(
        self,
        top_spread: float,
        bottom_spread: float,
        bot_profit: float,
        bot: BotModel,
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

        bot.trailling_profit = round_numbers(max(0.6, raw_trail_profit), 2)
        bot.trailling_deviation = round_numbers(
            max(0.6, bottom_spread * trail_tighten_mult),
            2,
        )

        if bot.stop_loss == 0:
            if is_aggressive_momo:
                bot.stop_loss = round_numbers(
                    bot.deal.opening_price - (expansion_range * 0.5),
                    self.symbol_data.price_precision,
                )
            else:
                bot.stop_loss = round_numbers(
                    bot.deal.opening_price * (1 - 0.03),
                    self.symbol_data.price_precision,
                )

    def market_trailing_analytics(
        self,
        bot: BotModel,
        db_table: Type[Union[PaperTradingTable, BotTable]],
        current_price: float,
    ) -> None:
        """
        ApexFlow-aware trailing manager.

        Philosophy:
        - stop_loss = emergency only
        - trailing_deviation = active stop after trailing
        - trailing_profit = trigger, never exit
        """

        controller = (
            self.base_streaming.bot_controller
            if db_table == BotTable
            else self.base_streaming.paper_trading_controller
        )

        original_bot = deepcopy(bot)

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
        bot_profit = self.compute_single_bot_profit(bot, current_price)

        # ─────────────────────────────
        # ApexFlow detectors
        # ─────────────────────────────
        row = self.apex_flow_closing.df.iloc[-1]
        detectors = self.apex_flow_closing.get_detectors()

        vce_signal = detectors.get("vce", False)
        mcd_signal = detectors.get("mcd", False)
        lcrs_signal = detectors.get("lcrs", False)

        expansion_range = row["high"] - row["low"]
        is_aggressive_momo = bot.name.lower().find("aggressive momo") != -1

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
        if bot.strategy == Strategy.long:
            self.set_long_trail_params(
                top_spread=top_spread,
                bottom_spread=bottom_spread,
                bot_profit=bot_profit,
                bot=bot,
                expansion_multiplier=expansion_multiplier,
                is_aggressive_momo=is_aggressive_momo,
                expansion_range=expansion_range,
                trail_tighten_mult=trail_tighten_mult,
            )

        # ─────────────────────────────
        # Persist only if changed
        # ─────────────────────────────
        if (
            bot.trailling_profit != original_bot.trailling_profit
            or bot.trailling_deviation != original_bot.trailling_deviation
            or bot.stop_loss != original_bot.stop_loss
        ):
            controller.save(bot)

    def process_deal(self) -> None:
        """
        Updates deals with klines websockets,
        when price and symbol match existent deal
        """
        symbol = self.symbol
        close_price = float(self.klines[-1][4])
        open_price = float(self.klines[-1][1])
        converted_symbol = symbol.replace("-", "")

        if converted_symbol in self.base_streaming.active_bot_pairs:
            self.current_bot = self.base_streaming.get_current_bot(converted_symbol)
            self.current_test_bot = self.base_streaming.get_current_test_bot(
                converted_symbol
            )

            try:
                if self.current_bot:
                    if self.current_bot.dynamic_trailling:
                        self.market_trailing_analytics(
                            bot=self.current_bot,
                            db_table=BotTable,
                            current_price=close_price,
                        )
                    deal = DealGateway(bot=self.current_bot, db_table=BotTable)
                    deal.deal_exit_orchestration(
                        close_price,
                        open_price,
                    )
                elif self.current_test_bot:
                    if self.current_test_bot.dynamic_trailling:
                        self.market_trailing_analytics(
                            bot=self.current_test_bot,
                            db_table=PaperTradingTable,
                            current_price=close_price,
                        )
                    deal = DealGateway(
                        bot=self.current_test_bot, db_table=PaperTradingTable
                    )
                    deal.deal_exit_orchestration(
                        close_price,
                        open_price,
                    )
                else:
                    return

            except BinanceErrors as error:
                if error.code in (-2010, -1013):
                    if self.current_bot:
                        bot = self.current_bot
                    elif self.current_test_bot:
                        bot = self.current_test_bot
                    else:
                        return

                    bot.add_log(error.message)
                    bot.status = Status.error
                    deal.save(bot)

        return
