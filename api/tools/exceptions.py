class OpenDealError(Exception):
    pass

class BaseDealError(OpenDealError):
    pass

class TraillingProfitError(OpenDealError):
    pass

class TakeProfitError(OpenDealError):
    pass