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


class TraillingStopLossError(UpdateDealError):
    pass


class UpdateTakeProfitError(UpdateDealError):
    pass