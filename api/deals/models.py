from time import time
from pydantic import BaseModel
from typing import List


class BinanceOrderModel(BaseModel):
    order_type: str
    time_in_force: str
    timestamp: str
    order_id: str
    order_side: str
    pair: str
    fills: list
    qty: str
    status: str
    price: str
    deal_type: str


class DealModel(BaseModel):
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
    stop_loss_price: float = 0
    trailling_profit: float = 0
    so_prices: float = 0
    post_closure_current_price: float = 0
    original_buy_price: float = 0  # historical buy_price after so triggere
    short_sell_price: float = 0
    short_sell_qty: float = 0
    short_sell_timestamp: float = time() * 1000



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
