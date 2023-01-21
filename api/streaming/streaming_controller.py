import os
import asyncio
from binance import AsyncClient, BinanceSocketManager
from pymongo import ReturnDocument
from deals.controllers import CreateDealController
from db import setup_db


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
        # Start streaming service globally
        # This will allow access for the entire FastApi scope
        asyncio.Event.connection_open = True

    async def setup_client(self):
        client = await AsyncClient.create(
            os.environ["BINANCE_KEY"], os.environ["BINANCE_SECRET"]
        )
        socket = BinanceSocketManager(client)
        return socket, client

    def combine_stream_names(self, interval):
        if self.settings["autotrade"] == 1:
            self.list_bots = list(
                self.streaming_db.bots.distinct("pair", {"status": "active"})
            )

        if self.test_settings["autotrade"] == 1:
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

    def process_deals_bot(
        self, current_bot, close_price, open_price, symbol, db_collection
    ):
        """
        Processes the deal market websocket price updates

        It updates the bots deals, safety orders, trailling orders, stop loss
        for both paper trading test bots and real bots
        """

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
            raise TerminateStreaming("Streaming needs to restart to reload bots.")

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
                return

            # Take profit trailling
            if bot["trailling"] == "true" and float(bot["deal"]["buy_price"]) > 0:

                # Temporary testing condition
                if db_collection == "paper_trading":
                    if bot["mode"] == "autotrade":
                        deal = CreateDealController(bot, db_collection)
                        # Returns bot, to keep modifying in subsequent checks
                        bot = deal.dynamic_take_profit(
                            symbol, current_bot["candlestick_interval"], close_price
                        )

                if (
                    "trailling_stop_loss_price" not in bot["deal"]
                    or bot["deal"]["trailling_stop_loss_price"] == 0
                ) or float(bot["deal"]["take_profit_price"]) == 0:
                    # If current price didn't break take_profit (first time hitting take_profit)
                    current_take_profit_price = float(bot["deal"]["buy_price"]) * (
                        1 + (float(bot["take_profit"]) / 100)
                    )
                    print(f"{symbol} Updated (Didn't break trailling)")
                else:
                    # If current price broke take profit, we start trailling
                    # This is necessary to avoid conflict between trailling take profit and safety orders
                    current_take_profit_price = float(
                        bot["deal"]["trailling_stop_loss_price"]
                    ) * (1 + (float(bot["take_profit"]) / 100))

                # Direction 1 (upward): breaking the current trailling
                if float(close_price) >= float(current_take_profit_price) and bot:
                    new_take_profit = float(close_price) * (
                        1 + (float(bot["take_profit"]) / 100)
                    )
                    # Update deal take_profit
                    bot["deal"]["take_profit_price"] = new_take_profit

                    if (
                        bot["deal"]["trailling_stop_loss_price"]
                        > bot["deal"]["buy_price"]
                        # Make sure it's red candlestick, to avoid slippage loss
                    ) and (float(open_price) - float(close_price)) < 0:
                        # Selling below buy_price will cause a loss
                        # instead let it drop until it hits safety order or stop loss
                        print(
                            f"{symbol} Updating take_profit_price, trailling_profit and trailling_stop_loss_price! {new_take_profit}"
                        )
                        # Update trailling_stop_loss
                        bot["deal"]["trailling_stop_loss_price"] = float(
                            new_take_profit
                        ) - (
                            float(new_take_profit)
                            * (float(bot["trailling_deviation"]) / 100)
                        )
                        print(
                            f'Updated {symbol} trailling_stop_loss_price {bot["deal"]["trailling_stop_loss_price"]}'
                        )
                    else:
                        # Protect against drops by selling at buy price + 0.75% commission
                        bot["deal"]["trailling_stop_loss_price"] = (
                            float(bot["deal"]["buy_price"]) * 1.075
                        )
                        print(
                            f'Updated {symbol} trailling_stop_loss_price {bot["deal"]["trailling_stop_loss_price"]}'
                        )

                    updated_bot = self.streaming_db[db_collection].update_one(
                        {"id": current_bot["id"]},
                        {"$set": {"deal": bot["deal"]}},
                    )
                    if not updated_bot:
                        self.streaming_db[db_collection].update_one(
                            {"id": current_bot["id"]},
                            {
                                "$push": {
                                    "errors": f'Error updating trailling order {current_bot["_id"]}'
                                }
                            },
                        )

                # Sell after hitting trailling stop_loss and if price already broken trailling
                price = bot["deal"]["trailling_stop_loss_price"]
                # Direction 2 (downward): breaking the trailling_stop_loss
                if float(price) > 0 and float(close_price) <= float(price):
                    print(f"Hit trailling_stop_loss_price {price}. Selling {symbol}")
                    try:
                        deal = CreateDealController(bot, db_collection)
                        deal.trailling_profit()
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
        pass

    def process_deals(self, result):
        """
        Updates deals with klines websockets,
        when price and symbol match existent deal
        """
        # Re-retrieve settings in the middle of streaming
        local_settings = self.streaming_db.research_controller.find_one(
            {"_id": "settings"}
        )
        if local_settings["update_required"]:
            self.streaming_db.research_controller.update_one(
                {"_id": "settings"}, {"$set": {"update_required": False}}
            )
            if self.client:
                print("Closing client connection")
                self.client.close_connection()
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
                self.process_deals_bot(
                    current_bot, close_price, open_price, symbol, "bots"
                )
            if current_test_bot:
                self.process_deals_bot(
                    current_test_bot, close_price, open_price, symbol, "paper_trading"
                )
            return

    async def get_klines(self, interval):
        print("Starting streaming klines")
        self.socket, self.client = await self.setup_client()
        params = self.combine_stream_names(interval)
        klines = self.socket.multiplex_socket(params)
        self.conn_key = klines

        async with klines as k:
            while True:
                res = await k.recv()

                if "result" in res:
                    print(f'Subscriptions: {res["result"]}')

                if "data" in res:
                    if "e" in res["data"] and res["data"]["e"] == "kline":
                        self.process_deals(res["data"])
                    else:
                        print(f'Error: {res["data"]}')

    async def get_user_data(self):
        print("Streaming user data")
        socket, client = await self.setup_client()
        user_data = socket.user_socket()
        async with user_data as ud:
            try:
                while True:
                    res = await ud.recv()
                    print(res)
            except Exception as error:
                print(f"get_user_data sockets error: {error}")
                client.close_connection()
