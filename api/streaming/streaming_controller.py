import logging
from datetime import datetime
from typing import Type, Union

import pandas as pd
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
from pybinbot.enum import Status, Strategy, ExchangeId
from tools.exceptions import BinanceErrors, BinbotErrors
from pybinbot.maths import round_numbers
from copy import deepcopy
from pybinbot.enum import BinanceKlineIntervals


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
        self.api: Union[BinanceApi, KucoinApi]

        binance_interval = BinanceKlineIntervals.fifteen_minutes
        # Prepare interval based on exchange
        if self.base_streaming.exchange == ExchangeId.KUCOIN:
            interval = binance_interval.to_kucoin_interval()
            self.symbol = (
                self.symbol_data.base_asset + "-" + self.symbol_data.quote_asset
            )
            self.api = self.base_streaming.kucoin_api
        else:
            interval = binance_interval.value
            self.api = self.base_streaming.binance_api

        # Get klines from the appropriate exchange
        self.klines = self.api.get_ui_klines(
            symbol=self.symbol,
            interval=interval,
        )
        self.current_bot: BotModel | None = None
        self.current_test_bot: BotModel | None = None

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

        df = pd.DataFrame(data)
        df.columns = [
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
        ] + [f"col_{i}" for i in range(7, len(df.columns))]

        close_prices = df["close"]
        rolling_mean = close_prices.rolling(window=20).mean()
        rolling_std = close_prices.rolling(window=20).std()

        df["bb_high"] = rolling_mean + (rolling_std * 2)
        df["bb_mid"] = rolling_mean
        df["bb_low"] = rolling_mean - (rolling_std * 2)

        df.reset_index(drop=True, inplace=True)

        bb_spreads = HABollinguerSpread(
            bb_high=df["bb_high"].iloc[-1],
            bb_mid=df["bb_mid"].iloc[-1],
            bb_low=df["bb_low"].iloc[-1],
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
        controller: Union[PaperTradingTableCrud | BotTableCrud] = (
            self.base_streaming.bot_controller
        )

        if db_table == PaperTradingTable:
            controller = self.base_streaming.paper_trading_controller

        # Avoid duplicate updates
        original_bot = deepcopy(bot)

        # --- Use quantile-based volatility for stop_loss only ---
        quantile_vol = self.calc_quantile_volatility(window=40, quantile=0.99)
        # fallback if not enough data
        if quantile_vol == 0:
            quantile_vol = 0.03  # 3% default

        # --- BB logic for trailing profit/deviation ---
        # not enough data
        if bb_spreads.bb_high == 0 or bb_spreads.bb_low == 0 or bb_spreads.bb_mid == 0:
            return

        # multiplied by 1000 to get to the same scale stop_loss
        top_spread = round_numbers(
            (abs((bb_spreads.bb_high - bb_spreads.bb_mid) / bb_spreads.bb_high) * 100),
            2,
        )
        whole_spread = round_numbers(
            (abs((bb_spreads.bb_high - bb_spreads.bb_low) / bb_spreads.bb_high) * 100),
            2,
        )
        bottom_spread = round_numbers(
            abs((bb_spreads.bb_mid - bb_spreads.bb_low) / bb_spreads.bb_mid) * 100,
            2,
        )

        # Otherwise it'll close too soon or incur too much loss
        if whole_spread > 8:
            whole_spread = 8
            top_spread = 6
            bottom_spread = 4

        if whole_spread < 2:
            whole_spread = 2
            top_spread = 1.5
            bottom_spread = 1

        bot.trailling = True
        # reset values to avoid too much risk when there's profit
        bot_profit = self.compute_single_bot_profit(bot, current_price)
        # Use quantile-based volatility for stop_loss (as percent, more aggressive scaling)
        # when prices go up only
        if bot.strategy == Strategy.long:
            # Only when TD_2 > TD_1
            bot.trailling_profit = top_spread if top_spread > 1 else 1
            # too much risk, reduce stop loss
            bot.trailling_deviation = bottom_spread if bottom_spread > 1 else 1
            if bot_profit > 6:
                bot.trailling_profit = 2.8
                bot.trailling_deviation = 2.6

            # Calculate stop_loss as a percent, clamp between 2% and 7%
            stop_loss_percent = max(3.0, min(quantile_vol * 100, 7.0))
            bot.stop_loss = stop_loss_percent

            if (
                bot.trailling_profit == original_bot.trailling_profit
                and bot.stop_loss == original_bot.stop_loss
                and bot.trailling_deviation == original_bot.trailling_deviation
            ):
                return

            controller.save(bot)
            spot_deal = DealGateway(bot, db_table=db_table)
            # reactivate includes saving
            spot_deal.open_deal()

            # No need to continue
            # Bots can only be either long or short
            return

        if bot.strategy == Strategy.margin_short:
            if bot_profit > 6:
                bot.trailling_profit = 2.8
                bot.trailling_deviation = 2.6

            # Decrease risk for margin shorts
            # as volatility is higher, we want to keep parameters tighter
            # also over time we'll be paying more interest, so better to liquidate sooner
            # that means smaller trailing deviation to close deal earlier
            elif bot.trailling_deviation > bottom_spread:
                bot.trailling_profit = bottom_spread if bottom_spread > 1 else 1
                bot.trailling_deviation = top_spread if top_spread > 1 else 1

            # check we are not duplicating the update
            if (
                bot.trailling_profit == original_bot.trailling_profit
                and bot.stop_loss == original_bot.stop_loss
                and bot.trailling_deviation == original_bot.trailling_deviation
            ):
                return

            margin_deal = DealGateway(bot, db_table=db_table)
            # reactivate includes saving
            margin_deal.open_deal()

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
