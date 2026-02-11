from typing import Dict, Tuple
from enum import Enum
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
        futures_request = GetFuturesAccountReqBuilder().build()
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
        for account_type, balances in kucoin_balances.items():
            account_type_str = (
                account_type.value if isinstance(account_type, Enum) else account_type
            )
            if account_type_str != "futures":
                continue

            for asset, value in balances.items():
                if asset != self.fiat:
                    raise NotImplementedError(
                        "Non-USDT-M futures accounts are not supported yet"
                    )

                balance = float(value["balance"])
                if balance <= 0:
                    continue

                estimated_total_fiat += balance
                fiat_available += float(value["available"])
                result_balances[asset] = balance

        return result_balances, estimated_total_fiat, fiat_available
