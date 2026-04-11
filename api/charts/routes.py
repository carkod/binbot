from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from user.models.user import UserTokenData
from user.services.auth import get_current_user
from databases.utils import get_session
from tools.handle_error import (
    json_response,
    json_response_error,
)
from charts.controllers import MarketDominationController
from charts.models import AdrSeriesResponse

charts_blueprint = APIRouter()


@charts_blueprint.get("/top-gainers", tags=["charts"])
def top_gainers(session: Session = Depends(get_session)):
    try:
        gainers, losers = MarketDominationController().gainers_losers()
        if gainers:
            return json_response(
                {
                    "data": gainers,
                    "message": "Successfully retrieved top gainers data.",
                    "error": 0,
                }
            )
        else:
            raise HTTPException(404, detail="No data found")

    except Exception as error:
        return json_response_error(f"Failed to retrieve top gainers data: {error}")


@charts_blueprint.get("/top-losers", tags=["charts"])
def top_losers(
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    try:
        gainers, losers = MarketDominationController().gainers_losers()
        if losers:
            return json_response(
                {
                    "data": losers,
                    "message": "Successfully retrieved top losers data.",
                    "error": 0,
                }
            )
        else:
            raise HTTPException(404, detail="No data found")

    except Exception as error:
        return json_response_error(f"Failed to retrieve top gainers data: {error}")


@charts_blueprint.get(
    "/adr-series",
    tags=["charts"],
    summary="Similar to market_domination, renamed and lighter data size",
    response_model=AdrSeriesResponse,
)
def get_adr_series(size: int = 14, session: Session = Depends(get_session)):
    data = MarketDominationController().get_adrs(size)
    try:
        if not data:
            raise HTTPException(404, detail="No ADR data found")

        return json_response(
            {
                "data": data,
                "message": "Successfully retrieved ADR series data.",
                "error": 0,
            }
        )

    except Exception as error:
        return json_response_error(f"Failed to retrieve ADR series data: {error}")
