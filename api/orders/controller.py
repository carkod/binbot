from time import time
from uuid import uuid4
from account.account import Account
from tools.exceptions import DeleteOrderError
from tools.enum_definitions import OrderType, TimeInForce, OrderSide
from tools.handle_error import json_response, json_response_message
from tools.round_numbers import supress_notation, zero_remainder


class OrderController(Account):
    """
    Always GTC and limit orders
    limit/market orders will be decided by matching_engine
    PRICE_FILTER decimals

    Methods and attributes here are all unrelated to database operations
    this is highly tied to the Binance API
    """

    def __init__(self) -> None:
        super().__init__()
        # Inherted attributes
        self.price_precision: int
        self.qty_precision: int
        pass

    def generate_id(self):
        return uuid4()

    def simulate_order(self, pair, side, qty=1):
        """
        Price is determined by market
        to help trigger the order immediately
        """
        price = float(self.matching_engine(pair, True, qty))
        order = {
            "symbol": pair,
            "orderId": self.generate_id().int,
            "orderListId": -1,
            "clientOrderId": self.generate_id().hex,
            "transactTime": time() * 1000,
            "price": price,
            "origQty": qty,
            "executedQty": qty,
            "cummulativeQuoteQty": qty,
            "status": "FILLED",
            "timeInForce": "GTC",
            "type": "LIMIT",
            "side": side,
            "fills": [],
        }
        return order

    def simulate_response_order(self, pair, side, qty=1):
        price = float(self.matching_engine(pair, True, qty))
        response_order = {
            "symbol": pair,
            "orderId": self.generate_id().int,
            "orderListId": -1,
            "clientOrderId": self.generate_id().hex,
            "transactTime": time() * 1000,
            "price": price,
            "origQty": qty,
            "executedQty": qty,
            "cummulativeQuoteQty": qty,
            "status": "FILLED",
            "timeInForce": "GTC",
            "type": "LIMIT",
            "side": side,
            "fills": [],
        }
        return response_order

    def simulate_margin_order(self, pair, side: OrderSide):
        """
        Quantity doesn't matter, as it is not a real order that needs
        to be process by the exchange

        Args:
        - symbol and pair are used interchangably
        - side: buy or sell
        """
        qty = 1
        price = float(self.matching_engine(pair, True, qty))
        order = {
            "symbol": pair,
            "orderId": self.generate_id().int,
            "orderListId": -1,
            "clientOrderId": self.generate_id().hex,
            "transactTime": time() * 1000,
            "price": price,
            "origQty": qty,
            "executedQty": qty,
            "cummulativeQuoteQty": qty,
            "status": "FILLED",
            "timeInForce": "GTC",
            "type": "LIMIT",
            "side": side,
            "marginBuyBorrowAmount": 5,
            "marginBuyBorrowAsset": "BTC",
            "isIsolated": "true",
            "fills": [],
        }
        return order

    def sell_order(self, symbol, qty, price=None):
        """
        If price is not provided by matching engine,
        sell at market price
        """
        price = float(self.matching_engine(symbol, False, qty))
        if price:
            payload = {
                "symbol": symbol,
                "side": OrderSide.sell,
                "type": OrderType.limit,
                "timeInForce": TimeInForce.gtc,
                "price": supress_notation(price, self.price_precision),
                "quantity": supress_notation(qty, self.qty_precision),
            }
        else:
            payload = {
                "symbol": symbol,
                "side": OrderSide.sell,
                "type": OrderType.market,
                "quantity": supress_notation(qty, self.qty_precision),
            }
            # Because market orders don't have price
            # get it from fills

        data = self.signed_request(url=self.order_url, method="POST", payload=payload)

        if float(data["price"]) == 0:
            total_qty: float = 0
            weighted_avg: float = 0
            for item in data["fills"]:
                weighted_avg += float(item["price"]) * float(item["qty"])
                total_qty += float(item["qty"])

            weighted_avg_price = weighted_avg / total_qty
            data["price"] = weighted_avg_price

        return data

    def buy_order(self, symbol, qty, price=None):
        if price:
            book_price = float(self.matching_engine(symbol, True, qty))
            payload = {
                "symbol": symbol,
                "side": OrderSide.buy,
                "type": OrderType.limit,
                "timeInForce": TimeInForce.gtc,
                "price": supress_notation(book_price, self.price_precision),
                "quantity": supress_notation(qty, self.qty_precision),
            }
            # If price is not provided by matching engine,
            # create iceberg orders
            if not book_price:
                payload["iceberg_qty"] = zero_remainder(qty)
                payload["price"] = supress_notation(book_price, self.price_precision)

        else:
            payload = {
                "symbol": symbol,
                "side": OrderSide.buy,
                "type": OrderType.market,
                "quantity": qty,
            }

        data = self.signed_request(url=self.order_url, method="POST", payload=payload)

        if data["price"] == 0:
            total_qty: float = 0
            weighted_avg: float = 0
            for item in data["fills"]:
                weighted_avg += float(item["price"]) * float(item["qty"])
                total_qty += float(item["qty"])

            weighted_avg_price = weighted_avg / total_qty
            data["price"] = weighted_avg_price

        return data

    def delete_order(self, symbol: str, orderId: int):
        """
        Cancels single order by symbol
        - Optimal for open orders table
        """
        if not symbol:
            raise DeleteOrderError("Missing symbol parameter")
        if not orderId:
            raise DeleteOrderError("Missing orderid parameter")

        payload = {
            "symbol": symbol,
            "orderId": orderId,
        }
        data = self.signed_request(
            url=f"{self.order_url}", method="DELETE", payload=payload
        )
        return data

    def delete_all_orders(self, symbol):
        """
        Delete All orders by symbol
        - Optimal for open orders table
        """
        data = self.signed_request(
            url=self.order_url,
            method="DELETE",
            payload={
                "symbol": symbol,
            },
        )

        if data and len(data) > 0:
            resp = json_response({"message": "Orders deleted", "data": data})
        else:
            resp = json_response_message("No open orders found!")
        return resp

    def buy_margin_order(self, symbol, qty, price=None):
        """
        python-binance wrapper function to make it less verbose and less dependant
        """
        if price:
            price = float(self.matching_engine(symbol, True, qty))
            payload = {
                "symbol": symbol,
                "side": OrderSide.buy,
                "type": OrderType.limit,
                "timeInForce": TimeInForce.gtc,
                "quantity": qty,
                "price": price,
                "isIsolated": "TRUE",
            }
        else:
            payload = {
                "symbol": symbol,
                "side": OrderSide.buy,
                "type": OrderType.market,
                "quantity": qty,
                "isIsolated": "TRUE",
            }

        data = self.signed_request(
            url=self.margin_order, method="POST", payload=payload
        )

        return data

    def sell_margin_order(self, symbol, qty, price=None):
        """
        python-binance wrapper function to make it less verbose and less dependant
        """
        if price:
            price = float(self.matching_engine(symbol, False, qty))
            payload = {
                "symbol": symbol,
                "side": OrderSide.sell,
                "type": OrderType.limit,
                "timeInForce": TimeInForce.gtc,
                "quantity": qty,
                "price": price,
                "isIsolated": "TRUE",
            }
        else:
            payload = {
                "symbol": symbol,
                "side": OrderSide.sell,
                "type": OrderType.market,
                "quantity": qty,
                "isIsolated": "TRUE",
            }

        data = self.signed_request(
            url=self.margin_order, method="POST", payload=payload
        )

        if float(data["price"]) == 0:
            data["price"] = data["fills"][0]["price"]

        return data
