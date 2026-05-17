from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from databases.utils import get_session
from tools.handle_error import (
    json_response,
    json_response_error,
)
from charts.controllers import MarketDominationController
from charts.models import AdrSeriesResponse

charts_blueprint = APIRouter()


@charts_blueprint.get(
    "/adr-series",
    tags=["charts"],
    summary="Similar to market_domination, renamed and lighter data size",
    response_model=AdrSeriesResponse,
)
def get_adr_series(size: int = 14, session: Session = Depends(get_session)):
    try:
        data = MarketDominationController(session=session).get_adrs(size)
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
