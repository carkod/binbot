from pydantic import BaseModel, validator
from typing import Any
class OrderSchema(BaseModel):
    order_type: str | None = None
    time_in_force: str | None = None
    timestamp: float = 0
    pair: str | None = None
    qty: str | None = None
    order_side: str | None = None
    order_id: str | None = None
    fills: Any = None
    price: float | None = None
    status: str | None = None
    deal_type: str | None = None # [base_order, take_profit, so_{x}, short_sell, short_buy, margin_short]

class DealSchema(BaseModel):
    buy_price: float = 0 # base currency quantity e.g. 3000 USDT in BTCUSDT
    buy_timestamp: float = 0
    buy_total_qty: float = 0
    current_price: float = 0
    sd: float = 0
    avg_buy_price: float = 0 # depricated - replaced with buy_price
    original_buy_price: float = 0 # historical buy_price after so executed. avg_buy_price = buy_price
    take_profit_price: float = 0 # quote currency quantity e.g. 0.00003 BTC in BTCUSDT (sell price)
    so_prices: float = 0
    sell_timestamp: float = 0
    sell_price: float = 0
    sell_qty: float = 0
    post_closure_current_price: float = 0
    trailling_stop_loss_price: float = 0
    short_sell_price: float = 0
    short_sell_qty: float = 0
    short_sell_timestamp: float = 0
    stop_loss_price: float = 0
    margin_short_base_order: float = 0 # borrowed amount
    margin_short_take_profit_price: float = 0
    margin_short_stop_loss_price: float = 0
    margin_load_id: str = ""
    margin_short_loan_interest: float = 0
    margin_short_loan_principal: float = 0
    margin_short_loan_timestamp: float = 0
    margin_short_repay_price: float = 0
    margin_short_sell_price: float = 0
    margin_short_sell_timestamp: float = 0
    margin_short_buy_back_price: float = 0



    @validator("buy_price", "current_price", "avg_buy_price", "original_buy_price", "take_profit_price", "sell_price", "short_sell_price")
    def check_prices(cls, v):
        if float(v) < 0:
            raise ValueError("Price must be a positive number")
        return v


class MarginOrderSchema(OrderSchema):
    marginBuyBorrowAmount: int = 0
    marginBuyBorrowAsset: str = "USDT"
    isIsolated: bool = False
