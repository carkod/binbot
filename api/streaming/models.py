from typing import Optional
from tools.enum_definitions import Strategy
from pydantic import BaseModel, field_validator, Field, ConfigDict
from datetime import datetime


class SingleCandle(BaseModel):
    """
    Pydantic model for a single candle.
    """

    symbol: str
    open_time: int = Field()
    close_time: int
    open_price: float
    close_price: float
    high_price: float
    low_price: float
    volume: float

    @field_validator("open_time", "close_time")
    @classmethod
    def validate_time(cls, v):
        if v is None:
            return 0
        elif isinstance(v, str):
            return int(v)
        elif isinstance(v, int):
            return v
        else:
            raise ValueError("must be a int or 0")

    @field_validator("open_price", "close_price", "high_price", "low_price", "volume")
    @classmethod
    def validate_price(cls, v):
        if v is None:
            return 0
        elif isinstance(v, str):
            return float(v)
        elif isinstance(v, float):
            return v
        else:
            raise ValueError("must be a float or 0")


class BollinguerSpread(BaseModel):
    """
    Pydantic model for the Bollinguer spread.
    (optional)
    """

    bb_high: float
    bb_mid: float
    bb_low: float


class SignalsConsumer(BaseModel):
    """
    Pydantic model for the signals consumer.
    """

    type: str = Field(default="signal")
    date: str = Field(default=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    spread: Optional[float] = Field(default=0)
    current_price: Optional[float] = Field(default=0)
    msg: str
    symbol: str
    algo: str
    bot_strategy: Strategy = Field(default=Strategy.long)
    bb_spreads: Optional[BollinguerSpread]
    autotrade: bool = Field(default=True, description="If it is in testing mode, False")

    model_config = ConfigDict(
        extra="allow",
        use_enum_values=True,
    )

    @field_validator("spread", "current_price")
    @classmethod
    def name_must_contain_space(cls, v):
        if v is None:
            return 0
        elif isinstance(v, str):
            return float(v)
        elif isinstance(v, float):
            return v
        else:
            raise ValueError("must be a float or 0")
