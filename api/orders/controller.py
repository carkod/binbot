from databases.crud.autotrade_crud import AutotradeCrud
from orders.binance_controller import BinanceOrderController
from orders.kucoin_controller import KucoinOrderController
from tools.enum_definitions import ExchangeId
from orders.abstract import OrderControllerAbstract
from account.abstract import AccountAbstract
from account.binance_account import BinanceAccount
from account.kucoin_account import KucoinAccount
from exchange_apis.api_protocol import ExchangeApiProtocol


class OrderFactory:
    """
    Multi-exchange implementation of OrderController.

    Delegates all trading methods to a concrete exchange-specific controller
    chosen based on autotrade settings.
    """

    def __init__(self) -> None:
        autotrade_settings = AutotradeCrud().get_settings()
        self.exchange_id: ExchangeId = autotrade_settings.exchange_id

    def get_account_controller(self) -> tuple[AccountAbstract, ExchangeApiProtocol]:
        if self.exchange_id == ExchangeId.KUCOIN:
            account = KucoinAccount()
            return account, account.api
        else:
            account = BinanceAccount()
            return account, account.api

    def get_order_controller(self) -> OrderControllerAbstract:
        if self.exchange_id == ExchangeId.KUCOIN:
            return KucoinOrderController()
        else:
            return BinanceOrderController()
