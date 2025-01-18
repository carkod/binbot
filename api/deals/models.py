from pydantic import BaseModel, Field, field_validator
from typing import Optional


class DealModel(BaseModel):
    """
    Data model that is used for operations,
    so it should all be numbers (int or float)
    """

    order_id: int = Field(default=0)
    buy_price: float = Field(default=0)
    buy_total_qty: float = Field(default=0)
    buy_timestamp: float = Field(default=0)
    current_price: float = Field(default=0)
    sd: float = Field(default=0)
    avg_buy_price: float = Field(default=0)
    take_profit_price: float = Field(default=0)
    sell_timestamp: float = Field(default=0)
    sell_price: float = Field(default=0)
    sell_qty: float = Field(default=0)
    trailling_stop_loss_price: float = Field(
        default=0,
        description="take_profit but for trailling, to avoid confusion, trailling_profit_price always be > trailling_stop_loss_price",
    )
    trailling_profit_price: float = Field(default=0)
    stop_loss_price: float = Field(default=0)
    trailling_profit: float = Field(default=0)
    original_buy_price: float = Field(
        default=0, description="historical buy_price after so trigger"
    )
    short_sell_price: float = Field(default=0)

    # fields for margin trading
    margin_short_loan_principal: float = Field(default=0)
    margin_loan_id: float = Field(default=0)
    hourly_interest_rate: float = Field(default=0)
    margin_short_sell_price: float = Field(default=0)
    margin_short_loan_interest: float = Field(default=0)
    margin_short_buy_back_price: float = Field(default=0)
    margin_short_sell_qty: float = Field(default=0)
    margin_short_buy_back_timestamp: float = 0
    margin_short_base_order: float = Field(default=0)
    margin_short_sell_timestamp: float = Field(default=0)
    margin_short_loan_timestamp: float = Field(default=0)

    # Refactored deal prices that combine both margin and spot
    opening_price: Optional[float] = Field(
        default=0,
        description="replaces previous buy_price or short_sell_price/margin_short_sell_price",
    )
    opening_qty: Optional[float] = Field(
        default=0,
        description="replaces previous buy_total_qty or short_sell_qty/margin_short_sell_qty",
    )
    opening_timestamp: Optional[float] = Field(default=0)
    closing_price: Optional[float] = Field(
        default=0,
        description="replaces previous sell_price or short_sell_price/margin_short_sell_price",
    )
    closing_qty: Optional[float] = Field(
        default=0,
        description="replaces previous sell_qty or short_sell_qty/margin_short_sell_qty",
    )
    closing_timestamp: Optional[float] = Field(
        default=0,
        description="replaces previous buy_timestamp or margin/short_sell timestamps",
    )

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
