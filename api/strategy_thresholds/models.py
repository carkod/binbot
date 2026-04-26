from pydantic import BaseModel, Field, model_validator
from typing import Any
from tools.handle_error import IResponseBase


MIN_TRIGGER = 0.008
MAX_TRIGGER = 0.05
MAX_STEP_DELTA = 0.005
MIN_TTL_MINUTES = 30
MAX_TTL_MINUTES = 240


class ThresholdRecommendation(BaseModel):
    strategy: str
    symbol: str
    buy_trigger_pct: float = Field(ge=MIN_TRIGGER, le=MAX_TRIGGER)
    sell_trigger_pct: float = Field(ge=MIN_TRIGGER, le=MAX_TRIGGER)
    ttl_minutes: int = Field(ge=MIN_TTL_MINUTES, le=MAX_TTL_MINUTES)
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(min_length=3)
    profile: str = Field(default="")


class MarketContextPayload(BaseModel):
    market_regime: str
    coin_regime: str
    market_stress_score: float = Field(ge=0)
    atr_pct: float | None = None
    bb_width: float | None = None
    extras: dict[str, Any] = Field(default_factory=dict)


class SuggestThresholdRequest(BaseModel):
    strategy: str
    symbol: str
    market_context: MarketContextPayload
    model: str | None = None
    apply: bool = True


class ApplyThresholdRequest(BaseModel):
    recommendation: ThresholdRecommendation
    source_provider: str = "manual"
    market_context_timestamp: float
    raw_model_response: dict[str, Any] = Field(default_factory=dict)


class ThresholdOverrideModel(BaseModel):
    id: str
    strategy_name: str
    symbol: str
    buy_trigger_pct: float
    sell_trigger_pct: float
    profile: str
    source_provider: str
    market_context_timestamp: float
    expires_at: float
    confidence: float
    reason: str
    raw_model_response: dict[str, Any]
    created_at: float


class ThresholdOverrideResponse(IResponseBase):
    data: ThresholdOverrideModel | None = None


class ThresholdOverrideListResponse(IResponseBase):
    data: list[ThresholdOverrideModel] = Field(default_factory=list)


class SuggestThresholdResponse(IResponseBase):
    data: ThresholdRecommendation | None = None


class GuardrailInput(BaseModel):
    recommendation: ThresholdRecommendation
    current_buy_trigger_pct: float | None = None
    current_sell_trigger_pct: float | None = None
    market_stress_score: float
    market_regime: str
    coin_regime: str

    @model_validator(mode="after")
    def validate_step_delta(self):
        if self.current_buy_trigger_pct is not None:
            if (
                abs(
                    self.recommendation.buy_trigger_pct
                    - self.current_buy_trigger_pct
                )
                > MAX_STEP_DELTA
            ):
                raise ValueError("buy_trigger_pct exceeds max step delta")

        if self.current_sell_trigger_pct is not None:
            if (
                abs(
                    self.recommendation.sell_trigger_pct
                    - self.current_sell_trigger_pct
                )
                > MAX_STEP_DELTA
            ):
                raise ValueError("sell_trigger_pct exceeds max step delta")

        if self.market_stress_score >= 0.35:
            raise ValueError("market stress too high")

        blocked_coin_regimes = {
            "VOLATILE",
            "TREND_UP",
            "TREND_DOWN",
            "BREAKOUT_UP",
            "BREAKDOWN",
        }
        if self.market_regime.upper() not in {"RANGE", "TRANSITIONAL"}:
            raise ValueError("market regime does not support threshold updates")
        if self.coin_regime.upper() in blocked_coin_regimes:
            raise ValueError("coin regime does not support threshold updates")

        return self
