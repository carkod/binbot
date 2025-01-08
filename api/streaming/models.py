from typing import Optional, Dict
from tools.enum_definitions import TrendEnum
from pydantic import BaseModel, field_validator


class SignalsConsumer(BaseModel):
    """
    Pydantic model for the signals consumer.
    """

    type: str = "signal"
    spread: float | str | None = 0
    current_price: float = 0
    msg: str
    symbol: str
    algo: str
    trend: Optional[TrendEnum] = TrendEnum.neutral
    bb_spreads: Optional[Dict[str, float]]

    model_config = {
        "arbitrary_types_allowed": True,
    }

    @field_validator("current_price", mode="before")
    @classmethod
    def convert_to_float(cls, v):
        if v is None:
            return 0
        elif isinstance(v, str):
            return float(v)
        else:
            return v

    @field_validator("spread")
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
