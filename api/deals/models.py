from time import time
from typing import List
from pydantic import BaseModel, field_validator


class BinanceOrderModel(BaseModel):
    """
    Data model given by Binance,
    therefore it should be strings
    """
    order_type: str
    time_in_force: str
    timestamp: str | int
    order_id: str | int
    order_side: str
    pair: str
    fills: list
    qty: str | float
    status: str
    price: str | float
    deal_type: str

    @field_validator("timestamp", "order_id", "price", "qty", "order_id")
    @classmethod
    def validate_str_numbers(cls, v):
        if isinstance(v, float):
            return str(v)
        elif isinstance(v, int):
            return str(v)
        elif isinstance(v, str):
            return v
        else:
            raise ValueError(f"{v} must be a number")


class BinanceRepayRecord(BaseModel):
    isolatedSymbol: str
    amount: str
    asset: str
    interest: str
    principal: str
    status: str
    timestamp: float
    txId: int


class BinanceRepayRecords(BaseModel):
    rows: list[BinanceRepayRecord]
    total: int  # no. repays


class DealModel(BaseModel):
    """
    Data model that is used for operations,
    so it should all be numbers (int or float)
    """
    buy_price: float = 0
    buy_total_qty: float = 0
    buy_timestamp: float = time() * 1000
    current_price: float = 0
    sd: float = 0
    avg_buy_price: float = 0
    take_profit_price: float = 0
    sell_timestamp: float = 0
    sell_price: float = 0
    sell_qty: float = 0
    trailling_stop_loss_price: float = 0
    trailling_profit_price: float = 0 # take_profit but for trailling, to avoid confusion, trailling_profit_price always be > trailling_stop_loss_price
    stop_loss_price: float = 0
    trailling_profit: float = 0
    so_prices: float = 0
    post_closure_current_price: float = 0
    original_buy_price: float = 0  # historical buy_price after so triggere
    short_sell_price: float = 0
    short_sell_qty: float = 0
    short_sell_timestamp: float = time() * 1000

    # fields for margin trading
    margin_short_loan_principal: float | str = 0
    margin_loan_id: float | str = 0
    hourly_interest_rate: float | str = 0
    margin_short_sell_price: float | str = 0
    margin_short_loan_interest: float | str = 0
    margin_short_buy_back_price: float | str = 0
    margin_short_sell_qty: float | str = 0
    margin_short_buy_back_timestamp: int | str = 0
    margin_short_base_order: float | str = 0
    margin_short_sell_timestamp: int | str = 0

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

class SafetyOrderModel(BaseModel):
    buy_price: float
    so_size: float
    name: str = "so_1"  # should be so_<index>
    order_id: str = ""
    buy_timestamp: float = 0
    errors: List[str] = []
    total_comission: float = 0
    so_volume_scale: float = 0
    created_at: float = time() * 1000
    updated_at: float = time() * 1000
    status: float = 0
