import json
import logging

from bots.schemas import BotSchema
from autotrade.controller import AutotradeSettingsController
from bots.controllers import Bot
from tools.enum_definitions import Status, Strategy
from db import Database
from deals.margin import MarginDeal
from deals.spot import SpotLongDeal
from tools.exceptions import BinanceErrors


class StreamingController(Database):
    def __init__(self, consumer):
        super().__init__()
        self.streaming_db = self._db
        # Gets any signal to restart streaming
        self.consumer = consumer
        self.autotrade_controller = AutotradeSettingsController()
        self.load_data_on_start()
        self.current_bot = None
        self.current_test_bot = None

    def load_data_on_start(self):
        """
        New function to replace get_klines without websockets
        """
        self.settings = self.autotrade_controller.get_autotrade_settings()
        self.test_settings = self.autotrade_controller.get_test_autotrade_settings()
        # Load real bot settings
        bot_controller = Bot(collection_name="bots")
        self.list_bots = bot_controller.get_active_pairs()
        # Load paper trading bot settings
        paper_trading_controller_paper = Bot(collection_name="paper_trading")
        self.list_paper_trading_bots = paper_trading_controller_paper.get_active_pairs()
        return

    def get_current_bot(self, symbol):
        if self.current_bot:
            return self.current_bot
        else:
            current_bot = Bot(collection_name="bots").get_one(symbol=symbol, status=Status.active)
            self.current_bot = current_bot
        return self.current_bot

    def get_current_test_bot(self, symbol):
        if self.current_test_bot:
            return self.current_test_bot
        else:
            current_test_bot = Bot(collection_name="paper_trading").get_one(symbol=symbol, status=Status.active)
            self.current_test_bot = current_test_bot
            return self.current_test_bot

    def execute_strategies(
        self,
        current_bot,
        close_price: str,
        open_price: str,
        db_collection_name,
    ):
        """
        Processes the deal market websocket price updates

        It updates the bots deals, safety orders, trailling orders, stop loss
        for both paper trading test bots and real bots
        """
        if len(current_bot["orders"]) > 0:
            try:
                int(current_bot["orders"][0]["order_id"])
            except Exception:
                print(current_bot["orders"][0]["order_id"])
                pass
        try:
            active_bot = BotSchema(**current_bot)
            pass
        except Exception as error:
            logging.info(error)
            return
        # Margin short
        if active_bot.strategy == Strategy.margin_short:
            margin_deal = MarginDeal(active_bot, db_collection_name)
            try:
                margin_deal.streaming_updates(close_price)
            except BinanceErrors as error:
                if error.code in (-2010, -1013):
                    margin_deal.update_deal_logs(error.message, active_bot)
            except Exception as error:
                logging.info(error)
                margin_deal.update_deal_logs(error, active_bot)
                pass

        else:
            # Long strategy starts
            if active_bot.strategy == Strategy.long:
                spot_long_deal = SpotLongDeal(active_bot, db_collection_name)
                try:
                    spot_long_deal.streaming_updates(close_price, open_price)
                except BinanceErrors as error:
                    if error.code in (-2010, -1013):
                        spot_long_deal.update_deal_logs(error.message, active_bot)
                        active_bot.status = Status.error
                        active_bot = self.save_bot_streaming(active_bot)
                except Exception as error:
                    logging.info(error)
                    spot_long_deal.update_deal_logs(error, active_bot)
                    pass

        pass

    def process_klines(self, message):
        """
        Updates deals with klines websockets,
        when price and symbol match existent deal
        """
        data = json.loads(message)
        close_price = data["close_price"]
        open_price = data["open_price"]
        symbol = data["symbol"]
        current_bot = self.get_current_bot(symbol)
        current_test_bot = self.get_current_test_bot(symbol)

        # temporary test that we get enough streaming update signals
        logging.info(f"Streaming update for {symbol}")

        if current_bot:
            self.execute_strategies(
                current_bot,
                close_price,
                open_price,
                "bots",
            )
        if current_test_bot:
            self.execute_strategies(
                current_test_bot,
                close_price,
                open_price,
                "paper_trading",
            )

        return

    def update_close_conditions(self, message):
        """
        Update bot with dynamic trailling enabled to update
        take_profit and trailling according to bollinguer bands
        dynamic movements in the market
        """
        data = json.loads(message)
        bb_spreads = data.bb_spreads
        if bb_spreads["bb_high"] and bb_spreads["bb_low"] and bb_spreads["bb_mid"]:
            top_spread = abs((bb_spreads["bb_high"] - bb_spreads["bb_mid"]) / bb_spreads["bb_high"]) * 100
            whole_spread = abs((bb_spreads["bb_high"] - bb_spreads["bb_low"]) / bb_spreads["bb_high"]) * 100
            bottom_spread = abs((bb_spreads["bb_mid"] - bb_spreads["bb_low"]) / bb_spreads["bb_mid"]) * 100

            # current_bot = self.get_current_bot(symbol)
            # current_test_bot = self.get_current_test_bot(symbol)

            # Otherwise it'll close too soon
            if whole_spread > 1.2:
                self.default_bot.trailling = True
                if self.default_bot.strategy == Strategy.long:
                    self.default_bot.stop_loss = whole_spread
                    self.default_bot.take_profit = top_spread
                    # too much risk, reduce stop loss
                    self.default_bot.trailling_deviation = bottom_spread

                if self.default_bot.strategy == Strategy.margin_short:
                    self.default_bot.stop_loss = whole_spread
                    self.default_bot.take_profit = bottom_spread
                    self.default_bot.trailling_deviation = top_spread
