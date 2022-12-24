from apis import BinanceApi
from tools.enum_definitions import EnumDefinitions
from flask import request
from tools.round_numbers import supress_notation
from account.account import Account
from tools.handle_error import json_response_error
from requests.exceptions import HTTPError

class BuyOrder(Account):
    """
    Binance Post order
    """


    def __init__(self):

        # Buy order
        self.side = EnumDefinitions.order_side[0]
        # Required by API for Limit orders
        self.timeInForce = EnumDefinitions.time_in_force[0]

    def post_order_limit(self):
        symbol = request.json.get("pair")
        qty = request.json.get("qty")
        price = request.json.get("price")

        # Limit order
        order_type = EnumDefinitions.order_types[0]
        qty_precision = self.get_qty_precision(symbol)

        # Get data for a single crypto e.g. BTT in BNB market
        payload = {
            "symbol": symbol,
            "side": self.side,
            "type": order_type,
            "timeInForce": self.timeInForce,
            "price": price,
            "quantity": supress_notation(qty, qty_precision),
        }
        try:
            data = self.signed_request(url=self.order_url, method="POST", payload=payload)
        except HTTPError as e:
            return json_response_error(e)
        return data

    def post_order_market(self):
        symbol = request.json.get("pair")
        qty = request.json.get("qty")

        # Limit order
        order_type = EnumDefinitions.order_types[1]

        # Get data for a single crypto e.g. BTT in BNB market
        payload = {
            "symbol": symbol,
            "side": self.side,
            "type": order_type,
            "timeInForce": self.timeInForce,
            "quantity": qty,
        }
        data = self.signed_request(url=self.order_url, method="POST", payload=payload)
        return data

    def post_take_profit_limit(self):
        symbol = request.json.get("pair")
        qty = request.json.get("qty")
        price = request.json.get("price")
        stop_price = (
            request.json.get("stop_price") if request.json.get("stop_price") else price
        )

        # Limit order
        order_type = EnumDefinitions.order_types[5]

        # Get data for a single crypto e.g. BTT in BNB market
        payload = {
            "symbol": symbol,
            "side": self.side,
            "type": order_type,
            "timeInForce": self.timeInForce,
            "price": price,
            "stopPrice": stop_price,
            "quantity": qty,
        }
        data = self.signed_request(url=self.order_url, method="POST", payload=payload)
        return data

    def post_stop_loss_limit(self):
        symbol = request.json.get("pair")
        qty = request.json.get("qty")
        price = request.json.get("price")
        stop_price = (
            request.json.get("stop_price") if request.json.get("stop_price") else price
        )

        # Limit order
        order_type = EnumDefinitions.order_types[3]

        # Get data for a single crypto e.g. BTT in BNB market
        payload = {
            "symbol": symbol,
            "side": self.side,
            "type": order_type,
            "timeInForce": self.timeInForce,
            "price": price,
            "stopPrice": stop_price,
            "quantity": qty,
            "newOrderRespType": "FULL",
        }
        data = self.signed_request(url=self.order_url, method="POST", payload=payload)
        return data
