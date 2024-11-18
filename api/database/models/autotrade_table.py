from time import time
from typing import Optional
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel
from tools.enum_definitions import BinanceKlineIntervals


class AutotradeTable(SQLModel, table=True):
    __tablename__ = "autotrade"

    id: Optional[UUID] = Field(
        default_factory=uuid4, primary_key=True, index=True, nullable=False, unique=True
    )
    autotrade: bool = Field(default=False)
    updated_at: float = Field(default=time() * 1000)
    # Assuming 10 USDC is the minimum, adding a bit more to avoid MIN_NOTIONAL fail
    base_order_size: float = Field(default=15)
    candlestick_interval: BinanceKlineIntervals = Field(
        default=BinanceKlineIntervals.fifteen_minutes
    )
    test_autotrade: bool = Field(default=False)
    trailling: bool = Field(default=False)
    trailling_deviation: float = Field(default=3)
    trailling_profit: float = Field(default=2.4)
    stop_loss: float = Field(default=0)
    take_profit: float = Field(default=2.3)
    balance_to_use: str = Field(default="USDC")
    balance_size_to_use: float = Field(default=100)
    max_request: int = Field(default=950)
    system_logs: list[str] = Field(default=[])
    telegram_signals: bool = Field(default=True)
    max_active_autotrade_bots: int = Field(default=1)

    class Config:
        arbitrary_types_allowed = True
