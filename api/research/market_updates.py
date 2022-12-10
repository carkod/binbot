import json
import threading
import logging
import numpy

from pymongo import ReturnDocument
from api.account.account import Account
from api.app import create_app
from api.deals.controllers import CreateDealController
from websocket import WebSocketApp
from api.tools.round_numbers import round_numbers


class MarketUpdates(Account):
    """
    Further explanation in docs/market_updates.md
    """

    def __init__(self, interval="5m"):
        self.app = create_app()
        self.markets_streams = None
        self.interval = interval
        self.markets = []

    def terminate_websockets(self, thread_name="market_updates"):
        """
        Restart websockets threads after list of active bots altered
        """
        logging.info("Starting thread cleanup")
        global stop_threads
        stop_threads = True
        # Notify market updates websockets to update
        for thread in threading.enumerate():
            if (
                hasattr(thread, "tag")
                and thread_name in thread.name
                and hasattr(thread, "_target")
            ):
                stop_threads = False
                print("closing websocket")
                thread._target.__self__.close()

        pass

    def start_stream(self):
        """
        Start/restart websocket streams
        """
        self.markets = list(self.app.db.bots.distinct("pair", {"status": "active"}))
        paper_trading_bots = list(
            self.app.db.paper_trading.distinct("pair", {"status": "active"})
        )
        self.markets = self.markets + paper_trading_bots
        params = []
        for market in self.markets:
            params.append(f"{market.lower()}@kline_{self.interval}")

        string_params = "/".join(params)
        url = f"{self.WS_BASE}{string_params}"
        ws = WebSocketApp(
            url,
            on_open=self.on_open,
            on_error=self.on_error,
            on_close=self.close_stream,
            on_message=self.on_message,
        )
        # This is required to allow the websocket to be closed anywhere in the app
        self.markets_streams = ws
        # Run the websocket with ping intervals to avoid disconnection
        ws.run_forever(ping_interval=70)

    def close_stream(self, ws, close_status_code, close_msg):
        print("Active socket closed", close_status_code, close_msg)

    def on_open(self, *args, **kwargs):
        print("Market data updates socket opened")

    def on_error(self, ws, error):
        error_msg = f'market_updates error: {error}. Symbol: {ws.symbol if hasattr(ws, "symbol") else ""}'
        print(error_msg)
        self.terminate_websockets()
        self.start_stream()

    def on_message(self, ws, message):
        json_response = json.loads(message)

        if "result" in json_response:
            print(f'Subscriptions: {json_response["result"]}')

        if "data" in json_response:
            if "e" in json_response["data"] and json_response["data"]["e"] == "kline":
                self.process_deals(json_response["data"], ws)
            else:
                print(f'Error: {json_response["data"]}')
        
    def update_take_profit(self, close_price, symbol, bot):
        data = self._get_candlestick(symbol, self.interval, stats=True)
        list_prices = numpy.array(data["trace"][0]["close"])
        sd = round_numbers((numpy.std(list_prices.astype(numpy.float))), 2)
        return


    def process_deals_bot(self, current_bot, close_price, symbol, db_collection):
        """
        Processes the deal market websocket price updates

        It updates the bots deals, safety orders, trailling orders, stop loss
        for both paper trading test bots and real bots
        """

        # Short strategy
        if "short_buy_price" in current_bot and float(current_bot["short_buy_price"]) > 0 and float(current_bot["short_buy_price"]) >= float(close_price):
            # If hit short_buy_price, resume long strategy by resetting short_buy_price
            try:
                CreateDealController(current_bot, db_collection=db_collection).execute_short_buy()
            except Exception as error:
                print(f"Short buy price update error: {error}")

            self.terminate_websockets()
            self.start_stream()

        # Long strategy starts
        if current_bot and "deal" in current_bot:
            # Update Current price only for active bots
            # This is to keep historical profit intact
            bot = self.app.db[db_collection].find_one_and_update(
                {"_id": current_bot["_id"]},
                {"$set": {"deal.current_price": close_price}},
                return_document=ReturnDocument.AFTER,
            )

            # Auto switch to short strategy
            if "short_sell_price" in current_bot and 0 < float(current_bot["short_sell_price"]) >= float(close_price):
                # If hit short_sell_price, resume long strategy by resetting short_sell_price
                try:
                    CreateDealController(current_bot, db_collection=db_collection).execute_short_sell()
                except Exception as error:
                    print(f"Autoswitch to short strategy error: {error}")

                return

            # Stop loss
            if (
                "stop_loss" in current_bot
                and float(current_bot["stop_loss"]) > 0.0
                and "stop_loss_price" in current_bot["deal"]
                and float(current_bot["deal"]["stop_loss_price"])
                > float(close_price)
            ):
                deal = CreateDealController(bot, db_collection)
                deal.execute_stop_loss(close_price)
                return

            # Take profit trailling
            if bot["trailling"] == "true" and bot["deal"]["buy_price"] != "":

                # self.update_take_profit(close_price, symbol, current_bot)

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
                    # Update trailling_stop_loss
                    bot["deal"]["trailling_stop_loss_price"] = float(
                        new_take_profit
                    ) - (
                        float(new_take_profit)
                        * (float(bot["trailling_deviation"]) / 100)
                    )
                    if (
                        bot["deal"]["trailling_stop_loss_price"]
                        > bot["deal"]["buy_price"]
                    ):
                        # Selling below buy_price will cause a loss
                        # instead let it drop until it hits safety order or stop loss
                        print(
                            f"{symbol} Updating take_profit_price, trailling_profit and trailling_stop_loss_price! {new_take_profit}"
                        )
                        updated_bot = self.app.db[db_collection].update_one(
                            {"_id": current_bot["_id"]},
                            {"$set": {"deal": bot["deal"]}},
                        )
                        if not updated_bot:
                            self.app.db[db_collection].update_one(
                                {"_id": current_bot["_id"]},
                                {
                                    "$push": {
                                        "errors": f'Error updating trailling order {current_bot["_id"]}'
                                    }
                                },
                            )

                # Sell after hitting trailling stop_loss and if price already broken trailling
                if "trailling_stop_loss_price" in bot["deal"]:
                    price = bot["deal"]["trailling_stop_loss_price"]
                    # Direction 2 (downward): breaking the trailling_stop_loss
                    if float(close_price) <= float(price):
                        print(
                            f"Hit trailling_stop_loss_price {price}. Selling {symbol}"
                        )
                        try:
                            deal = CreateDealController(bot, db_collection)
                            deal.trailling_profit(price)
                        except Exception as error:
                            print(error)
                            return
                        self.terminate_websockets()
                        self.start_stream()
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

    def process_deals(self, result, ws):
        """
        Updates deals with klines websockets,
        when price and symbol match existent deal
        """
        if "k" in result:
            close_price = result["k"]["c"]
            symbol = result["k"]["s"]
            ws.symbol = symbol
            current_bot = self.app.db.bots.find_one(
                {"pair": symbol, "status": "active"}
            )
            current_test_bot = self.app.db.paper_trading.find_one(
                {"pair": symbol, "status": "active"}
            )
            if current_bot:
                self.process_deals_bot(current_bot, close_price, symbol, "bots")
            if current_test_bot:
                self.process_deals_bot(
                    current_test_bot, close_price, symbol, "paper_trading"
                )
            return
