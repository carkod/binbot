import json
import logging
from db import setup_db
from deals.controllers import CreateDealController
from deals.margin import MarginDeal
from deals.spot import SpotLongDeal
from pymongo import ReturnDocument
from datetime import datetime
from time import time
from streaming.socket_client import SpotWebsocketStreamClient


class TerminateStreaming(Exception):
    pass


class StreamingController:
    def __init__(self):
        # For some reason, db connections internally only work with
        # db:27017 instead of localhost=:2018
        self.streaming_db = setup_db()
        self.socket = None
        # test wss://data-stream.binance.com
        self.client = SpotWebsocketStreamClient(on_message=self.on_message, on_error=self.on_error, is_combined=True)
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
        return


    def execute_strategies(
        self,
        current_bot,
        close_price: str,
        open_price: str,
        symbol: str,
        db_collection,
    ):
        """
        Processes the deal market websocket price updates

        It updates the bots deals, safety orders, trailling orders, stop loss
        for both paper trading test bots and real bots
        """
        # Margin short
        if current_bot["strategy"] == "margin_short":
            margin_deal = MarginDeal(current_bot, db_collection=db_collection)
            margin_deal.streaming_updates(close_price)
            return

        else:
            # Short strategy
            if (
                "short_buy_price" in current_bot
                and float(current_bot["short_buy_price"]) > 0
                and float(current_bot["short_buy_price"]) >= float(close_price)
            ):
                # If hit short_buy_price, resume long strategy by resetting short_buy_price
                CreateDealController(
                    current_bot, db_collection=db_collection
                ).execute_short_buy()

            # Long strategy starts
            if current_bot["strategy"] == "long":
                SpotLongDeal(
                    current_bot, db_collection=db_collection
                ).streaming_updates(close_price, open_price)
                self._update_required()

        pass

    def on_error(self, socket, msg):
        logging.error(msg)
        self.get_klines()

    def on_message(self, socket, message):
        # If fails to connect, this will cancel loop
        res = json.loads(message)

        if "result" in res:
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
        # Add margin time to update_required signal to avoid restarting constantly
        # About 1000 seconds (16.6 minutes) - similar to candlestick ticks of 15m
        if local_settings["update_required"]:
            logging.info(
                f'Time elapsed for update_required: {time() - local_settings["update_required"]}'
            )
            if (time() - local_settings["update_required"]) > 20:
                self.streaming_db.research_controller.update_one(
                    {"_id": "settings"}, {"$set": {"update_required": time()}}
                )
                logging.info("Restarting streaming_controller")
                self.get_klines()

        if "k" in result:
            close_price = result["k"]["c"]
            open_price = result["k"]["o"]
            symbol = result["k"]["s"]
            print(symbol)
            current_bot = self.streaming_db.bots.find_one(
                {"pair": symbol, "status": "active"}
            )
            current_test_bot = self.streaming_db.paper_trading.find_one(
                {"pair": symbol, "status": "active"}
            )
            if current_bot:
                self.execute_strategies(
                    current_bot,
                    close_price,
                    open_price,
                    symbol,
                    "bots",
                )
            if current_test_bot:
                self.execute_strategies(
                    current_test_bot,
                    close_price,
                    open_price,
                    symbol,
                    "paper_trading",
                )
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
        print(f'Markets {markets}')
        self.client.klines(markets=markets, interval=interval)

    def close_trailling_orders(self, result, db_collection: str = "bots"):
        """
        This database query closes any orders found that are trailling orders i.e.
        stop_loss, take_profit, trailling_profit, margin_short_stop_loss, margin_short_trailling_profit
        the two latter also denoted as stop_loss and take_profit for simplification purposes

        If no order is found with the given order_id, then try with the paper_trading collection
        as it could be a test bot

        Finally, if paper_trading doesn't match that order_id either, then try any order in the DB
        """
        order_id = result["i"]
        # Close successful take_profit
        query = self.streaming_db[db_collection].update_one(
            {"orders": {"$elemMatch": {"order_id": order_id}}},
            {
                "$set": {
                    "status": {
                        "$or": [
                            {
                                "$eq": [
                                    (result["X"] == "FILLED"),
                                    "$deal_type",
                                    "take_profit",
                                ]
                            },
                            {
                                "$eq": [
                                    (result["X"] == "FILLED"),
                                    "$deal_type",
                                    "stop_loss",
                                ]
                            },
                        ]
                    },
                    "deal.current_price": result["p"],
                    "deal.sell_price": result["p"],
                    "orders.$.status": result["X"],
                    "orders.$.price": result["p"],
                    "orders.$.qty": result["q"],
                    "orders.$.order_side": result["S"],
                    "orders.$.order_type": result["o"],
                    "orders.$.timestamp": result["T"],
                },
                "$inc": {"total_commission": float(result["n"])},
                "$push": {"errors": "Bot completed!"},
            },
        )
        return query

    def process_user_data(self, result):
        # Parse result. Print result for raw result from Binance
        order_id = result["i"]
        # Example of real update
        # {'e': 'executionReport', 'E': 1676750256695, 's': 'UNFIUSDT', 'c': 'web_86e55fed9bad494fba5e213dbe5b2cfc', 'S': 'SELL', 'o': 'LIMIT', 'f': 'GTC', 'q': '8.20000000', 'p': '6.23700000', 'P': '0.00000000', 'F': '0.00000000', 'g': -1, 'C': 'KrHPY4jWdWwFBHUMtBBfJl', 'x': 'CANCELED', ...}
        query = self.close_trailling_orders(result)
        logging.debug(f'Order updates modified: {query.raw_result["nModified"]}')
        if query.raw_result["nModified"] == 0:
            # Order not found in bots, so try paper_trading collection
            query = self.close_trailling_orders(result, db_collection="paper_trading")
            logging.debug(f'Order updates modified: {query.raw_result["nModified"]}')
            if query.raw_result["nModified"] == 0:
                logging.debug(
                    f"No bot found with order client order id: {order_id}. Order status: {result['X']}"
                )
                return
        return

    async def get_user_data(self):
        logging.info("Streaming user data")
        socket, client = await self.setup_client()
        user_data = socket.user_socket()
        async with user_data as ud:
            while True:
                try:
                    res = await ud.recv()

                    if "e" in res:
                        if "executionReport" in res["e"]:
                            self.process_user_data(res)
                        elif "outboundAccountPosition" in res["e"]:
                            logging.info(f'Assets changed {res["e"]}')
                        elif "balanceUpdate" in res["e"]:
                            logging.info(f'Funds transferred {res["e"]}')
                    else:
                        logging.info(f"Unrecognized user data: {res}")

                    pass
                except Exception as error:
                    logging.info(f"get_user_data sockets error: {error}")
                    pass

                await client.close_connection()
