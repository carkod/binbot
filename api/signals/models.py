from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field
from pybinbot import StandardResponse


class SignalCreate(BaseModel):
    """Inbound payload from binquant when a strategy emits a signal."""

    algorithm_name: str = Field(..., max_length=128)
    symbol: str = Field(..., max_length=64)
    generated_at: datetime
    direction: str = Field(..., max_length=16)
    autotrade: bool = False
    current_regime: str | None = Field(default=None, max_length=32)
    context: dict[str, Any] = Field(default_factory=dict)
    bot_params: dict[str, Any] = Field(default_factory=dict)
    indicators: dict[str, Any] = Field(default_factory=dict)


class SignalRecord(SignalCreate):
    id: int


class SignalListRecord(BaseModel):
    id: int
    algorithm_name: str = Field(..., max_length=128)
    symbol: str = Field(..., max_length=64)
    generated_at: datetime
    direction: str = Field(..., max_length=16)
    autotrade: bool = False
    current_regime: str | None = Field(default=None, max_length=32)
    context: dict[str, Any] | None = None
    bot_params: dict[str, Any] | None = None
    indicators: dict[str, Any] | None = None


class SignalResponse(StandardResponse):
    data: SignalRecord


class SignalListResponse(StandardResponse):
    data: list[SignalListRecord]
