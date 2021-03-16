import json
import os

import requests
from api.tools.handle_error import handle_error
from api.tools.jsonresp import jsonResp, jsonResp_message
from websocket import create_connection, enableTrace, WebSocketApp


class OrderUpdates:
    def __init__(self):
        self.key = os.getenv("BINANCE_KEY")
        self.secret = os.getenv("BINANCE_SECRET")
        self.user_datastream_listenkey = os.getenv("USER_DATA_STREAM")
        self.all_orders_url = os.getenv("ALL_ORDERS")
        self.order_url = os.getenv("ORDER")

        # streams
        self.base = os.getenv("WS_BASE")
        self.path = "/ws"
        self.active_ws = None
        self.listenkey = None

        enableTrace(True)

    def get_listenkey(self):
        url = self.user_datastream_listenkey

        # Get data for a single crypto e.g. BTT in BNB market
        params = []
        headers = {"X-MBX-APIKEY": self.key}
        url = self.user_datastream_listenkey

        # Response after request
        res = requests.post(url=url, params=params, headers=headers)
        handle_error(res)
        data = res.json()
        return data

    def get_stream(self):
        if not self.active_ws or not self.listen_key:
            self.listen_key = self.get_listenkey()["listenKey"]

        url = self.base + self.path + "/" + self.listen_key
        ws = create_connection(url, on_open=self.on_open, on_error=self.on_error, on_close=self.close_stream)
        result = ws.recv()
        result = json.loads(result)
        # Parse result. Print result for raw result from Binance
        client_order_id = result["C"] if result["X"] == "CANCELED" else result["c"]
        order_result = {
            "symbol": result["s"],
            "order_status": result["X"],
            "timestamp": result["E"],
            "client_order_id": client_order_id,
            "created_at": result["O"],
        }

        print(f"Stream returned an order update!{order_result}")

    def close_stream(self, ws):
        if self.active_ws:
            self.active_ws.close()
            print("Active socket closed")

    def on_open(self, ws):
        print("Open")

    def on_error(self, ws, error):
        print(f"Error: {error}")
