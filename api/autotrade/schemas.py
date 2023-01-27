from time import time
from typing import Literal

from pydantic import BaseModel
from tools.handle_error import StandardResponse

class AutotradeSettingsSchema(BaseModel):
    _id: str
    updated_at: float = time() * 1000
    candlestick_interval: str = "15m"
    autotrade: Literal[0, 1] = 0
    strategy: str = "long"
    test_autotrade: Literal[0, 1] = 0
    trailling: Literal["true", "false"] = "true"
    trailling_deviation: float = 3
    trailling_profit: float = 2.4
    stop_loss: float = 0
    take_profit: float = 2.3
    balance_to_use: str = "USDT"
    balance_size_to_use: str = "100"
    max_request: int = 950
    system_logs: list[str] = []
    update_required: bool = False
    telegram_signals: int = 1
    max_active_autotrade_bots: int = 1
    base_order_size: str = "15"  # Assuming 10 USDT is the minimum, adding a bit more to avoid MIN_NOTIONAL fail


class AutotradeSettingsResponse(StandardResponse):
    data: AutotradeSettingsSchema
