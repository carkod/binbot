from account.schemas import BalanceSchema
from databases.crud.balances_crud import BalancesCrud
from exchange_apis.binance.assets import Assets
from exchange_apis.kucoin.base import KucoinApi
from tools.enum_definitions import ExchangeId
from databases.utils import get_session
from sqlmodel import Session
from tools.maths import round_numbers
from exchange_apis.kucoin.deals.base import KucoinBaseBalance
from typing import Dict


class ConsolidatedAccounts:
    def __init__(self, session: Session = None):
        if not session:
            self.session = get_session()
        else:
            self.session = session

        self.kucoin_api = KucoinApi()
        self.binance_assets = Assets(session=self.session)
        self.autotrade_settings = self.binance_assets.autotrade_settings
        self.balances_crud = BalancesCrud(session=self.session)

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
            kucoin_balance = KucoinBaseBalance()
            total_balances, estimated_total_fiat, fiat_available = (
                kucoin_balance.normalized_compute_balance()
            )

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
                        try:
                            rate = self.binance_assets.get_ticker_price(
                                f"{asset['asset']}{self.autotrade_settings.fiat}"
                            )
                        except Exception as error:
                            print(error)

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

        return result

    def store_balance(self):
        if self.autotrade_settings.exchange_id == ExchangeId.KUCOIN:
            kucoin_balances = self.get_balance()
            response = self.balances_crud.create_balance_series(
                kucoin_balances.balances,
                round_numbers(kucoin_balances.estimated_total_fiat, 4),
            )
            return response
        else:
            return Assets(session=self.session).store_balance()
