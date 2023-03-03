import os

from binance import AsyncClient, BinanceSocketManager
from db import setup_db
from deals.controllers import CreateDealController
from deals.margin import MarginDeal
from pymongo import ReturnDocument
from datetime import datetime
from time import time


class TerminateStreaming(Exception):
    pass


class StreamingController:
    def __init__(self):
        # For some reason, db connections internally only work with
        # db:27017 instead of localhost=:2018
        self.streaming_db = setup_db()
        self.socket = None
        self.client = None
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

        This will queue up a timer to restart streaming_controller when timer is reached
        This timer is added, so that update_required petitions can be accumulated and
        avoid successively restarting streaming_controller, which consumes a lot of memory

        This means that everytime there is an update in the list of active bots,
        it will reset the timer
        """
        self.streaming_db.research_controller.update_one(
            {"_id": "settings"}, {"$set": {"update_required": time()}}
        )
        return

    async def setup_client(self):
        client = await AsyncClient.create(
            os.environ["BINANCE_KEY"], os.environ["BINANCE_SECRET"]
        )
        socket = BinanceSocketManager(client)
        return socket, client

    def combine_stream_names(self):
        interval = self.settings["candlestick_interval"]
        self.list_bots = list(
            self.streaming_db.bots.distinct("pair", {"status": "active"})
        )
        self.list_paper_trading_bots = list(
            self.streaming_db.paper_trading.distinct("pair", {"status": "active"})
        )

        markets = self.list_bots + self.list_paper_trading_bots
        params = []
        if len(markets) == 0:
            # Listen to dummy stream to always trigger streaming
            markets.append("BNBBTC")
        for market in markets:
            params.append(f"{market.lower()}@kline_{interval}")

        return params

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
            if current_bot and "deal" in current_bot:
                # Update Current price only for active bots
                # This is to keep historical profit intact
                bot = self.streaming_db[db_collection].find_one_and_update(
                    {"id": current_bot["id"]},
                    {"$set": {"deal.current_price": close_price}},
                    return_document=ReturnDocument.AFTER,
                )

                # Auto switch to short strategy
                if "short_sell_price" in current_bot and 0 < float(
                    current_bot["short_sell_price"]
                ) >= float(close_price):
                    # If hit short_sell_price, resume long strategy by resetting short_sell_price
                    try:
                        CreateDealController(
                            current_bot, db_collection=db_collection
                        ).execute_short_sell()
                    except Exception as error:
                        print(f"Autoswitch to short strategy error: {error}")

                    return

                # Stop loss
                if (
                    "stop_loss" in bot
                    and float(bot["stop_loss"]) > 0
                    and "stop_loss_price" in bot["deal"]
                    and float(bot["deal"]["stop_loss_price"]) > float(close_price)
                ):
                    deal = CreateDealController(bot, db_collection)
                    deal.execute_stop_loss(close_price)
                    self._update_required()
                    return

                # Take profit trailling
                if bot["trailling"] == "true" and float(bot["deal"]["buy_price"]) > 0:
                    # If current price didn't break take_profit (first time hitting take_profit or trailling_stop_loss lower than base_order buy_price)
                    if bot["deal"]["trailling_stop_loss_price"] == 0:
                        trailling_price = float(bot["deal"]["buy_price"]) * (
                            1 + (float(bot["take_profit"]) / 100)
                        )
                        # If trailling_stop_loss < base order it will reset every time
                        print(
                            f"{datetime.utcnow()} {symbol} Setting trailling_stop_loss"
                        )
                    else:
                        # Current take profit + next take_profit
                        trailling_price = float(bot["deal"]["take_profit_price"]) * (
                            1 + (float(bot["take_profit"]) / 100)
                        )
                        print(
                            f"{datetime.utcnow()} {symbol} Updated (Didn't break trailling), updating trailling price points"
                        )

                    # Direction 1 (upward): breaking the current trailling
                    if bot and float(close_price) >= float(trailling_price):
                        new_take_profit = float(trailling_price) * (
                            1 + (float(bot["take_profit"]) / 100)
                        )
                        new_trailling_stop_loss = float(trailling_price) - (
                            float(trailling_price)
                            * (float(bot["trailling_deviation"]) / 100)
                        )
                        # Update deal take_profit
                        bot["deal"]["take_profit_price"] = new_take_profit
                        # take_profit but for trailling, to avoid confusion
                        # trailling_profit_price always be > trailling_stop_loss_price
                        bot["deal"]["trailling_profit_price"] = new_take_profit

                        if new_trailling_stop_loss > bot["deal"]["buy_price"]:
                            # Selling below buy_price will cause a loss
                            # instead let it drop until it hits safety order or stop loss
                            print(
                                f"{symbol} Updating take_profit_price, trailling_profit and trailling_stop_loss_price! {new_take_profit}"
                            )
                            # Update trailling_stop_loss
                            bot["deal"][
                                "trailling_stop_loss_price"
                            ] = new_trailling_stop_loss
                            print(
                                f'{datetime.utcnow()} Updated {symbol} trailling_stop_loss_price {bot["deal"]["trailling_stop_loss_price"]}'
                            )
                        else:
                            # Protect against drops by selling at buy price + 0.75% commission
                            bot["deal"]["trailling_stop_loss_price"] = (
                                float(bot["deal"]["buy_price"]) * 1.075
                            )
                            print(
                                f'{datetime.utcnow()} Updated {symbol} trailling_stop_loss_price {bot["deal"]["trailling_stop_loss_price"]}'
                            )

                        bot = self.streaming_db[db_collection].find_one_and_update(
                            {"id": current_bot["id"]},
                            {"$set": {"deal": bot["deal"]}},
                            upsert=False,
                            return_document=ReturnDocument.AFTER,
                        )
                        if not bot:
                            self.streaming_db[db_collection].update_one(
                                {"id": current_bot["id"]},
                                {
                                    "$push": {
                                        "errors": f'Error updating trailling order {current_bot["_id"]}'
                                    }
                                },
                            )

                    # Direction 2 (downward): breaking the trailling_stop_loss
                    # Make sure it's red candlestick, to avoid slippage loss
                    # Sell after hitting trailling stop_loss and if price already broken trailling
                    if (
                        float(bot["deal"]["trailling_stop_loss_price"]) > 0
                        # Broken stop_loss
                        and float(close_price)
                        < float(bot["deal"]["trailling_stop_loss_price"])
                        # Red candlestick
                        and (float(open_price) > float(close_price))
                    ):
                        print(
                            f'Hit trailling_stop_loss_price {bot["deal"]["trailling_stop_loss_price"]}. Selling {symbol}'
                        )
                        try:
                            deal = CreateDealController(bot, db_collection)
                            deal.trailling_profit()
                            # This terminates the bot
                            self._update_required()

                        except Exception as error:
                            print(error)
                            return

                # Open safety orders
                # When bot = None, when bot doesn't exist (unclosed websocket)
                if "safety_orders" in bot and len(bot["safety_orders"]) > 0:
                    for key, so in enumerate(bot["safety_orders"]):
                        # Index is the ID of the safety order price that matches safety_orders list
                        if ("status" in so and so["status"] == 0) and float(
                            so["buy_price"]
                        ) >= float(close_price):
                            deal = CreateDealController(bot, db_collection)
                            deal.so_update_deal(key)

                # Execute dynamic_take_profit at the end,
                # so that trailling_take_profit and trailling_stop_loss can execute before
                # else trailling_stop_loss could be hit but then changed because of dynamic_tp
                if bot["trailling"] == "true" and bot["dynamic_trailling"]:
                    deal = CreateDealController(bot, db_collection)
                    # Returns bot, to keep modifying in subsequent checks
                    bot = deal.dynamic_take_profit(symbol, current_bot, close_price)

        pass

    async def process_klines(self, result):
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
            print(
                f'Time to update_required {time() - local_settings["update_required"]}'
            )
            if time() - local_settings["update_required"] > 15:
                self.streaming_db.research_controller.update_one(
                    {"_id": "settings"}, {"$set": {"update_required": None}}
                )
                await self.client.close_connection()
                raise TerminateStreaming("Streaming needs to restart to reload bots.")

        if "k" in result:
            close_price = result["k"]["c"]
            open_price = result["k"]["o"]
            symbol = result["k"]["s"]
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

    async def get_klines(self):
        self.socket, self.client = await self.setup_client()
        params = self.combine_stream_names()
        print(f"Starting streaming klines {params}")
        klines = self.socket.multiplex_socket(params)
        self.conn_key = klines

        async with klines as k:
            while True:
                res = await k.recv()

                if "result" in res:
                    print(f'Subscriptions: {res["result"]}')

                if "data" in res:
                    if "e" in res["data"] and res["data"]["e"] == "kline":
                        await self.process_klines(res["data"])
                    else:
                        print(f'Error: {res["data"]}')

                await self.client.close_connection()

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
        print(f'Order updates modified: {query.raw_result["nModified"]}')
        if query.raw_result["nModified"] == 0:
            # Order not found in bots, so try paper_trading collection
            query = self.close_trailling_orders(result, db_collection="paper_trading")
            print(f'Order updates modified: {query.raw_result["nModified"]}')
            if query.raw_result["nModified"] == 0:
                print(
                    f"No bot found with order client order id: {order_id}. Order status: {result['X']}"
                )
                return
        return

    async def get_user_data(self):
        print("Streaming user data")
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
                            print(f'Assets changed {res["e"]}')
                        elif "balanceUpdate" in res["e"]:
                            print(f'Funds transferred {res["e"]}')
                    else:
                        print(f"Unrecognized user data: {res}")

                    pass
                except Exception as error:
                    print(f"get_user_data sockets error: {error}")
                    pass

                await client.close_connection()

    async def get_isolated_margin_data(self):
        print("Streaming isolated margin data")
        socket, client = await self.setup_client()
        # im_data = socket.isolated_margin_socket(symbol)
        pass
