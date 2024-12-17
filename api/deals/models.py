from time import time
from pydantic import BaseModel, field_validator
from database.models.order_table import OrderModel


class BinanceOrderModel(OrderModel):
    """
    Data model given by Binance,
    therefore it should be strings
    """

    pass

    @field_validator("timestamp", "order_id", "price", "qty", "order_id")
    @classmethod
    def validate_str_numbers(cls, v):
        if isinstance(v, float):
            return v
        elif isinstance(v, int):
            return v
        elif isinstance(v, str):
            return float(v)
        else:
            raise ValueError(f"{v} must be a number")


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
    # take_profit but for trailling, to avoid confusion, trailling_profit_price always be > trailling_stop_loss_price
    trailling_profit_price: float = 0
    stop_loss_price: float = 0
    trailling_profit: float = 0
    so_prices: float = 0
    post_closure_current_price: float = 0
    original_buy_price: float = 0  # historical buy_price after so trigger
    short_sell_price: float = 0
    short_sell_qty: float = 0
    short_sell_timestamp: float = time() * 1000

    # fields for margin trading
    margin_short_loan_principal: float = 0
    margin_loan_id: float = 0
    hourly_interest_rate: float = 0
    margin_short_sell_price: float = 0
    margin_short_loan_interest: float = 0
    margin_short_buy_back_price: float = 0
    margin_short_sell_qty: float = 0
    margin_short_buy_back_timestamp: int = 0
    margin_short_base_order: float = 0
    margin_short_sell_timestamp: int = 0
    margin_short_loan_timestamp: int = 0

    @field_validator(
        "buy_price",
        "current_price",
        "avg_buy_price",
        "original_buy_price",
        "take_profit_price",
        "sell_price",
        "short_sell_price",
        "trailling_stop_loss_price",
        "trailling_profit_price",
        "stop_loss_price",
        "trailling_profit",
        "margin_short_loan_principal",
        "margin_short_sell_price",
        "margin_short_loan_interest",
        "margin_short_buy_back_price",
        "margin_short_base_order",
        "margin_short_sell_qty",
    )
    @classmethod
    def check_prices(cls, v):
        if float(v) < 0:
            raise ValueError("Price must be a positive number")
        elif isinstance(v, str):
            return float(v)
        return v
