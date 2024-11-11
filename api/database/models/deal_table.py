from time import time
from sqlmodel import SQLModel, Field


class DealTable(SQLModel, table=True):
    """
    Data model that is used for operations,
    so it should all be numbers (int or float)
    """
    id: int | None = Field(default=None, primary_key=True)
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
    margin_short_loan_timestamp: int | str = 0
