import json

from requests import HTTPError
from api.apis import BinanceApi
from api.tools.enum_definitions import EnumDefinitions
from api.tools.handle_error import handle_error, jsonResp_error_message
from flask import request


class SellOrder(BinanceApi):
    """
    Simple Binance Sell Order
    """

    def __init__(self):

        # Buy order
        self.side = EnumDefinitions.order_side[1]
        # Required by API for Limit orders
        self.timeInForce = EnumDefinitions.time_in_force[0]

    def post_order_limit(self):
        """
        Returns successful order
        Returns validation failed order (MIN_NOTIONAL, LOT_SIZE etc..)
        """
        data = json.loads(request.data)
        symbol = data["pair"]
        qty = data["qty"]
        price = data["price"]

        # Limit order
        order_type = EnumDefinitions.order_types[0]

        # Get data for a single crypto e.g. BTT in BNB market
        payload = {
            "symbol": symbol,
            "side": self.side,
            "type": order_type,
            "timeInForce": self.timeInForce,
            "price": price,
            "quantity": qty,
        }
        try:
            data = self.signed_request(url=self.order_url, method="POST", payload=payload)
        except HTTPError as e:
            return jsonResp_error_message(e)
        return data

    def post_take_profit_limit(self):
        """
        Returns successful order
        Returns validation failed order (MIN_NOTIONAL, LOT_SIZE etc..)
        """
        data = json.loads(request.data)
        symbol = data["pair"]
        qty = data["qty"]
        price = data["price"]
        stop_price = data["stop_price"] if "stop_price" in data else price

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
            "newOrderRespType": "FULL",
        }
        data = self.signed_request(url=self.order_url, method="POST", payload=payload)
        return data

    def post_stop_loss_limit(self):
        """
        Returns successful order
        Returns validation failed order (MIN_NOTIONAL, LOT_SIZE etc..)
        """
        data = json.loads(request.data)
        symbol = data["pair"]
        qty = data["qty"]
        price = data["price"]
        stop_price = data["stop_price"] if "stop_price" in data else price

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
