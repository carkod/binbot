import os
from pybit.unified_trading import HTTP


class Bybit:
    def __init__(self):
        self.session = HTTP(
            testnet=False,
            api_key=os.environ["BYBIT_KEY"],
            api_secret=os.environ["BYBIT_SECRET"],
            log_requests=True,
        )

    def get_balance(self):
        data = self.session.get_wallet_balance()
        return data
