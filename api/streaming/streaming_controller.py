import json
import logging
from deals.base import BaseDeal
from tools.enum_definitions import Status
from db import setup_db
from deals.margin import MarginDeal
from deals.spot import SpotLongDeal
from time import time
from streaming.socket_client import SpotWebsocketStreamClient
from tools.exceptions import BinanceErrors, TerminateStreaming

class StreamingController(BaseDeal):
    def __init__(self):
        # For some reason, db connections internally only work with
        # db:27017 instead of localhost=:2018
        self.streaming_db = setup_db()
        self.socket = None
        # test wss://data-stream.binance.com
        self.client = SpotWebsocketStreamClient(
            on_message=self.on_message, on_error=self.on_error, is_combined=True
        )
        self.conn_key = None
        self.list_bots = []
        self.list_paper_trading_bots = []
        self.settings = self.streaming_db.research_controller.find_one(
            {"_id": "settings"}
        )
        self.test_settings = self.streaming_db.research_controller.find_one(
            {"_id": "test_autotrade_settings"}
        )

    def _update_required(self):
        """
        Terminate streaming and restart list of bots required

        This will count and store number of times update is required,
        so that we can add a condition to restart when it hits certain threshold

        This is to avoid excess memory consumption
        """
        self.streaming_db.research_controller.update_one(
            {"_id": "settings"}, {"$set": {"update_required": time()}}
        )

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
                # Go to _update_required
                self._update_required()
                pass

        else:
            # Long strategy starts
            if current_bot["strategy"] == "long":
                spot_long_deal = SpotLongDeal(
                    current_bot, db_collection_name
                )
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
                    # Go to _update_required
                    self._update_required()
                    pass

        pass

    def on_error(self, socket, msg):
        logging.error(f'Streaming_Controller error:{msg}')
        self.get_klines()

    def on_message(self, socket, message):
        # If fails to connect, this will cancel loop
        res = json.loads(message)

        if "result" in res and res["result"]:
            logging.info(f'Subscriptions: {res["result"]}')

        if "data" in res:
            if "e" in res["data"] and res["data"]["e"] == "kline":
                self.process_klines(res["data"])
            else:
                logging.error(f'Error: {res["data"]}')
                self.client.stop()

    def process_klines(self, result):
        """
        Updates deals with klines websockets,
        when price and symbol match existent deal
        """
        # Re-retrieve settings in the middle of streaming
        local_settings = self.streaming_db.research_controller.find_one(
            {"_id": "settings"}
        )

        if "k" in result:
            close_price = result["k"]["c"]
            open_price = result["k"]["o"]
            symbol = result["k"]["s"]
            current_bot = self.streaming_db.bots.find_one(
                {"pair": symbol, "status": Status.active}
            )
            current_test_bot = self.streaming_db.paper_trading.find_one(
                {"pair": symbol, "status": Status.active}
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

        # Add margin time to update_required signal to avoid restarting constantly
        # About 1000 seconds (16.6 minutes) - similar to candlestick ticks of 15m
        if local_settings["update_required"]:
            logging.debug(
                f'Time elapsed for update_required: {time() - local_settings["update_required"]}'
            )
            if (time() - local_settings["update_required"]) > 40:
                self.streaming_db.research_controller.update_one(
                    {"_id": "settings"}, {"$set": {"update_required": time()}}
                )
                logging.info(f"Restarting streaming_controller {self.list_bots}")
                # raise TerminateStreaming()
                self.get_klines()
        return

    def get_klines(self):
        interval = self.settings["candlestick_interval"]
        self.list_bots = list(
            self.streaming_db.bots.distinct("pair", {"status": "active"})
        )
        self.list_paper_trading_bots = list(
            self.streaming_db.paper_trading.distinct("pair", {"status": "active"})
        )
        # Reset to new update_required system
        self.streaming_db.research_controller.update_one(
            {"_id": "settings"}, {"$set": {"update_required": time()}}
        )

        markets = self.list_bots + self.list_paper_trading_bots
        logging.info(f"Streaming updates: {markets}")
        self.client.klines(markets=markets, interval=interval)

    def update_order_data(self, result, db_collection: str = "bots"):
        """
        Keep order data up to date

        When buy_order or sell_order is executed, they are often in
        status NEW, and it takes time to update to FILLED.
        This keeps order data up to date as they are executed
        throught the executionReport websocket

        Args:
            result (dict): executionReport websocket result
            db_collection (str, optional): Defaults to "bots".

        """
        order_id = result["i"]
        update = {
            "$set": {
                "orders.$.status": result["X"],
                "orders.$.qty": result["q"],
                "orders.$.order_side": result["S"],
                "orders.$.order_type": result["o"],
                "orders.$.timestamp": result["T"],
            },
            "$inc": {"total_commission": float(result["n"])},
            "$push": {"errors": "Order status updated"},
        }
        if float(result["p"]) > 0:
            update["$set"]["orders.$.price"] = float(result["p"])
        else:
            update["$set"]["orders.$.price"] = float(result["L"])

        query = self.streaming_db[db_collection].update_one(
            {"orders": {"$elemMatch": {"order_id": order_id}}},
            update,
        )
        return query

    def get_user_data(self):
        listen_key = self.get_listen_key()
        self.user_data_client = SpotWebsocketStreamClient(
            on_message=self.on_user_data_message, on_error=self.on_error
        )
        self.user_data_client.user_data(listen_key=listen_key, action=SpotWebsocketStreamClient.subscribe)

    def on_user_data_message(self, socket, message):
        logging.info("Streaming user data")
        res = json.loads(message)

        if "e" in res:
            if "executionReport" in res["e"]:
                query = self.update_order_data(res)
                if query.raw_result["nModified"] == 0:
                    logging.debug(
                        f'No bot found with order client order id: {res["i"]}. Order status: {res["X"]}'
                    )
                return

            elif "outboundAccountPosition" in res["e"]:
                logging.info(f'Assets changed {res["e"]}')
            elif "balanceUpdate" in res["e"]:
                logging.info(f'Funds transferred {res["e"]}')
