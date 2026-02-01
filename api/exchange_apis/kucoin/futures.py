from datetime import datetime
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
from pybinbot import KucoinApi, KucoinKlineIntervals
from uuid import uuid4
from kucoin_universal_sdk.generate.account.transfer.model_flex_transfer_req import (
    FlexTransferReq,
    FlexTransferReqBuilder,
)
from kucoin_universal_sdk.generate.futures.market import (
    GetKlinesReqBuilder,
)
from kucoin_universal_sdk.generate.account.transfer.model_flex_transfer_resp import (
    FlexTransferResp,
)


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
        self.key = key
        self.secret = secret
        self.passphrase = passphrase
        # Placeholder: set up futures client/api here
        self.client = self.setup_client()
        self.futures_market_api = (
            self.client.rest_service().get_futures_service().get_market_api()
        )
        self.futures_order_api = (
            self.client.rest_service().get_futures_service().get_order_api()
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
        side: "buy" or "sell"
        order_type: "limit" or "market"
        price: required for limit orders
        """
        client_oid = str(uuid4())
        builder = (
            AddOrderReqBuilder()
            .set_client_oid(client_oid)
            .set_symbol(symbol)
            .set_side(side.lower())
            .set_type(order_type.lower())
            .set_leverage(leverage)
        )
        # Use size parameter for quantity (lot size)
        if qty:
            builder = builder.set_size(int(qty))
        if order_type.upper() == "LIMIT" and price is not None:
            builder = builder.set_price(str(price))
        request = builder.build()
        resp = self.futures_order_api.add_order(request)
        return resp

    def buy(
        self,
        symbol: str,
        qty: float,
        order_type: str = "LIMIT",
        price: float = None,
        leverage: int = 1,
        **kwargs,
    ) -> AddOrderResp:
        return self.place_order(
            symbol, "BUY", qty, order_type, price, leverage, **kwargs
        )

    def sell(
        self,
        symbol: str,
        qty: float,
        order_type: str = "LIMIT",
        price: float = None,
        leverage: int = 1,
        **kwargs,
    ) -> AddOrderResp:
        return self.place_order(
            symbol, "SELL", qty, order_type, price, leverage, **kwargs
        )

    def cancel_order(self, order_id: str) -> CancelOrderByIdResp:
        """
        Cancel a futures order by order_id.
        """
        builder = CancelOrderByIdReqBuilder().set_order_id(order_id)
        request = builder.build()
        resp = self.futures_order_api.cancel_order_by_id(request)
        return resp

    def get_order(self, order_id: str) -> GetOrderByOrderIdResp:
        """
        Get order status/details by order_id.
        """
        builder = GetOrderByOrderIdReqBuilder().set_order_id(order_id)
        request = builder.build()
        resp = self.futures_order_api.get_order_by_order_id(request)
        return resp

    def transfer_main_to_futures(
        self, currency: str, amount: float
    ) -> FlexTransferResp:
        """
        Transfer funds from main account to futures account.
        """
        client_oid = str(uuid4())
        req = (
            FlexTransferReqBuilder()
            .set_client_oid(client_oid)
            .set_currency(currency)
            .set_amount(str(amount))
            .set_type(FlexTransferReq.TypeEnum.INTERNAL)
            .set_from_account_type(FlexTransferReq.FromAccountTypeEnum.MAIN)
            .set_to_account_type(FlexTransferReq.ToAccountTypeEnum.CONTRACT)
            .build()
        )
        return self.transfer_api.flex_transfer(req)

    def transfer_trade_to_futures(
        self, currency: str, amount: float
    ) -> FlexTransferResp:
        """
        Transfer funds from trade (spot) account to futures account.
        """
        client_oid = str(uuid4())
        req = (
            FlexTransferReqBuilder()
            .set_client_oid(client_oid)
            .set_currency(currency)
            .set_amount(str(amount))
            .set_type(FlexTransferReq.TypeEnum.INTERNAL)
            .set_from_account_type(FlexTransferReq.FromAccountTypeEnum.TRADE)
            .set_to_account_type(FlexTransferReq.ToAccountTypeEnum.CONTRACT)
            .build()
        )
        return self.transfer_api.flex_transfer(req)

    def get_ui_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 500,
        start_time=None,
        end_time=None,
    ) -> list[list]:
        """
        Get raw klines/candlestick data from Kucoin Futures.

        Args:
            symbol: Trading pair symbol (e.g., "BTC-USDT")
            interval: Kline interval (e.g., "15min", "1hour", "1day")
            limit: Number of klines to retrieve (max 1500, default 500)
            start_time: Start time in milliseconds (optional)
            end_time: End time in milliseconds (optional)
        Returns:
            List of klines in format compatible with Binance format:
            [timestamp, open, high, low, close, volume, close_time, ...]
        """
        # Compute time window based on limit and interval
        interval_ms = KucoinKlineIntervals.get_interval_ms(interval)
        now_ms = int(datetime.now().timestamp() * 1000)
        # Align end_time to interval boundary
        end_time = now_ms - (now_ms % interval_ms)
        start_time = end_time - (limit * interval_ms)

        builder = (
            GetKlinesReqBuilder()
            .set_symbol(symbol)
            .set_granularity(interval)
            .set_from_(start_time // 1000)
            .set_to(end_time // 1000)
        )

        request = builder.build()
        response = self.futures_market_api.get_klines(request)

        # Convert Kucoin format to Binance-compatible format
        klines = []
        for kline in response.data:
            open_time = kline[0] * 1000  # convert to ms
            open_price = float(kline[1])
            high_price = float(kline[2])
            low_price = float(kline[3])
            close_price = float(kline[4])
            volume = float(kline[5])
            close_time = open_time + interval_ms - 1

            klines.append(
                [
                    open_time,
                    open_price,
                    high_price,
                    low_price,
                    close_price,
                    volume,
                    close_time,
                ]
            )

        return klines
