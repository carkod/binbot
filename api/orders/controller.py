from orders.abstract import OrderControllerAbstract
from account.factory import AccountBase
from orders.factory import OrderControllerBase

class OrderController(OrderControllerBase, AccountBase):
    """
    Binance-specific implementation of OrderController.

    Always GTC and limit orders
    limit/market orders will be decided by matching_engine
    PRICE_FILTER decimals

    Inherits common methods from OrderControllerAbstract
    and Binance-specific account methods from Account
    """

    def __init__(self) -> None:
        OrderControllerBase.__init__(self)
        AccountBase.__init__(self)
