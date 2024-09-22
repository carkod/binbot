from account.account import Account
from tools.exceptions import DeleteOrderError
from database.mongodb.db import Database
from tools.enum_definitions import OrderType, TimeInForce, OrderSide
from tools.handle_error import json_response, json_response_message
from tools.round_numbers import supress_notation


poll_percentage = 0


class OrderController(Database, Account):
    """
    Always GTC and limit orders
    limit/market orders will be decided by matching_engine
    PRICE_FILTER decimals
    """

    def __init__(self) -> None:
        super().__init__()
        self.save_bot_streaming = self.save_bot_streaming
        pass

    @property
    def price_precision(self, symbol):
        if self._price_precision == 0:
            self._price_precision = self.calculate_price_precision(symbol)

        return self._price_precision

    @property
    def qty_precision(self, symbol):
        if self._qty_precision == 0:
            self._qty_precision = self.calculate_qty_precision(symbol)

        return self._qty_precision

    def zero_remainder(self, x):
        number = x

        while True:
            if number % x == 0:
                return number
            else:
                number += x

    def sell_order(self, symbol, qty, price=None):
        """
        If price is not provided by matching engine,
        sell at market price
        """
        if price:
            book_price = float(self.matching_engine(symbol, False, qty))
            payload = {
                "symbol": symbol,
                "side": OrderSide.sell,
                "type": OrderType.limit,
                "timeInForce": TimeInForce.gtc,
                "price": supress_notation(price, self.price_precision(symbol)),
                "quantity": supress_notation(qty, self.qty_precision),
            }

            # If price is not provided by matching engine,
            # create iceberg orders
            if not book_price:
                payload["iceberg_qty"] = self.zero_remainder(qty)
                payload["price"] = supress_notation(book_price, self.price_precision(symbol))
            
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
            total_qty = 0
            weighted_avg = 0
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
                "price": supress_notation(book_price, self.price_precision(symbol)),
                "quantity": supress_notation(qty, self.qty_precision),
            }
            # If price is not provided by matching engine,
            # create iceberg orders
            if not book_price:
                payload["iceberg_qty"] = self.zero_remainder(qty)
                payload["price"] = supress_notation(book_price, self.price_precision(symbol))

        else:
            payload = {
                "symbol": symbol,
                "side": OrderSide.buy,
                "type": OrderType.market,
                "quantity": qty,
            }

        data = self.signed_request(url=self.order_url, method="POST", payload=payload)

        if data["price"] == 0:
            total_qty = 0
            weighted_avg = 0
            for item in data["fills"]:
                weighted_avg += float(item["price"]) * float(item["qty"])
                total_qty += float(item["qty"])

            weighted_avg_price = weighted_avg / total_qty
            data["price"] = weighted_avg_price

        return data

    def delete_order(self, symbol: str, orderId: str):
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
        params = [
            ("symbol", symbol),
        ]
        data = self.signed_request(url=self.order_url, method="DELETE", params=params)

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
