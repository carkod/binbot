from databases.crud.autotrade_crud import AutotradeCrud
from orders.binance_controller import BinanceOrderController
from orders.kucoin_controller import KucoinOrderController
from tools.enum_definitions import ExchangeId
from orders.abstract import OrderControllerAbstract


class OrderController:
    """
    Multi-exchange implementation of OrderController.

    Delegates all trading methods to a concrete exchange-specific controller
    chosen based on autotrade settings.
    """

    def __init__(self) -> None:
        autotrade_settings = AutotradeCrud().get_settings()
        exchange_id: ExchangeId = autotrade_settings.exchange_id
        self._delegate: OrderControllerAbstract
        if exchange_id == ExchangeId.KUCOIN:
            self._delegate = KucoinOrderController()
        else:
            self._delegate = BinanceOrderController()

    def __getattr__(self, name):
        """
        Delegate missing attributes to the underlying exchange-specific controller.

        Pretty much equivalent to inheritance OrderController(KubcoinOrderController) or
        OrderController(BinanceOrderController) based on exchange_id.
        """
        return getattr(self._delegate, name)
