from pydantic import BaseModel, Field, field_validator
from databases.utils import Amount


class DealModel(BaseModel):
    """
    Data model that is used for operations,
    so it should all be numbers (int or float)
    """

    base_order_size: Amount = Field(default=0, gt=-1)
    current_price: Amount = Field(default=0)
    take_profit_price: Amount = Field(default=0)
    trailling_stop_loss_price: Amount = Field(
        default=0,
        description="take_profit but for trailling, to avoid confusion, trailling_profit_price always be > trailling_stop_loss_price",
    )
    trailling_profit_price: Amount = Field(default=0)
    stop_loss_price: Amount = Field(default=0)

    # fields for margin trading
    total_interests: float = Field(default=0, gt=-1)
    total_commissions: float = Field(default=0, gt=-1)
    margin_loan_id: int = Field(
        default=0,
        ge=0,
        description="Txid from Binance. This is used to check if there is a loan, 0 means no loan",
    )
    margin_repay_id: int = Field(
        default=0, ge=0, description="= 0, it has not been repaid"
    )

    # Refactored deal prices that combine both margin and spot
    opening_price: Amount = Field(
        default=0,
        description="replaces previous buy_price or short_sell_price/margin_short_sell_price",
    )
    opening_qty: Amount = Field(
        default=0,
        description="replaces previous buy_total_qty or short_sell_qty/margin_short_sell_qty",
    )
    opening_timestamp: int = Field(default=0)
    closing_price: Amount = Field(
        default=0,
        description="replaces previous sell_price or short_sell_price/margin_short_sell_price",
    )
    closing_qty: Amount = Field(
        default=0,
        description="replaces previous sell_qty or short_sell_qty/margin_short_sell_qty",
    )
    closing_timestamp: int = Field(
        default=0,
        description="replaces previous buy_timestamp or margin/short_sell timestamps",
    )

    @field_validator("margin_loan_id", mode="before")
    @classmethod
    def validate_margin_loan_id(cls, value):
        if isinstance(value, float):
            return int(value)
        else:
            return value

    @field_validator("margin_loan_id", mode="after")
    @classmethod
    def cast_float(cls, value):
        if isinstance(value, float):
            return int(value)
        else:
            return value
