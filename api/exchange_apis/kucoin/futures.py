from kucoin_universal_sdk.api import DefaultClient
from kucoin_universal_sdk.model import TransportOptionBuilder
from kucoin_universal_sdk.model import ClientOptionBuilder
from kucoin_universal_sdk.model import (
    GLOBAL_FUTURES_API_ENDPOINT,
)
from kucoin_universal_sdk.generate.futures.order import (
    AddOrderReqBuilder,
    CancelOrderByIdReqBuilder,
    GetOrderByOrderIdReqBuilder,
)
from kucoin_universal_sdk.generate.futures.order.model_add_order_req import AddOrderReq
from kucoin_universal_sdk.generate.futures.order.model_add_order_resp import (
    AddOrderResp,
)
from kucoin_universal_sdk.generate.futures.order.model_cancel_order_by_id_resp import (
    CancelOrderByIdResp,
)
from kucoin_universal_sdk.generate.futures.order.model_get_order_by_order_id_resp import (
    GetOrderByOrderIdResp,
)
from pybinbot import KucoinApi


class KucoinFutures(KucoinApi):
    """
    Basic Kucoin Futures order endpoints using KucoinApi as base.

    To be replaced in the future with KucoinApi class inheriting from
    Futures API KucoinApi(KucoinFutures) in pybinbot
    """

    def __init__(self, key: str, secret: str, passphrase: str):
        super().__init__(
            key=key,
            secret=secret,
            passphrase=passphrase,
        )
        self.futures_client = self.setup_futures_client()
        self.futures_market_api = (
            self.futures_client.rest_service().get_futures_service().get_market_api()
        )

    def setup_futures_client(self) -> DefaultClient:
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
            .set_transport_option(http_transport_option)
            .set_futures_endpoint(GLOBAL_FUTURES_API_ENDPOINT)
            .build()
        )
        client = DefaultClient(client_option)
        return client

    def place_order(
        self,
        symbol: str,
        side: AddOrderReq.SideEnum,
        qty: float,
        price: float,
        leverage: int = 1,
        **kwargs,
    ) -> AddOrderResp:
        """
        Place a futures order (buy/sell).
        side: "BUY" or "SELL"
        order_type: "LIMIT" or "MARKET"
        price: required for LIMIT
        """
        builder = (
            AddOrderReqBuilder()
            .set_symbol(symbol)
            .set_side(side)
            .set_size(str(qty))
            .set_leverage(str(leverage))
            .set_type(AddOrderReq.TypeEnum.LIMIT)
            .set_price(str(price))
        )

        request = builder.build()
        futures_order_api = (
            self.futures_client.rest_service().get_futures_service().get_order_api()
        )
        resp = futures_order_api.add_order(request)
        return resp

    def cancel_order(self, order_id: str) -> CancelOrderByIdResp:
        """
        Cancel a futures order by order_id.
        """
        request = CancelOrderByIdReqBuilder().set_order_id(order_id).build()
        futures_order_api = (
            self.futures_client.rest_service().get_futures_service().get_order_api()
        )
        resp = futures_order_api.cancel_order_by_id(request)
        return resp

    def retrieve_order(self, order_id: str) -> GetOrderByOrderIdResp:
        """
        Get order status/details by order_id.
        """
        request = GetOrderByOrderIdReqBuilder().set_order_id(order_id).build()
        futures_order_api = (
            self.futures_client.rest_service().get_futures_service().get_order_api()
        )
        resp = futures_order_api.get_order_by_order_id(request)
        return resp
