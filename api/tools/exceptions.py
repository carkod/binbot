class IsolateBalanceError(Exception):
    def __init__(self, message) -> None:
        self.message = message


class BinanceErrors(Exception):
    def __init__(self, msg, code):
        self.code = code
        self.message = msg
        super().__init__(self.code, self.message)
        return None

    def __str__(self) -> str:
        return f"Binance Error: {self.code} {self.message}"


class InvalidSymbol(BinanceErrors):
    pass


class NotEnoughFunds(BinanceErrors):
    pass


class BinbotErrors(Exception):
    def __init__(self, msg, code=None):
        self.message = msg
        super().__init__(self.message)
        return None

    def __str__(self) -> str:
        return f"Binbot error: {self.message}"


class QuantityTooLow(BinbotErrors):
    """
    Raised when LOT_SIZE filter error triggers
    This error should happen in the least cases,
    unless purposedly triggered to check quantity
    e.g. BTC = 0.0001 amounts are usually so small that it's hard to see if it's nothing or a considerable amount compared to others
    """

    pass


class MarginLoanNotFound(BinbotErrors):
    pass


class OpenDealError(Exception):
    pass


class UpdateDealError(Exception):
    pass


class BaseDealError(OpenDealError):
    pass


class TraillingProfitError(OpenDealError):
    pass


class TakeProfitError(OpenDealError):
    pass


class ShortStrategyError(OpenDealError):
    pass


class TerminateStreaming(Exception):
    """
    This is required sometimes
    - Bot autoswtiched strategy, so streaming updates will keep trying to update something already sold
    causing exceptions to be raised constantly.


    On the other hand, we want to minimize number of times this exception is raised to avoid
    overloading the server with reloads
    """

    pass
