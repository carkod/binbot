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
