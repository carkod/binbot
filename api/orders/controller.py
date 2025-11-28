from databases.crud.autotrade_crud import AutotradeCrud
from orders.kucoin_controller import KucoinOrderController
from tools.enum_definitions import ExchangeId
from orders.abstract import OrderControllerAbstract
from exchange_apis.binance.orders import BinanceOrderController


class OrderFactory:
    """
    Multi-exchange implementation of OrderController.

    Delegates all trading methods to a concrete exchange-specific controller
    chosen based on autotrade settings.
    """

    def __init__(self) -> None:
        autotrade_settings = AutotradeCrud().get_settings()
        self.exchange_id: ExchangeId = autotrade_settings.exchange_id

    def get_controller(self) -> OrderControllerAbstract:
        if self.exchange_id == ExchangeId.KUCOIN:
            controller = KucoinOrderController()
            return controller, controller.api
        else:
            controller = BinanceOrderController()
            return controller, controller.api
