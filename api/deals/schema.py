from deals.models import BinanceOrderModel


class MarginOrderSchema(BinanceOrderModel):
    margin_buy_borrow_amount: int = 0
    margin_buy_borrow_asset: str = "USDC"
    is_isolated: bool = False
