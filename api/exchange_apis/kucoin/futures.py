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
from pybinbot import KucoinApi, KucoinKlineIntervals, OrderType
from uuid import uuid4
from kucoin_universal_sdk.generate.account.transfer.model_flex_transfer_req import (
    FlexTransferReq,
    FlexTransferReqBuilder,
)
from kucoin_universal_sdk.generate.futures.market import (
    GetKlinesReqBuilder,
    GetSymbolReqBuilder,
    GetPartOrderBookReqBuilder,
)
from kucoin_universal_sdk.generate.account.transfer.model_flex_transfer_resp import (
    FlexTransferResp,
)
from kucoin_universal_sdk.generate.futures.positions.model_modify_margin_leverage_req import (
    ModifyMarginLeverageReqBuilder,
)
from kucoin_universal_sdk.generate.futures.positions.model_modify_margin_leverage_resp import (
    ModifyMarginLeverageResp,
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
        self.futures_client = self.setup_futures_client()
        self.futures_market_api = (
            self.futures_client.rest_service().get_futures_service().get_market_api()
        )
        self.futures_order_api = (
            self.futures_client.rest_service().get_futures_service().get_order_api()
        )
        self.futures_positions_api = (
            self.futures_client.rest_service().get_futures_service().get_positions_api()
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

    def _tick_size(self, symbol: str) -> float:
        """
        Cached in production
        """
        req = GetSymbolReqBuilder().set_symbol(symbol).build()
        info = self.futures_market_api.get_symbol(req)
        if info.tick_size is None:
            raise ValueError(f"tick_size not available for symbol {symbol}")
        return float(info.tick_size)

    def _aggressive_price(
        self, symbol: str, size: float, side: AddOrderReq.SideEnum
    ) -> float:
        """
        Cross spread by 1 tick max
        """
        # Use part order book (top levels) as level2 equivalent
        req = GetPartOrderBookReqBuilder().set_size(size).set_symbol(symbol).build()
        book = self.futures_market_api.get_part_order_book(req)

        tick = self._tick_size(symbol)

        if side == AddOrderReq.SideEnum.BUY:
            best_ask = float(book.asks[0][0])
            return best_ask + tick

        best_bid = float(book.bids[0][0])
        return best_bid - tick

    def buy(
        self,
        symbol: str,
        qty: float,
        leverage: int = 1,
    ) -> AddOrderResp:
        price = self._aggressive_price(symbol, size=qty, side=AddOrderReq.SideEnum.BUY)
        return self.place_futures_order(
            symbol=symbol,
            side=AddOrderReq.SideEnum.BUY,
            size=qty,
            leverage=leverage,
            price=price,
            order_type=OrderType.limit,
        )

    def sell(
        self,
        symbol: str,
        qty: float,
        leverage: int = 1,
    ) -> AddOrderResp:
        price = self._aggressive_price(symbol, size=qty, side=AddOrderReq.SideEnum.SELL)
        return self.place_futures_order(
            symbol=symbol,
            side=AddOrderReq.SideEnum.SELL,
            size=qty,
            leverage=leverage,
            price=price,
            order_type=OrderType.limit,
            reduce_only=True,
        )

    def cancel_order(self, order_id: str) -> CancelOrderByIdResp:
        """
        Cancel a futures order by order_id.
        """
        builder = CancelOrderByIdReqBuilder().set_order_id(order_id)
        request = builder.build()
        resp = self.futures_order_api.cancel_order_by_id(request)
        return resp

    def retrieve_order(self, order_id: str) -> GetOrderByOrderIdResp:
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

    def get_futures_ui_klines(
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

    def set_futures_leverage(
        self, symbol: str, leverage: int
    ) -> ModifyMarginLeverageResp:
        """Set cross-margin leverage for a futures symbol.

        This uses the Kucoin futures positions API `modify_margin_leverage` endpoint.
        """
        req = (
            ModifyMarginLeverageReqBuilder()
            .set_symbol(symbol)
            .set_leverage(str(leverage))
            .build()
        )
        return self.futures_positions_api.modify_margin_leverage(req)

    def place_futures_order(
        self,
        symbol: str,
        side: AddOrderReq.SideEnum,
        size: float,
        leverage: int = 5,
        order_type: OrderType = OrderType.limit,
        margin_mode: AddOrderReq.MarginModeEnum = AddOrderReq.MarginModeEnum.ISOLATED,
        reduce_only: bool = False,
        close_order: bool = False,
        price: float | None = None,
    ) -> AddOrderResp:
        """Place a Kucoin futures order using the official SDK.

        Args:
            symbol: Futures contract symbol, e.g. "BTCUSDTM" or "BTC-USDT" depending on market.
            side: "buy" or "sell" (case-insensitive).
            size: Contract size (lot size) as float.
            price: Limit price as float; required for limit orders.
            leverage: Leverage multiplier.
            order_type: Internal OrderType (limit/market).
            margin_mode: Optional margin mode, "ISOLATED" or "CROSS".
            reduce_only: Optional reduce-only flag.
            close_order: Optional close-position flag.
            client_oid: Optional client order id; if omitted a UUID is generated.
        """

        client_oid = str(uuid4())

        if order_type == OrderType.limit:
            type_enum = AddOrderReq.TypeEnum.LIMIT
        else:
            type_enum = AddOrderReq.TypeEnum.MARKET

        builder = (
            AddOrderReqBuilder()
            .set_client_oid(client_oid)
            .set_symbol(symbol)
            .set_side(side)
            .set_type(type_enum)
            .set_margin_mode(margin_mode)
        )

        if leverage is not None:
            builder = builder.set_leverage(str(leverage))

        if price is not None:
            builder = builder.set_price(str(price))

        builder = builder.set_size(int(size))

        if reduce_only is not None:
            builder = builder.set_reduce_only(reduce_only)

        if close_order is not None:
            builder = builder.set_close_order(close_order)

        req = builder.build()
        return self.futures_order_api.add_order(req)
