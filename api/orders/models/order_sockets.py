import json
import os

import requests
from api.tools.handle_error import handle_error
from api.tools.jsonresp import jsonResp, jsonResp_message
from websocket import create_connection, enableTrace


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

    def subscribe_exectionReport(self):
        url = self.base + self.path
        ws = create_connection(url)
        subscribe = json.dumps(
            {"method": "SUBSCRIBE", "params": ["executionReport"], "id": 1}
        )
        ws.send(subscribe)
        self.active_ws = ws
        response = ws.recv()
        result = json.loads(response)["result"]
        if not result:
            return True
        # ws.close()
        return False
        # data = ws.recv_data()

    async def get_stream(self, take_order_client_id=None):
        if not self.active_ws or not self.listen_key:
            self.listen_key = self.get_listenkey()["listenKey"]
            if self.subscribe_exectionReport():
                print("Subscribed to ExecutionReport!")
            else:
                print("Failed to subscribe to ExecutionReport!")

        url = self.base + self.path + "/" + self.listen_key
        async with create_connection(url) as websocket:
            result = await websocket.recv()
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

        if result["X"] == "FILLED" and client_order_id == take_order_client_id:
            self.close_stream()

        return order_result

    def close_stream(self):
        if self.active_ws:
            self.active_ws.close()
            print("Active socket closed")
