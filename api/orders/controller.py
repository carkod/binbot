from time import time
from uuid import uuid4
from account.account import Account
from tools.exceptions import DeleteOrderError
from tools.enum_definitions import OrderType, TimeInForce, OrderSide
from tools.handle_error import json_response, json_response_message
from tools.round_numbers import supress_notation, zero_remainder, round_timestamp
from database.symbols_crud import SymbolsCrud


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
        self.symbols_crud = SymbolsCrud()
        pass

    def generate_id(self):
        return uuid4()

    def generate_short_id(self):
        id = uuid4().int
        return int(str(id)[:8])

    def get_ts(self):
        """
        Get timestamp in milliseconds
        """
        return round_timestamp(time() * 1000)

    def calculate_price_precision(self, symbol: str) -> int:
        """
        Calculate the price precision for the symbol
        taking data from API db
        """
        symbol_info = self.symbols_crud.get_symbol(symbol)
        return symbol_info.price_precision

    def calculate_qty_precision(self, symbol: str) -> int:
        """
        Calculate the quantity precision for the symbol
        taking data from API db
        """
        symbol_info = self.symbols_crud.get_symbol(symbol)
        return symbol_info.qty_precision

    def simulate_order(self, pair: str, side: OrderSide, qty=1):
        """
        Price is determined by market
        to help trigger the order immediately
        """
        price = float(self.matching_engine(pair, True, qty))
        order = {
            "symbol": pair,
            "orderId": self.generate_short_id(),
            "orderListId": -1,
            "clientOrderId": self.generate_id().hex,
            "transactTime": self.get_ts(),
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

    def simulate_response_order(self, pair: str, side: OrderSide, qty=1):
        price = float(self.matching_engine(pair, True, qty))
        response_order = {
            "symbol": pair,
            "orderId": self.generate_short_id(),
            "orderListId": -1,
            "clientOrderId": self.generate_id().hex,
            "transactTime": self.get_ts(),
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
        price = float(self.matching_engine(pair, False, qty))
        order = {
            "symbol": pair,
            "orderId": self.generate_short_id(),
            "orderListId": -1,
            "clientOrderId": self.generate_id().hex,
            "transactTime": self.get_ts(),
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

    def sell_order(self, symbol: str, qty: float):
        """
        If price is not provided by matching engine,
        sell at market price
        """
        price = float(self.matching_engine(symbol, True, qty))
        if price > 0:
            payload = {
                "symbol": symbol,
                "side": OrderSide.sell,
                "type": OrderType.limit,
                "timeInForce": TimeInForce.fok,
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

        data = self.signed_request(url=self.order_url, method="POST", payload=payload)
        # Fixed expired orders
        if data["status"] == "EXPIRED":
            data = self.signed_request(
                url=self.order_url, method="POST", payload=payload
            )

        return data

    def buy_order(self, symbol: str, qty: float):
        book_price = self.matching_engine(symbol, False, qty)

        if book_price > 0:
            payload = {
                "symbol": symbol,
                "side": OrderSide.buy,
                "type": OrderType.limit,
                "timeInForce": TimeInForce.fok,
                "price": supress_notation(book_price, self.price_precision),
                "quantity": supress_notation(qty, self.qty_precision),
            }
            # If price is not provided by matching engine,
            # create iceberg orders
            if not book_price:
                payload["iceberg_qty"] = zero_remainder(qty)
                payload["price"] = supress_notation(book_price, self.price_precision)

        else:
            # Use market price if matching engine can't find a price
            payload = {
                "symbol": symbol,
                "side": OrderSide.buy,
                "type": OrderType.market,
                "quantity": supress_notation(qty, self.qty_precision),
            }

        data = self.signed_request(url=self.order_url, method="POST", payload=payload)

        if data["status"] == "EXPIRED":
            data = self.signed_request(
                url=self.order_url, method="POST", payload=payload
            )

        return data

    def delete_order(self, symbol: str, order_id: int):
        """
        Cancels single order by symbol
        - Optimal for open orders table
        """
        if not symbol:
            raise DeleteOrderError("Missing symbol parameter")
        if not order_id:
            raise DeleteOrderError("Missing order_id parameter")

        payload = {
            "symbol": symbol,
            "orderId": order_id,
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

    def buy_margin_order(self, symbol: str, qty: float):
        """
        python-binance wrapper function to make it less verbose and less dependant
        """
        price = self.matching_engine(symbol, False, qty)

        if price > 0:
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

    def sell_margin_order(self, symbol: str, qty: float):
        """
        python-binance wrapper function to make it less verbose and less dependant
        """
        price = self.matching_engine(symbol, True, qty)

        if price > 0:
            payload = {
                "symbol": symbol,
                "side": OrderSide.sell,
                "type": OrderType.limit,
                "timeInForce": TimeInForce.gtc,
                "quantity": supress_notation(qty, self.qty_precision),
                "price": price,
                "isIsolated": "TRUE",
            }
        else:
            payload = {
                "symbol": symbol,
                "side": OrderSide.sell,
                "type": OrderType.market,
                "quantity": supress_notation(qty, self.qty_precision),
                "isIsolated": "TRUE",
            }

        data = self.signed_request(
            url=self.margin_order, method="POST", payload=payload
        )

        if float(data["price"]) == 0:
            data["price"] = data["fills"][0]["price"]

        return data
