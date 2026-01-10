import logging
from datetime import datetime
from typing import Type, Union

import pandas as pd
from streaming.apex_flow_closing import ApexFlowClose
from deals.gateway import DealGateway
from bots.models import BotModel
from databases.crud.autotrade_crud import AutotradeCrud
from databases.crud.bot_crud import BotTableCrud
from databases.crud.candles_crud import CandlesCrud
from databases.tables.bot_table import BotTable, PaperTradingTable
from databases.crud.paper_trading_crud import PaperTradingTableCrud
from databases.crud.symbols_crud import SymbolsCrud
from exchange_apis.binance.base import BinanceApi
from exchange_apis.kucoin.base import KucoinApi
from streaming.models import HABollinguerSpread
from pybinbot import (
    Status,
    Strategy,
    ExchangeId,
    round_numbers,
    BinanceKlineIntervals,
    Indicators,
)
from tools.exceptions import BinanceErrors, BinbotErrors
from copy import deepcopy


class BaseStreaming:
    """
    Static data that doesn't change often, loaded once on startup
    and used across the application
    """

    def __init__(self) -> None:
        self.binance_api = BinanceApi()
        self.kucoin_api = KucoinApi()
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


class StreamingController:
    def __init__(self, base: BaseStreaming, symbol: str) -> None:
        super().__init__()
        # Gets any signal to restart streaming
        self.autotrade_controller = AutotradeCrud()
        self.symbol_data = base.symbols_crud.get_symbol(symbol)
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
        self.df, _, _ = Indicators().pre_process(
            exchange=self.base_streaming.exchange, candles=candles
        )
        self.btc_df, _, _ = Indicators().pre_process(
            exchange=self.base_streaming.exchange, candles=self.btc_klines.copy()
        )

        self.df = Indicators.bollinguer_spreads(self.df)
        self.btc_df = Indicators.bollinguer_spreads(self.btc_df, window=20)

        self.df = Indicators().post_process(self.df)
        self.btc_df = Indicators().post_process(self.btc_df)

    def calc_quantile_volatility(
        self, window: int = 100, quantile: float = 0.9
    ) -> float:
        """
        Calculate rolling quantile-based volatility for stop loss adaptation.
        Returns the specified quantile of rolling absolute returns over the window.
        Uses absolute returns instead of log returns, larger window, and higher quantile.
        """
        if not self.klines or len(self.klines) < window:
            return 0.0

        # Extract close prices from klines
        close_prices = [float(k[4]) for k in self.klines[-window:]]
        prices = pd.Series(close_prices)

        # Use absolute returns instead of log returns
        abs_returns = prices.pct_change().abs().dropna()
        if len(abs_returns) < 5:
            return 0.0
        rolling_vol = (
            abs_returns.rolling(window=min(40, len(abs_returns) // 2)).mean().dropna()
        )
        if len(rolling_vol) < 5:
            return 0.0
        quantile_value = float(rolling_vol.quantile(quantile))
        return quantile_value

    def process_klines(self) -> None:
        """
        Updates deals with klines websockets,
        when price and symbol match existent deal
        """
        symbol = self.symbol
        logging.info(f"Processing klines for {symbol}")
        close_price = float(self.klines[-1][4])
        open_price = float(self.klines[-1][1])
        converted_symbol = symbol.replace("-", "")

        if converted_symbol in self.base_streaming.active_bot_pairs:
            current_bot = self.base_streaming.get_current_bot(converted_symbol)
            current_test_bot = self.base_streaming.get_current_test_bot(
                converted_symbol
            )

            try:
                if current_bot:
                    deal = DealGateway(bot=current_bot, db_table=BotTable)
                    deal.deal_updates(
                        close_price,
                        open_price,
                    )
                elif current_test_bot:
                    deal = DealGateway(bot=current_test_bot, db_table=PaperTradingTable)
                    deal.deal_updates(
                        close_price,
                        open_price,
                    )
                else:
                    return

            except BinanceErrors as error:
                if error.code in (-2010, -1013):
                    if current_bot:
                        bot = current_bot
                    elif current_test_bot:
                        bot = current_test_bot
                    else:
                        return

                    bot.add_log(error.message)
                    bot.status = Status.error
                    deal.save(bot)

        return

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

    def update_bots_parameters(
        self,
        bot: BotModel,
        db_table: Type[Union[PaperTradingTable, BotTable]],
        current_price: float,
        bb_spreads: HABollinguerSpread,
    ) -> None:
        """
        ApexFlow-aware asymmetric trailing:
        - Trailing deviation and stop loss adapt geometrically based on PnL
        - Trailing profit expands if ApexFlow detects volatility/momentum expansion
        - Detector signals prevent premature exit while keeping stop geometry safe
        """
        controller: Union[PaperTradingTableCrud, BotTableCrud] = (
            self.base_streaming.bot_controller
            if db_table == BotTable
            else self.base_streaming.paper_trading_controller
        )

        original_bot = deepcopy(bot)

        # --- Compute quantile-based volatility for stop loss ---
        quantile_vol = self.calc_quantile_volatility(window=40, quantile=0.99)
        if quantile_vol == 0:
            quantile_vol = 0.03  # fallback 3%

        # --- Bollinger spreads ---
        if bb_spreads.bb_high == 0 or bb_spreads.bb_low == 0 or bb_spreads.bb_mid == 0:
            return

        top_spread = round_numbers(
            abs((bb_spreads.bb_high - bb_spreads.bb_mid) / bb_spreads.bb_high) * 100, 2
        )
        whole_spread = round_numbers(
            abs((bb_spreads.bb_high - bb_spreads.bb_low) / bb_spreads.bb_high) * 100, 2
        )
        bottom_spread = round_numbers(
            abs((bb_spreads.bb_mid - bb_spreads.bb_low) / bb_spreads.bb_mid) * 100, 2
        )

        # Clamp spreads to sane ranges
        whole_spread = min(max(whole_spread, 2), 8)
        top_spread = min(max(top_spread, 1.5), 6)
        bottom_spread = min(max(bottom_spread, 1), 4)

        # --- Compute current profit ---
        bot_profit = self.compute_single_bot_profit(bot, current_price)

        # --- ApexFlow Detector Check ---
        detectors = self.apex_flow_closing.get_detectors()
        vce_signal = detectors.get("vce", False)
        mcd_signal = detectors.get("mcd", False)
        lcrs_signal = detectors.get("lcrs", False)

        # --- Trend filter (EMA fast/slow) ---
        ema_fast, ema_slow = self.apex_flow_closing.get_trend_ema()
        trend_up = ema_fast > ema_slow if ema_fast and ema_slow else True

        # Determine if Apex allows exit
        if bot.strategy == Strategy.long:
            detector_exit_flag = (
                not (vce_signal or mcd_signal or lcrs_signal) or not trend_up
            )
        else:
            detector_exit_flag = (
                not (vce_signal or mcd_signal or lcrs_signal) or trend_up
            )

        # --- Expansion-aware multiplier ---
        expansion_multiplier = 1.0
        if vce_signal:
            expansion_multiplier += 0.2
        if mcd_signal:
            expansion_multiplier += 0.1
        expansion_multiplier = min(expansion_multiplier, 1.5)

        # --- Asymmetric geometry: tighten for profits, protect losses ---
        # Compute geometric multiplier for trailing deviation based on PnL
        trail_tighten_mult = 1.0
        if bot_profit > 0:
            trail_tighten_mult = max(0.6, 1.0 - (bot_profit / 100))  # tighten for gains
        else:
            trail_tighten_mult = 1.0  # leave room for losses

        # --- Adjust trailing parameters ---
        bot.trailling = True
        if bot.strategy == Strategy.long:
            bot.trailling_profit = round_numbers(
                max(0.5, top_spread * trail_tighten_mult * expansion_multiplier), 2
            )
            bot.trailling_deviation = round_numbers(
                max(0.6, bottom_spread * trail_tighten_mult), 2
            )
            bot.stop_loss = round_numbers(
                max(3.0, min(quantile_vol * 100 * trail_tighten_mult, 7.0)), 2
            )

        elif bot.strategy == Strategy.margin_short:
            bot.trailling_profit = round_numbers(
                max(0.5, bottom_spread * trail_tighten_mult * expansion_multiplier), 2
            )
            bot.trailling_deviation = round_numbers(
                max(0.6, top_spread * trail_tighten_mult), 2
            )
            bot.stop_loss = round_numbers(
                max(3.0, min(quantile_vol * 100 * trail_tighten_mult, 7.0)), 2
            )

        # --- Force trailing & stop to be outside current price if Apex blocks exit ---
        if not detector_exit_flag:
            if bot.strategy == Strategy.long:
                # move stop below current price and trailing deviation above price
                bot.stop_loss = max(
                    bot.stop_loss, abs(bot.stop_loss + (current_price - bot.stop_loss))
                )
                bot.trailling_deviation = max(
                    bot.trailling_deviation,
                    abs(
                        bot.trailling_deviation
                        + (current_price - bot.trailling_deviation)
                    ),
                )
            else:
                bot.stop_loss = max(
                    bot.stop_loss, abs(bot.stop_loss - (current_price - bot.stop_loss))
                )
                bot.trailling_deviation = max(
                    bot.trailling_deviation,
                    abs(
                        bot.trailling_deviation
                        - (current_price - bot.trailling_deviation)
                    ),
                )

        # --- Save only if changed ---
        if (
            bot.trailling_profit != original_bot.trailling_profit
            or bot.trailling_deviation != original_bot.trailling_deviation
            or bot.stop_loss != original_bot.stop_loss
        ):
            controller.save(bot)
            deal = DealGateway(bot, db_table=db_table)
            # Only open/reopen deal if Apex allows exit
            if detector_exit_flag:
                deal.open_deal()

    def dynamic_trailling(self) -> None:
        """
        Update bot with dynamic trailling enabled to update
        take_profit and trailling according to bollinguer bands
        dynamic movements in the market
        """
        symbol = self.symbol
        close_price = float(self.klines[-1][4])
        converted_symbol = symbol.replace("-", "")

        # Check if it matches any active bots
        self.load_current_bots(converted_symbol)

        bb_spreads = self.build_bb_spreads()

        if self.current_bot and self.current_bot.dynamic_trailling:
            self.update_bots_parameters(
                bot=self.current_bot,
                bb_spreads=bb_spreads,
                db_table=BotTable,
                current_price=close_price,
            )

        if self.current_test_bot and self.current_test_bot.dynamic_trailling:
            self.update_bots_parameters(
                bot=self.current_test_bot,
                bb_spreads=bb_spreads,
                db_table=PaperTradingTable,
                current_price=close_price,
            )
        pass
