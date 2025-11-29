from databases.crud.symbols_crud import SymbolsCrud
from orders.abstract import OrderControllerAbstract
from tools.enum_definitions import (
    OrderType,
    TimeInForce,
    OrderSide,
    OrderStatus,
)
from tools.handle_error import json_response, json_response_message
from exchange_apis.binance.account import BinanceAccount
from apis import BinbotApi
from tools.maths import round_numbers


class BinanceOrderController(OrderControllerAbstract, BinanceAccount):
    """
    Combines all Binance's API controller operations
    and other dependencies into one single interface shared everywhere

    Exchange-specific implementations should sit in their respective base.py
    anything that requires processing between Exchange API and our application
    logic should be implemented here.

    This provides a easy plug and play interface for the rest of the application,
    keeps classes not too complex and adheres to a Single Responsibility Principle (one place for all).

    That allows routes to do the json responses independently
    and reusability for everyone else.

    TODO: maybe better naming conventions instead of Order, because it sounds like it only covers orders
    """

    def __init__(self) -> None:
        super().__init__()
        OrderControllerAbstract.__init__(self)
        BinanceAccount.__init__(self)
        self.api = BinbotApi()
        self.symbols_crud = SymbolsCrud()

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

    def get_book_order_deep(self, symbol: str, order_side: bool) -> float:
        """
        Get deepest price to avoid market movements causing orders to fail
        which means bid/ask are flipped

        Buy order = get bid prices = True
        Sell order = get ask prices = False
        """
        data = self.api.get_book_depth(symbol)
        if order_side:
            price, _ = data["bids"][0]
        else:
            price, _ = data["asks"][0]
        return float(price)

    def match_qty_engine(self, symbol: str, order_side: bool, qty: float = 1) -> float:
        """
        Similar to matching_engine,
        it is used to find a price that matches the quantity provided
        so qty != 0

        @param: order_side -
            Buy order = get bid prices = False
            Sell order = get ask prices = True
        @param: base_order_size - quantity wanted to be bought/sold in fiat (USDC at time of writing)
        """
        data = self.api.get_book_depth(symbol)
        if order_side:
            total_length = len(data["asks"])
        else:
            total_length = len(data["bids"])

        price, base_qty = self._get_price_from_book_order(data, order_side, 0)

        buyable_qty = float(qty) / float(price)
        if buyable_qty < base_qty:
            return base_qty
        else:
            for i in range(1, total_length):
                price, base_qty = self._get_price_from_book_order(data, order_side, i)
                if buyable_qty > base_qty:
                    return base_qty
                else:
                    continue
            raise Exception("Not enough liquidity to match the order quantity")

    def matching_engine(self, symbol: str, order_side: bool, qty: float = 0) -> float:
        """
        Match quantity with available 100% fill order price,
        so that order can immediately buy/sell

        _get_price_from_book_order previously did max 100 ask/bid levels,
        however that causes trading price to be too far from market price,
        therefore incurring in impossible sell or losses.
        Setting it to 10 levels max to avoid drifting too much from market price.

        @param: order_side -
            Buy order = get bid prices = False
            Sell order = get ask prices = True
        @param: base_order_size - quantity wanted to be bought/sold in fiat (USDC at time of writing)
        """
        data = self.api.get_book_depth(symbol)
        price, base_qty = self._get_price_from_book_order(data, order_side, 0)

        if qty == 0:
            return price
        else:
            buyable_qty = float(qty) / float(price)
            if buyable_qty < base_qty:
                return price
            else:
                for i in range(1, 11):
                    price, base_qty = self._get_price_from_book_order(
                        data, order_side, i
                    )
                    if buyable_qty > base_qty:
                        return price
                    else:
                        continue
                # caller to use market price
                return 0

    def calculate_total_commissions(self, fills: dict) -> float:
        """
        Calculate total commissions for a given order
        """
        total_commission: float = 0
        for chunk in fills:
            total_commission += round_numbers(float(chunk["commission"]))
        return total_commission

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
                order_type=OrderType.market,
            )

        if float(data["price"]) == 0:
            data["price"] = self.calculate_avg_price(data["fills"])

        data["commissions"] = self.calculate_total_commissions(data["fills"])
        return data

    def buy_order(self, symbol: str, qty: float):
        book_price = self.matching_engine(symbol, False, qty)

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
                order_type=order_type,
            )

        if float(data["price"]) == 0:
            data["price"] = self.calculate_avg_price(data["fills"])

        data["commissions"] = self.calculate_total_commissions(data["fills"])
        return data

    def close_all_orders(self, symbol):
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
