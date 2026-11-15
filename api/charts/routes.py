from time import time
from typing import Literal
from api.charts.models import CvdAggregateResponse, CvdSymbolResponse
from api.databases.crud.cvd_crud import query_cvd_aggregate, query_cvd_symbol
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from api.databases.crud.top_gainers_losers_series_crud import (
    TopGainersLosersSeriesCrud,
)
from api.databases.utils import get_session
from api.tools.handle_error import (
    json_response,
    json_response_error,
)
from api.charts.controllers import MarketDominationController
from api.charts.models import (
    FastestMoversResponse,
    GainersLosersAggregateResponse,
    GainersLosersSeriesResponse,
)
from pybinbot import MarketBreadthSeriesResponse

charts_blueprint = APIRouter()


@charts_blueprint.get(
    "/gainers-losers-aggregate",
    tags=["charts"],
    summary="Registered KuCoin futures gain and loss magnitude from stored samples",
    response_model=GainersLosersAggregateResponse,
)
def get_gainers_losers_aggregate(
    limit: int = Query(default=672, ge=1, le=672),
    session: Session = Depends(get_session),
):
    try:
        data = TopGainersLosersSeriesCrud.query_aggregate_series(session, limit=limit)
        return json_response(
            {
                "data": data,
                "message": "Successfully retrieved futures gain/loss history.",
                "error": 0,
            }
        )
    except Exception as error:
        return json_response_error(f"Failed to retrieve gain/loss history: {error}")


@charts_blueprint.get(
    "/fastest_movers",
    tags=["charts"],
    summary="Fastest one-hour KuCoin futures movers from stored market snapshots",
    response_model=FastestMoversResponse,
)
def get_fastest_movers(
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
):
    try:
        data = TopGainersLosersSeriesCrud(session=session).query_fastest_movers(
            limit=limit
        )
        return json_response(
            {
                "data": data,
                "message": "Successfully retrieved fastest futures movers.",
                "error": 0,
            }
        )
    except Exception as error:
        return json_response_error(f"Failed to retrieve fastest movers: {error}")


@charts_blueprint.get(
    "/market-breadth",
    tags=["charts"],
    summary="24h market breadth history for strategy consumers",
    response_model=MarketBreadthSeriesResponse,
)
def get_market_breadth(size: int = 14, session: Session = Depends(get_session)):
    try:
        data = MarketDominationController(session=session).get_market_breadth_series(
            size
        )
        if not data:
            raise HTTPException(404, detail="No market breadth data found")

        return json_response(
            {
                "data": data,
                "message": "Successfully retrieved market breadth data.",
                "error": 0,
            }
        )

    except Exception as error:
        return json_response_error(f"Failed to retrieve market breadth data: {error}")


@charts_blueprint.get(
    "/gainers-losers-series",
    tags=["charts"],
    summary="Hourly top-10 gainers/losers snapshots (no auth, freely accessible)",
    response_model=GainersLosersSeriesResponse,
)
def get_gainers_losers_series(
    limit: int = 168, session: Session = Depends(get_session)
):
    try:
        data = TopGainersLosersSeriesCrud(session=session).query_series(limit=limit)
        if not data:
            raise HTTPException(404, detail="No gainers/losers data found")

        return json_response(
            {
                "data": data,
                "message": "Successfully retrieved gainers/losers series.",
                "error": 0,
            }
        )
    except HTTPException:
        raise
    except Exception as error:
        return json_response_error(f"Failed to retrieve gainers/losers series: {error}")


@charts_blueprint.get(
    "/cvd-aggregate", tags=["charts"], response_model=CvdAggregateResponse
)
def get_cvd_aggregate(
    interval: Literal["15m"] = "15m",
    limit: int = Query(default=672, ge=1, le=672),
    session: Session = Depends(get_session),
):
    """Stored aggressive USDT buy minus sell notionals; cumulative from reset_at.

    CVD sums observed deltas, including partial minutes; gaps are never backfilled.
    Counts are conservative minima/maxima across each interval's fixed universe.
    """
    return query_cvd_aggregate(session, limit, time())


@charts_blueprint.get("/cvd-symbol", tags=["charts"], response_model=CvdSymbolResponse)
def get_cvd_symbol(
    symbol: str = Query(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9]+$"),
    interval: Literal["1m"] = "1m",
    limit: int = Query(default=15, ge=1, le=10080),
    session: Session = Depends(get_session),
):
    """Stored per-symbol USDT CVD, rebased at reset_at; at most seven days.

    Quiet covered minutes are zero; missing/uncovered minutes are gaps. Coverage
    and freshness belong to this symbol. universe_changed marks multiplier changes.
    Inactive/delisted symbols retain their collected history until retention expires.
    """
    return query_cvd_symbol(session, symbol.upper(), limit, time())
