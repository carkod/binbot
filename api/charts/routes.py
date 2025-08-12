from fastapi import APIRouter, HTTPException

from tools.handle_error import (
    json_response,
    json_response_error,
)
from charts.controllers import MarketDominationController
from charts.models import CandlestickResponse, AdrSeriesResponse
from tools.handle_error import StandardResponse
from databases.crud.candles_crud import CandlesCrud

charts_blueprint = APIRouter()


@charts_blueprint.get(
    "/timeseries",
    summary="Retrieve timeseries data",
    response_model=CandlestickResponse,
    tags=["charts"],
)
def get_timeseries(symbol: str, limit: int = 500):
    """
    Retrieve candlesticks data stored in DB from Binance
    in a timeseries format by Binquant
    """
    data = CandlesCrud().get_timeseries(symbol, limit)
    return {
        "data": data,
        "message": "Successfully retrieved timeseries data.",
    }


@charts_blueprint.get("/top-gainers", tags=["charts"])
def top_gainers():
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
def top_losers():
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
    "/btc-correlation", response_model=StandardResponse, tags=["charts"]
)
def get_btc_correlation(symbol: str):
    corr, btc_price = CandlesCrud().get_btc_correlation(asset_symbol=symbol)
    if corr:
        return json_response(
            {
                "data": {
                    "correlation": corr,
                    "24hr_price_change": btc_price,
                },
                "message": "Successfully retrieved BTC correlation data.",
                "error": 0,
            }
        )
    else:
        raise HTTPException(404, detail="Not enough one day candlestick data")


@charts_blueprint.get(
    "/adr-series",
    tags=["charts"],
    summary="Similar to market_domination, renamed and lighter data size",
    response_model=AdrSeriesResponse,
)
def get_adr_series(size: int = 14):
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


@charts_blueprint.get(
    "/algorithm-performance",
    tags=["charts"],
    summary="Get algorithm profit and loss",
    response_model=AdrSeriesResponse,
)
def algorithm_performance(size: int = 14):
    algorithm_performance_data = MarketDominationController().algo_performance()
    if algorithm_performance_data:
        return json_response(
            {
                "data": algorithm_performance_data,
                "message": "Successfully retrieved algorithm performance data.",
                "error": 0,
            }
        )
    else:
        raise HTTPException(404, detail="No algorithm performance data found")
