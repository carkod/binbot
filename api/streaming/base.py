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
)
from tools.config import Config
from databases.utils import independent_session


class BaseStreaming:
    """
    Static data that doesn't change often, loaded once on startup
    and used across the application
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
        candlestick_interval = self.autotrade_settings.candlestick_interval
        if self.exchange == ExchangeId.KUCOIN:
            self.interval: KucoinKlineIntervals | BinanceKlineIntervals
            if isinstance(candlestick_interval, BinanceKlineIntervals):
                interval = BinanceKlineIntervals.to_kucoin_interval(
                    candlestick_interval
                )
                self.interval = KucoinKlineIntervals(interval)
            elif isinstance(candlestick_interval, KucoinKlineIntervals):
                self.interval = candlestick_interval
            else:
                raise ValueError(
                    f"Invalid interval type: {candlestick_interval}. Must be BinanceKlineIntervals or KucoinKlineIntervals."
                )
        else:
            self.interval = candlestick_interval

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
