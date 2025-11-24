from tools.enum_definitions import ExchangeId
from databases.crud.autotrade_crud import AutotradeCrud
from account.binance_account import BinanceAccount
from account.kucoin_account import KucoinAccount
from account.account_abstract import AccountAbstract


def account_factory() -> AccountAbstract:
    """
    Factory function to create the appropriate OrderController
    based on the configured exchange.

    Returns:
        AccountAbstract: Either BinanceAccount or KucoinAccount
    """
    autotrade_settings = AutotradeCrud().get_settings()
    exchange_id = autotrade_settings.exchange_id

    if exchange_id == ExchangeId.KUCOIN:
        return KucoinAccount()
    else:
        return BinanceAccount()
