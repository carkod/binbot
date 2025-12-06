import os

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
        Returns a dict: {asset: {total: float, breakdown: {account_type: float, ...}}}
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

    def get_isolated_balance(self, symbol: str) -> GetIsolatedMarginAccountResp:
        request = GetIsolatedMarginAccountReqBuilder().set_symbol(symbol).build()
        response = self.account_api.get_isolated_margin_account(request)
        return response

    def get_book_depth(self, symbol: str) -> GetPartOrderBookResp:
        request = GetPartOrderBookReqBuilder().set_symbol(symbol).build()
        response = self.spot_api.get_part_order_book(request)
        return response
