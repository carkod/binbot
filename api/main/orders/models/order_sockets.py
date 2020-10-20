import json
import os

import requests
from main.tools import handle_error
from websocket import create_connection


class OrderUpdates:
    def __init__(self):
        self.key = os.getenv("BINANCE_KEY")
        self.secret = os.getenv("BINANCE_SECRET")
        self.ws_base_url = os.getenv("WS_BASE")
        self.user_datastream_listenkey = os.getenv("USER_DATA_STREAM")
        self.all_orders_url = os.getenv("ALL_ORDERS")
        self.order_url = os.getenv("ORDER")

        # streams
        self.host = os.getenv("WS_BASE")
        self.port = os.getenv("WS_BASE_PORT")
        self.path = "/ws"
        self.active_ws = None

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

    def open_stream(self):
        url = self.host + ":" + self.port + self.path
        ws = create_connection(url)
        subscribe = json.dumps(
            {"method": "SUBSCRIBE", "params": ["executionReport"], "id": 1}
        )
        ws.send(subscribe)
        self.active_ws = ws
        result = ws.recv()
        result = json.loads(result)
        if not result["result"]:
            print("Received '%s'" % result)
            return True
        # ws.close()
        return False
        # data = ws.recv_data()

    def get_stream(self, listenkey):
        url = self.host + ":" + self.port + self.path + "/" + listenkey
        ws = create_connection(url)
        result = ws.recv()
        result = json.loads(result)

        # Parse result. Print result for raw result from Binance
        client_order_id = result["C"] if result["X"] == "CANCELED" else result["c"]
        order_result = [
            ("symbol", result["s"]),
            ("order_status", result["X"]),
            ("timestamp", result["E"]),
            ("client_order_id", client_order_id),
            ("created_at", result["O"]),
        ]

        print("order result %s", order_result)

        return order_result

    def close_stream(self):
        if self.active_ws:
            self.active_ws.close()
            print("Active socket closed")
