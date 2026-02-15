from datetime import datetime
from decimal import Decimal
from pybinbot import KucoinRest, KucoinKlineIntervals, OrderType, OrderStatus, DealType
from uuid import uuid4
from time import time
from typing import List
from bots.models import OrderModel
from tools.config import Config
from kucoin_universal_sdk.generate.futures.order import (
    AddOrderReqBuilder,
    GetOrderByOrderIdReqBuilder,
)
from kucoin_universal_sdk.generate.futures.order.model_add_order_req import AddOrderReq
from kucoin_universal_sdk.generate.futures.order.model_add_order_resp import (
    AddOrderResp,
)
from kucoin_universal_sdk.generate.futures.order.model_get_order_by_order_id_resp import (
    GetOrderByOrderIdResp,
)
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
from kucoin_universal_sdk.generate.futures.positions.model_get_position_details_req import (
    GetPositionDetailsReqBuilder,
)
from kucoin_universal_sdk.generate.futures.positions.model_get_position_details_resp import (
    GetPositionDetailsResp,
)
from kucoin_universal_sdk.generate.futures.positions import (
    SwitchMarginModeReq,
    SwitchMarginModeReqBuilder,
    SwitchMarginModeResp,
)
from kucoin_universal_sdk.generate.futures.order import (
    CancelAllOrdersV3ReqBuilder,
)


