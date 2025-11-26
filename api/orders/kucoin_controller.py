from exchange_apis.kucoin import KucoinApi
from orders.abstract import OrderControllerAbstract
from tools.enum_definitions import OrderSide
from account.kucoin_account import KucoinAccount
from kucoin_universal_sdk.generate.spot.order import AddOrderReq


class KucoinOrderController(OrderControllerAbstract, KucoinAccount):
    """
    KuCoin-specific implementation of OrderController.

    Inherits common methods from OrderControllerAbstract
    and KuCoin-specific account methods from KucoinAccount
    """

    def __init__(self) -> None:
        OrderControllerAbstract.__init__(self)
        KucoinAccount.__init__(self)
        self.api = KucoinApi()

    def _get_price_from_book_order(self, data, order_side: bool, index: int):
        """
        Helper to extract price and base quantity from order book data
        """
        if order_side:
            price, base_qty = data["bids"][index]
        else:
            price, base_qty = data["asks"][index]
        return float(price), float(base_qty)

    def _convert_to_kucoin_symbol(self, binance_symbol: str) -> str:
        """
        Convert Binance symbol format to KuCoin format
        Example: BTCUSDT -> BTC-USDT
        """
        # Common quote currencies
        quote_currencies = ["USDT", "USDC", "BTC", "ETH", "BNB", "BUSD"]

        for quote in quote_currencies:
            if binance_symbol.endswith(quote):
                base = binance_symbol[: -len(quote)]
                return f"{base}-{quote}"

        # If no common quote found, assume last 4 chars are quote
        return f"{binance_symbol[:-4]}-{binance_symbol[-4:]}"

    def _map_to_binance_format(self, order_details: dict) -> dict:
        """
        Map KuCoin order response to Binance-like Binance format.

        Uses fields from KuCoin's get_order response, e.g.:
        id, symbol, type, side, price, size, dealSize, dealFunds, fee,
        feeCurrency, timeInForce, createdAt, clientOid, status, etc.
        """
        return {
            "symbol": order_details["symbol"],
            "orderId": order_details["id"],
            "clientOrderId": order_details["clientOid"],
            "transactTime": int(order_details["createdAt"]),
            "price": str(order_details["price"]),
            "origQty": str(order_details["size"]),
            "executedQty": str(order_details["dealSize"]),
            "cummulativeQuoteQty": str(order_details["dealFunds"]),
            "status": order_details["status"],
            "timeInForce": order_details["timeInForce"],
            "type": order_details["type"],
            "side": order_details["side"],
            "commission": str(order_details["fee"]),
            "commissionAsset": order_details["feeCurrency"],
        }

    def simulate_response_order(self, pair: str, side: OrderSide, qty=1):
        """Simulate response order for KuCoin"""
        price = float(self.matching_engine(pair, False, qty))
        order_id = self.generate_id().hex
        client_order_id = self.generate_id().hex
        ts = self.get_ts()

        return {
            "symbol": pair,
            "orderId": order_id,
            "clientOrderId": client_order_id,
            "transactTime": ts,
            "price": str(price),
            "origQty": str(qty),
            "executedQty": str(qty),
            "cummulativeQuoteQty": str(price * qty),
            "status": "FILLED",
            "timeInForce": "GTC",
            "type": "LIMIT",
            "side": side,
            "fills": [
                {
                    "price": str(price),
                    "qty": str(qty),
                    "commission": "0",
                    "commissionAsset": "USDT",
                }
            ],
        }

    def simulate_margin_order(self, pair, side: OrderSide):
        """
        Simulate KuCoin margin order
        Note: KuCoin margin structure differs from Binance
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

    def matching_engine(self, symbol: str, order_side: bool, qty: float = 0) -> float:
        """
        KuCoin implementation of matching engine
        Delegates to KucoinAccount's matching_engine
        """
        data = self.api.get_part_order_book(symbol=symbol, size=str(qty))[0][0]
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

    def sell_order(self, symbol: str, qty: float):
        """
        KuCoin sell order implementation
        Places a market sell order and maps response to Binance format
        """
        # Convert symbol from Binance format (BTCUSDT) to KuCoin format (BTC-USDT)
        book_price = self.matching_engine(symbol, order_side=False, qty=qty)

        if book_price > 0:
            # Place market sell order
            response = self.api.add_order(
                symbol=symbol,
                side=AddOrderReq.SideEnum.SELL,
                order_type=AddOrderReq.TypeEnum.LIMIT,
                size=qty,
            )
        else:
            response = self.api.add_order(
                symbol=symbol,
                side=AddOrderReq.SideEnum.SELL,
                order_type=AddOrderReq.TypeEnum.MARKET,
                size=qty,
            )

        order_details = self.api.get_order(response["orderId"])

        # Map KuCoin response to Binance format
        return self._map_to_binance_format(order_details)

    def buy_order(
        self,
        symbol: str,
        qty: float,
        price: float,
    ):
        """
        KuCoin buy order implementation
        Places a market buy order and maps response to Binance format
        """
        book_price = self.matching_engine(symbol, order_side=False)

        if book_price > 0:
            # Place market buy order with price
            kucoin_response = self.api.add_order(
                symbol=symbol,
                side=AddOrderReq.SideEnum.BUY,
                order_type=AddOrderReq.TypeEnum.LIMIT,
                size=qty,
                price=price,
                time_in_force=AddOrderReq.TimeInForceEnum.GTC,
            )
        else:
            kucoin_response = self.api.add_order(
                symbol=symbol,
                side=AddOrderReq.SideEnum.BUY,
                order_type=AddOrderReq.TypeEnum.MARKET,
                size=qty,
                time_in_force=AddOrderReq.TimeInForceEnum.FOK,
            )

        order_details = self.api.get_order(kucoin_response["orderId"])

        # Map KuCoin response to Binance format
        return self._map_to_binance_format(order_details)

    def delete_order(self, symbol: str, order_id: int):
        """
        Cancel single KuCoin order
        Returns Binance-compatible response
        """
        self.api.cancel_order(str(order_id))

        return {
            "symbol": symbol,
            "origClientOrderId": "",
            "orderId": order_id,
            "orderListId": -1,
            "clientOrderId": "",
            "price": "0",
            "origQty": "0",
            "executedQty": "0",
            "cummulativeQuoteQty": "0",
            "status": "CANCELED",
            "timeInForce": "GTC",
            "type": "LIMIT",
            "side": "SELL",
        }

    def delete_all_orders(self, symbol: str):
        """
        Delete all KuCoin orders for a symbol
        Returns list of cancelled order IDs
        """
        kucoin_response = self.api.cancel_all_orders(symbol=symbol)

        # Return list of cancelled order IDs (Binance compatible)
        cancelled_ids = kucoin_response.get("cancelledOrderIds", [])
        return [{"orderId": order_id} for order_id in cancelled_ids]

    def buy_margin_order(self, symbol: str, qty: float):
        """
        KuCoin margin buy order
        Places a margin buy order and maps response to Binance format
        """
        book_price = self.matching_engine(symbol, order_side=True)
        if book_price > 0:
            kucoin_response = self.api.add_margin_order(
                symbol=symbol,
                side=AddOrderReq.SideEnum.BUY,
                order_type=AddOrderReq.TypeEnum.LIMIT,
                size=qty,
                price=book_price,
                time_in_force=AddOrderReq.TimeInForceEnum.GTC,
            )
        else:
            kucoin_response = self.api.add_margin_order(
                symbol=symbol,
                side=AddOrderReq.SideEnum.BUY,
                order_type=AddOrderReq.TypeEnum.MARKET,
                size=qty,
                time_in_force=AddOrderReq.TimeInForceEnum.FOK,
            )

        order_details = self.api.get_margin_order(kucoin_response["orderId"])

        return self._map_to_binance_format(order_details)

    def sell_margin_order(self, symbol: str, qty: float):
        """
        KuCoin margin sell order
        Places a margin sell order and maps response to Binance format
        """
        book_price = self.matching_engine(symbol, order_side=False)
        if book_price > 0:
            kucoin_response = self.api.add_margin_order(
                symbol=symbol,
                side=AddOrderReq.SideEnum.SELL,
                order_type=AddOrderReq.TypeEnum.LIMIT,
                size=qty,
                price=book_price,
                time_in_force=AddOrderReq.TimeInForceEnum.GTC,
            )
        else:
            kucoin_response = self.api.add_margin_order(
                symbol=symbol,
                side=AddOrderReq.SideEnum.SELL,
                order_type=AddOrderReq.TypeEnum.MARKET,
                size=qty,
                time_in_force=AddOrderReq.TimeInForceEnum.FOK,
            )

        order_details = self.api.get_margin_order(kucoin_response["orderId"])

        return self._map_to_binance_format(order_details)
