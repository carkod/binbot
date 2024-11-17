from deals.models import BinanceOrderModel


class MarginOrderSchema(BinanceOrderModel):
    is_isolated: bool = False
