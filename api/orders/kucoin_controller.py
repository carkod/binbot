from exchange_apis.kucoin import KucoinApi
from orders.abstract import OrderControllerAbstract
from tools.enum_definitions import OrderSide
from account.kucoin_account import KucoinAccount


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

    def simulate_order(self, pair: str, side: OrderSide, qty=1):
        """
        Simulate a KuCoin order without executing
        Note: KuCoin order structure may differ from Binance
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
        """Simulate response order for KuCoin"""
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
        return super().matching_engine(symbol, order_side, qty)

    def sell_order(
        self, symbol: str, qty: float, price_precision: int = 0, qty_precision: int = 0
    ):
        """
        KuCoin sell order implementation
        Places a market sell order and maps response to Binance format
        """
        # Convert symbol from Binance format (BTCUSDT) to KuCoin format (BTC-USDT)
        kucoin_symbol = self._convert_to_kucoin_symbol(symbol)

        # Place market sell order
        kucoin_response = self.place_order(
            symbol=kucoin_symbol, side="sell", order_type="market", size=str(qty)
        )

        # Map KuCoin response to Binance format
        return self._map_to_binance_format(kucoin_response, symbol, "SELL", qty)

    def buy_order(
        self, symbol: str, qty: float, price_precision: int = 0, qty_precision: int = 0
    ):
        """
        KuCoin buy order implementation
        Places a market buy order and maps response to Binance format
        """
        # Convert symbol from Binance format (BTCUSDT) to KuCoin format (BTC-USDT)
        kucoin_symbol = self._convert_to_kucoin_symbol(symbol)

        # Place market buy order
        kucoin_response = self.place_order(
            symbol=kucoin_symbol, side="buy", order_type="market", size=str(qty)
        )

        # Map KuCoin response to Binance format
        return self._map_to_binance_format(kucoin_response, symbol, "BUY", qty)

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

    def _map_to_binance_format(
        self, kucoin_response: dict, symbol: str, side: str, qty: float
    ) -> dict:
        """
        Map KuCoin order response to Binance format

        KuCoin response: {"orderId": "..."}
        Binance format: {symbol, orderId, clientOrderId, transactTime, price, origQty,
                        executedQty, status, timeInForce, type, side, fills}
        """
        # Get order details from KuCoin
        order_id = kucoin_response.get("orderId")

        # For market orders, we need to fetch the order details to get execution info
        try:
            order_details = self.get_order(order_id)

            return {
                "symbol": symbol,
                "orderId": order_id,
                "orderListId": -1,
                "clientOrderId": order_details.get("clientOid", ""),
                "transactTime": int(order_details.get("createdAt", 0)),
                "price": str(order_details.get("price", "0")),
                "origQty": str(order_details.get("size", qty)),
                "executedQty": str(order_details.get("dealSize", "0")),
                "cummulativeQuoteQty": str(order_details.get("dealFunds", "0")),
                "status": self._map_order_status(order_details.get("status", "active")),
                "timeInForce": self._map_time_in_force(
                    order_details.get("timeInForce", "GTC")
                ),
                "type": order_details.get("type", "market").upper(),
                "side": side,
                "fills": self._extract_fills(order_details),
            }
        except Exception:
            # Fallback to basic response if order fetch fails
            return {
                "symbol": symbol,
                "orderId": order_id,
                "orderListId": -1,
                "clientOrderId": "",
                "transactTime": self.get_ts(),
                "price": "0",
                "origQty": str(qty),
                "executedQty": "0",
                "cummulativeQuoteQty": "0",
                "status": "NEW",
                "timeInForce": "GTC",
                "type": "MARKET",
                "side": side,
                "fills": [],
            }

    def _map_order_status(self, kucoin_status: str) -> str:
        """
        Map KuCoin order status to Binance format
        KuCoin: active, done
        Binance: NEW, PARTIALLY_FILLED, FILLED, CANCELED, EXPIRED
        """
        status_map = {
            "active": "NEW",
            "done": "FILLED",
        }
        return status_map.get(kucoin_status, "NEW")

    def _map_time_in_force(self, kucoin_tif: str) -> str:
        """Map KuCoin time in force to Binance format"""
        tif_map = {
            "GTC": "GTC",
            "GTT": "GTT",
            "IOC": "IOC",
            "FOK": "FOK",
        }
        return tif_map.get(kucoin_tif, "GTC")

    def _extract_fills(self, order_details: dict) -> list:
        """
        Extract fills from KuCoin order details
        Binance fills format: [{price, qty, commission, commissionAsset}]
        """
        # KuCoin doesn't provide fill-by-fill data in the same way
        # Return a single fill if the order has executed
        if float(order_details.get("dealSize", 0)) > 0:
            return [
                {
                    "price": str(order_details.get("price", "0")),
                    "qty": str(order_details.get("dealSize", "0")),
                    "commission": str(order_details.get("fee", "0")),
                    "commissionAsset": order_details.get("feeCurrency", "USDT"),
                }
            ]
        return []

    def delete_order(self, symbol: str, order_id: int):
        """
        Cancel single KuCoin order
        Returns Binance-compatible response
        """
        # KuCoin cancel_order returns: {"cancelledOrderIds": ["order_id"]}
        self.cancel_order(str(order_id))

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
        # Convert to KuCoin symbol format
        kucoin_symbol = self._convert_to_kucoin_symbol(symbol)

        # KuCoin returns: {"cancelledOrderIds": ["id1", "id2", ...]}
        kucoin_response = self.cancel_all_orders(kucoin_symbol)

        # Return list of cancelled order IDs (Binance compatible)
        cancelled_ids = kucoin_response.get("cancelledOrderIds", [])
        return [{"orderId": order_id} for order_id in cancelled_ids]

    def buy_margin_order(self, symbol: str, qty: float):
        """
        KuCoin margin buy order
        TODO: Implement KuCoin-specific margin order placement
        """
        raise NotImplementedError(
            "KuCoin buy_margin_order needs to be implemented with KuCoin SDK"
        )

    def sell_margin_order(self, symbol: str, qty: float):
        """
        KuCoin margin sell order
        TODO: Implement KuCoin-specific margin order placement
        """
        raise NotImplementedError(
            "KuCoin sell_margin_order needs to be implemented with KuCoin SDK"
        )
