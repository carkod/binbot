from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from account.controller import ConsolidatedAccounts
from databases.crud.grid_ladder_crud import GridLadderCrud
from databases.tables.symbol_table import SymbolTable
from databases.utils import get_session
from pybinbot import GridLadderStatus
from grid_ladders.calculations import calculate_grid_levels, calculate_grid_step
from grid_ladders.capital import evaluate_grid_capital
from grid_ladders.models import (
    GridLadderCloseRequest,
    GridLadderCreate,
    GridLadderListResponse,
    GridLadderRecord,
    GridLadderResponse,
)
from grid_ladders.sizing import KucoinGridMarginRules
from user.models.user import UserTokenData
from user.services.auth import get_current_user


grid_ladder_blueprint = APIRouter(prefix="/grid-ladders", tags=["grid-ladders"])


def _get_available_fiat_balance() -> float:
    balance = ConsolidatedAccounts().get_balance()
    return balance.fiat_available


def _build_margin_sizer(session: Session, symbol: str) -> KucoinGridMarginRules:
    symbol_row = session.get(SymbolTable, symbol)
    if symbol_row is None:
        raise HTTPException(status_code=404, detail="Symbol not found")

    return KucoinGridMarginRules(
        futures_leverage=symbol_row.futures_leverage,
        qty_precision=0,
        multiplier=1,
        lot_size=1,
        taker_fee_rate=0,
    )


@grid_ladder_blueprint.post("", response_model=GridLadderResponse)
def post_grid_ladder(
    payload: GridLadderCreate,
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    grid_ladder_crud = GridLadderCrud(session)
    if grid_ladder_crud.get_active_for_symbol(payload.symbol) is not None:
        raise HTTPException(
            status_code=400,
            detail="An active grid ladder already exists for this symbol",
        )

    active_ladders = grid_ladder_crud.get_active()
    available_fiat_balance = _get_available_fiat_balance()
    try:
        evaluate_grid_capital(
            active_ladders,
            available_fiat_balance,
            payload.total_margin,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    sizer = _build_margin_sizer(session, payload.symbol)
    try:
        calculated_levels = calculate_grid_levels(
            range_low=payload.range_low,
            range_high=payload.range_high,
            level_count=payload.level_count,
            total_margin=payload.total_margin,
            sizer=sizer,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    grid_step = calculate_grid_step(
        payload.range_low,
        payload.range_high,
        payload.level_count,
    )
    reserved_margin = sum(level.margin_required for level in calculated_levels)
    ladder = grid_ladder_crud.create(
        symbol=payload.symbol,
        fiat=payload.fiat,
        exchange=payload.exchange,
        market_type=payload.market_type,
        algorithm_name=payload.algorithm_name,
        range_low=payload.range_low,
        range_high=payload.range_high,
        grid_step=grid_step,
        level_count=payload.level_count,
        total_margin=payload.total_margin,
        reserved_margin=reserved_margin,
        breakout_low=payload.breakout_low,
        breakout_high=payload.breakout_high,
        context=payload.context,
    )
    grid_ladder_crud.create_levels(
        ladder.id,
        [
            {
                "level_index": level.level_index,
                "price": level.price,
                "side": level.side,
                "contracts": level.contracts,
                "margin_required": level.margin_required,
                "take_profit_price": level.take_profit_price,
            }
            for level in calculated_levels
        ],
    )
    created_ladder = grid_ladder_crud.get(ladder.id)
    if created_ladder is None:
        raise HTTPException(status_code=500, detail="Grid ladder was not created")

    return GridLadderResponse(
        detail=GridLadderRecord.model_validate(created_ladder),
    )


@grid_ladder_blueprint.get("", response_model=GridLadderListResponse)
def list_grid_ladders(
    limit: int = 100,
    offset: int = 0,
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    grid_ladder_crud = GridLadderCrud(session)
    ladders = grid_ladder_crud.get_all(limit=limit, offset=offset)
    return GridLadderListResponse(
        detail=[GridLadderRecord.model_validate(ladder) for ladder in ladders],
    )


@grid_ladder_blueprint.get("/active", response_model=GridLadderListResponse)
def list_active_grid_ladders(
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    grid_ladder_crud = GridLadderCrud(session)
    ladders = grid_ladder_crud.get_active()
    return GridLadderListResponse(
        detail=[GridLadderRecord.model_validate(ladder) for ladder in ladders],
    )


@grid_ladder_blueprint.get("/{ladder_id}", response_model=GridLadderResponse)
def get_grid_ladder_by_id(
    ladder_id: UUID,
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    grid_ladder_crud = GridLadderCrud(session)
    ladder = grid_ladder_crud.get(ladder_id)
    if ladder is None:
        raise HTTPException(status_code=404, detail="Grid ladder not found")

    return GridLadderResponse(
        detail=GridLadderRecord.model_validate(ladder),
    )


@grid_ladder_blueprint.post("/{ladder_id}/close", response_model=GridLadderResponse)
def close_grid_ladder_by_id(
    ladder_id: UUID,
    payload: GridLadderCloseRequest,
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    grid_ladder_crud = GridLadderCrud(session)
    ladder = grid_ladder_crud.close(ladder_id, status=GridLadderStatus.closed)
    if ladder is None:
        raise HTTPException(status_code=404, detail="Grid ladder not found")

    return GridLadderResponse(
        detail=GridLadderRecord.model_validate(ladder),
    )
