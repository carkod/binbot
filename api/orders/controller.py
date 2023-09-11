from account.account import Account
from tools.enum_definitions import OrderType, TimeInForce, OrderSide
from tools.handle_error import json_response, json_response_error, json_response_message
from tools.round_numbers import supress_notation
from decimal import Decimal


poll_percentage = 0

class OrderController(Account):
    def __init__(self) -> None:
        super().__init__()
        # Always GTC and limit orders
        # limit/market orders will be decided by matching_engine
        # PRICE_FILTER decimals
        self.price_precision = -1 * (
            Decimal(str(self.price_filter_by_symbol(self.active_bot.pair, "tickSize")))
            .as_tuple()
            .exponent
        )
        self.qty_precision = -1 * (
            Decimal(str(self.lot_size_by_symbol(self.active_bot.pair, "stepSize")))
            .as_tuple()
            .exponent
        )
        pass

    def sell_order(self, symbol, qty, price=None):
        """
        If price is not provided by matching engine,
        sell at market price
        """
        if price:
            price = float(self.matching_engine(symbol, False, qty))
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
        data = self.signed_request(
            url=self.order_url, method="POST", payload=payload
        )
        return data

    def buy_order(self, symbol, qty, price=None):

        if price:
            price = float(self.matching_engine(symbol, True, qty))
            payload = {
                "symbol": symbol,
                "side": OrderSide.buy,
                "type": OrderType.limit,
                "timeInForce": TimeInForce.gtc,
                "price": supress_notation(price, self.price_precision),
                "quantity": supress_notation(qty, self.qty_precision),
            }
        else:
            payload = {
                "symbol": symbol,
                "side": OrderSide.buy,
                "type": OrderType.market,
                "quantity": qty,
            }

        data = self.signed_request(url=self.order_url, method="POST", payload=payload)
        return data

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

        data = self.signed_request(url=self.margin_order, method="POST", payload=payload)
        if data["status"] != "FILLED":
            delete_payload = {
                "symbol": symbol,
                "isIsolated": "TRUE",
                "orderId": data["orderId"]
            }
            try:
                self.signed_request(url=self.margin_order, method="DELETE", payload=delete_payload)                
            except Exception as error:
                return
            
            self.buy_margin_order(symbol, qty)
            
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

        data = self.signed_request(url=self.margin_order, method="POST", payload=payload)

        if float(data["price"]) == 0:
            data["price"] = data["fills"][0]["price"]

        return data
