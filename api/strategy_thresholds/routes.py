from fastapi import APIRouter, Depends
from sqlmodel import Session
from pybinbot import timestamp
from user.services.auth import get_current_user

from databases.utils import get_session
from databases.crud.strategy_threshold_override_crud import (
    StrategyThresholdOverrideCrud,
)
from databases.tables.strategy_threshold_override_table import (
    StrategyThresholdOverrideTable,
)
from strategy_thresholds.models import (
    ApplyThresholdRequest,
    GuardrailInput,
    SuggestThresholdRequest,
    SuggestThresholdResponse,
    ThresholdOverrideListResponse,
    ThresholdOverrideModel,
    ThresholdOverrideResponse,
    ThresholdRecommendation,
)
from openai_api.threshold_advisor import OpenAiThresholdAdvisor, OpenAiThresholdError


strategy_threshold_blueprint = APIRouter(prefix="/strategy-threshold-overrides")


def _to_model(row: StrategyThresholdOverrideTable) -> ThresholdOverrideModel:
    return ThresholdOverrideModel(
        id=str(row.id),
        strategy_name=row.strategy_name,
        symbol=row.symbol,
        buy_trigger_pct=row.buy_trigger_pct,
        sell_trigger_pct=row.sell_trigger_pct,
        profile=row.profile,
        source_provider=row.source_provider,
        market_context_timestamp=row.market_context_timestamp,
        expires_at=row.expires_at,
        confidence=row.confidence,
        reason=row.reason,
        raw_model_response=row.raw_model_response,
        created_at=row.created_at,
    )


@strategy_threshold_blueprint.get("", response_model=ThresholdOverrideListResponse, tags=["strategy threshold overrides"])
def list_overrides(
    strategy_name: str,
    symbol: str,
    limit: int = 20,
    offset: int = 0,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_user),
):
    rows = StrategyThresholdOverrideCrud(session).list_for_symbol(
        strategy_name=strategy_name,
        symbol=symbol,
        limit=limit,
        offset=offset,
    )
    return ThresholdOverrideListResponse(
        message="Successfully found threshold overrides.",
        data=[_to_model(r) for r in rows],
    )


@strategy_threshold_blueprint.get("/active", response_model=ThresholdOverrideResponse, tags=["strategy threshold overrides"])
def get_active_override(
    strategy_name: str,
    symbol: str,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_user),
):
    row = StrategyThresholdOverrideCrud(session).get_active(
        strategy_name=strategy_name,
        symbol=symbol,
        now_ts=timestamp(),
    )
    return ThresholdOverrideResponse(
        message="Successfully found active override.",
        data=_to_model(row) if row else None,
    )


@strategy_threshold_blueprint.post("/apply", response_model=ThresholdOverrideResponse, tags=["strategy threshold overrides"])
def apply_override(
    payload: ApplyThresholdRequest,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_user),
):
    expires_at = payload.market_context_timestamp + payload.recommendation.ttl_minutes * 60
    row = StrategyThresholdOverrideTable(
        strategy_name=payload.recommendation.strategy,
        symbol=payload.recommendation.symbol,
        buy_trigger_pct=payload.recommendation.buy_trigger_pct,
        sell_trigger_pct=payload.recommendation.sell_trigger_pct,
        profile=payload.recommendation.profile,
        source_provider=payload.source_provider,
        market_context_timestamp=payload.market_context_timestamp,
        expires_at=expires_at,
        confidence=payload.recommendation.confidence,
        reason=payload.recommendation.reason,
        raw_model_response=payload.raw_model_response,
    )
    created = StrategyThresholdOverrideCrud(session).create(row)
    return ThresholdOverrideResponse(
        message="Successfully applied threshold override.",
        data=_to_model(created),
    )


@strategy_threshold_blueprint.post("/suggest", response_model=SuggestThresholdResponse, tags=["strategy threshold overrides"])
def suggest_override(
    payload: SuggestThresholdRequest,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_user),
):
    client = OpenAiThresholdAdvisor(model=payload.model)

    try:
        recommendation, raw_model_response = client.suggest(
            strategy=payload.strategy,
            symbol=payload.symbol,
            context=payload.market_context,
        )
        recommendation = ThresholdRecommendation.model_validate(recommendation)

        current = StrategyThresholdOverrideCrud(session).get_active(
            strategy_name=payload.strategy,
            symbol=payload.symbol,
            now_ts=timestamp(),
        )

        GuardrailInput(
            recommendation=recommendation,
            current_buy_trigger_pct=current.buy_trigger_pct if current else None,
            current_sell_trigger_pct=current.sell_trigger_pct if current else None,
            market_stress_score=payload.market_context.market_stress_score,
            market_regime=payload.market_context.market_regime,
            coin_regime=payload.market_context.coin_regime,
        )

        if payload.apply:
            row = StrategyThresholdOverrideTable(
                strategy_name=recommendation.strategy,
                symbol=recommendation.symbol,
                buy_trigger_pct=recommendation.buy_trigger_pct,
                sell_trigger_pct=recommendation.sell_trigger_pct,
                profile=recommendation.profile,
                source_provider="openai",
                market_context_timestamp=timestamp(),
                expires_at=timestamp() + recommendation.ttl_minutes * 60,
                confidence=recommendation.confidence,
                reason=recommendation.reason,
                raw_model_response=raw_model_response,
            )
            StrategyThresholdOverrideCrud(session).create(row)

        return SuggestThresholdResponse(
            message="Successfully generated threshold recommendation.",
            data=recommendation,
        )
    except (OpenAiThresholdError, ValueError) as error:
        return SuggestThresholdResponse(
            message=f"Rejected threshold recommendation: {error}",
            error=1,
            data=None,
        )
