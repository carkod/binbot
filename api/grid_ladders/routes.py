from dataclasses import dataclass
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlmodel import Session

from account.controller import ConsolidatedAccounts
from databases.crud.grid_ladder_crud import GridLadderCrud
from databases.tables.grid_ladder_table import GridLadderTable
from databases.tables.symbol_table import SymbolTable
from databases.utils import get_session
from pybinbot import ExchangeId, GridLadderStatus, KucoinFutures, MarketType
from pybinbot.models.grid_ladder import (
    GridLadderCloseRequest,
    GridLadderListResponse,
    GridLadderRecord,
    GridLadderResponse,
)
from grid_ladders.calculations import calculate_grid_levels
from grid_ladders.capital import evaluate_grid_capital
from grid_ladders.models import GridLadderCreate
from grid_ladders.sizing import KucoinGridMarginRules
from tools.config import Config
from user.models.user import UserTokenData
from user.services.auth import get_current_user


grid_ladder_blueprint = APIRouter(prefix="/grid-ladders", tags=["grid-ladders"])


def _grid_ladder_record(ladder: GridLadderTable) -> GridLadderRecord:
    data = ladder.model_dump()
    data["levels"] = [level.model_dump() for level in ladder.levels]
    data["orders"] = [order.model_dump() for order in ladder.orders]
    return GridLadderRecord.model_validate(jsonable_encoder(data))


@dataclass(frozen=True)
class GridContractMeta:
    multiplier: float
    lot_size: float
    qty_precision: int
    taker_fee_rate: float
    min_notional: float


def _fetch_kucoin_futures_contract_meta(symbol_row: SymbolTable) -> GridContractMeta:
    """
    Pull real contract metadata for a KuCoin futures symbol so the grid
    sizer doesn't fall back to placeholder values. Lives in its own function
    so tests can monkeypatch it without booting the KuCoin SDK.
    """
    config = Config()
    futures_api = KucoinFutures(
        key=config.kucoin_key,
        secret=config.kucoin_secret,
        passphrase=config.kucoin_passphrase,
    )
    info = futures_api.get_symbol_info(symbol_row.get_futures_symbol())
    return GridContractMeta(
        multiplier=float(getattr(info, "multiplier", 1) or 1),
        lot_size=float(getattr(info, "lot_size", 1) or 1),
        qty_precision=0,
        taker_fee_rate=float(getattr(info, "taker_fee_rate", 0) or 0),
        min_notional=0.0,
    )


def _build_margin_sizer(
    session: Session,
    symbol: str,
    exchange: ExchangeId | str,
    market_type: MarketType | str,
) -> KucoinGridMarginRules:
    symbol_row = session.get(SymbolTable, symbol)
    if symbol_row is None:
        raise HTTPException(status_code=404, detail="Symbol not found")

    exchange_value = exchange.value if isinstance(exchange, ExchangeId) else exchange
    market_type_value = (
        market_type.value if isinstance(market_type, MarketType) else market_type
    )

    if exchange_value != ExchangeId.KUCOIN.value:
        raise HTTPException(
            status_code=400,
            detail=f"Grid ladders only support KuCoin, got {exchange_value}",
        )
    if market_type_value != MarketType.FUTURES.value:
        raise HTTPException(
            status_code=400,
            detail=(
                "Grid ladders only support FUTURES market_type, "
                f"got {market_type_value}"
            ),
        )

    contract_meta = _fetch_kucoin_futures_contract_meta(symbol_row)
    min_notional = next(
        (
            row.min_notional
            for row in symbol_row.exchange_values
            if row.exchange_id == ExchangeId.KUCOIN and row.min_notional
        ),
        0.0,
    )
    return KucoinGridMarginRules(
        futures_leverage=symbol_row.futures_leverage,
        qty_precision=contract_meta.qty_precision,
        multiplier=contract_meta.multiplier,
        lot_size=contract_meta.lot_size,
        taker_fee_rate=contract_meta.taker_fee_rate,
        min_notional=min_notional or contract_meta.min_notional,
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

    balance = ConsolidatedAccounts(session=session).get_balance()
    available_fiat_balance = balance.fiat_available
    try:
        evaluate_grid_capital(
            active_ladders,
            available_fiat_balance,
            payload.total_margin,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    sizer = _build_margin_sizer(
        session,
        payload.symbol,
        payload.exchange,
        payload.market_type,
    )
    try:
        calculated = calculate_grid_levels(
            range_low=payload.range_low,
            range_high=payload.range_high,
            level_count=payload.level_count,
            total_margin=payload.total_margin,
            sizer=sizer,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    reserved_margin = sum(level.margin_required for level in calculated.levels)
    ladder = grid_ladder_crud.create(
        symbol=payload.symbol,
        fiat=payload.fiat,
        exchange=payload.exchange,
        market_type=payload.market_type,
        algorithm_name=payload.algorithm_name,
        range_low=payload.range_low,
        range_high=payload.range_high,
        grid_step=calculated.grid_step,
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
            for level in calculated.levels
        ],
    )
    created_ladder = grid_ladder_crud.get(ladder.id)
    if created_ladder is None:
        raise HTTPException(status_code=500, detail="Grid ladder was not created")

    return GridLadderResponse(
        detail=_grid_ladder_record(created_ladder),
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
        detail=[_grid_ladder_record(ladder) for ladder in ladders],
    )


@grid_ladder_blueprint.get("/active", response_model=GridLadderListResponse)
def list_active_grid_ladders(
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    grid_ladder_crud = GridLadderCrud(session)
    ladders = grid_ladder_crud.get_active()
    return GridLadderListResponse(
        detail=[_grid_ladder_record(ladder) for ladder in ladders],
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
        detail=_grid_ladder_record(ladder),
    )


@grid_ladder_blueprint.post("/{ladder_id}/close", response_model=GridLadderResponse)
def close_grid_ladder_by_id(
    ladder_id: UUID,
    payload: GridLadderCloseRequest,
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    grid_ladder_crud = GridLadderCrud(session)
    ladder = grid_ladder_crud.close(
        ladder_id,
        status=GridLadderStatus.closed,
        context_updates={"close_reason": payload.reason},
    )
    if ladder is None:
        raise HTTPException(status_code=404, detail="Grid ladder not found")

    return GridLadderResponse(
        detail=_grid_ladder_record(ladder),
    )
