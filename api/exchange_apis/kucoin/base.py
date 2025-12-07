import os
from time import time
from kucoin_universal_sdk.api import DefaultClient
from kucoin_universal_sdk.generate.spot.market import (
    GetPartOrderBookReqBuilder,
    GetAllSymbolsReqBuilder,
)
from kucoin_universal_sdk.generate.account.account import (
    GetSpotAccountListReqBuilder,
    GetIsolatedMarginAccountReqBuilder,
)
from kucoin_universal_sdk.model import ClientOptionBuilder
from kucoin_universal_sdk.model import (
    GLOBAL_API_ENDPOINT,
)
from kucoin_universal_sdk.model import TransportOptionBuilder
from kucoin_universal_sdk.generate.spot.market import GetPartOrderBookResp
from kucoin_universal_sdk.generate.account.account.model_get_isolated_margin_account_resp import (
    GetIsolatedMarginAccountResp,
)
from kucoin_universal_sdk.generate.spot.order.model_add_order_sync_resp import (
    AddOrderSyncResp,
)
from kucoin_universal_sdk.generate.spot.order.model_add_order_sync_req import (
    AddOrderSyncReq,
    AddOrderSyncReqBuilder,
)
from kucoin_universal_sdk.generate.spot.order.model_batch_add_orders_sync_req import (
    BatchAddOrdersSyncReqBuilder,
)
from kucoin_universal_sdk.generate.spot.order.model_batch_add_orders_sync_order_list import (
    BatchAddOrdersSyncOrderList,
)
from kucoin_universal_sdk.generate.spot.order.model_cancel_order_by_order_id_sync_req import (
    CancelOrderByOrderIdSyncReqBuilder,
)
from kucoin_universal_sdk.generate.spot.order.model_get_order_by_order_id_req import (
    GetOrderByOrderIdReqBuilder,
)
from kucoin_universal_sdk.generate.spot.order.model_get_open_orders_req import (
    GetOpenOrdersReqBuilder,
)
from kucoin_universal_sdk.generate.margin.order.model_add_order_req import (
    AddOrderReq,
    AddOrderReqBuilder,
)
from kucoin_universal_sdk.generate.margin.order.model_cancel_order_by_order_id_req import (
    CancelOrderByOrderIdReqBuilder,
)
from kucoin_universal_sdk.generate.margin.order.model_get_order_by_order_id_resp import (
    GetOrderByOrderIdResp,
)
from typing import Tuple
import random


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
            .set_transport_option(http_transport_option)
            .build()
        )
        self.client = DefaultClient(client_option)
        self.spot_api = self.client.rest_service().get_spot_service().get_market_api()
        self.account_api = (
            self.client.rest_service().get_account_service().get_account_api()
        )
        self.margin_api = (
            self.client.rest_service().get_margin_service().get_market_api()
        )
        self.margin_order_api = (
            self.client.rest_service().get_margin_service().get_order_api()
        )
        self.order_api = self.client.rest_service().get_spot_service().get_order_api()

    def get_part_order_book(self, symbol: str, size: str):
        request = GetPartOrderBookReqBuilder().set_symbol(symbol).set_size(size).build()
        response = self.spot_api.get_part_order_book(request)
        return response

    def get_all_symbols(self):
        request = GetAllSymbolsReqBuilder().build()
        response = self.spot_api.get_all_symbols(request)
        return response

    def get_ticker_price(self, symbol: str):
        request = GetPartOrderBookReqBuilder().set_symbol(symbol).build()
        response = self.spot_api.get_ticker(request)
        return response["price"]

    def get_account_balance(self):
        """
        Aggregate all balances from all account types (spot, main, trade, margin, futures).
        Returns a dict:
            {
                asset:
                    {
                        total: float,
                        breakdown:
                            {
                                    account_type: float, ...
                            }
                    }
            }
        """
        spot_request = GetSpotAccountListReqBuilder().build()
        margin_request = GetIsolatedMarginAccountReqBuilder().build()
        all_accounts = self.account_api.get_spot_account_list(spot_request)
        balance_items = dict()
        for item in all_accounts.data:
            if float(item.balance) > 0:
                balance_items[item.currency] = {
                    "balance": float(item.balance),
                    "free": float(item.available),
                    "locked": float(item.holds),
                }

        margin_accounts = self.account_api.get_isolated_margin_account(margin_request)
        if float(margin_accounts.total_asset_of_quote_currency) > 0:
            balance_items["USDT"]["balance"] += float(
                margin_accounts.total_asset_of_quote_currency
            )

        return balance_items

    def get_single_spot_balance(self, asset: str) -> float:
        spot_request = GetSpotAccountListReqBuilder().build()
        all_accounts = self.account_api.get_spot_account_list(spot_request)
        total_balance = 0.0
        for item in all_accounts.data:
            if item.currency == asset:
                return float(item.balance)

        return total_balance

    def get_isolated_balance(self, symbol: str) -> GetIsolatedMarginAccountResp:
        request = GetIsolatedMarginAccountReqBuilder().set_symbol(symbol).build()
        response = self.account_api.get_isolated_margin_account(request)
        return response

    def get_book_depth(self, symbol: str) -> GetPartOrderBookResp:
        request = GetPartOrderBookReqBuilder().set_symbol(symbol).build()
        response = self.spot_api.get_part_order_book(request)
        return response

    def simulate_order(
        self,
        symbol: str,
        side: AddOrderSyncReq.SideEnum,
        order_type: AddOrderSyncReq.TypeEnum = AddOrderSyncReq.TypeEnum.LIMIT,
        qty: float = 1,
    ) -> Tuple[AddOrderSyncResp, GetOrderByOrderIdResp]:
        """
        Fake synchronous order response shaped similarly to add_order_sync.
        Returns a dict echoing inputs and a computed price when missing.
        """
        book_price = self.matching_engine(symbol, order_side=side, qty=qty)
        # fake data
        ts = int(time() * 1000)
        order_id = str(random.randint(1000000000, 9999999999))
        order_response = AddOrderSyncResp.model_validate(
            {
                "order_time": ts,
                "order_id": order_id,
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "time_in_force": AddOrderSyncReq.TimeInForceEnum.GTC.value,
                "size": str(qty),
                "price": str(book_price),
                "status": "Done",
                "in_order_book": True,
                "fee": "0",
            }
        )
        system_order = GetOrderByOrderIdResp.model_validate(
            {
                "order_id": order_id,
                "symbol": symbol,
                "op_type": "DEAL",
                "type": order_type,
                "side": side,
                "price": str(book_price),
                "size": str(qty),
                "funds": str(float(book_price) * qty),
                "deal_funds": str(float(book_price) * qty),
                "deal_size": str(qty),
                "fee": "0",
                "fee_currency": symbol.split("-")[1],
                "stp": "CN",
                "stop": "",
                "stop_price": "0",
                "time_in_force": AddOrderSyncReq.TimeInForceEnum.GTC,
                "post_only": False,
                "hidden": False,
                "iceberg": False,
                "visible_size": "0",
                "cancel_after": 0,
                "channel": "API",
                "client_oid": "",
                "remark": "",
                "tags": "",
                "is_active": False,
                "cancel_exist": False,
                "created_at": ts,
            }
        )
        return order_response, system_order

    def matching_engine(self, symbol: str, order_side: bool, qty: float = 0) -> float:
        """
        Match quantity with available 100% fill order price,
        so that order can immediately buy/sell

        AMMEND

        @param: order_side -
            Buy order = get bid prices = False
            Sell order = get ask prices = True
        """
        data = self.get_book_depth(symbol)
        price = data.bids[0][0] if order_side else data.asks[0][0]
        base_qty = data.bids[0][1] if order_side else data.asks[0][1]

        if qty == 0:
            return price
        else:
            buyable_qty = float(qty) / float(price)
            if buyable_qty < base_qty:
                return price
            else:
                for i in range(1, 11):
                    price = data.bids[i][0] if order_side else data.asks[i][0]
                    base_qty = data.bids[i][1] if order_side else data.asks[i][1]
                    buyable_qty = float(qty) / float(price)
                    base_qty = 1
                    if buyable_qty > base_qty:
                        return price
                    else:
                        continue
                # caller to use market price
                return 0

    def buy_order(
        self,
        symbol: str,
        qty: float,
        order_type: AddOrderSyncReq.TypeEnum = AddOrderSyncReq.TypeEnum.LIMIT,
        price: float = 0,
    ) -> Tuple[AddOrderSyncResp, GetOrderByOrderIdResp]:
        builder = (
            AddOrderSyncReqBuilder()
            .set_symbol(symbol)
            .set_side(AddOrderSyncReq.SideEnum.BUY)
            .set_type(order_type)
            .set_size(str(qty))
        )
        if order_type == AddOrderSyncReq.TypeEnum.LIMIT and price > 0:
            builder = builder.set_price(str(price)).set_time_in_force(
                AddOrderSyncReq.TimeInForceEnum.GTC
            )
        req = builder.build()
        order_response = self.order_api.add_order_sync(req)
        # order_response returns incomplete info
        system_order = self.get_order_by_order_id(
            symbol=symbol, order_id=order_response.order_id
        )
        return order_response, system_order

    def sell_order(
        self,
        symbol: str,
        qty: float,
        order_type: AddOrderSyncReq.TypeEnum = AddOrderSyncReq.TypeEnum.LIMIT,
        price: float = 0,
    ) -> Tuple[AddOrderSyncResp, GetOrderByOrderIdResp]:
        builder = (
            AddOrderSyncReqBuilder()
            .set_symbol(symbol)
            .set_side(AddOrderSyncReq.SideEnum.SELL)
            .set_type(order_type)
            .set_size(str(qty))
        )
        if order_type == AddOrderSyncReq.TypeEnum.LIMIT and price > 0:
            builder = builder.set_price(str(price)).set_time_in_force(
                AddOrderSyncReq.TimeInForceEnum.GTC
            )
        req = builder.build()
        order_response = self.order_api.add_order_sync(req)
        system_order = self.get_order_by_order_id(
            symbol=symbol, order_id=order_response.order_id
        )
        return order_response, system_order

    def batch_add_orders_sync(self, orders: list[dict]) -> AddOrderSyncResp:
        """
        Batch place up to 5 limit orders for the same symbol.
        Each dict in `orders` should contain: symbol, side, type, size, price (for limit), optional fields as per SDK.
        """
        order_list: list[BatchAddOrdersSyncOrderList] = []
        for o in orders:
            item = BatchAddOrdersSyncOrderList(
                client_oid=o.get("clientOid"),
                symbol=o["symbol"],
                side=(
                    BatchAddOrdersSyncOrderList.SideEnum.BUY
                    if str(o["side"]).lower() == "buy"
                    else BatchAddOrdersSyncOrderList.SideEnum.SELL
                ),
                type=BatchAddOrdersSyncOrderList.TypeEnum.LIMIT,
                size=str(o["size"]),
                price=str(o["price"]) if "price" in o else None,
                time_in_force=BatchAddOrdersSyncOrderList.TimeInForceEnum.GTC,
            )
            order_list.append(item)

        req = BatchAddOrdersSyncReqBuilder().set_order_list(order_list).build()
        return self.order_api.batch_add_orders_sync(req)

    def cancel_order_by_order_id_sync(self, symbol: str, order_id: str):
        req = (
            CancelOrderByOrderIdSyncReqBuilder()
            .set_symbol(symbol)
            .set_order_id(order_id)
            .build()
        )
        return self.order_api.cancel_order_by_order_id_sync(req)

    def get_order_by_order_id(
        self, symbol: str, order_id: str
    ) -> GetOrderByOrderIdResp:
        req = (
            GetOrderByOrderIdReqBuilder()
            .set_symbol(symbol)
            .set_order_id(order_id)
            .build()
        )
        return self.order_api.get_order_by_order_id(req)

    def get_open_orders(self, symbol: str):
        req = GetOpenOrdersReqBuilder().set_symbol(symbol).build()
        return self.order_api.get_open_orders(req)

    # --- Margin (Isolated) operations ---
    def create_margin_order(
        self,
        symbol: str,
        side: AddOrderReq.SideEnum,
        order_type: AddOrderReq.TypeEnum,
        qty: float,
        price: float = 0,
        time_in_force: AddOrderReq.TimeInForceEnum = AddOrderReq.TimeInForceEnum.GTC,
        client_oid: str | None = None,
        auto_borrow: bool = False,
        auto_repay: bool = False,
    ):
        builder = (
            AddOrderReqBuilder()
            .set_symbol(symbol)
            .set_side(side)
            .set_type(order_type)
            .set_size(str(qty))
            .set_time_in_force(time_in_force)
            .set_is_isolated(True)
        )
        if client_oid:
            builder = builder.set_client_oid(client_oid)
        if order_type == AddOrderReq.TypeEnum.LIMIT and price > 0:
            builder = builder.set_price(str(price))
        if auto_borrow:
            builder = builder.set_auto_borrow(True)
        if auto_repay:
            builder = builder.set_auto_repay(True)

        req = builder.build()
        return self.margin_order_api.add_order(req)

    def cancel_margin_order_by_order_id(self, symbol: str, order_id: str):
        # Margin API uses cancel by order id req builder from margin.order
        req_cancel = (
            CancelOrderByOrderIdReqBuilder()
            .set_symbol(symbol)
            .set_order_id(order_id)
            .build()
        )
        return self.margin_order_api.cancel_order_by_order_id(req_cancel)

    def get_margin_order_by_order_id(
        self, symbol: str, order_id: str
    ) -> GetOrderByOrderIdResp:
        req = (
            GetOrderByOrderIdReqBuilder()
            .set_symbol(symbol)
            .set_order_id(order_id)
            .build()
        )
        return self.margin_order_api.get_order_by_order_id(req)

    def get_margin_open_orders(self, symbol: str):
        req = GetOpenOrdersReqBuilder().set_symbol(symbol).build()
        return self.margin_order_api.get_open_orders(req)

    def simulate_margin_order(
        self,
        symbol: str,
        side: AddOrderReq.SideEnum,
        order_type: AddOrderReq.TypeEnum,
        qty: float,
    ) -> Tuple[AddOrderSyncResp, GetOrderByOrderIdResp]:
        """
        Fake isolated margin order response echoing inputs.
        """
        book_price = self.matching_engine(
            symbol, order_side=(side == AddOrderReq.SideEnum.SELL), qty=qty
        )
        ts = int(time() * 1000)
        order_id = str(random.randint(1000000000, 9999999999))
        order_response = AddOrderSyncResp.model_validate(
            {
                "order_time": ts,
                "order_id": order_id,
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "time_in_force": AddOrderSyncReq.TimeInForceEnum.GTC.value,
                "size": str(qty),
                "price": str(book_price),
                "status": "Done",
                "in_order_book": True,
                "fee": "0",
            }
        )
        system_order = GetOrderByOrderIdResp.model_validate(
            {
                "order_id": order_id,
                "symbol": symbol,
                "op_type": "DEAL",
                "type": order_type,
                "side": side,
                "price": str(book_price),
                "size": str(qty),
                "funds": str(float(book_price) * qty),
                "deal_funds": str(float(book_price) * qty),
                "deal_size": str(qty),
                "fee": "0",
                "fee_currency": symbol.split("-")[1],
                "stp": "CN",
                "stop": "",
                "stop_price": "0",
                "time_in_force": AddOrderSyncReq.TimeInForceEnum.GTC,
                "post_only": False,
                "hidden": False,
                "iceberg": False,
                "visible_size": "0",
                "cancel_after": 0,
                "channel": "API",
                "client_oid": "",
                "remark": "",
                "tags": "",
                "is_active": False,
                "cancel_exist": False,
                "created_at": ts,
            }
        )
        return order_response, system_order
