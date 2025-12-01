from exchange_apis.binance.assets import Assets
from exchange_apis.kucoin.base import KucoinApi
from tools.enum_definitions import ExchangeId


class ConsolidatedAccounts:
    def __init__(self, session):
        self.kucoin_api = KucoinApi()
        self.binance_assets = Assets(session=session)
        self.autotrade_settings = self.binance_assets.autotrade_settings

    def get_balance(self) -> dict:
        total_balance = dict()
        estimated_total_fiat = 0.0
        if self.autotrade_settings.exchange_id == ExchangeId.KUCOIN:
            kucoin_balances = self.kucoin_api.get_account_balance()
            for key, value in kucoin_balances.items():
                if float(value["balance"]) > 0:
                    # we don't want to convert USDC, USDC, TUSD or USDT to itself
                    if key not in [
                        self.autotrade_settings.fiat,
                        "USDC",
                        "TUSD",
                        "USDT",
                    ]:
                        rate = self.kucoin_api.get_ticker_price(
                            f"{key}-{self.autotrade_settings.fiat}"
                        )
                        estimated_total_fiat += float(value["balance"]) * float(rate)
                    else:
                        estimated_total_fiat += float(value["balance"])

                    total_balance[key] = float(value["balance"])

        else:
            binance_balances = self.binance_assets.get_raw_balance()

            for asset in binance_balances:
                if float(asset["free"]) > 0 or float(asset["locked"]) > 0:
                    if asset["asset"] not in [
                        self.autotrade_settings.fiat,
                        "USDC",
                        "TUSD",
                        "USDT",
                    ]:
                        rate = self.binance_assets.get_ticker_price(
                            f"{asset['asset']}{self.autotrade_settings.fiat}"
                        )
                        estimated_total_fiat += (
                            float(asset["free"]) + float(asset["locked"])
                        ) * float(rate)
                    else:
                        estimated_total_fiat += float(asset["free"]) + float(
                            asset["locked"]
                        )

                    total_balance[asset["asset"]] += float(asset["free"]) + float(
                        asset["locked"]
                    )

        return total_balance

    def store_balance(self):
        if self.autotrade_settings.exchange_id == ExchangeId.KUCOIN:
            kucoin_balances = self.kucoin_api.get_account_balance()
            # Store kucoin_balances to database or perform other operations
            return kucoin_balances
        else:
            return self.binance_assets.store_balance()