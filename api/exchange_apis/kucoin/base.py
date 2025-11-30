import os

from kucoin_universal_sdk.api import DefaultClient
from kucoin_universal_sdk.generate.spot.market import (
    GetPartOrderBookReqBuilder,
    GetAllSymbolsReqBuilder,
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

    def get_ticker_price(self, symbol: str):
        request = GetPartOrderBookReqBuilder().set_symbol(symbol).build()
        response = self.spot_market_api.get_ticker(request)
        return response["price"]

    def get_account_balance(self):
        """
        Aggregate all balances from all account types (spot, main, trade, margin, futures).
        Returns a dict: {asset: {total: float, breakdown: {account_type: float, ...}}}
        """
        api = self.kucoin_rest_service.get_account_service().get_account_api()
        # 1. Get all accounts (spot/main/trade)
        all_accounts = api.get_account_list()
        asset_map: dict[str, dict] = {}
        for acc in all_accounts:
            acc_dict = dict(acc) if not isinstance(acc, dict) else acc
            asset = acc_dict.get("currency")
            if asset is None:
                continue
            try:
                balance = float(acc_dict.get("balance", 0))
            except Exception:
                balance = 0.0
            acc_type = acc_dict.get("type", "spot")
            if asset not in asset_map:
                asset_map[asset] = {"total": 0.0, "breakdown": {}}
            breakdown = asset_map[asset]["breakdown"]
            if not isinstance(breakdown, dict):
                breakdown = {}
            asset_map[asset]["total"] = float(asset_map[asset]["total"]) + balance
            breakdown[acc_type] = float(breakdown.get(acc_type, 0.0)) + balance
            asset_map[asset]["breakdown"] = breakdown

        # 2. For each account, fetch details for more info (optional, can be slow)
        #    Uncomment if you want per-accountId details
        # for acc in all_accounts:
        #     acc_id = acc["id"]
        #     detail = api.get_account_detail(acc_id)
        #     # You can add more info to asset_map here if needed

        # 3. Margin accounts (cross/isolated)
        try:
            margin_api = self.kucoin_rest_service.get_margin_service().get_account_api()
            margin_info = margin_api.get_margin_account()
            for macc in margin_info.get("accounts", []):
                macc_dict = dict(macc) if not isinstance(macc, dict) else macc
                asset = macc_dict.get("currency")
                if asset is None:
                    continue
                try:
                    balance = float(macc_dict.get("balance", 0))
                except Exception:
                    balance = 0.0
                if asset not in asset_map:
                    asset_map[asset] = {"total": 0.0, "breakdown": {}}
                breakdown = asset_map[asset]["breakdown"]
                if not isinstance(breakdown, dict):
                    breakdown = {}
                asset_map[asset]["total"] = float(asset_map[asset]["total"]) + balance
                breakdown["margin"] = float(breakdown.get("margin", 0.0)) + balance
                asset_map[asset]["breakdown"] = breakdown
        except Exception:
            pass

        # 4. Futures accounts
        try:
            futures_api = self.kucoin_rest_service.get_futures_service().get_account_api()
            futures_info = futures_api.get_futures_account()
            for facc in futures_info.get("accounts", []):
                facc_dict = dict(facc) if not isinstance(facc, dict) else facc
                asset = facc_dict.get("currency")
                if asset is None:
                    continue
                try:
                    balance = float(facc_dict.get("balance", 0))
                except Exception:
                    balance = 0.0
                if asset not in asset_map:
                    asset_map[asset] = {"total": 0.0, "breakdown": {}}
                breakdown = asset_map[asset]["breakdown"]
                if not isinstance(breakdown, dict):
                    breakdown = {}
                asset_map[asset]["total"] = float(asset_map[asset]["total"]) + balance
                breakdown["futures"] = float(breakdown.get("futures", 0.0)) + balance
                asset_map[asset]["breakdown"] = breakdown
        except Exception:
            pass

        # 5. Filter out zero balances
        result = {a: v for a, v in asset_map.items() if isinstance(v.get("total", 0.0), float) and float(v["total"]) > 0.0}
        return result
