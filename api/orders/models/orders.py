from account.account import Account
from tools.enum_definitions import EnumDefinitions
from tools.handle_error import json_response, json_response_error, json_response_message
from tools.round_numbers import round_numbers
from db import setup_db

poll_percentage = 0


class Orders(Account):
    def __init__(self):
        # Buy order
        self.side = EnumDefinitions.order_side[0]
        # Required by API for Limit orders
        self.timeInForce = EnumDefinitions.time_in_force[0]
        # Instance of app for cron jobs
        self.db = setup_db()

    def get_all_orders(self, status: str|None = None, limit:int=50, offset: int=0, startTime: float | None = None):
        # here we want to get the value of user (i.e. ?user=some-value)
        self.pages = self.db.orders.count()

        # Filters
        args = {}
        if status:
            args["status"] = status

        if startTime:
            args["time"] = {"$gte": startTime}

        orders = list(
            self.db.orders.find(args)
            .sort([("updateTime", -1)])
            .skip(offset)
            .limit(limit)
        )
        if orders:
            resp = json_response({"data": orders, "pages": self.pages})
        else:
            resp = json_response({"message": "Orders not found!"})
        return resp


    def get_open_orders(self):
        data = self.signed_request(url=self.order_url)

        if data and len(data) > 0:
            resp = json_response({"message": "Open orders found!", "data": data})
        else:
            resp = json_response_error("No open orders found!")
        return resp

    def delete_order(self, symbol: str, orderId: str):
        """
        Cancels single order by symbol
        - Optimal for open orders table
        """
        if not symbol:
            resp = json_response_error("Missing symbol parameter")
        if not orderId:
            resp = json_response_error("Missing orderid parameter")

        payload = {
            "symbol": symbol,
            "orderId": orderId,
        }
        try:
            data = self.signed_request(url=f'{self.order_url}', method="DELETE", payload=payload)
            resp = json_response({"message": "Order deleted!", "data": data})
        except Exception as e:
            resp = json_response_error(e)

        return resp

    def delete_all_orders(self, symbol):
        """
        Delete All orders by symbol
        - Optimal for open orders table
        """
        params = [
            ("symbol", symbol),
        ]
        data = self.signed_request(url=self.order_url, method="DELETE", params=params)

        if data and len(data) > 0:
            resp = json_response({"message": "Orders deleted", "data": data})
        else:
            resp = json_response_message("No open orders found!")
        return resp
