import json
import os

import requests
from api.deals.deal_updates import DealUpdates
from api.tools.handle_error import handle_error
from api.tools.jsonresp import jsonResp, jsonResp_message
from flask import current_app
from websocket import WebSocketApp, create_connection, enableTrace


class KlineSockets:
    def __init__(self, app, symbol="BNBBTC", subs=True, interval="30m"):
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
        """
        Activate kline stream when bot activates SO
        @params:
        - id: ObjectId
        - symbol: string (e.g. BNBBTC, later needs to be lowercased)
        - subs: bool (True = SUBSCRIBE otherwise UNSUBSCRIBE)
        """
        url = f"{self.base}{self.path}/{self.symbol.lower()}@kline_{self.interval}"
        ws = WebSocketApp(
            url,
            on_open=self.on_open,
            on_error=self.on_error,
            on_close=self.close_stream,
            on_message=self.on_message,
        )

        ws.run_forever()

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
        try:
            result = response["e"]
        except KeyError:
            print(f"Error: {result}")

        if response["e"] == "kline":
            self.process_kline_stream(response)

    def process_kline_stream(self, result):
        if result["k"]["x"]:
            close_price = result["k"]["c"]
            close_time = result["k"]["T"]
            symbol = result["k"]["s"]
