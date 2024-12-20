from time import time
from typing import Optional
from pydantic import BaseModel
from tools.enum_definitions import BinanceKlineIntervals, Strategy


class AutotradeSettingsMock(BaseModel):
    autotrade: bool = False
    updated_at: float = time() * 1000
    # Assuming 10 USDC is the minimum, adding a bit more to avoid MIN_NOTIONAL fail
    base_order_size: float = 15
    candlestick_interval: BinanceKlineIntervals = BinanceKlineIntervals.fifteen_minutes
    # Deprecated, this is now up to binquant to set
    strategy: Optional[Strategy] = Strategy.long
    test_autotrade: bool = False
    trailling: bool = False
    trailling_deviation: float = 3
    trailling_profit: float = 2.4
    stop_loss: float = 0
    take_profit: float = 2.3
    balance_to_use: str = "USDC"
    balance_size_to_use: float = 100
    max_request: int = 950
    system_logs: list[str] = []
    # Number of times update is requested
    telegram_signals: bool = True
    max_active_autotrade_bots: int = 1
