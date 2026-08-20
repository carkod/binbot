from fastapi import APIRouter, Depends, HTTPException
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
from api.charts.models import GainersLosersSeriesResponse
from pybinbot import MarketBreadthSeriesResponse

charts_blueprint = APIRouter()


@charts_blueprint.get(
    "/market-breadth",
    tags=["charts"],
    summary="Market breadth time-series (advancers/decliners ratio)",
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
