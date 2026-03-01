from datetime import datetime
from typing import Union
from bots.models import BotModel
from databases.crud.autotrade_crud import AutotradeCrud
from databases.crud.bot_crud import BotTableCrud
from databases.crud.candles_crud import CandlesCrud
from databases.crud.paper_trading_crud import PaperTradingTableCrud
from databases.crud.symbols_crud import SymbolsCrud
from pybinbot import (
    BinanceApi,
    BinanceKlineIntervals,
    BinbotErrors,
    ExchangeId,
    KucoinKlineIntervals,
    Status,
    KucoinApi,
    KucoinFutures,
    round_numbers,
)
from tools.config import Config
from databases.utils import independent_session


class BaseStreaming:
    """
    Static data that doesn't change often, loaded once on startup and used across the application
    """

    def __init__(self) -> None:
        self.config = Config()
        self.session = independent_session()
        self.binance_api = BinanceApi(
            key=self.config.binance_key, secret=self.config.binance_secret
        )
        self.kucoin_api = KucoinApi(
            key=self.config.kucoin_key,
            secret=self.config.kucoin_secret,
            passphrase=self.config.kucoin_passphrase,
        )
        self.kucoin_futures_api = KucoinFutures(
            key=self.config.kucoin_key,
            secret=self.config.kucoin_secret,
            passphrase=self.config.kucoin_passphrase,
        )
        self.bot_controller = BotTableCrud(session=self.session)
        self.paper_trading_controller = PaperTradingTableCrud()
        self.symbols_crud = SymbolsCrud()
        self.cs = CandlesCrud()
        self.autotrade_crud = AutotradeCrud()
        self.autotrade_settings = self.autotrade_crud.get_settings()
        self.exchange = ExchangeId(self.autotrade_settings.exchange_id)
        self.benchmark_symbol = "BTCUSDT"
        self.kucoin_benchmark_symbol = "BTC-USDT"

        binance_interval = BinanceKlineIntervals(
            self.autotrade_settings.candlestick_interval
        )
        kucoin_interval = KucoinKlineIntervals(
            BinanceKlineIntervals.to_kucoin_interval(binance_interval)
        )
        self.interval: Union[BinanceKlineIntervals, KucoinKlineIntervals]
        self.api: Union[BinanceApi, None]
        # Prepare interval based on exchange
        if self.exchange == ExchangeId.KUCOIN:
            self.interval = kucoin_interval
            # To be set in child classes, because kucoin has different api for spot and futures
            self.api = None
        else:
            self.interval = binance_interval
            self.api = self.binance_api

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

    def get_interests_short_margin(self, bot: BotModel) -> tuple[float, float, float]:
        close_timestamp = bot.deal.closing_timestamp
        if close_timestamp == 0:
            close_timestamp = int(datetime.now().timestamp() * 1000)

        asset = bot.pair.split(bot.fiat)[0]
        interest_details = self.binance_api.get_interest_history(
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
