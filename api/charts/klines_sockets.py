import json
import os

import requests
from api.deals.deal_updates import DealUpdates
from websocket import WebSocketApp, enableTrace
import threading
class KlineSockets:
    def __init__(self, app, symbol="BNBBTC", subs=True, interval="1m"):
        self.key = os.getenv("BINANCE_KEY")
        self.secret = os.getenv("BINANCE_SECRET")
        self.user_datastream_listenkey = os.getenv("USER_DATA_STREAM")
        self.all_orders_url = os.getenv("ALL_ORDERS")
        self.order_url = os.getenv("ORDER")

        # streams
        self.base = os.getenv("WS_BASE")
        self.path = "/ws"
        self.app = app
        self.symbol = symbol
        self.subs = subs
        self.interval = interval

        enableTrace(True)

    def start_stream(self):
        # Start stream
        url = f"{self.base}{self.path}/{self.symbol.lower()}@kline_{self.interval}"
        ws = WebSocketApp(
            url,
            on_open=self.on_open,
            on_error=self.on_error,
            on_close=self.close_stream,
            on_message=self.on_message,
        )
        wst = threading.Thread(target=ws.run_forever)
        wst.start()
        return

    def close_stream(self, ws):
        ws.close()
        print("Active socket closed")

    def on_open(self, ws):
        print("Sockets stream opened")
        request = {
            "method": "SUBSCRIBE" if self.subs else "UNSUBSCRIBE",
            "params": [
                f"{self.symbol.lower()}@kline_{self.interval}",
            ],
            "id": 2,
        }
        ws.send(json.dumps(request))

    def on_error(self, ws, error):
        print(f"Websocket error: {error}")

    def on_message(self, wsapp, message):
        print("On Message executed")
        response = json.loads(message)

        if "result" in response and response["result"]:
            print(f'Subscriptions: {response["result"]}')

        elif "e" in response and response["e"] == "kline":
            self.process_kline_stream(response)

        else:
            print(f"Error: {response}")

    def process_kline_stream(self, result):
        if result["k"]["x"]:
            close_price = result["k"]["c"]
            close_time = result["k"]["T"]
            symbol = result["k"]["s"]

            # Update Current price
            bot = self.app.db.bots.find_one_and_update(
                {"pair": symbol}, {"$set": {"deal.current_price": close_price}}
            )

            # Open safety orders
            if "safety_order_prices" in bot["deal"]:
                for index, price in enumerate(bot["deal"]["safety_order_prices"]):
                    # Index is the ID of the safety order price that matches safety_orders list
                    if float(price) == float(close_price):
                        deal = DealUpdates(bot, self.app)
                        # No need to pass price to update deal
                        # The price already matched market price
                        deal.so_update_deal(index)
