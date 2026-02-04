from datetime import datetime
from bots.models import BotModel
from databases.crud.autotrade_crud import AutotradeCrud
from databases.crud.bot_crud import BotTableCrud
from databases.crud.candles_crud import CandlesCrud
from databases.crud.paper_trading_crud import PaperTradingTableCrud
from databases.crud.symbols_crud import SymbolsCrud
from pybinbot import (
    OrderStatus,
    Status,
    ExchangeId,
    KucoinKlineIntervals,
    BinanceApi,
    BinbotErrors,
)
from tools.config import Config
from exchange_apis.kucoin.futures import KucoinFutures


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
        self.kucoin_api = KucoinFutures(
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
        self.interval = self.autotrade_settings.candlestick_interval
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

    def order_updates(self, bot: BotModel) -> BotModel:
        """
        Take order id from list of bot.orders
        and fetch order details from exchange
        """
        for order in bot.orders:
            if (
                self.exchange == ExchangeId.KUCOIN
                and order.status != OrderStatus.FILLED
            ):
                system_order = self.kucoin_api.get_order(order_id=str(order.order_id))

                # Check if order is expired based on 15m interval
                # this should be a good measure, because candles have closed
                interval_ms = KucoinKlineIntervals.get_interval_ms(self.interval.value)
                now_ms = int(datetime.now().timestamp() * 1000)
                order_ms = int(order.timestamp * 1000)
                is_expired = (now_ms - order_ms) > interval_ms

                if system_order and float(system_order.deal_size) > 0:
                    order.price = float(system_order.price)
                    order.qty = float(system_order.deal_size)
                    order.status = (
                        OrderStatus.FILLED
                        if system_order.status == "done"
                        or system_order.status == "match"
                        else OrderStatus.NEW
                    )

                if not system_order or is_expired:
                    self.kucoin_api.cancel_order(order_id=str(order.order_id))
                    bot.status = Status.inactive
                    bot.add_log(
                        f"Order {order.order_id} expired and cancelled. Bot set to inactive.",
                    )

            self.bot_controller.save(data=bot)

        return bot
