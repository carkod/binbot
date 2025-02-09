from time import time
from pydantic import BaseModel
from tools.enum_definitions import AutotradeSettingsDocument, BinanceKlineIntervals
from tools.handle_error import StandardResponse


class AutotradeSettingsSchema(BaseModel):
    id: AutotradeSettingsDocument = AutotradeSettingsDocument.settings
    autotrade: bool = False
    updated_at: float = time() * 1000
    # Assuming 10 USDC is the minimum, adding a bit more to avoid MIN_NOTIONAL fail
    base_order_size: float = 15
    candlestick_interval: BinanceKlineIntervals = BinanceKlineIntervals.fifteen_minutes
    test_autotrade: bool = False
    trailling: bool = False
    trailling_deviation: float = 3
    trailling_profit: float = 2.4
    stop_loss: float = 0
    take_profit: float = 2.3
    fiat: str = "USDC"
    balance_size_to_use: float = 100
    max_request: int = 950
    # Number of times update is requested
    telegram_signals: bool = True
    max_active_autotrade_bots: int = 1


class AutotradeSettingsResponse(StandardResponse):
    data: AutotradeSettingsSchema


class TestAutotradeSettingsSchema(BaseModel):
    id: AutotradeSettingsDocument = AutotradeSettingsDocument.settings
    autotrade: bool = False
    updated_at: float = time() * 1000
    # Assuming 10 USDC is the minimum, adding a bit more to avoid MIN_NOTIONAL fail
    base_order_size: float = 15
    candlestick_interval: BinanceKlineIntervals = BinanceKlineIntervals.fifteen_minutes
    trailling: bool = False
    trailling_deviation: float = 3
    trailling_profit: float = 2.4
    stop_loss: float = 0
    take_profit: float = 2.3
    fiat: str = "USDC"
    balance_size_to_use: float = 100
    max_request: int = 950
    # Number of times update is requested
    telegram_signals: bool = True
    max_active_autotrade_bots: int = 1
