from typing import Dict, Tuple
from databases.crud.autotrade_crud import AutotradeCrud
from databases.crud.bot_crud import BotTableCrud
from exchange_apis.kucoin.futures.api import KucoinFutures
from kucoin_universal_sdk.generate.account.account import (
    GetFuturesAccountReqBuilder,
)


class KucoinFuturesBalance:
    def __init__(self):
        self.kucoin_api = KucoinFutures()
        self.autotrade_settings = AutotradeCrud().get_settings()
        self.bot_crud = BotTableCrud()
        self.fiat = self.autotrade_settings.fiat

    def get_account_balance_by_type(self) -> dict[str, dict[str, dict[str, float]]]:
        """Return a futures-only balance snapshot in a
        "by account type" shape for compatibility.

        For futures, the Kucoin API exposes a single account snapshot
        (no MAIN/TRADE/MARGIN split), so we normalize it under a
        synthetic "futures" account type.
        """
        futures_request = GetFuturesAccountReqBuilder().set_currency(self.fiat).build()
        account = self.kucoin_api.futures_account_api.get_futures_account(
            futures_request
        )

        balance_by_type: dict[str, dict[str, dict[str, float]]] = {}

        if account.currency is not None:
            balance_by_type["futures"] = {
                account.currency: {
                    "balance": float(account.account_equity or 0.0),
                    "available": float(account.available_balance or 0.0),
                    "holds": float(account.frozen_funds or 0.0),
                }
            }

        return balance_by_type

    def compute_futures_balance(self) -> Tuple[Dict[str, float], float, float]:
        """Compute balance but only for futures account.

        For now we only support USDT-M futures. If we ever detect a
        futures account currency different from the configured fiat
        (e.g. non-USDT-M), we raise NotImplementedError.

        Returns:
            (total_balances, estimated_total_fiat, fiat_available)
        """

        result_balances: Dict[str, float] = {}
        estimated_total_fiat = 0.0
        fiat_available = 0.0

        kucoin_balances = self.get_account_balance_by_type()
        # because with Futures, we don't have underlying asset,
        # balances only return USDT
        fiat_balance = kucoin_balances["futures"][self.fiat]

        estimated_total_fiat += float(fiat_balance["balance"])
        fiat_available += float(fiat_balance["available"])
        result_balances[self.fiat] = float(fiat_balance["balance"])

        return result_balances, estimated_total_fiat, fiat_available
