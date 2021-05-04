import json
import os

import requests
from flask import current_app
from api.tools.handle_error import handle_error
from api.tools.jsonresp import jsonResp, jsonResp_message
from websocket import create_connection, enableTrace, WebSocketApp
from api.deals.deal_updates import DealUpdates

class OrderUpdates:
    def __init__(self, app):
        self.key = os.getenv("BINANCE_KEY")
        self.secret = os.getenv("BINANCE_SECRET")
        self.user_datastream_listenkey = os.getenv("USER_DATA_STREAM")
        self.all_orders_url = os.getenv("ALL_ORDERS")
        self.order_url = os.getenv("ORDER")

        # streams
        self.base = os.getenv("WS_BASE")
        self.path = "/stream"
        self.active_ws = None
        self.listenkey = None
        self.app = app

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

        url = self.base + self.path + "?streams=" + self.listen_key
        ws = create_connection(
            url,
            on_open=self.on_open,
            on_error=self.on_error,
            on_close=self.close_stream,
        )
        self.active_ws = ws
        result = json.loads(ws.recv())["data"]
        print("Received socket data:")
        print(result)
        if result["e"] == "executionReport":
            self.process_report_execution(result)
    
    def kline_stream(self, id, symbol, subs=True, interval="1d"):
        """
        Activate kline stream when bot activates SO
        @params: 
        - id: ObjectId
        - symbol: string (e.g. BNBBTC, later needs to be lowercased)
        - subs: bool (True = SUBSCRIBE otherwise UNSUBSCRIBE)
        """
        if not self.active_ws or not self.listen_key:
            self.listen_key = self.get_listenkey()["listenKey"]
        url = self.base + self.path + "?streams=" + self.listen_key
        ws = create_connection(
            url,
            on_open=self.on_open,
            on_error=self.on_error,
            on_close=self.close_stream,
        )
        request = {
            "method": "SUBSCRIBE" if subs else "UNSUBSCRIBE",
            "params": [
                f"{symbol.lower()}@kline_{interval}",
            ],
            "id": 1
        }
        ws.send(json.dumps(request))
        response = json.loads(ws.recv())
        if "error" not in response:
            list_subs_req = {
                "method": "LIST_SUBSCRIPTIONS",
                "id": 2
            }
            ws.send(json.dumps(list_subs_req))
            response = json.loads(ws.recv())
            if "error" not in response:
                for subs in response["result"]:
                    if subs == f"{symbol.lower()}@kline_{interval}":
                        print(f"Successfully subscribed to {symbol}")
            else:
                print(response["error"]["msg"])
        else:
            print(response["error"]["msg"])
        self.close_stream(ws)

    def close_stream(self, ws):
        if self.active_ws:
            self.active_ws.close()
            print("Active socket closed")

    def on_open(self, ws):
        print("Open")

    def on_error(self, ws, error):
        print(f"Error: {error}")

    def process_report_execution(self, result):
        # Parse result. Print result for raw result from Binance
        order_id = result["i"]
        order_result = {
            "symbol": result["s"],
            "order_status": result["X"],
            "timestamp": result["E"],
            "order_id": order_id,
            "created_at": result["O"],
        }

        if result["X"] == "FILLED":
            # Close successful orders
            completed = self.app.db.bots.find_one_and_update(
                {
                    "orders": {
                        "$elemMatch": {"deal_type": "take_profit", "order_id": order_id }
                    }
                },
                {"$set": {"active": "false"}},
            )
            if completed:
                print(f"Bot take_profit completed! Bot {completed['_id']} deactivated")

            # Update Safety orders
            order_price = float(result["p"])
            bot = self.app.db.bots.find_one(
                {
                    "orders": {
                        "$elemMatch": {
                            "deal_type": "safety_order",
                            "order_id": order_id,
                        }
                    }
                }
            )

            if bot:
                # It is a safety order, now find safety order deal price
                deal = DealUpdates(bot, self.app)
                deal.default_deal.update(bot)
                order = deal.update_take_profit(order_id)

        else:
            print(f"No bot found with order client order id: {order_id}")
