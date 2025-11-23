from time import time
from typing import Optional
from sqlalchemy import Column, Enum
from sqlmodel import Field, SQLModel
from tools.enum_definitions import (
    AutotradeSettingsDocument,
    BinanceKlineIntervals,
    CloseConditions,
    ExchangeId,
)


class SettingsDocument(SQLModel):
    """
    Base model for autotrade settings
    """

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
    autoswitch: bool = Field(
        default=True,
        description="Automatically switch between long bot or short bot based on stop loss a.k.a. margin_short_reversal in bots",
    )
    exchange_id: ExchangeId = Field(
        default=ExchangeId.BINANCE,
        description="Exchange where autotrade bots will operate",
    )


class AutotradeTable(SettingsDocument, table=True):
    """
    Generic settings for bots that set parameters for autotrading

    Bots will be triggered by signals
    and they will trade using these settings when applicable
    """

    __tablename__ = "autotrade"

    id: Optional[str] = Field(
        default=AutotradeSettingsDocument.settings,
        primary_key=True,
        nullable=False,
        unique=True,
    )
    candlestick_interval: BinanceKlineIntervals = Field(
        default=BinanceKlineIntervals.fifteen_minutes,
        sa_column=Column(Enum(BinanceKlineIntervals)),
    )
    close_condition: CloseConditions = Field(
        default=CloseConditions.dynamic_trailling,
        sa_column=Column(Enum(CloseConditions)),
    )

    model_config = {
        "from_attributes": True,
        "use_enum_values": True,
        "json_schema_extra": {
            "description": "Autotrade global settings used by Binquant",
            "examples": [
                {
                    "autotrade": True,
                    "base_order_size": 15,
                    "candlestick_interval": "15m",
                    "trailling": False,
                    "trailling_deviation": 3,
                    "trailling_profit": 2.4,
                    "stop_loss": 0,
                    "take_profit": 2.3,
                    "fiat": "USDC",
                    "max_request": 950,
                    "telegram_signals": True,
                    "max_active_autotrade_bots": 1,
                    "close_condition": "dynamic_trailling",
                    "exchange_id": "binance",
                }
            ],
        },
    }


class TestAutotradeTable(SettingsDocument, table=True):
    """
    Test autotrade
    """

    __tablename__ = "test_autotrade"

    id: Optional[str] = Field(
        default=AutotradeSettingsDocument.test_autotrade_settings,
        primary_key=True,
        nullable=False,
        unique=True,
    )
    # For some reason can't reassign enum columns to more than 1 table
    candlestick_interval: BinanceKlineIntervals = Field(
        default=BinanceKlineIntervals.fifteen_minutes,
        sa_column=Column(Enum(BinanceKlineIntervals)),
    )
    close_condition: CloseConditions = Field(
        default=CloseConditions.dynamic_trailling,
        sa_column=Column(Enum(CloseConditions)),
    )

    model_config = {
        "from_attributes": True,
        "use_enum_values": True,
        "json_schema_extra": {
            "description": "Autotrade global settings used by Binquant",
            "examples": [
                {
                    "autotrade": True,
                    "base_order_size": 15,
                    "candlestick_interval": "15m",
                    "trailling": False,
                    "trailling_deviation": 3,
                    "trailling_profit": 2.4,
                    "stop_loss": 0,
                    "take_profit": 2.3,
                    "fiat": "USDC",
                    "max_request": 950,
                    "telegram_signals": True,
                    "max_active_autotrade_bots": 1,
                    "close_condition": "dynamic_trailling",
                    "exchange_id": "binance",
                }
            ],
        },
    }
