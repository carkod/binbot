from time import time
from pydantic import BaseModel, Field
from tools.enum_definitions import (
    AutotradeSettingsDocument,
    BinanceKlineIntervals,
    CloseConditions,
    ExchangeId,
)
from tools.handle_error import StandardResponse


class AutotradeSettingsSchema(BaseModel):
    id: AutotradeSettingsDocument = AutotradeSettingsDocument.settings
    candlestick_interval: BinanceKlineIntervals = Field(
        default=BinanceKlineIntervals.fifteen_minutes,
    )
    close_condition: CloseConditions = Field(
        default=CloseConditions.dynamic_trailling,
    )
    autotrade: bool = Field(default=False)
    updated_at: float = Field(default=time() * 1000)
    # Assuming 10 USDC is the minimum, adding a bit more to avoid MIN_NOTIONAL fail
    base_order_size: float = Field(default=15)
    trailling: bool = Field(default=False)
    trailling_deviation: float = Field(default=3)
    trailling_profit: float = Field(default=2.4)
    stop_loss: float = Field(default=0)
    take_profit: float = Field(default=2.3)
    fiat: str = Field(default="USDC")
    max_request: int = Field(default=950)
    telegram_signals: bool = Field(default=True)
    max_active_autotrade_bots: int = Field(default=1)
    autoswitch: bool = Field(default=True)
    exchange_id: ExchangeId = Field(
        default=ExchangeId.BINANCE,
        description="Exchange where autotrade bots will operate",
    )


class AutotradeSettingsResponse(StandardResponse):
    data: AutotradeSettingsSchema
    model_config = {
        "ser_json_exclude": {"id"},
        "ser_dict_exclude": {"id"},
    }


class TestAutotradeSettingsSchema(BaseModel):
    id: AutotradeSettingsDocument = AutotradeSettingsDocument.test_autotrade_settings
    candlestick_interval: BinanceKlineIntervals = Field(
        default=BinanceKlineIntervals.fifteen_minutes,
    )
    close_condition: CloseConditions = Field(
        default=CloseConditions.dynamic_trailling,
    )
    autotrade: bool = Field(default=False)
    updated_at: float = Field(default=time() * 1000)
    # Assuming 10 USDC is the minimum, adding a bit more to avoid MIN_NOTIONAL fail
    base_order_size: float = Field(default=15)
    trailling: bool = Field(default=False)
    trailling_deviation: float = Field(default=3)
    trailling_profit: float = Field(default=2.4)
    stop_loss: float = Field(default=0)
    take_profit: float = Field(default=2.3)
    fiat: str = Field(default="USDC")
    max_request: int = Field(default=950)
    telegram_signals: bool = Field(default=True)
    max_active_autotrade_bots: int = Field(default=1)
    autoswitch: bool = Field(default=True)
    exchange_id: ExchangeId = Field(
        default=ExchangeId.BINANCE,
        description="Exchange where autotrade bots will operate",
    )
