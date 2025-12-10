import os
from time import time
import random
import uuid
from kucoin_universal_sdk.api import DefaultClient
from kucoin_universal_sdk.generate.spot.market import (
    GetPartOrderBookReqBuilder,
    GetAllSymbolsReqBuilder,
    GetFullOrderBookReqBuilder,
    GetKLinesReqBuilder,
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
from kucoin_universal_sdk.generate.margin.debit.model_repay_req import (
    RepayReqBuilder,
)
from kucoin_universal_sdk.generate.margin.debit.model_repay_resp import (
    RepayResp,
)
from kucoin_universal_sdk.generate.margin.debit.model_borrow_req import (
    BorrowReqBuilder,
)
from kucoin_universal_sdk.generate.margin.debit.model_borrow_resp import (
    BorrowResp,
)
from kucoin_universal_sdk.generate.account.transfer.model_flex_transfer_req import (
    FlexTransferReqBuilder,
    FlexTransferReq,
)
from kucoin_universal_sdk.generate.account.transfer.model_flex_transfer_resp import (
    FlexTransferResp,
)


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
        self.debit_api = self.client.rest_service().get_margin_service().get_debit_api()
        self.transfer_api = (
            self.client.rest_service().get_account_service().get_transfer_api()
        )
        self.order_api = self.client.rest_service().get_spot_service().get_order_api()

    def get_part_order_book(self, symbol: str, size: int):
        request = (
            GetPartOrderBookReqBuilder().set_symbol(symbol).set_size(str(size)).build()
        )
        response = self.spot_api.get_part_order_book(request)
        return response

    def get_full_order_book(self, symbol: str, size: int):
        request = GetFullOrderBookReqBuilder().set_symbol(symbol).build()
        response = self.spot_api.get_full_order_book(request)
        return response

    def get_all_symbols(self):
        request = GetAllSymbolsReqBuilder().build()
        response = self.spot_api.get_all_symbols(request)
        return response

    def get_raw_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 500,
        start_time=None,
        end_time=None,
    ):
        """
        Get raw klines/candlestick data from Kucoin.

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
        builder = GetKLinesReqBuilder().set_symbol(symbol).set_type(interval)

        if start_time:
            builder = builder.set_start_at(int(start_time / 1000))  # Convert to seconds
        if end_time:
            builder = builder.set_end_at(int(end_time / 1000))  # Convert to seconds

        request = builder.build()
        response = self.spot_api.get_k_lines(request)

        # Helper to calculate interval duration in milliseconds
        def get_interval_ms(interval_str: str) -> int:
            """Convert Kucoin interval string to milliseconds"""
            interval_map = {
                "1min": 60 * 1000,
                "3min": 3 * 60 * 1000,
                "5min": 5 * 60 * 1000,
                "15min": 15 * 60 * 1000,
                "30min": 30 * 60 * 1000,
                "1hour": 60 * 60 * 1000,
                "2hour": 2 * 60 * 60 * 1000,
                "4hour": 4 * 60 * 60 * 1000,
                "6hour": 6 * 60 * 60 * 1000,
                "8hour": 8 * 60 * 60 * 1000,
                "12hour": 12 * 60 * 60 * 1000,
                "1day": 24 * 60 * 60 * 1000,
                "1week": 7 * 24 * 60 * 60 * 1000,
            }
            return interval_map.get(interval_str, 60 * 1000)  # Default to 1 minute

        interval_ms = get_interval_ms(interval)

        # Convert Kucoin format to Binance-compatible format
        # Kucoin returns: [time, open, close, high, low, volume, turnover]
        # Binance format: [open_time, open, high, low, close, volume, close_time, ...]
        klines = []
        if response.data:
            for k in response.data[:limit]:
                # k format: [timestamp(seconds), open, close, high, low, volume, turnover]
                open_time = int(k[0]) * 1000  # Convert to milliseconds
                close_time = open_time + interval_ms  # Calculate proper close time
                klines.append(
                    [
                        open_time,  # open_time in milliseconds
                        k[1],  # open
                        k[3],  # high
                        k[4],  # low
                        k[2],  # close
                        k[5],  # volume
                        close_time,  # close_time properly calculated
                    ]
                )

        return klines

    def get_ticker_price(self, symbol: str) -> float:
        request = GetPartOrderBookReqBuilder().set_symbol(symbol).set_size("1").build()
        response = self.spot_api.get_ticker(request)
        return float(response.price)

    def get_account_balance(self):
        """
        Aggregate all balances from all account types (spot, main, trade, margin, futures).

        The right data shape for Kucion should be provided by
        get_account_balance_by_type method.

        However, this method provides a normalized version for backwards compatibility (Binance) and consistency with current balances table.

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
        all_accounts = self.account_api.get_spot_account_list(spot_request)
        balance_items = dict()
        for item in all_accounts.data:
            if float(item.balance) > 0:
                balance_items[item.currency] = {
                    "balance": float(item.balance),
                    "free": float(item.available),
                    "locked": float(item.holds),
                }

        margin_request = GetIsolatedMarginAccountReqBuilder().build()
        margin_accounts = self.account_api.get_isolated_margin_account(margin_request)
        if float(margin_accounts.total_asset_of_quote_currency) > 0:
            balance_items["USDT"]["balance"] += float(
                margin_accounts.total_asset_of_quote_currency
            )

        return balance_items

    def get_account_balance_by_type(self):
        """
        Get balances grouped by account type.
        Returns:
            {
                'MAIN': {'USDT': {...}, 'BTC': {...}, ...},
                'TRADE': {'USDT': {...}, ...},
                'MARGIN': {...},
                ...
            }
        Each currency has: balance (total), available, holds
        """
        spot_request = GetSpotAccountListReqBuilder().build()
        all_accounts = self.account_api.get_spot_account_list(spot_request)

        balance_by_type: dict[str, dict[str, dict[str, float]]] = {}
        for item in all_accounts.data:
            if float(item.balance) > 0:
                account_type = item.type  # MAIN, TRADE, MARGIN, etc.
                if account_type not in balance_by_type:
                    balance_by_type[account_type] = {}
                balance_by_type[account_type][item.currency] = {
                    "balance": float(item.balance),
                    "available": float(item.available),
                    "holds": float(item.holds),
                }

        return balance_by_type

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

    def simulate_order(
        self,
        symbol: str,
        side: AddOrderSyncReq.SideEnum,
        order_type: AddOrderSyncReq.TypeEnum = AddOrderSyncReq.TypeEnum.LIMIT,
        qty: float = 1,
    ) -> GetOrderByOrderIdResp:
        """
        Fake synchronous order response shaped similarly to add_order_sync.
        Returns a dict echoing inputs and a computed price when missing.
        """
        book_price = self.matching_engine(symbol, order_side=side, qty=qty)
        # fake data
        ts = int(time() * 1000)
        order_id = str(random.randint(1000000000, 9999999999))

        order = GetOrderByOrderIdResp.model_validate(
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
        return order

    def simple_matching_engine(self, symbol: str, order_side: bool) -> float:
        """
        Get top of book price for immediate buy/sell
        this is good for paper trading
        or initial price estimates

        @param: order_side -
            Buy order = get bid prices = False
            Sell order = get ask prices = True
        """
        # Part order book only returns top 1 level at time of writing
        data = self.get_part_order_book(symbol, size=1)
        price = data.bids[0][0] if order_side else data.asks[0][0]
        return price

    def matching_engine(self, symbol: str, order_side: bool, qty: float = 0) -> float:
        """
        Match quantity with available 100% fill order price,
        so that order can immediately buy/sell

        Only use this if we need to find optimal price for given qty

        @param: order_side -
            Buy order = get bid prices = False
            Sell order = get ask prices = True
        """
        # Part order book only returns top 1 level at time of writing
        data = self.get_full_order_book(symbol, size=10)
        price = data.bids[0][0] if order_side else data.asks[0][0]
        base_qty = data.bids[0][1] if order_side else data.asks[0][1]

        if qty == 0:
            return float(price)
        else:
            buyable_qty = float(qty) / float(price)
            if buyable_qty < float(base_qty):
                return float(price)
            else:
                for i in range(1, 11):
                    price = data.bids[i][0] if order_side else data.asks[i][0]
                    base_qty = data.bids[i][1] if order_side else data.asks[i][1]
                    buyable_qty = float(qty) / float(price)
                    base_qty = 1
                    if buyable_qty > float(base_qty):
                        return float(price)
                    else:
                        continue
                # caller to use market price
                return 0

    def buy_order(
        self,
        symbol: str,
        qty: float,
        order_type: AddOrderSyncReq.TypeEnum = AddOrderSyncReq.TypeEnum.LIMIT,
    ) -> GetOrderByOrderIdResp:
        book_price = self.matching_engine(
            symbol, order_side=AddOrderSyncReq.SideEnum.SELL, qty=qty
        )
        builder = (
            AddOrderSyncReqBuilder()
            .set_symbol(symbol)
            .set_side(AddOrderSyncReq.SideEnum.BUY)
            .set_type(order_type)
            .set_size(str(qty))
            .set_price(str(book_price))
        )

        req = builder.build()
        order_response = self.order_api.add_order_sync(req)
        # order_response returns incomplete info
        order = self.get_order_by_order_id(
            symbol=symbol, order_id=order_response.order_id
        )
        return order

    def sell_order(
        self,
        symbol: str,
        qty: float,
        order_type: AddOrderSyncReq.TypeEnum = AddOrderSyncReq.TypeEnum.LIMIT,
        price: float = 0,
    ) -> GetOrderByOrderIdResp:
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
        order = self.get_order_by_order_id(
            symbol=symbol, order_id=order_response.order_id
        )
        return order

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
    def buy_margin_order(
        self,
        symbol: str,
        qty: float,
        order_type: AddOrderReq.TypeEnum = AddOrderReq.TypeEnum.LIMIT,
        price: float = 0,
        time_in_force: AddOrderReq.TimeInForceEnum = AddOrderReq.TimeInForceEnum.GTC,
        client_oid: str | None = None,
        auto_borrow: bool = False,
        auto_repay: bool = False,
    ) -> GetOrderByOrderIdResp:
        builder = (
            AddOrderReqBuilder()
            .set_symbol(symbol)
            .set_side(AddOrderReq.SideEnum.BUY)
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
        order_response = self.margin_order_api.add_order(req)
        order = self.get_margin_order_by_order_id(
            symbol=symbol, order_id=order_response.order_id
        )
        return order

    def sell_margin_order(
        self,
        symbol: str,
        qty: float,
        order_type: AddOrderReq.TypeEnum = AddOrderReq.TypeEnum.LIMIT,
        price: float = 0,
        time_in_force: AddOrderReq.TimeInForceEnum = AddOrderReq.TimeInForceEnum.GTC,
        client_oid: str | None = None,
        auto_borrow: bool = False,
        auto_repay: bool = False,
    ) -> GetOrderByOrderIdResp:
        builder = (
            AddOrderReqBuilder()
            .set_symbol(symbol)
            .set_side(AddOrderReq.SideEnum.SELL)
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
        order_response = self.margin_order_api.add_order(req)
        order = self.get_margin_order_by_order_id(
            symbol=symbol, order_id=order_response.order_id
        )
        return order

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
        order_type: AddOrderReq.TypeEnum = AddOrderReq.TypeEnum.LIMIT,
        qty: float = 1,
    ) -> GetOrderByOrderIdResp:
        """
        Fake isolated margin order response echoing inputs.
        """
        book_price = self.matching_engine(
            symbol, order_side=(side == AddOrderReq.SideEnum.SELL), qty=qty
        )
        ts = int(time() * 1000)
        order_id = str(random.randint(1000000000, 9999999999))
        order = GetOrderByOrderIdResp.model_validate(
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
        return order

    def repay_margin_loan(
        self,
        asset: str,
        symbol: str,
        amount: float,
    ) -> RepayResp:
        req = (
            RepayReqBuilder()
            .set_currency(asset)
            .set_symbol(symbol)
            .set_size(str(amount))
            .set_is_isolated(True)
            .build()
        )
        return self.debit_api.repay(req)

    def transfer_isolated_margin_to_spot(
        self, asset: str, symbol: str, amount: float
    ) -> FlexTransferResp:
        """
        Transfer funds from isolated margin to spot (main) account.
        `symbol` is the isolated pair like "BTC-USDT".
        """
        client_oid = str(uuid.uuid4())
        req = (
            FlexTransferReqBuilder()
            .set_client_oid(client_oid)
            .set_currency(asset)
            .set_amount(str(amount))
            .set_type(FlexTransferReq.TypeEnum.INTERNAL)
            .set_from_account_type(FlexTransferReq.FromAccountTypeEnum.ISOLATED)
            .set_from_account_tag(symbol)
            .set_to_account_type(FlexTransferReq.ToAccountTypeEnum.MAIN)
            .build()
        )
        return self.transfer_api.flex_transfer(req)

    def transfer_spot_to_isolated_margin(
        self, asset: str, symbol: str, amount: float
    ) -> FlexTransferResp:
        """
        Transfer funds from spot (main) account to isolated margin account.
        `symbol` must be the isolated pair like "BTC-USDT".
        """
        client_oid = str(uuid.uuid4())
        req = (
            FlexTransferReqBuilder()
            .set_client_oid(client_oid)
            .set_currency(asset)
            .set_amount(str(amount))
            .set_type(FlexTransferReq.TypeEnum.INTERNAL)
            .set_from_account_type(FlexTransferReq.FromAccountTypeEnum.MAIN)
            .set_to_account_type(FlexTransferReq.ToAccountTypeEnum.ISOLATED)
            .set_to_account_tag(symbol)
            .build()
        )
        return self.transfer_api.flex_transfer(req)

    def transfer_main_to_trade(self, asset: str, amount: float) -> FlexTransferResp:
        """
        Transfer funds from main to trade (spot) account.
        """
        client_oid = str(uuid.uuid4())
        req = (
            FlexTransferReqBuilder()
            .set_client_oid(client_oid)
            .set_currency(asset)
            .set_amount(str(amount))
            .set_type(FlexTransferReq.TypeEnum.INTERNAL)
            .set_from_account_type(FlexTransferReq.FromAccountTypeEnum.MAIN)
            .set_to_account_type(FlexTransferReq.ToAccountTypeEnum.TRADE)
            .build()
        )
        return self.transfer_api.flex_transfer(req)

    def transfer_trade_to_main(self, asset: str, amount: float) -> FlexTransferResp:
        """
        Transfer funds from trade (spot) account to main.
        """
        client_oid = str(uuid.uuid4())
        req = (
            FlexTransferReqBuilder()
            .set_client_oid(client_oid)
            .set_currency(asset)
            .set_amount(str(amount))
            .set_type(FlexTransferReq.TypeEnum.INTERNAL)
            .set_from_account_type(FlexTransferReq.FromAccountTypeEnum.TRADE)
            .set_to_account_type(FlexTransferReq.ToAccountTypeEnum.MAIN)
            .build()
        )
        return self.transfer_api.flex_transfer(req)

    def create_margin_loan(
        self,
        asset: str,
        symbol: str,
        amount: float,
        is_isolated: bool = True,
    ) -> BorrowResp:
        """
        Create a margin loan (borrow) on KuCoin.
        For isolated margin, pass the trading pair in `symbol` (e.g., "BTC-USDT") and set `is_isolated=True`.
        """
        req = (
            BorrowReqBuilder()
            .set_currency(asset)
            .set_symbol(symbol)
            .set_size(str(amount))
            .set_is_isolated(is_isolated)
            .build()
        )
        return self.debit_api.borrow(req)
