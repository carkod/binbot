import json
import threading
from pymongo import ReturnDocument

from api.account.account import Account
from api.app import create_app
from api.deals.controllers import CreateDealController
from websocket import WebSocketApp

class MarketUpdates(Account):
    """
    Further explanation in docs/market_updates.md
    """

    def __init__(self, interval="5m"):
        self.app = create_app()
        self.markets_streams = None
        self.interval = interval
        self.markets = []
    
    def _restart_websockets(self, thread_name="market_updates"):
        """
        Restart websockets threads after list of active bots altered
        """
        print("Starting thread cleanup")
        global stop_threads
        stop_threads = True
        # Notify market updates websockets to update
        for thread in threading.enumerate():
            print("Currently active threads: ", thread.name)
            if (
                hasattr(thread, "tag")
                and thread_name in thread.name
                and hasattr(thread, "_target")
            ):
                stop_threads = False
                print("closing websocket")
                thread._target.__self__.close()

        pass

    def start_stream(self, ws=None):
        """
        Start/restart websocket streams
        """
        # Close websocekts before starting
        if self.markets_streams:
            self.markets_streams.close()
        if ws:
            ws.close()

        self.markets = list(self.app.db.bots.distinct("pair", {"status": "active"}))
        paper_trading_bots = list(self.app.db.paper_trading.distinct("pair", {"status": "active"}))
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
        self._restart_websockets()
        self.start_stream(ws)

    def on_message(self, ws, message):
        json_response = json.loads(message)

        if "result" in json_response:
            print(f'Subscriptions: {json_response["result"]}')

        if "data" in json_response:
            if "e" in json_response["data"] and json_response["data"]["e"] == "kline":
                self.process_deals(json_response["data"], ws)
            else:
                print(f'Error: {json_response["data"]}')

    def process_deals_bot(self, current_bot, close_price, symbol, ws, db_collection):
        """
        Processes the deal market websocket price updates

        It updates the bots deals, safety orders, trailling orders, stop loss
        for both paper trading test bots and real bots
        """
        if current_bot and "deal" in current_bot:
            # Update Current price only for active bots
            # This is to keep historical profit intact
            bot = self.app.db[db_collection].find_one_and_update(
                {"_id": current_bot["_id"]},
                {"$set": {"deal.current_price": close_price}},
                return_document=ReturnDocument.AFTER
            )

            # Stop loss
            if (
                "stop_loss" in current_bot
                and float(current_bot["stop_loss"]) > 0.0
                and "stop_loss_price" in current_bot["deal"]
                and float(current_bot["deal"]["stop_loss_price"]) > float(close_price)
            ):
                deal = CreateDealController(bot, db_collection)
                deal.execute_stop_loss(close_price)
                return

            # Take profit trailling
            if bot["trailling"] == "true" and bot["deal"]["buy_price"] != "":

                if ("trailling_stop_loss_price" not in bot["deal"] or bot["deal"]["trailling_stop_loss_price"] == 0) or float(
                    bot["deal"]["take_profit_price"]
                ) <= 0:
                    # If current price didn't break take_profit
                    current_take_profit_price = float(bot["deal"]["buy_price"]) * (
                        1 + (float(bot["take_profit"]) / 100)
                    )
                    print(f'{symbol} Updated (Didn\'t break trailling)')
                else:
                    # If current price broke take profit, we start trailling
                    # This is necessary to avoid conflict between trailling take profit and safety orders
                    current_take_profit_price = float(
                        bot["deal"]["trailling_stop_loss_price"]
                    ) * (1 + (float(bot["take_profit"]) / 100))

                if float(close_price) >= float(current_take_profit_price):
                    new_take_profit = current_take_profit_price * (
                        1 + (float(bot["take_profit"]) / 100)
                    )
                    # Update deal take_profit
                    bot["deal"]["take_profit_price"] = new_take_profit
                    # Update trailling_stop_loss
                    bot["deal"][ "trailling_stop_loss_price"] = float(
                        new_take_profit
                    ) - (
                        float(new_take_profit)
                        * (float(bot["trailling_deviation"]) / 100)
                    )
                    print(f'{symbol} Updating take_profit_price, trailling_profit and trailling_stop_loss_price! {new_take_profit}')
                    updated_bot = self.app.db[db_collection].update_one(
                        {"_id": current_bot["_id"]}, {"$set": {"deal": bot["deal"]}}
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
                    if float(close_price) <= float(price):
                        print(f"Hit trailling_stop_loss_price {price}. Selling {symbol}")
                        deal = CreateDealController(bot, db_collection)
                        try:
                            deal.trailling_profit(price)
                            self._restart_websockets()
                            self.start_stream(ws)
                        except Exception as error:
                            return

            # Open safety orders
            # When bot = None, when bot doesn't exist (unclosed websocket)
            if (
                "safety_orders" in bot
                and len(bot["safety_orders"]) > 0
            ):
                for key, so in enumerate(bot["safety_orders"]):
                    # Index is the ID of the safety order price that matches safety_orders list
                    if ("status" in so and so["status"] == 0) and float(so["buy_price"]) >= float(close_price):
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

            self.process_deals_bot(current_bot, close_price, symbol, ws, "bots")
            self.process_deals_bot(current_test_bot, close_price, symbol, ws, "paper_trading")
