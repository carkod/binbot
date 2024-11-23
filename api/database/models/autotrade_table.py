from time import time
from typing import Optional
from sqlalchemy import Column, Enum
from sqlmodel import Field, SQLModel
from tools.enum_definitions import (
    AutotradeSettingsDocument,
    BinanceKlineIntervals,
    CloseConditions,
)


class AutotradeTable(SQLModel, table=True):
    """
    Generic settings for bots that set parameters for autotrading

    Bots will be triggered by signals
    and they will trade using these settings when applicable
    """

    __tablename__ = "autotrade"

    id: Optional[str] = Field(
        default=str(AutotradeSettingsDocument.settings),
        primary_key=True,
        nullable=False,
        unique=True,
    )
    autotrade: bool = Field(default=False)
    updated_at: float = Field(default=time() * 1000)
    # Assuming 10 USDC is the minimum, adding a bit more to avoid MIN_NOTIONAL fail
    base_order_size: float = Field(default=15)
    candlestick_interval: BinanceKlineIntervals = Field(
        default=BinanceKlineIntervals.fifteen_minutes,
        sa_column=Column(Enum(BinanceKlineIntervals)),
    )
    test_autotrade: bool = Field(default=False)
    trailling: bool = Field(default=False)
    trailling_deviation: float = Field(default=3)
    trailling_profit: float = Field(default=2.4)
    stop_loss: float = Field(default=0)
    take_profit: float = Field(default=2.3)
    balance_to_use: str = Field(default="USDC")
    max_request: int = Field(default=950)
    telegram_signals: bool = Field(default=True)
    max_active_autotrade_bots: int = Field(default=1)
    close_condition: CloseConditions = Field(
        default=CloseConditions.dynamic_trailling,
        sa_column=Column(Enum(CloseConditions)),
    )

    class Config:
        arbitrary_types_allowed = True


class TestAutotradeTable(SQLModel, table=True):
    """
    Test autotrade
    """

    __tablename__ = "test_autotrade"

    id: Optional[str] = Field(
        default="test_autotrade_settings", primary_key=True, nullable=False, unique=True
    )
    updated_at: float = Field(default=time() * 1000)
    # Assuming 10 USDC is the minimum, adding a bit more to avoid MIN_NOTIONAL fail
    base_order_size: float = Field(default=15)
    candlestick_interval: BinanceKlineIntervals = Field(
        default=BinanceKlineIntervals.fifteen_minutes
    )
    trailling: bool = Field(default=False)
    trailling_deviation: float = Field(default=3)
    trailling_profit: float = Field(default=2.4)
    stop_loss: float = Field(default=0)
    take_profit: float = Field(default=2.3)
    balance_to_use: str = Field(default="USDC")
    max_request: int = Field(default=950)
    telegram_signals: bool = Field(default=True)
    max_active_autotrade_bots: int = Field(default=1)

    class Config:
        arbitrary_types_allowed = True
