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


class TraillingStopLossError(UpdateDealError):
    pass


class UpdateTakeProfitError(UpdateDealError):
    pass


"""
This is required sometimes
- Bot autoswtiched strategy, so streaming updates will keep trying to update something already sold
causing exceptions to be raised constantly.


On the other hand, we want to minimize number of times this exception is raised to avoid
overloading the server with reloads
"""
class TerminateStreaming(Exception):
    pass
