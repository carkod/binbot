from account.schemas import BalanceSchema, KucoinBalance
from databases.crud.balances_crud import BalancesCrud
from exchange_apis.binance.assets import Assets
from pybinbot import ExchangeId, round_numbers, KucoinApi, KucoinFutures, BinbotErrors
from databases.utils import get_session
from sqlmodel import Session
from exchange_apis.kucoin.deals.base import KucoinBaseBalance
from typing import Dict
from enum import Enum
from tools.config import Config


class ConsolidatedAccounts:
    def __init__(self, session: Session = None):
        if not session:
            self.session = get_session()
        else:
            self.session = session

        self.config = Config()
        self.kucoin_api = KucoinApi(
            key=self.config.kucoin_key,
            secret=self.config.kucoin_secret,
            passphrase=self.config.kucoin_passphrase,
        )
        self.kucoin_futures_api = KucoinFutures(
            key=self.config.kucoin_key,
            secret=self.config.kucoin_secret,
            passphrase=self.config.kucoin_passphrase,
        )
        self.binance_assets = Assets(session=self.session)
        self.autotrade_settings = self.binance_assets.autotrade_settings
        self.balances_crud = BalancesCrud(session=self.session)
        self.fiat = self.autotrade_settings.fiat

    @staticmethod
    def _deposit_amount(entry) -> float:
        if isinstance(entry, dict):
            amount = entry.get("amount") or entry.get("size") or 0
        else:
            amount = getattr(entry, "amount", None)
            if amount is None:
                amount = getattr(entry, "size", 0)

        try:
            return float(amount)
        except (TypeError, ValueError):
            return 0.0

    def get_total_deposit(self) -> float:
        if self.autotrade_settings.exchange_id != ExchangeId.KUCOIN:
            raise NotImplementedError(
                "Total deposit aggregation is only implemented for KuCoin."
            )

        try:
            deposits = self.kucoin_futures_api.get_deposit_history()
        except BinbotErrors:
            return 0.0

        if not deposits:
            return 0.0

        if isinstance(deposits, dict):
            candidates = (
                deposits.get("items")
                or deposits.get("data")
                or deposits.get("deposits")
                or []
            )
        else:
            candidates = deposits

        if isinstance(candidates, dict):
            candidates = candidates.get("items") or []

        return sum(self._deposit_amount(deposit) for deposit in candidates)

    def get_balance(self) -> BalanceSchema:
        """
        Always try to use this function to get balances to have
        one funnel for balance data

        This helps with architecting caching
        and endpoint limit weights as we are making multiple external calls and db interactions

        - We use get_ticker_price to get conversion rates
        - We use get_account_balance to get raw balances
        """

        result = BalanceSchema()
        total_balances: Dict[str, float] = dict()
        estimated_total_fiat = 0.0
        fiat_available = 0.0
        if self.autotrade_settings.exchange_id == ExchangeId.KUCOIN:
            kucoin_balance = self.get_kucoin_balances_by_type()
            for _, balances in kucoin_balance.balances.items():
                for asset, balance in balances.items():
                    total_balances[asset] = total_balances.get(asset, 0) + balance

            estimated_total_fiat = kucoin_balance.estimated_total_fiat
            fiat_available = kucoin_balance.fiat_available

        else:
            binance_balances = self.binance_assets.get_raw_balance()

            for asset in binance_balances:
                if float(asset["free"]) > 0 or float(asset["locked"]) > 0:
                    if asset["asset"] == self.autotrade_settings.fiat:
                        fiat_available += float(asset["free"])

                    if asset["asset"] not in [
                        self.autotrade_settings.fiat,
                        "TUSD",
                        "USDT",
                        "TRY",  # blocked, but still in shows in balance
                        "BAKE",  # delisted, but still in shows in balance
                        "NFT",
                    ]:
                        rate = self.binance_assets.get_ticker_price(
                            f"{asset['asset']}{self.autotrade_settings.fiat}"
                        )
                        fiat_available += float(asset["free"]) * float(rate)
                        estimated_total_fiat += (
                            float(asset["free"]) + float(asset["locked"])
                        ) * float(rate)
                    else:
                        continue

                    total_balances[asset["asset"]] = (
                        total_balances.get(asset["asset"], 0)
                        + float(asset["free"])
                        + float(asset["locked"])
                    )

        result.balances = total_balances
        result.estimated_total_fiat = estimated_total_fiat
        result.fiat_available = fiat_available
        result.fiat_currency = self.autotrade_settings.fiat
        if self.autotrade_settings.exchange_id == ExchangeId.KUCOIN:
            result.total_deposit = self.get_total_deposit()
        else:
            result.total_deposit = 0.0

        return result

    def store_balance(self):
        if self.autotrade_settings.exchange_id == ExchangeId.KUCOIN:
            kucoin_balances = self.get_balance()
            net_estimated_total_fiat = (
                kucoin_balances.estimated_total_fiat - kucoin_balances.total_deposit
            )
            response = self.balances_crud.create_balance_series(
                kucoin_balances.balances,
                round_numbers(net_estimated_total_fiat, 4),
                exchange_id=ExchangeId.KUCOIN,
            )
            return response
        else:
            return Assets(session=self.session).store_balance()

    def clean_balance_assets(self, bypass: bool = False):
        """
        Move any assets from trade or margin accounts to main account that are below a certain threshold

        Kucoin doesn't punish us for using the endpoint too much so no need to bypass
        """
        if self.autotrade_settings.exchange_id == ExchangeId.KUCOIN:
            kucoin_balance = KucoinBaseBalance()
            kucoin_balance.clean_assets()
        else:
            Assets(session=self.session).clean_balance_assets(bypass=bypass)

    def get_kucoin_balances_by_type(self) -> KucoinBalance:
        """
        Get balances grouped by account type for KuCoin exchange
        """
        balances_by_type = self.kucoin_api.get_account_balance_by_type()
        futures_balances = self.kucoin_futures_api.get_futures_balance(self.fiat)

        fiat_available = futures_balances.available_balance
        estimated_total_fiat = futures_balances.account_equity

        result_balances: dict[str, dict[str, float]] = {}

        for account_type, balances in balances_by_type.items():
            account_type_str = (
                account_type.value if isinstance(account_type, Enum) else account_type
            )
            for key, value in balances.items():
                if float(value["balance"]) > 0:
                    if key == self.fiat:
                        fiat_available += float(value["balance"])
                    # we don't want to convert USDC, TUSD or USDT to itself
                    if key != self.fiat:
                        rate = self.kucoin_api.get_ticker_price(f"{key}-{self.fiat}")
                        estimated_total_fiat += float(value["balance"]) * float(rate)
                    else:
                        estimated_total_fiat += float(value["balance"])

                    # Accumulate balances without overwriting other account types
                    result_balances.setdefault(account_type_str, {})[key] = float(
                        value["balance"]
                    )

        return KucoinBalance(
            balances=result_balances,
            estimated_total_fiat=estimated_total_fiat,
            fiat_available=fiat_available,
            fiat_currency=self.fiat,
        )
