from orders.abstract import OrderControllerAbstract
from tools.enum_definitions import (
    OrderType,
    TimeInForce,
    OrderSide,
    OrderStatus,
)
from tools.handle_error import json_response, json_response_message
from account.binance_account import BinanceAccount
from apis import BinbotApi


class BinanceOrderController(OrderControllerAbstract, BinanceAccount):
    def __init__(self) -> None:
        OrderControllerAbstract.__init__(self)
        BinanceAccount.__init__(self)
        self.api = BinbotApi()

    def calculate_avg_price(self, fills: list[dict]) -> float:
        """
        Calculate average price of fills
        """
        total_qty: float = 0
        total_price: float = 0
        for fill in fills:
            total_qty += float(fill["qty"])
            total_price += float(fill["price"]) * float(fill["qty"])
        return total_price / total_qty

    def simulate_order(self, pair: str, side: OrderSide, qty=1):
        """
        Price is determined by market
        to help trigger the order immediately
        """
        price = self.matching_engine(pair, True, 0)
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
        price = self.matching_engine(pair, True, qty)
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

    def sell_order(
        self, symbol: str, qty: float, price_precision: int = 0, qty_precision: int = 0
    ):
        """
        If price is not provided by matching engine,
        sell at market price
        """
        book_price = self.matching_engine(symbol, True, qty)
        if price_precision == 0:
            price_precision = self.price_precision
        if qty_precision == 0:
            qty_precision = self.qty_precision

        if book_price > 0:
            side = OrderSide.sell
            order_type = OrderType.limit
            time_in_force = TimeInForce.gtc
        else:
            side = OrderSide.sell
            order_type = OrderType.market
            time_in_force = TimeInForce.fok

        data = self.api.post_sell_order(
            symbol=symbol,
            side=side,
            qty=qty,
            price_precision=price_precision,
            qty_precision=qty_precision,
            order_type=order_type,
            price=book_price,
            time_in_force=time_in_force,
        )

        # Fixed expired orders
        if data["status"] == OrderStatus.EXPIRED.value:
            # do a market order, otherwise we could enter into a Expired infinite loop
            data = self.api.post_sell_order(
                symbol=symbol,
                side=OrderSide.sell,
                qty=qty,
                price=book_price,
                time_in_force=time_in_force,
                price_precision=price_precision,
                qty_precision=qty_precision,
                order_type=OrderType.market,
            )

        if float(data["price"]) == 0:
            data["price"] = self.calculate_avg_price(data["fills"])

        data["commissions"] = self.calculate_total_commissions(data["fills"])
        return data

    def buy_order(
        self, symbol: str, qty: float, price_precision: int = 0, qty_precision: int = 0
    ):
        book_price = self.matching_engine(symbol, False, qty)

        # this gives flexibility to use quote values
        if price_precision == 0:
            price_precision = self.price_precision
        if qty_precision == 0:
            qty_precision = self.qty_precision

        if book_price > 0:
            side = OrderSide.buy
            order_type = OrderType.limit
            time_in_force = TimeInForce.gtc
        else:
            # Use market price if matching engine can't find a price
            side = OrderSide.buy
            order_type = OrderType.market
            time_in_force = TimeInForce.fok

        data = self.api.post_buy_order(
            symbol=symbol,
            side=side,
            qty=qty,
            price_precision=price_precision,
            qty_precision=qty_precision,
            order_type=order_type,
            price=book_price,
            time_in_force=time_in_force,
        )

        if data["status"] == OrderStatus.EXPIRED.value:
            side = OrderSide.buy
            order_type = OrderType.market

            data = self.api.post_buy_order(
                symbol=symbol,
                side=side,
                qty=qty,
                price=book_price,
                time_in_force=time_in_force,
                price_precision=price_precision,
                qty_precision=qty_precision,
                order_type=order_type,
            )

        if float(data["price"]) == 0:
            data["price"] = self.calculate_avg_price(data["fills"])

        data["commissions"] = self.calculate_total_commissions(data["fills"])
        return data

    def delete_all_orders(self, symbol):
        """
        Delete All orders by symbol
        - Optimal for open orders table
        """
        data = self.api.close_all_orders(symbol)

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
            order_type = OrderType.limit
            time_in_force = TimeInForce.gtc
        else:
            order_type = OrderType.market
            time_in_force = TimeInForce.fok

        data = self.api.buy_isolated_margin_order(
            symbol=symbol,
            qty=qty,
            order_type=order_type,
            price=price,
            time_in_force=time_in_force,
        )

        if float(data["price"]) == 0:
            data["price"] = self.calculate_avg_price(data["fills"])

        data["commissions"] = self.calculate_total_commissions(data["fills"])
        return data

    def sell_margin_order(self, symbol: str, qty: float):
        """
        python-binance wrapper function to make it less verbose and less dependant
        """
        price = self.matching_engine(symbol, True, qty)

        if price > 0:
            order_type = OrderType.limit
            time_in_force = TimeInForce.gtc
        else:
            order_type = OrderType.market
            time_in_force = TimeInForce.fok

        data = self.api.sell_isolated_margin_order(
            symbol=symbol,
            qty=qty,
            order_type=order_type,
            price=price,
            time_in_force=time_in_force,
        )

        if float(data["price"]) == 0:
            data["price"] = self.calculate_avg_price(data["fills"])

        data["commissions"] = self.calculate_total_commissions(data["fills"])
        return data
