import os
import uuid

from kucoin_universal_sdk.api import DefaultClient
from kucoin_universal_sdk.generate.spot.market import (
    GetPartOrderBookReqBuilder,
    GetAllSymbolsReqBuilder,
)
from kucoin_universal_sdk.generate.spot.order import (
    AddOrderReqBuilder,
    AddOrderReq,
    CancelOrderByOrderIdReqBuilder,
    CancelAllOrdersBySymbolReqBuilder,
    GetOrderByOrderIdReqBuilder,
    GetOpenOrdersReqBuilder,
)
from kucoin_universal_sdk.model import ClientOptionBuilder
from kucoin_universal_sdk.model import (
    GLOBAL_API_ENDPOINT,
    GLOBAL_FUTURES_API_ENDPOINT,
    GLOBAL_BROKER_API_ENDPOINT,
)
from kucoin_universal_sdk.model import TransportOptionBuilder


class KucoinApi:
    def __init__(self):
        self.key = os.getenv("KUCOIN_KEY", "")
        self.secret = os.getenv("KUCOIN_SECRET", "")
        self.passphrase = os.getenv("KUCOIN_PASSPHRASE", "")
        self.setup_client()

    def setup_client(self):
        http_transport_option = (
            TransportOptionBuilder()
            .set_keep_alive(True)
            .set_max_pool_size(10)
            .set_max_connection_per_pool(10)
            .build()
        )
        client_option = (
            ClientOptionBuilder()
            .set_key(self.key)
            .set_secret(self.secret)
            .set_passphrase(self.passphrase)
            .set_spot_endpoint(GLOBAL_API_ENDPOINT)
            .set_futures_endpoint(GLOBAL_FUTURES_API_ENDPOINT)
            .set_broker_endpoint(GLOBAL_BROKER_API_ENDPOINT)
            .set_transport_option(http_transport_option)
            .build()
        )
        self.client = DefaultClient(client_option)
        self.kucoin_rest_service = self.client.rest_service()
        self.spot_market_api = (
            self.kucoin_rest_service.get_spot_service().get_market_api()
        )
        self.margin_market_api = (
            self.kucoin_rest_service.get_margin_service().get_market_api()
        )
        self.spot_order_api = (
            self.kucoin_rest_service.get_spot_service().get_order_api()
        )

    def get_server_time(self):
        response = self.spot_market_api.get_server_time()
        return response

    def get_part_order_book(self, symbol: str, size: str):
        request = GetPartOrderBookReqBuilder().set_symbol(symbol).set_size(size).build()
        response = self.spot_market_api.get_part_order_book(request)
        return response

    def get_all_symbols(self):
        request = GetAllSymbolsReqBuilder().build()
        response = self.spot_market_api.get_all_symbols(request)
        return response

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        size: str = None,
        price: str = None,
        time_in_force: str = "GTC",
        client_oid: str = None,
    ):
        """
        Place an order on KuCoin using the SDK

        Args:
            symbol: Trading pair (e.g., "BTC-USDT")
            side: "buy" or "sell"
            order_type: "limit" or "market"
            size: Order size (amount of base currency)
            price: Order price (required for limit orders)
            time_in_force: GTC, GTT, IOC, or FOK
            client_oid: Client order ID

        Returns:
            Order response with orderId
        """
        builder = AddOrderReqBuilder()
        builder.set_symbol(symbol)
        builder.set_side(
            AddOrderReq.SideEnum.BUY
            if side.lower() == "buy"
            else AddOrderReq.SideEnum.SELL
        )
        builder.set_type(
            AddOrderReq.TypeEnum.LIMIT
            if order_type.lower() == "limit"
            else AddOrderReq.TypeEnum.MARKET
        )

        if client_oid:
            builder.set_client_oid(client_oid)
        else:
            builder.set_client_oid(str(uuid.uuid4()))

        if size:
            builder.set_size(str(size))

        if order_type.lower() == "limit" and price:
            builder.set_price(str(price))
            if time_in_force == "GTC":
                builder.set_time_in_force(AddOrderReq.TimeInForceEnum.GTC)
            elif time_in_force == "GTT":
                builder.set_time_in_force(AddOrderReq.TimeInForceEnum.GTT)
            elif time_in_force == "IOC":
                builder.set_time_in_force(AddOrderReq.TimeInForceEnum.IOC)
            elif time_in_force == "FOK":
                builder.set_time_in_force(AddOrderReq.TimeInForceEnum.FOK)

        req = builder.build()
        resp = self.spot_order_api.add_order(req)

        # Convert response to dict format
        return {"orderId": resp.order_id, "clientOid": resp.client_oid}

    def cancel_order(self, order_id: str):
        """Cancel an order by order ID using SDK"""
        builder = CancelOrderByOrderIdReqBuilder()
        builder.set_order_id(order_id)
        req = builder.build()
        resp = self.spot_order_api.cancel_order_by_order_id(req)

        return {
            "cancelledOrderIds": [resp.order_id]
            if hasattr(resp, "order_id")
            else [order_id]
        }

    def cancel_all_orders(self, symbol: str = None):
        """
        Cancel all orders using SDK

        Args:
            symbol: Optional - cancel orders for specific symbol

        Returns:
            Response with cancelled order IDs
        """
        if symbol:
            # Cancel orders for specific symbol
            builder = CancelAllOrdersBySymbolReqBuilder()
            builder.set_symbol(symbol)
            req = builder.build()
            resp = self.spot_order_api.cancel_all_orders_by_symbol(req)
            return {"cancelledOrderIds": [resp.data] if hasattr(resp, "data") else []}
        else:
            # Cancel all orders (no parameters)
            resp = self.spot_order_api.cancel_all_orders()
            # SDK returns different format, normalize it
            if hasattr(resp, "cancelled_order_ids"):
                return {"cancelledOrderIds": resp.cancelled_order_ids}
            return {"cancelledOrderIds": []}

    def get_order(self, order_id: str):
        """Get order details by order ID using SDK"""
        builder = GetOrderByOrderIdReqBuilder()
        builder.set_order_id(order_id)
        req = builder.build()
        resp = self.spot_order_api.get_order_by_order_id(req)

        # Convert SDK response to dict
        return {
            "id": resp.id if hasattr(resp, "id") else order_id,
            "symbol": resp.symbol if hasattr(resp, "symbol") else "",
            "type": resp.type if hasattr(resp, "type") else "market",
            "side": resp.side if hasattr(resp, "side") else "",
            "price": resp.price if hasattr(resp, "price") else "0",
            "size": resp.size if hasattr(resp, "size") else "0",
            "dealSize": resp.deal_size if hasattr(resp, "deal_size") else "0",
            "dealFunds": resp.deal_funds if hasattr(resp, "deal_funds") else "0",
            "fee": resp.fee if hasattr(resp, "fee") else "0",
            "feeCurrency": resp.fee_currency
            if hasattr(resp, "fee_currency")
            else "USDT",
            "status": resp.status if hasattr(resp, "status") else "active",
            "timeInForce": resp.time_in_force
            if hasattr(resp, "time_in_force")
            else "GTC",
            "createdAt": resp.created_at if hasattr(resp, "created_at") else 0,
            "clientOid": resp.client_oid if hasattr(resp, "client_oid") else "",
        }

    def get_open_orders(self, symbol: str = None):
        """
        Get list of open orders using SDK

        Args:
            symbol: Optional - filter by symbol

        Returns:
            List of open orders
        """
        builder = GetOpenOrdersReqBuilder()
        if symbol:
            builder.set_symbol(symbol)

        req = builder.build()
        resp = self.spot_order_api.get_open_orders(req)

        # Convert to list format
        if hasattr(resp, "data"):
            return resp.data
        return []
