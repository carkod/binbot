from typing import Dict, Tuple
from enum import Enum
from tools.config import Config
from databases.crud.autotrade_crud import AutotradeCrud
from databases.crud.bot_crud import BotTableCrud
from exchange_apis.kucoin.futures.api import KucoinFutures
    

class KucoinFuturesBalance:
    def __init__(self):
        self.config = Config()
        self.kucoin_api = KucoinFutures(
            key=self.config.kucoin_key,
            secret=self.config.kucoin_secret,
            passphrase=self.config.kucoin_passphrase,
        )
        self.autotrade_settings = AutotradeCrud().get_settings()
        self.bot_crud = BotTableCrud()
        self.fiat = self.autotrade_settings.fiat

    def compute_futures_balance(self) -> Tuple[Dict[str, float], float, float]:
        """
        compute_balance but only for futures account.

        Returns:
            (total_balances, estimated_total_fiat, fiat_available)
        """

        result_balances: Dict[str, float] = {}
        estimated_total_fiat = 0.0
        fiat_available = 0.0

        kucoin_balances = self.kucoin_api.get_account_balance_by_type()
        for account_type, balances in kucoin_balances.items():
            account_type_str = (
                account_type.value if isinstance(account_type, Enum) else account_type
            )
            if account_type_str == "futures":
                for key, value in balances.items():
                    if float(value["balance"]) > 0:
                        # we don't want to convert USDC, TUSD or USDT to itself
                        if key not in [
                            self.fiat,
                            "USDC",
                            "TUSD",
                            "USDT",
                        ]:
                            rate = self.kucoin_api.get_ticker_price(
                                f"{key}-{self.fiat}"
                            )
                            estimated_total_fiat += float(value["balance"]) * float(
                                rate
                            )
                        else:
                            estimated_total_fiat += float(value["balance"])

                        result_balances[key] = float(value["balance"])

        return result_balances, estimated_total_fiat, fiat_available
