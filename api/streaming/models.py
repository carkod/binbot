from typing import Optional, Dict
from tools.enum_definitions import TrendEnum
from pydantic import BaseModel, ConfigDict, field_validator


class SignalsConsumer(BaseModel):
    """
    Pydantic model for the signals consumer.
    """

    type: str = "signal"
    spread: float | str | None = 0
    current_price: float | str | None = 0
    msg: str
    symbol: str
    algo: str
    trend: TrendEnum | None = TrendEnum.neutral
    bb_spreads: Optional[Dict[str, float]]
    model_config = ConfigDict(
        extra="allow",
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
            raise ValueError("must be a float or None")
