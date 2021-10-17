import hashlib
import hmac
import time as tm
from urllib.parse import urlparse

import requests
from api.account.account import Account
from api.tools.enum_definitions import EnumDefinitions
from api.tools.handle_error import handle_error
from api.tools.handle_error import jsonResp, jsonResp_message
from api.tools.round_numbers import round_numbers
from flask import current_app, request

poll_percentage = 0


class Orders(Account):

    def __init__(self):
        Account.__init__(self)
        # Buy order
        self.side = EnumDefinitions.order_side[0]
        # Required by API for Limit orders
        self.timeInForce = EnumDefinitions.time_in_force[0]
        # Instance of app for cron jobs

    def get_all_orders(self):
        # here we want to get the value of user (i.e. ?user=some-value)
        limit = 50 if not request.args.get("limit") else int(request.args.get("limit"))
        offset = (
            0 if not request.args.get("offset") else int(request.args.get("offset"))
        )
        self.pages = self.app.db.orders.count()
        status = request.args.get("status", None)
        startTime = (
            int(request.args.get("start-time", None))
            if request.args.get("start-time")
            else None
        )

        # Filters
        args = {}
        if status:
            args["status"] = status

        if startTime:
            args["time"] = {"$gte": startTime}

        orders = list(
            self.app.db.orders.find(args)
            .sort([("updateTime", -1)])
            .skip(offset)
            .limit(limit)
        )
        if orders:
            resp = jsonResp({"data": orders, "pages": self.pages})
        else:
            resp = jsonResp({"message": "Orders not found!"})
        return resp

    def poll_historical_orders(self):
        global poll_percentage
        url = self.all_orders_url
        symbols = self.get_exchange_info()["symbols"]
        symbols_count = len(symbols)

        # Empty collection first
        self.app.db.orders.remove()
        with self.app.app_context():
            for i in range(symbols_count):

                timestamp = int(round(tm.time() * 1000))
                params = [
                    ("symbol", symbols[i]["symbol"]),
                    ("timestamp", timestamp),
                    ("recvWindow", self.recvWindow),
                ]
                data = self._user_data_request(url=self.order_url, params=params)

                # Check that we have no empty orders
                if (len(data) > 0) and self.app:
                    for o in data:
                        # Save in the DB
                        self.app.db.orders.save(
                            o, {"$currentDate": {"createdAt": "true"}}
                        )
                        if i == (symbols_count - 1):
                            poll_percentage = 0
                        else:
                            poll_percentage = round_numbers(
                                (i / symbols_count) * 100, 0
                            )
                print(f"Polling historical orders: {poll_percentage}")

    def get_open_orders(self):
        timestamp = int(round(tm.time() * 1000))
        url = self.open_orders
        params = [("timestamp", timestamp), ("recvWindow", self.recvWindow)]
        data = self._user_data_request(url=self.order_url, params=params)

        if len(data) > 0:
            resp = jsonResp({"message": "Open orders found!", "data": data})
        else:
            resp = jsonResp_message("No open orders found!")
        return resp

    def delete_order(self):
        """
        Cancels single order by symbol
        - Optimal for open orders table
        """
        timestamp = int(round(tm.time() * 1000))
        url = self.order_url
        symbol = request.view_args["symbol"]
        orderId = request.view_args["orderid"]
        params = [
            ("symbol", symbol),
            ("timestamp", timestamp),
            ("recvWindow", self.recvWindow),
            ("orderId", orderId),
        ]
        data = self._user_data_request(url=self.order_url, method="DELETE", params=params)

        if len(data) > 0:
            resp = jsonResp({"message": "Order deleted!", "data": data})
        else:
            resp = jsonResp_message("Failed to delete order")
        return resp

    def delete_all_orders(self):
        """
        Delete All orders by symbol
        - Optimal for open orders table
        """
        symbol = request.args["symbol"]
        timestamp = int(round(tm.time() * 1000))
        url = self.open_orders
        # query params -> args
        # path params -> view_args
        symbol = request.args["symbol"]
        params = [
            ("symbol", symbol),
            ("timestamp", timestamp),
            ("recvWindow", self.recvWindow),
        ]
        data = self._user_data_request(url=self.order_url, method="DELETE", params=params)

        if len(data) > 0:
            resp = jsonResp({"message": "Orders deleted", "data": data})
        else:
            resp = jsonResp_message("No open orders found!")
        return resp
