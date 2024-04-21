from typing import Any

from pydantic import BaseModel, field_validator

from tools.enum_definitions import DealType


class OrderSchema(BaseModel):
    """
    No need for validation,
    order coming from Binance

    """

    order_type: str | None = None
    time_in_force: str | None = None
    timestamp: float = 0
    pair: str | None = None
    qty: str | float | int | None = None
    order_side: str | None = None
    order_id: int | None = None
    fills: Any = None
    price: float | None = None
    status: str | None = None
    deal_type: DealType

    @field_validator("order_id")
    @classmethod
    def check_order_id(cls, v):
        if isinstance(v, str):
            return int(v)
        elif isinstance(v, int):
            return v
        else:
            raise ValueError("must be an integer")


class DealSchema(BaseModel):
    buy_price: float = 0  # base currency quantity e.g. 3000 USDT in BTCUSDT
    base_order_price: float = (
        0  # To replace buy_price - better naming for both long and short positions
    )
    buy_timestamp: float = 0
    buy_total_qty: float = 0
    current_price: float = 0
    sd: float = 0
    avg_buy_price: float = 0  # depricated - replaced with buy_price
    original_buy_price: float = (
        0  # historical buy_price after so executed. avg_buy_price = buy_price
    )
    take_profit_price: float = (
        0  # quote currency quantity e.g. 0.00003 BTC in BTCUSDT (sell price)
    )
    so_prices: float = 0
    sell_timestamp: float = 0
    sell_price: float = 0
    sell_qty: float = 0
    trailling_stop_loss_price: float = 0
    trailling_profit_price: float = 0
    short_sell_price: float = 0
    short_sell_qty: float = 0
    short_sell_timestamp: float = 0
    stop_loss_price: float = 0
    margin_short_base_order: float = 0  # borrowed amount
    margin_loan_id: str = ""
    margin_short_loan_interest: float = 0
    margin_short_loan_principal: float = 0
    margin_short_loan_timestamp: float = 0
    margin_short_repay_price: float = 0
    margin_short_sell_price: float = 0
    margin_short_sell_timestamp: float = 0
    margin_short_buy_back_price: float = 0
    margin_short_buy_back_timestamp: float = 0
    hourly_interest_rate: float = 0

    @field_validator(
        "buy_price",
        "current_price",
        "avg_buy_price",
        "original_buy_price",
        "take_profit_price",
        "sell_price",
        "short_sell_price",
    )
    @classmethod
    def check_prices(cls, v):
        if float(v) < 0:
            raise ValueError("Price must be a positive number")
        if isinstance(v, str):
            return float(v)
        return v


class MarginOrderSchema(OrderSchema):
    margin_buy_borrow_amount: int = 0
    margin_buy_borrow_asset: str = "USDT"
    is_isolated: bool = False
