from typing import Dict, Tuple
from enum import Enum
from databases.crud.autotrade_crud import AutotradeCrud
from databases.crud.bot_crud import BotTableCrud
from exchange_apis.kucoin.base import KucoinApi
from tools.enum_definitions import QuoteAssets


class KucoinBaseBalance:
    def __init__(self):
        self.kucoin_api = KucoinApi()
        self.autotrade_settings = AutotradeCrud().get_settings()
        self.bot_crud = BotTableCrud()
        self.fiat = self.autotrade_settings.fiat

    def get_symbol(self, pair: str, quote: QuoteAssets | str) -> str:
        """
        Converts a trading pair to KuCoin's symbol format.

        Args:
            pair (str): The trading pair in the format "BASEQUOTE" (e.g., "BTCUSDT").

        Returns:
            str: The trading pair in KuCoin's format "BASE-QUOTE" (e.g., "BTC-USDT").
        """
        if isinstance(quote, QuoteAssets):
            quote = quote.value

        base = pair.replace(quote, "")
        symbol = f"{base}-{quote}"
        return symbol

    def compute_balance(self) -> Tuple[Dict[str, Dict[str, float]], float, float]:
        """
        Computes total balances, estimated total fiat, and fiat available
        using the KuCoin APIs available on the passed `accounts` instance.
        Similar to ConsolidatedAccounts.get_balance but with the account type
        separtion (main, trade, margin, futures).

        Returns:
            (total_balances, estimated_total_fiat, fiat_available)
        """

        result_balances: Dict[str, Dict[str, float]] = {}
        estimated_total_fiat = 0.0
        fiat_available = 0.0

        kucoin_balances = self.kucoin_api.get_account_balance_by_type()
        for account_type, balances in kucoin_balances.items():
            account_type_str = (
                account_type.value if isinstance(account_type, Enum) else account_type
            )
            if account_type_str not in result_balances:
                result_balances[account_type_str] = {}
            for key, value in balances.items():
                if account_type_str == "main" and key == self.fiat:
                    fiat_available += float(value["balance"])
                if float(value["balance"]) > 0:
                    # we don't want to convert USDC, TUSD or USDT to itself
                    if key not in [
                        self.fiat,
                        "USDC",
                        "TUSD",
                        "USDT",
                    ]:
                        rate = self.kucoin_api.get_ticker_price(f"{key}-{self.fiat}")
                        estimated_total_fiat += float(value["balance"]) * float(rate)
                    else:
                        estimated_total_fiat += float(value["balance"])

                    result_balances[account_type_str][key] = float(value["balance"])

        return result_balances, estimated_total_fiat, fiat_available

    def normalized_compute_balance(
        self,
    ) -> Tuple[Dict[str, float], float, float]:
        """
        compute_balance but backwards compatible with currently stored
        balances structure.

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
            for key, value in balances.items():
                if float(value["balance"]) > 0:
                    if account_type_str == "main" and key == self.fiat:
                        fiat_available += float(value["balance"])
                    # we don't want to convert USDC, TUSD or USDT to itself
                    if key not in [
                        self.fiat,
                        "USDC",
                        "TUSD",
                        "USDT",
                    ]:
                        rate = self.kucoin_api.get_ticker_price(f"{key}-{self.fiat}")
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

    def clean_assets(self, bypass: bool = False):
        """
        Move any assets from trade or margin accounts to main account that are below a certain threshold
        """
        kucoin_balances = self.kucoin_api.get_account_balance_by_type()
        active_symbols = self.bot_crud.get_active_pairs()

        for account_type, balances in kucoin_balances.items():
            account_type_str = (
                account_type.value if isinstance(account_type, Enum) else account_type
            )
            if account_type_str != "main":
                for key, value in balances.items():
                    # assume that we always use USDT (fiat) as trade asset
                    # this wouldn't work if USDTEUR, i.e. asset would be cleaned
                    if key not in active_symbols or key == self.fiat:
                        balance_amount = float(balances[key]["balance"])
                        if balance_amount > 0:
                            self.kucoin_api.transfer_trade_to_main(
                                asset=self.fiat,
                                amount=balance_amount,
                            )
