from os import getenv
from kucoin_universal_sdk.api import DefaultClient
from kucoin_universal_sdk.model import TransportOptionBuilder
from kucoin_universal_sdk.model import ClientOptionBuilder
from kucoin_universal_sdk.model import (
    GLOBAL_API_ENDPOINT,
)


class KucoinRest:
    def __init__(self):
        self.key = getenv("KUCOIN_KEY", "")
        self.secret = getenv("KUCOIN_SECRET", "")
        self.passphrase = getenv("KUCOIN_PASSPHRASE", "")

    def setup_client(self) -> DefaultClient:
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
        return self.client
