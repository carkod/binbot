from typing import Dict, Tuple
from databases.crud.autotrade_crud import AutotradeCrud
from exchange_apis.kucoin.base import KucoinApi


class KucoinBaseBalance:
    def __init__(self):
        self.kucoin_api = KucoinApi()
        self.autotrade_settings = AutotradeCrud().get_settings()
        self.fiat = self.autotrade_settings.fiat

    def get_symbol(self, pair: str, quote: str) -> str:
        """
        Converts a trading pair to KuCoin's symbol format.

        Args:
            pair (str): The trading pair in the format "BASEQUOTE" (e.g., "BTCUSDT").

        Returns:
            str: The trading pair in KuCoin's format "BASE-QUOTE" (e.g., "BTC-USDT").
        """
        base = pair.replace(quote, "")
        symbol = f"{base}-{quote}"
        return symbol

    def compute_balance(self) -> Tuple[Dict[str, float], float, float]:
        """
        Computes total balances, estimated total fiat, and fiat available
        using the KuCoin APIs available on the passed `accounts` instance.

        Returns:
            (total_balances, estimated_total_fiat, fiat_available)
        """

        result_balances: Dict[str, float] = {}
        estimated_total_fiat = 0.0
        fiat_available = 0.0

        kucoin_balances = self.kucoin_api.get_account_balance()
        for key, value in kucoin_balances.items():
            if float(value["balance"]) > 0:
                # we don't want to convert USDC, TUSD or USDT to itself
                if key not in [
                    self.fiat,
                    "USDC",
                    "TUSD",
                    "USDT",
                ]:
                    rate = self.kucoin_api.get_ticker_price(f"{key}-{self.fiat}")
                    fiat_available += float(value["balance"]) * float(rate)
                    estimated_total_fiat += float(value["balance"]) * float(rate)
                else:
                    estimated_total_fiat += float(value["balance"])

                result_balances[key] = float(value["balance"])

        return result_balances, estimated_total_fiat, fiat_available

    def get_single_balance(self, asset: str) -> float:
        """
        Get single asset balance from KuCoin account balances.

        Args:
            asset (str): The asset symbol to retrieve the balance for.
        Returns:
            float: The balance of the specified asset.
        """
        kucoin_balances = self.kucoin_api.get_account_balance()
        if asset in kucoin_balances:
            return float(kucoin_balances[asset]["balance"])
        return 0.0
