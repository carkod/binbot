import json
import logging

from deals.base import BaseDeal
from tools.enum_definitions import Status
from db import Database
from deals.margin import MarginDeal
from deals.spot import SpotLongDeal
from tools.exceptions import BinanceErrors


class StreamingController(BaseDeal):
    def __init__(self, consumer):
        self.streaming_db = Database()
        # Gets any signal to restart streaming
        self.consumer = consumer
        self.load_data_on_start()

    def load_data_on_start(self):
        """
        New function to replace get_klines without websockets

        After each "update_required" restart, this function will reload bots and settings
        """
        self.settings = self.streaming_db.get_autotrade_settings()
        self.test_settings = self.streaming_db.get_test_autotrade_settings()
        self.list_bots = self.streaming_db.get_active_bots()
        self.list_paper_trading_bots = self.streaming_db.get_active_paper_trading_bots()

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
        # Margin short
        if current_bot["strategy"] == "margin_short":
            margin_deal = MarginDeal(current_bot, db_collection_name)
            try:
                margin_deal.streaming_updates(close_price)
            except BinanceErrors as error:
                if error.code in (-2010, -1013):
                    margin_deal.update_deal_logs(error.message)
            except Exception as error:
                logging.info(error)
                margin_deal.update_deal_logs(error)
                pass

        else:
            # Long strategy starts
            if current_bot["strategy"] == "long":
                spot_long_deal = SpotLongDeal(current_bot, db_collection_name)
                try:
                    spot_long_deal.streaming_updates(close_price, open_price)
                except BinanceErrors as error:
                    if error.code in (-2010, -1013):
                        spot_long_deal.update_deal_logs(error.message)
                        current_bot["status"] = Status.error
                        self.save_bot_streaming()
                except Exception as error:
                    logging.info(error)
                    spot_long_deal.update_deal_logs(error)
                    pass

        pass

    def process_klines(self, result):
        """
        Updates deals with klines websockets,
        when price and symbol match existent deal
        """

        if "k" in result:
            close_price = result["k"]["c"]
            open_price = result["k"]["o"]
            symbol = result["k"]["s"]
            current_bot = self.streaming_db.get_active_bot_by_symbol(symbol)
            current_test_bot = self.streaming_db.get_active_paper_trading_bot_by_symbol(
                symbol
            )

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