class KucoinFutures(KucoinRest):
    """
    Basic Kucoin Futures order endpoints using KucoinApi as base.

    To be replaced in the future with KucoinApi class inheriting from
    Futures API KucoinApi(KucoinFutures) in pybinbot
    """

    def __init__(self):
        self.config = Config()
        self.DEFAULT_LEVERAGE = (
            1.5  # assuming stop loss 3% by default, conservative risk
        )
        self.DEFAULT_MULTIPLIER = 1  # for USDT-M futures
        super().__init__(
            key=self.config.kucoin_key,
            secret=self.config.kucoin_secret,
            passphrase=self.config.kucoin_passphrase,
        )
        self.setup_futures_api()

    def get_symbol_info(self, symbol: str):
        req = GetSymbolReqBuilder().set_symbol(symbol).build()
        return self.futures_market_api.get_symbol(req)

    def _tick_size(self, symbol: str) -> float:
        """
        Cached in production
        """
        info = self.get_symbol_info(symbol)
        if info.tick_size is None:
            raise ValueError(f"tick_size not available for symbol {symbol}")
        return float(info.tick_size)

    def matching_engine(
        self, symbol: str, size: float, side: AddOrderReq.SideEnum
    ) -> float:
        """
        Cross spread by 1 tick max
        """
        req = (
            GetPartOrderBookReqBuilder()
            .set_size(str(int(size)))
            .set_symbol(symbol)
            .build()
        )
        book = self.futures_market_api.get_full_order_book(req)

        tick = Decimal(str(self._tick_size(symbol)))

        if side == AddOrderReq.SideEnum.BUY:
            best_ask = Decimal(book.asks[0][0])
            price = best_ask + tick
        else:
            best_bid = Decimal(book.bids[0][0])
            price = best_bid - tick

        return float(price)

    def buy(
        self,
        symbol: str,
        qty: float,
    ) -> OrderModel:
        """
        Place an order and get the order
        leverage is set separately via set_futures_leverage
        """
        price = self.matching_engine(symbol, size=qty, side=AddOrderReq.SideEnum.BUY)

        order_resp = self.place_futures_order(
            symbol=symbol,
            side=AddOrderReq.SideEnum.BUY,
            size=int(qty),
            price=price,
            order_type=OrderType.limit,
        )
        if not order_resp or not order_resp.order_id:
            order_resp = self.place_futures_order(
                symbol=symbol,
                side=AddOrderReq.SideEnum.BUY,
                size=int(qty),
                price=price,
                order_type=OrderType.market,
            )

        # Fetch order details as source of truth for status/fills
        order_details = self.retrieve_order(order_resp.order_id)

        if order_details and order_details.status is not None:
            status = OrderStatus.map_from_kucoin_status(order_details.status.value)
            filled_size = (
                float(order_details.filled_size)
                if order_details.filled_size is not None
                else float(order_details.size or 0)
            )
            price_used = (
                float(order_details.avg_deal_price)
                if order_details.avg_deal_price is not None
                else float(order_details.price or price)
            )
            timestamp = order_details.created_at
        else:
            status = OrderStatus.NEW
            filled_size = qty
            price_used = price
            timestamp = int(time() * 1000)

        return OrderModel(
            order_id=order_resp.order_id,
            order_type=OrderType.limit.value,
            pair=symbol,
            timestamp=timestamp,
            order_side=AddOrderReq.SideEnum.BUY.value,
            qty=filled_size,
            price=price_used,
            status=status,
            time_in_force=order_details.time_in_force,
            deal_type=DealType.base_order,
        )

    def sell(
        self,
        symbol: str,
        qty: float,
        leverage: int = 1,
    ) -> OrderModel:
        price = self.matching_engine(symbol, size=qty, side=AddOrderReq.SideEnum.SELL)
        order_resp = self.place_futures_order(
            symbol=symbol,
            side=AddOrderReq.SideEnum.SELL,
            size=qty,
            leverage=leverage,
            price=price,
            order_type=OrderType.limit,
            reduce_only=True,
        )

        if not order_resp or not order_resp.order_id:
            order_resp = self.place_futures_order(
                symbol=symbol,
                side=AddOrderReq.SideEnum.SELL,
                size=qty,
                leverage=leverage,
                price=price,
                order_type=OrderType.market,
                reduce_only=True,
            )

        order_details = self.retrieve_order(order_resp.order_id)

        if order_details and order_details.status is not None:
            status = OrderStatus.map_from_kucoin_status(order_details.status.value)
            filled_size = (
                float(order_details.filled_size)
                if order_details.filled_size is not None
                else float(order_details.size or 0)
            )
            price_used = (
                float(order_details.avg_deal_price)
                if order_details.avg_deal_price is not None
                else float(order_details.price or price)
            )
            timestamp = order_details.created_at
        else:
            status = OrderStatus.NEW
            filled_size = qty
            price_used = price
            timestamp = int(time() * 1000)

        return OrderModel(
            order_id=order_resp.order_id,
            order_type=OrderType.limit.value,
            pair=symbol,
            timestamp=timestamp,
            order_side=AddOrderReq.SideEnum.SELL.value,
            qty=filled_size,
            price=price_used,
            status=status,
            time_in_force=order_details.time_in_force,
            deal_type=DealType.base_order,
        )

    def cancel_all_futures_orders(self, symbol: str) -> List[str]:
        """Cancel all open futures orders, optionally filtered by symbol.

        Uses the futures Cancel All Orders V3 endpoint, which supports
        an optional symbol filter. This cancels standard (non-stop)
        futures orders in bulk, rather than one order_id at a time.
        """
        request = CancelAllOrdersV3ReqBuilder().set_symbol(symbol).build()
        # We intentionally ignore the detailed response; any errors will
        # be raised via the transport layer.
        response = self.futures_order_api.cancel_all_orders_v3(request)
        return response.cancelled_order_ids

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

    def set_futures_margin_mode(
        self, symbol: str, margin_mode: SwitchMarginModeReq.MarginModeEnum
    ) -> SwitchMarginModeResp:
        """Set margin mode (ISOLATED or CROSS) for a futures symbol.

        This uses the dedicated futures positions margin-mode endpoint.
        """
        req = (
            SwitchMarginModeReqBuilder()
            .set_symbol(symbol)
            .set_margin_mode(margin_mode)
            .build()
        )
        return self.futures_positions_api.switch_margin_mode(req)

    def get_futures_position(self, symbol: str) -> GetPositionDetailsResp:
        """
        Get current futures position details for a symbol.
        """
        req = GetPositionDetailsReqBuilder().set_symbol(symbol).build()
        return self.futures_positions_api.get_position_details(req)

    def place_futures_order(
        self,
        symbol: str,
        side: AddOrderReq.SideEnum,
        size: float,
        leverage: int = 2,
        order_type: OrderType = OrderType.limit,
        margin_mode: str | None = "ISOLATED",
        reduce_only: bool = False,
        close_order: bool = False,
        price: float | None = None,
        stop: AddOrderReq.StopEnum | None = None,
        stop_price: float | None = None,
        stop_price_type: AddOrderReq.StopPriceTypeEnum | None = None,
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
            stop: Optional stop direction (DOWN/UP). If provided, stop_price and
                stop_price_type must also be set.
            stop_price: Optional stop trigger price. Required when stop is set.
            stop_price_type: Optional stop price type (TP/MP/IP). Required when
                stop is set.
            client_oid: Optional client order id; if omitted a UUID is generated.
        """

        client_oid = str(uuid4())

        # Ensure the symbol-level margin mode is set before placing the order.
        if margin_mode is not None:
            # Map the string ("ISOLATED"/"CROSS") to the futures margin-mode enum
            mm_enum = SwitchMarginModeReq.MarginModeEnum[margin_mode]
            self.set_futures_margin_mode(symbol, mm_enum)

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

        # Optional stop-loss / take-profit trigger parameters
        if stop is not None:
            if stop_price is None or stop_price_type is None:
                raise ValueError(
                    "stop_price and stop_price_type must be provided when stop is set"
                )
            builder = builder.set_stop(stop)
            builder = builder.set_stop_price(str(stop_price))
            builder = builder.set_stop_price_type(stop_price_type)

        req = builder.build()
        return self.futures_order_api.add_order(req)
