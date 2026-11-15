from time import time
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
    "/cvd-aggregate",
    tags=["charts"],
    summary="Market-wide KuCoin Futures CVD from stored executions",
    description="""
    Read Postgres-only **15-minute UTC buckets**, oldest first, ending with the
    current interval. The population is active, registered linear USDT contracts;
    buy/sell values are aggressive taker notionals (`price × contracts × multiplier`).

    CVD accumulates observed buy minus sell from zero at `reset_at`, the selected
    window's start, and rebases as the window advances. Partial observations
    contribute; missing trades are never estimated or backfilled. History begins
    at collector startup and is retained for seven days. No observations in the
    requested range returns an empty `data` list; otherwise missing intervals
    have null buy/sell/CVD and unknown expected-symbol counts.

    `expected_symbols` is the maximum and `covered_symbols` the minimum across
    observed minutes. `complete` requires all 15 minutes finalized, full coverage
    and an unchanged nonempty universe; `gap` means incomplete. `current` marks
    the open interval. Finalization waits two minutes for late arrivals.
    `universe_changed` identifies membership or multiplier changes, including
    changes within an interval. Clients should break chart lines at gaps and
    population changes. A covered quiet market contributes zero, not a gap.

    `source` identifies the feed, `updated_at` the latest saved checkpoint,
    `stale` means no checkpoint or one older than 90 seconds, and `partial`
    indicates any incomplete interval or universe change in the selected window.
    """,
    response_model=CvdAggregateResponse,
    response_description="USDT notionals and rebased CVD with coverage and freshness",
)
def get_cvd_aggregate(
    limit: int = Query(
        default=672, ge=1, le=672, description="Number of 15-minute UTC buckets."
    ),
    session: Session = Depends(get_session),
):
    return query_cvd_aggregate(session, limit, time())


@charts_blueprint.get(
    "/cvd-symbol",
    tags=["charts"],
    summary="Individual KuCoin Futures contract CVD from stored executions",
    description="""
    Read one contract's stored **one-minute UTC buckets**, oldest first, ending
    with the current minute. Uses the same collector as market-wide CVD, with
    no exchange calls. Historical inactive/delisted contracts remain readable
    until seven-day retention expires.

    Buy/sell values are aggressive taker USDT notionals
    (`price × contracts × multiplier`). CVD accumulates observed buy minus sell
    from zero at `reset_at`, rebasing as the selected window advances. Partial
    observations contribute; missing trades are never estimated or backfilled.
    An empty selected range returns an empty `data` list. Within a populated
    range, missing minutes have null buy/sell/CVD, unknown expected-symbol count
    and zero coverage. Covered quiet minutes have zero buy/sell.

    Expected/covered symbol counts are 1 for a recorded/covered contract.
    `complete` requires coverage and finalization; `gap` means incomplete.
    The current minute and closed minutes awaiting the two-minute late-arrival
    allowance remain partial. `universe_changed` means this contract's multiplier
    changed. Clients should break chart lines at gaps and multiplier changes.

    Coverage and `updated_at` belong to this symbol; unrelated markets cannot
    mask an outage. `stale` means no checkpoint or one older than 90 seconds.
    `partial` indicates any incomplete minute or multiplier change in the window.
    """,
    response_model=CvdSymbolResponse,
    response_description="Contract USDT notionals and rebased CVD with symbol coverage",
)
def get_cvd_symbol(
    symbol: str = Query(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9]+$",
        description="Case-insensitive KuCoin Futures contract ID, e.g. SOLUSDTM.",
    ),
    limit: int = Query(
        default=15, ge=1, le=10080, description="Number of one-minute UTC buckets."
    ),
    session: Session = Depends(get_session),
):
    return query_cvd_symbol(session, symbol.upper(), limit, time())
